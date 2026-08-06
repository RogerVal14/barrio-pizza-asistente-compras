"""Conversión de unidades, recomendación de compra y clasificación de líneas."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from src.validation import ValidationResult, issue_keys


INCOMPLETE_CODES = {
    "INVENTARIO_FALTANTE",
    "HISTORICO_FALTANTE",
    "VALOR_NO_NUMERICO",
    "CANTIDAD_NEGATIVA",
    "FORMATO_NO_POSITIVO",
    "FORMATO_NO_ENTERO",
    "CLAVE_DUPLICADA",
    "SEMANA_DUPLICADA",
    "VALOR_NULO",
}


def formats_to_base(quantity_formats: float, base_per_format: float) -> float:
    """Convierte formatos completos a la unidad base sin redondear."""

    return float(quantity_formats) * float(base_per_format)


def base_to_formats(need_base: float, base_per_format: float) -> int:
    """Convierte necesidad base a formatos completos mediante techo matemático."""

    if pd.isna(need_base) or pd.isna(base_per_format):
        raise ValueError("La necesidad y el factor de formato deben ser numéricos.")
    if float(base_per_format) <= 0:
        raise ValueError("El factor de conversión debe ser mayor que cero.")
    return int(math.ceil(max(float(need_base), 0.0) / float(base_per_format)))


def calculate_need(projected: float, inventory: float) -> float:
    """Aplica necesidad_base = max(proyección - inventario, 0)."""

    if pd.isna(projected) or pd.isna(inventory):
        return np.nan
    return max(float(projected) - float(inventory), 0.0)


def classify_line(
    ordered_formats: float,
    recommended_formats: int,
    *,
    omitted: bool = False,
    calculable: bool = True,
) -> str:
    """Clasifica comparando formatos enteros; el redondeo interno no penaliza."""

    if not calculable or pd.isna(ordered_formats) or pd.isna(recommended_formats):
        return "DATO INCOMPLETO"
    ordered = int(ordered_formats)
    recommended = int(recommended_formats)
    if omitted and recommended > 0:
        return "OMITIDO"
    if ordered < recommended:
        return "FALTANTE"
    if ordered > recommended:
        return "SOBREPEDIDO"
    if recommended == 0 and ordered == 0:
        return "SIN NECESIDAD"
    return "CORRECTO"


def _collapse_source(
    frame: pd.DataFrame,
    value_column: str,
    output_column: str,
) -> pd.DataFrame:
    """Conserva claves únicas y vuelve nulo el valor si la fuente está duplicada."""

    required = ["sucursal", "ingrediente_id", value_column]
    available = frame[required].dropna(subset=["sucursal", "ingrediente_id"]).copy()
    if available.empty:
        return pd.DataFrame(
            columns=["sucursal", "ingrediente_id", output_column, f"{output_column}_duplicado"]
        )

    rows: list[dict[str, object]] = []
    for (branch, ingredient), group in available.groupby(
        ["sucursal", "ingrediente_id"], dropna=False
    ):
        duplicated = len(group) > 1
        value = group[value_column].iloc[0] if not duplicated else np.nan
        rows.append(
            {
                "sucursal": branch,
                "ingrediente_id": ingredient,
                output_column: value,
                f"{output_column}_duplicado": duplicated,
            }
        )
    return pd.DataFrame(rows)


def build_purchase_review(
    validated: ValidationResult,
    forecasts: pd.DataFrame,
    safety_margin: float = 0.0,
) -> pd.DataFrame:
    """Construye la revisión completa del catálogo para cada sucursal histórica."""

    margin = float(safety_margin)
    if not 0.0 <= margin <= 0.20:
        raise ValueError("El margen de seguridad debe estar entre 0% y 20%.")

    catalog_columns = [
        "ingrediente_id",
        "nombre",
        "proveedor",
        "unidad_base",
        "formato_compra",
        "unidad_base_por_formato",
        "es_perecedero",
    ]
    catalog = validated.catalogo[catalog_columns].copy()
    catalog_unique = catalog.drop_duplicates("ingrediente_id", keep=False)
    review = validated.combinaciones.merge(
        catalog_unique,
        on="ingrediente_id",
        how="left",
        validate="many_to_one",
    )
    review = review.merge(
        forecasts,
        on=["sucursal", "ingrediente_id"],
        how="left",
        validate="one_to_one",
    )

    inventory = _collapse_source(
        validated.inventario, "stock_actual_unidad_base", "inventario_actual"
    )
    order = _collapse_source(validated.orden, "cantidad_formatos", "formatos_ordenados")
    order["aparece_en_orden"] = True

    review = review.merge(
        inventory,
        on=["sucursal", "ingrediente_id"],
        how="left",
        validate="one_to_one",
    )
    review = review.merge(
        order,
        on=["sucursal", "ingrediente_id"],
        how="left",
        validate="one_to_one",
    )
    review["aparece_en_orden"] = review["aparece_en_orden"].eq(True)
    review["producto_omitido_orden"] = ~review["aparece_en_orden"]
    review.loc[review["producto_omitido_orden"], "formatos_ordenados"] = 0.0
    review["margen_seguridad"] = margin
    review["consumo_proyectado_ajustado"] = review["consumo_proyectado"] * (1.0 + margin)

    bad_keys = issue_keys(validated.incidencias, INCOMPLETE_CODES)
    statuses: list[str] = []
    reasons: list[str] = []
    needs: list[float] = []
    recommendations: list[float] = []

    issue_lookup: dict[tuple[str, str], list[str]] = {}
    if not validated.incidencias.empty:
        relevant = validated.incidencias[
            validated.incidencias["codigo"].isin(INCOMPLETE_CODES)
        ].dropna(subset=["sucursal", "ingrediente_id"])
        for key, group in relevant.groupby(["sucursal", "ingrediente_id"]):
            issue_lookup[(str(key[0]), str(key[1]))] = group["detalle"].astype(str).tolist()

    for row in review.itertuples(index=False):
        key = (str(row.sucursal), str(row.ingrediente_id))
        factor = row.unidad_base_por_formato
        inventory_value = row.inventario_actual
        projection = row.consumo_proyectado_ajustado
        ordered = row.formatos_ordenados
        key_problem = key in bad_keys
        calculable = (
            not key_problem
            and pd.notna(factor)
            and float(factor) > 0
            and pd.notna(inventory_value)
            and float(inventory_value) >= 0
            and pd.notna(projection)
            and float(projection) >= 0
            and pd.notna(ordered)
            and float(ordered) >= 0
            and np.isclose(float(ordered) % 1, 0)
        )
        if calculable:
            need = calculate_need(float(projection), float(inventory_value))
            recommended = base_to_formats(need, float(factor))
            status = classify_line(
                float(ordered),
                recommended,
                omitted=bool(row.producto_omitido_orden),
                calculable=True,
            )
            reason = ""
        else:
            need = np.nan
            recommended = np.nan
            status = "DATO INCOMPLETO"
            specific = issue_lookup.get(key, [])
            reason = " ".join(dict.fromkeys(specific)) or "Faltan datos confiables para calcular."
        needs.append(need)
        recommendations.append(recommended)
        statuses.append(status)
        reasons.append(reason)

    review["necesidad_base"] = needs
    review["formatos_recomendados"] = pd.Series(recommendations, dtype="Float64")
    review["estado"] = statuses
    review["razon_dato_incompleto"] = reasons
    review["cantidad_ordenada_base"] = (
        review["formatos_ordenados"] * review["unidad_base_por_formato"]
    )
    review["cantidad_recomendada_base"] = (
        review["formatos_recomendados"] * review["unidad_base_por_formato"]
    )
    review["diferencia_formatos"] = (
        review["formatos_ordenados"] - review["formatos_recomendados"]
    )
    review["diferencia_base"] = (
        review["cantidad_ordenada_base"] - review["cantidad_recomendada_base"]
    )
    review["es_perecedero_bool"] = (
        review["es_perecedero"].astype(str).str.strip().str.lower().isin({"si", "sí", "true", "1"})
    )
    return review.sort_values(["sucursal", "proveedor", "nombre"], na_position="last").reset_index(
        drop=True
    )


def unknown_order_lines(validated: ValidationResult) -> pd.DataFrame:
    """Devuelve líneas pedidas fuera de catálogo sin enriquecerlas con datos inventados."""

    catalog_ids = set(validated.catalogo["ingrediente_id"].dropna().astype(str))
    unknown = validated.orden[
        validated.orden["ingrediente_id"].notna()
        & ~validated.orden["ingrediente_id"].astype(str).isin(catalog_ids)
    ].copy()
    keep = [column for column in ["sucursal", "ingrediente_id", "cantidad_formatos"] if column in unknown]
    return unknown[keep].reset_index(drop=True)


def corrected_order(review: pd.DataFrame) -> pd.DataFrame:
    """Genera la orden corregida conocida; mantiene nulos cuando no es calculable."""

    corrected = review[
        [
            "proveedor",
            "sucursal",
            "ingrediente_id",
            "nombre",
            "formato_compra",
            "unidad_base",
            "formatos_ordenados",
            "formatos_recomendados",
            "diferencia_formatos",
            "cantidad_ordenada_base",
            "cantidad_recomendada_base",
            "estado",
        ]
    ].copy()
    corrected = corrected.rename(
        columns={
            "formatos_ordenados": "cantidad_formatos_original",
            "formatos_recomendados": "cantidad_formatos_corregida",
            "diferencia_formatos": "diferencia_formatos_corregir",
        }
    )
    return corrected.sort_values(["proveedor", "sucursal", "nombre"], na_position="last")
