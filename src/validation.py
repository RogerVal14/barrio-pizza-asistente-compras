"""Validaciones explícitas de esquema, calidad e integridad referencial."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

import numpy as np
import pandas as pd


REQUIRED_COLUMNS: dict[str, list[str]] = {
    "catalogo": [
        "ingrediente_id",
        "nombre",
        "proveedor",
        "unidad_base",
        "formato_compra",
        "unidad_base_por_formato",
        "es_perecedero",
    ],
    "historico": ["sucursal", "ingrediente_id", "semana", "consumo_unidad_base"],
    "inventario": ["sucursal", "ingrediente_id", "stock_actual_unidad_base"],
    "orden": ["sucursal", "ingrediente_id", "cantidad_formatos"],
}

KEY_COLUMNS: dict[str, list[str]] = {
    "catalogo": ["ingrediente_id"],
    "historico": ["sucursal", "ingrediente_id", "semana"],
    "inventario": ["sucursal", "ingrediente_id"],
    "orden": ["sucursal", "ingrediente_id"],
}

NUMERIC_COLUMNS: dict[str, list[str]] = {
    "catalogo": ["unidad_base_por_formato"],
    "historico": ["consumo_unidad_base"],
    "inventario": ["stock_actual_unidad_base"],
    "orden": ["cantidad_formatos"],
}

ISSUE_COLUMNS = [
    "nivel",
    "categoria",
    "codigo",
    "archivo",
    "sucursal",
    "ingrediente_id",
    "fila",
    "detalle",
    "por_que_importa",
]


@dataclass(frozen=True)
class ValidationResult:
    """Datos normalizados, cuadrícula esperada e incidencias encontradas."""

    catalogo: pd.DataFrame
    historico: pd.DataFrame
    inventario: pd.DataFrame
    orden: pd.DataFrame
    sucursales: list[str]
    combinaciones: pd.DataFrame
    incidencias: pd.DataFrame

    @property
    def has_blocking_schema_errors(self) -> bool:
        if self.incidencias.empty:
            return False
        return bool(
            (
                (self.incidencias["nivel"] == "Error")
                & (self.incidencias["codigo"] == "COLUMNA_AUSENTE")
            ).any()
        )


def _empty_issues() -> pd.DataFrame:
    return pd.DataFrame(columns=ISSUE_COLUMNS)


def _issue(
    issues: list[dict[str, object]],
    *,
    level: str,
    code: str,
    file_name: str,
    detail: str,
    impact: str,
    branch: object = None,
    ingredient: object = None,
    row: object = None,
) -> None:
    issues.append(
        {
            "nivel": level,
            "categoria": "Calidad de datos",
            "codigo": code,
            "archivo": file_name,
            "sucursal": branch,
            "ingrediente_id": ingredient,
            "fila": row,
            "detalle": detail,
            "por_que_importa": impact,
        }
    )


def _normalize(frame: pd.DataFrame) -> pd.DataFrame:
    # El índice de un CSV no es una clave de negocio. Se normaliza para que
    # concatenaciones externas con índices repetidos no vuelvan ambiguo el reporte de fila.
    result = frame.copy().reset_index(drop=True)
    result.columns = [str(column).strip() for column in result.columns]
    for column in result.select_dtypes(include="object").columns:
        result[column] = result[column].map(
            lambda value: value.strip() if isinstance(value, str) else value
        )
        result[column] = result[column].replace("", np.nan)
    return result


def _row_context(row: pd.Series) -> tuple[object, object]:
    return row.get("sucursal"), row.get("ingrediente_id")


def _validate_schema_and_values(
    name: str, frame: pd.DataFrame, issues: list[dict[str, object]]
) -> pd.DataFrame:
    result = _normalize(frame)
    missing_columns = [col for col in REQUIRED_COLUMNS[name] if col not in result.columns]
    for column in missing_columns:
        _issue(
            issues,
            level="Error",
            code="COLUMNA_AUSENTE",
            file_name=name,
            detail=f"Falta la columna obligatoria '{column}'.",
            impact="El archivo no puede procesarse con seguridad hasta recuperar la columna.",
        )

    for column in REQUIRED_COLUMNS[name]:
        if column not in result.columns:
            result[column] = np.nan

    for index, row in result.iterrows():
        for column in REQUIRED_COLUMNS[name]:
            if pd.isna(row[column]):
                branch, ingredient = _row_context(row)
                _issue(
                    issues,
                    level="Error",
                    code="VALOR_NULO",
                    file_name=name,
                    branch=branch,
                    ingredient=ingredient,
                    row=int(index) + 2,
                    detail=f"La columna '{column}' tiene un valor nulo.",
                    impact="Los nulos no se convierten a cero porque podrían cambiar la recomendación.",
                )

    for column in NUMERIC_COLUMNS[name]:
        raw = result[column].copy()
        numeric = pd.to_numeric(raw, errors="coerce")
        invalid_mask = raw.notna() & numeric.isna()
        for index in result.index[invalid_mask]:
            branch, ingredient = _row_context(result.loc[index])
            _issue(
                issues,
                level="Error",
                code="VALOR_NO_NUMERICO",
                file_name=name,
                branch=branch,
                ingredient=ingredient,
                row=int(index) + 2,
                detail=f"'{raw.loc[index]}' no es numérico en '{column}'.",
                impact="La cantidad no puede intervenir en una proyección o compra confiable.",
            )
        result[column] = numeric

        for index in result.index[numeric < 0]:
            branch, ingredient = _row_context(result.loc[index])
            _issue(
                issues,
                level="Error",
                code="CANTIDAD_NEGATIVA",
                file_name=name,
                branch=branch,
                ingredient=ingredient,
                row=int(index) + 2,
                detail=f"'{column}' contiene la cantidad negativa {numeric.loc[index]}.",
                impact="Una cantidad negativa invalida la recomendación de esa combinación.",
            )

    if name == "catalogo":
        invalid_factor = result["unidad_base_por_formato"].notna() & (
            result["unidad_base_por_formato"] <= 0
        )
        for index in result.index[invalid_factor]:
            _issue(
                issues,
                level="Error",
                code="FORMATO_NO_POSITIVO",
                file_name=name,
                ingredient=result.at[index, "ingrediente_id"],
                row=int(index) + 2,
                detail="El factor de conversión del formato es cero o negativo.",
                impact="No es posible convertir entre formatos y unidad base.",
            )

    if name == "orden":
        values = result["cantidad_formatos"]
        fractional = values.notna() & ~np.isclose(values % 1, 0)
        for index in result.index[fractional]:
            _issue(
                issues,
                level="Error",
                code="FORMATO_NO_ENTERO",
                file_name=name,
                branch=result.at[index, "sucursal"],
                ingredient=result.at[index, "ingrediente_id"],
                row=int(index) + 2,
                detail=f"La orden contiene {values.loc[index]} formatos; deben ser enteros.",
                impact="Los proveedores despachan formatos completos, no fracciones.",
            )

    key = KEY_COLUMNS[name]
    duplicate_mask = result.duplicated(key, keep=False) & result[key].notna().all(axis=1)
    for index in result.index[duplicate_mask]:
        branch, ingredient = _row_context(result.loc[index])
        _issue(
            issues,
            level="Error",
            code="CLAVE_DUPLICADA" if name != "historico" else "SEMANA_DUPLICADA",
            file_name=name,
            branch=branch,
            ingredient=ingredient,
            row=int(index) + 2,
            detail=f"La clave {tuple(result.loc[index, key])} aparece más de una vez.",
            impact="No se agregan duplicados silenciosamente; la combinación queda pendiente de revisión.",
        )

    return result


def _safe_ids(frame: pd.DataFrame, column: str) -> set[str]:
    if column not in frame:
        return set()
    return set(frame[column].dropna().astype(str))


def _add_integrity_issues(
    catalog: pd.DataFrame,
    historical: pd.DataFrame,
    inventory: pd.DataFrame,
    order: pd.DataFrame,
    branches: list[str],
    combinations: pd.DataFrame,
    issues: list[dict[str, object]],
) -> None:
    catalog_ids = _safe_ids(catalog, "ingrediente_id")
    branch_ids = set(branches)

    for source_name, frame in (
        ("historico", historical),
        ("inventario", inventory),
        ("orden", order),
    ):
        if "ingrediente_id" in frame:
            unknown_mask = frame["ingrediente_id"].notna() & ~frame["ingrediente_id"].isin(
                catalog_ids
            )
            for index in frame.index[unknown_mask]:
                _issue(
                    issues,
                    level="Error",
                    code="INGREDIENTE_DESCONOCIDO",
                    file_name=source_name,
                    branch=frame.at[index, "sucursal"] if "sucursal" in frame else None,
                    ingredient=frame.at[index, "ingrediente_id"],
                    row=int(index) + 2,
                    detail=(
                        f"El ingrediente '{frame.at[index, 'ingrediente_id']}' no existe en el catálogo."
                    ),
                    impact="No se inventan proveedor, unidad ni factor de conversión.",
                )

        if source_name in {"inventario", "orden"} and "sucursal" in frame:
            unknown_branch = frame["sucursal"].notna() & ~frame["sucursal"].isin(branch_ids)
            for index in frame.index[unknown_branch]:
                _issue(
                    issues,
                    level="Error",
                    code="SUCURSAL_DESCONOCIDA",
                    file_name=source_name,
                    branch=frame.at[index, "sucursal"],
                    ingredient=frame.at[index, "ingrediente_id"],
                    row=int(index) + 2,
                    detail=f"La sucursal '{frame.at[index, 'sucursal']}' no aparece en el histórico.",
                    impact="La cuadrícula operativa se deriva de las sucursales con consumo histórico.",
                )

    valid_inventory_keys = inventory[
        inventory["sucursal"].isin(branch_ids) & inventory["ingrediente_id"].isin(catalog_ids)
    ][["sucursal", "ingrediente_id"]].drop_duplicates()
    inventory_coverage = combinations.merge(
        valid_inventory_keys,
        on=["sucursal", "ingrediente_id"],
        how="left",
        indicator=True,
        validate="one_to_one",
    )
    for row in inventory_coverage.loc[inventory_coverage["_merge"] == "left_only"].itertuples():
        _issue(
            issues,
            level="Error",
            code="INVENTARIO_FALTANTE",
            file_name="inventario",
            branch=row.sucursal,
            ingredient=row.ingrediente_id,
            detail="No existe inventario para esta combinación.",
            impact="No se asume inventario cero; la recomendación queda como dato incompleto.",
        )

    known_order = order[
        order["sucursal"].isin(branch_ids) & order["ingrediente_id"].isin(catalog_ids)
    ][["sucursal", "ingrediente_id"]].drop_duplicates()
    order_coverage = combinations.merge(
        known_order,
        on=["sucursal", "ingrediente_id"],
        how="left",
        indicator=True,
        validate="one_to_one",
    )
    for row in order_coverage.loc[order_coverage["_merge"] == "left_only"].itertuples():
        _issue(
            issues,
            level="Advertencia",
            code="PRODUCTO_OMITIDO_ORDEN",
            file_name="orden",
            branch=row.sucursal,
            ingredient=row.ingrediente_id,
            detail="El ingrediente del catálogo no aparece en la orden de la sucursal.",
            impact="Se evalúa como 0 formatos solicitados y se conserva la etiqueta de omisión.",
        )

    historical_counts = (
        historical[
            historical["sucursal"].isin(branch_ids)
            & historical["ingrediente_id"].isin(catalog_ids)
        ]
        .assign(
            semana_valida=lambda frame: frame["semana"].map(
                lambda value: bool(re.fullmatch(r"S\d+", str(value))) if pd.notna(value) else False
            ),
            valor_valido=lambda frame: frame["consumo_unidad_base"].notna()
            & (frame["consumo_unidad_base"] >= 0),
        )
        .loc[lambda frame: frame["semana_valida"] & frame["valor_valido"]]
        .groupby(["sucursal", "ingrediente_id"], as_index=False)["semana"]
        .nunique()
        .rename(columns={"semana": "semanas_validas"})
    )
    history_coverage = combinations.merge(
        historical_counts,
        on=["sucursal", "ingrediente_id"],
        how="left",
        validate="one_to_one",
    )
    history_coverage["semanas_validas"] = history_coverage["semanas_validas"].fillna(0)
    expected_weeks = max(6, int(history_coverage["semanas_validas"].max()))
    for row in history_coverage.itertuples():
        count = int(row.semanas_validas)
        if count == 0:
            _issue(
                issues,
                level="Error",
                code="HISTORICO_FALTANTE",
                file_name="historico",
                branch=row.sucursal,
                ingredient=row.ingrediente_id,
                detail="No hay semanas históricas válidas para esta combinación.",
                impact="Sin histórico no se fabrica una proyección.",
            )
        elif count < expected_weeks:
            _issue(
                issues,
                level="Advertencia",
                code="HISTORICO_INCOMPLETO",
                file_name="historico",
                branch=row.sucursal,
                ingredient=row.ingrediente_id,
                detail=f"Solo hay {count} de {expected_weeks} semanas históricas esperadas.",
                impact="La proyección puede calcularse, pero su confianza se reduce.",
            )


def validate_data(
    catalogo: pd.DataFrame,
    historico: pd.DataFrame,
    inventario: pd.DataFrame,
    orden: pd.DataFrame,
) -> ValidationResult:
    """Valida las cuatro fuentes y construye la matriz completa de revisión."""

    issues: list[dict[str, object]] = []
    catalog = _validate_schema_and_values("catalogo", catalogo, issues)
    historical = _validate_schema_and_values("historico", historico, issues)
    inventory = _validate_schema_and_values("inventario", inventario, issues)
    purchase_order = _validate_schema_and_values("orden", orden, issues)

    branches = sorted(_safe_ids(historical, "sucursal"))
    catalog_ids = sorted(_safe_ids(catalog, "ingrediente_id"))
    combinations = pd.MultiIndex.from_product(
        [branches, catalog_ids], names=["sucursal", "ingrediente_id"]
    ).to_frame(index=False)

    _add_integrity_issues(
        catalog,
        historical,
        inventory,
        purchase_order,
        branches,
        combinations,
        issues,
    )

    issue_frame = pd.DataFrame(issues, columns=ISSUE_COLUMNS) if issues else _empty_issues()
    if not issue_frame.empty:
        level_order = pd.CategoricalDtype(["Error", "Advertencia", "Información"], ordered=True)
        issue_frame["nivel"] = issue_frame["nivel"].astype(level_order)
        issue_frame = issue_frame.sort_values(
            ["nivel", "codigo", "sucursal", "ingrediente_id"], na_position="last"
        ).reset_index(drop=True)
        issue_frame["nivel"] = issue_frame["nivel"].astype("object")

    return ValidationResult(
        catalogo=catalog,
        historico=historical,
        inventario=inventory,
        orden=purchase_order,
        sucursales=branches,
        combinaciones=combinations,
        incidencias=issue_frame,
    )


def issue_keys(issues: pd.DataFrame, codes: Iterable[str]) -> set[tuple[str, str]]:
    """Extrae claves afectadas por una lista de códigos de calidad."""

    if issues.empty:
        return set()
    selected = issues[issues["codigo"].isin(list(codes))].dropna(
        subset=["sucursal", "ingrediente_id"]
    )
    return set(zip(selected["sucursal"].astype(str), selected["ingrediente_id"].astype(str)))
