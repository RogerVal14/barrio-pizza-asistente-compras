"""Benchmarking explicable de órdenes entre sucursales.

El resultado se presenta como comportamiento inusual, no como anomalía
confirmada. Con pocas sucursales la comparación sirve como contexto para la
revisión humana y nunca reemplaza el diagnóstico principal de compra.
"""

from __future__ import annotations

from collections.abc import Collection
from math import isfinite
from numbers import Real

import numpy as np
import pandas as pd

from src.alerts import purchase_format_phrase


LINE_KEY_COLUMNS = ["sucursal", "ingrediente_id"]
VALID_CALCULABLE_STATES = {
    "OMITIDO",
    "FALTANTE",
    "CORRECTO",
    "SOBREPEDIDO",
    "SIN NECESIDAD",
}
REQUIRED_COLUMNS = {
    "sucursal",
    "ingrediente_id",
    "nombre",
    "proveedor",
    "unidad_base",
    "formato_compra",
    "unidad_base_por_formato",
    "consumo_proyectado",
    "inventario_actual",
    "formatos_ordenados",
    "formatos_recomendados",
    "diferencia_formatos",
    "cantidad_ordenada_base",
    "cantidad_recomendada_base",
    "estado",
    "es_perecedero_bool",
}
OUTPUT_COLUMNS = [
    "severidad",
    "diagnostico_principal",
    "direccion",
    "sucursal",
    "ingrediente_id",
    "ingrediente",
    "proveedor",
    "es_perecedero",
    "formato_compra",
    "unidad_base",
    "formatos_ordenados",
    "formatos_recomendados",
    "diferencia_formatos",
    "cantidad_ordenada_base",
    "cantidad_recomendada_base",
    "factor_vs_recomendacion",
    "ratio_sucursal",
    "mediana_factor_pares",
    "ratio_mediana_pares",
    "mediana_formatos_ordenados_pares",
    "mediana_formatos_recomendados_pares",
    "mad_factor_pares",
    "modified_z_score",
    "cantidad_pares",
    "metodo_deteccion",
    "nivel_confianza",
    "magnitud_relativa",
    "estado_compra",
    "razon",
    "accion_recomendada",
    "mensaje",
]
SEVERITY_ORDER = {"Crítica": 0, "Alta": 1, "Media": 2, "Baja": 3}


def _empty_result() -> pd.DataFrame:
    return pd.DataFrame(columns=OUTPUT_COLUMNS)


def _finite_mask(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    return numeric.notna() & pd.Series(
        np.isfinite(numeric.to_numpy(dtype=float)),
        index=series.index,
    )


def _integer_mask(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    finite = _finite_mask(numeric)
    result = pd.Series(False, index=series.index)
    result.loc[finite] = np.isclose(
        numeric.loc[finite].to_numpy(dtype=float),
        np.rint(numeric.loc[finite].to_numpy(dtype=float)),
    )
    return result


def _text_mask(series: pd.Series) -> pd.Series:
    return series.notna() & series.astype(str).str.strip().ne("")


def _finite_number(value: object) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool) and isfinite(float(value))


def _display_number(value: object, decimals: int = 2) -> str:
    if not _finite_number(value):
        return str(value)
    numeric = float(value)
    if numeric.is_integer():
        return str(int(numeric))
    return f"{numeric:.{decimals}f}".rstrip("0").rstrip(".").replace(".", ",")


def _ratio_label(value: float | None, unavailable_reason: str = "No aplica") -> str:
    if value is None or not isfinite(float(value)):
        return unavailable_reason
    return f"{_display_number(value)}×"


def _confidence(peer_count: int) -> str:
    return "Baja" if peer_count == 2 else "Moderada"


def _primary_diagnosis(state: str) -> str:
    return {
        "OMITIDO": "Producto omitido",
        "FALTANTE": "Faltante",
        "SOBREPEDIDO": "Sobrepedido",
        "SIN NECESIDAD": "Sin necesidad",
        "CORRECTO": "Correcto",
    }.get(state, "Revisión de compra")


def _severity(direction: str, state: str, perishable: bool) -> str:
    if direction == "MUY POR DEBAJO":
        return "Crítica" if state == "OMITIDO" else "Alta"
    return "Media" if perishable else "Baja"


def _assert_unique_lines(frame: pd.DataFrame, label: str) -> None:
    missing = set(LINE_KEY_COLUMNS).difference(frame.columns)
    if missing:
        raise ValueError(f"{label} no contiene las claves requeridas: {sorted(missing)}")
    duplicated = frame.duplicated(LINE_KEY_COLUMNS, keep=False)
    if duplicated.any():
        examples = (
            frame.loc[duplicated, LINE_KEY_COLUMNS]
            .drop_duplicates()
            .head(5)
            .to_dict("records")
        )
        raise ValueError(f"{label} contiene líneas duplicadas: {examples}")


def summarize_attention_overlap(
    primary_alerts: pd.DataFrame,
    cross_branch_behaviors: pd.DataFrame,
) -> dict[str, int]:
    """Resume líneas únicas y superposición sin sumar categorías dos veces."""

    _assert_unique_lines(primary_alerts, "Las alertas principales")
    _assert_unique_lines(cross_branch_behaviors, "Los comportamientos inusuales")
    primary_keys = primary_alerts[LINE_KEY_COLUMNS].copy()
    behavior_keys = cross_branch_behaviors[LINE_KEY_COLUMNS].copy()
    overlap = primary_keys.merge(
        behavior_keys,
        on=LINE_KEY_COLUMNS,
        how="inner",
        validate="one_to_one",
    )
    unique_lines = pd.concat([primary_keys, behavior_keys], ignore_index=True).drop_duplicates(
        LINE_KEY_COLUMNS
    )
    return {
        "alertas_principales": len(primary_keys),
        "comportamientos_inusuales": len(behavior_keys),
        "superposicion": len(overlap),
        "lineas_unicas": len(unique_lines),
    }


def scope_cross_branch_behaviors(
    behaviors: pd.DataFrame,
    review_scope: pd.DataFrame,
) -> pd.DataFrame:
    """Aplica el alcance de filtros conservando una fila por línea."""

    _assert_unique_lines(behaviors, "Los comportamientos inusuales")
    _assert_unique_lines(review_scope, "La revisión filtrada")
    keys = review_scope[LINE_KEY_COLUMNS]
    return behaviors.merge(
        keys,
        on=LINE_KEY_COLUMNS,
        how="inner",
        validate="one_to_one",
    )


def _build_result(
    row: pd.Series,
    *,
    direction: str,
    factor: float | None,
    peer_median: float | None,
    peer_order_median: float,
    peer_recommendation_median: float,
    peer_mad: float | None,
    modified_z_score: float | None,
    peer_count: int,
    method: str,
) -> dict[str, object]:
    ordered = float(row["_ordered"])
    recommended = float(row["_recommended"])
    difference = float(row["_difference"])
    state = str(row["estado"])
    perishable = bool(row["es_perecedero_bool"])
    severity = _severity(direction, state, perishable)
    diagnosis = _primary_diagnosis(state)
    confidence = _confidence(peer_count)
    absolute_difference = int(abs(round(difference)))
    format_name = str(row["formato_compra"])
    ingredient = str(row["nombre"])
    branch = str(row["sucursal"])
    ratio_branch = _ratio_label(
        factor,
        "No aplica (recomendación = 0)",
    )
    ratio_peers = _ratio_label(
        peer_median,
        "No aplica (pares sin recomendación positiva)",
    )

    if recommended > 0 and factor is not None:
        reason = (
            f"Ratio de la sucursal: {ratio_branch}; mediana de {peer_count} pares: "
            f"{ratio_peers}; diferencia: {int(difference):+d} formatos."
        )
    else:
        reason = (
            f"Ratio de la sucursal: {ratio_branch}; mediana de ratios de los pares: "
            f"{ratio_peers}; diferencia: {int(difference):+d} formatos. "
            "La recomendación es cero y la mediana de exceso de los pares también es cero."
        )

    if direction == "MUY POR ENCIMA":
        action = (
            "Revisar la justificación local y, si no existe una excepción operativa, retirar "
            f"{purchase_format_phrase(format_name, absolute_difference)}."
        )
        context_message = (
            f"{branch} pidió {purchase_format_phrase(format_name, int(round(ordered)))} "
            f"de {ingredient}, muy por encima del patrón comparable. {reason}"
        )
    else:
        action = (
            f"Aumentar la orden en {purchase_format_phrase(format_name, absolute_difference)} "
            "antes de aprobarla, salvo que exista inventario o información operativa "
            "aún no registrada."
        )
        context_message = (
            f"{branch} pidió {purchase_format_phrase(format_name, int(round(ordered)))} "
            f"de {ingredient}, muy por debajo del patrón comparable. {reason}"
        )

    if state == "OMITIDO":
        message = (
            f"PRODUCTO OMITIDO: {branch} no incluyó {ingredient} en su orden. "
            "Contexto secundario de comportamiento inusual entre sucursales: "
            f"{reason}"
        )
    else:
        message = (
            "COMPORTAMIENTO INUSUAL ENTRE SUCURSALES: "
            f"{context_message}"
        )

    magnitude = (
        abs(float(factor) - float(peer_median))
        if factor is not None and peer_median is not None
        else abs(difference)
    )
    return {
        "severidad": severity,
        "diagnostico_principal": diagnosis,
        "direccion": direction,
        "sucursal": branch,
        "ingrediente_id": row["ingrediente_id"],
        "ingrediente": ingredient,
        "proveedor": row["proveedor"],
        "es_perecedero": "Sí" if perishable else "No",
        "formato_compra": format_name,
        "unidad_base": row["unidad_base"],
        "formatos_ordenados": ordered,
        "formatos_recomendados": recommended,
        "diferencia_formatos": difference,
        "cantidad_ordenada_base": float(row["_ordered_base"]),
        "cantidad_recomendada_base": float(row["_recommended_base"]),
        "factor_vs_recomendacion": (
            factor if factor is not None else "No aplica (recomendación = 0)"
        ),
        "ratio_sucursal": ratio_branch,
        "mediana_factor_pares": (
            peer_median
            if peer_median is not None
            else "No aplica (pares sin recomendación positiva)"
        ),
        "ratio_mediana_pares": ratio_peers,
        "mediana_formatos_ordenados_pares": peer_order_median,
        "mediana_formatos_recomendados_pares": peer_recommendation_median,
        "mad_factor_pares": peer_mad if peer_mad is not None else "No aplica",
        "modified_z_score": (
            modified_z_score if modified_z_score is not None else "No aplica"
        ),
        "cantidad_pares": peer_count,
        "metodo_deteccion": method,
        "nivel_confianza": confidence,
        "magnitud_relativa": magnitude,
        "estado_compra": state,
        "razon": reason,
        "accion_recomendada": action,
        "mensaje": message,
    }


def detect_cross_branch_order_anomalies(
    review: pd.DataFrame,
    *,
    catalog_ingredient_ids: Collection[object] | None = None,
    min_peers: int = 2,
    modified_z_threshold: float = 3.5,
    high_factor_threshold: float = 2.0,
    low_factor_threshold: float = 0.5,
) -> pd.DataFrame:
    """Detecta comportamientos inusuales frente a sucursales comparables."""

    if min_peers < 2:
        raise ValueError("min_peers debe ser al menos 2 para comparar sucursales.")
    missing = REQUIRED_COLUMNS.difference(review.columns)
    if missing:
        raise ValueError(f"Faltan columnas obligatorias para benchmarking: {sorted(missing)}")
    if review.empty:
        return _empty_result()
    _assert_unique_lines(review, "La revisión de compra")

    working = review.copy()
    numeric_sources = {
        "_ordered": "formatos_ordenados",
        "_recommended": "formatos_recomendados",
        "_difference": "diferencia_formatos",
        "_ordered_base": "cantidad_ordenada_base",
        "_recommended_base": "cantidad_recomendada_base",
        "_inventory": "inventario_actual",
        "_forecast": "consumo_proyectado",
        "_format_size": "unidad_base_por_formato",
    }
    for target, source in numeric_sources.items():
        working[target] = pd.to_numeric(working[source], errors="coerce")

    eligible = pd.Series(True, index=working.index)
    for column in numeric_sources:
        eligible &= _finite_mask(working[column])
    eligible &= _integer_mask(working["_ordered"])
    eligible &= _integer_mask(working["_recommended"])
    eligible &= _integer_mask(working["_difference"])
    eligible &= working["_ordered"] >= 0
    eligible &= working["_recommended"] >= 0
    eligible &= working["_ordered_base"] >= 0
    eligible &= working["_recommended_base"] >= 0
    eligible &= working["_inventory"] >= 0
    eligible &= working["_forecast"] >= 0
    eligible &= working["_format_size"] > 0
    eligible &= np.isclose(
        working["_difference"],
        working["_ordered"] - working["_recommended"],
        equal_nan=False,
    )
    eligible &= working["estado"].isin(VALID_CALCULABLE_STATES)
    eligible &= working["es_perecedero_bool"].notna()
    for column in [
        "sucursal",
        "ingrediente_id",
        "nombre",
        "proveedor",
        "unidad_base",
        "formato_compra",
    ]:
        eligible &= _text_mask(working[column])
    if "razon_dato_incompleto" in working.columns:
        incomplete_reason = working["razon_dato_incompleto"]
        eligible &= incomplete_reason.isna() | incomplete_reason.astype(str).str.strip().eq("")
    if catalog_ingredient_ids is not None:
        known_ids = {str(value).strip() for value in catalog_ingredient_ids}
        eligible &= working["ingrediente_id"].astype(str).str.strip().isin(known_ids)

    working["_factor"] = pd.Series([None] * len(working), index=working.index, dtype=object)
    positive_recommendation = eligible & (working["_recommended"] > 0)
    working.loc[positive_recommendation, "_factor"] = (
        working.loc[positive_recommendation, "_ordered"]
        / working.loc[positive_recommendation, "_recommended"]
    ).astype(float)
    eligible_rows = working.loc[eligible].copy()
    if eligible_rows.empty:
        return _empty_result()

    results: list[dict[str, object]] = []
    for _, row in eligible_rows.iterrows():
        peers = eligible_rows[
            (eligible_rows["ingrediente_id"] == row["ingrediente_id"])
            & (eligible_rows["sucursal"] != row["sucursal"])
        ]
        ordered = float(row["_ordered"])
        recommended = float(row["_recommended"])
        difference = float(row["_difference"])

        if recommended > 0:
            comparable = peers[peers["_recommended"] > 0].copy()
            peer_factors = pd.to_numeric(comparable["_factor"], errors="coerce")
            comparable = comparable.loc[_finite_mask(peer_factors)].copy()
            peer_factors = pd.to_numeric(comparable["_factor"], errors="coerce").astype(float)
            if len(comparable) < min_peers:
                continue
            peer_median = float(peer_factors.median())
            peer_mad = float((peer_factors - peer_median).abs().median())
            factor = float(row["_factor"])
            modified_z = (
                float(0.6745 * (factor - peer_median) / peer_mad)
                if peer_mad > 0
                else None
            )
            high_limit = max(
                peer_median * high_factor_threshold,
                peer_median + 1.0,
            )
            low_limit = peer_median * low_factor_threshold
            robust_high = modified_z is not None and modified_z > modified_z_threshold
            robust_low = modified_z is not None and modified_z < -modified_z_threshold
            fallback_high = factor >= high_limit
            fallback_low = factor <= low_limit
            if difference >= 1 and (robust_high or fallback_high):
                direction = "MUY POR ENCIMA"
            elif difference <= -1 and (robust_low or fallback_low):
                direction = "MUY POR DEBAJO"
            else:
                continue
            method = (
                "Modified z-score sobre ratio orden/recomendación"
                if robust_high or robust_low
                else "Umbral relativo con MAD igual a cero o baja dispersión"
            )
            results.append(
                _build_result(
                    row,
                    direction=direction,
                    factor=factor,
                    peer_median=peer_median,
                    peer_order_median=float(comparable["_ordered"].median()),
                    peer_recommendation_median=float(comparable["_recommended"].median()),
                    peer_mad=peer_mad,
                    modified_z_score=modified_z,
                    peer_count=len(comparable),
                    method=method,
                )
            )
            continue

        if recommended == 0 and ordered >= 1 and difference >= 1:
            comparable = peers.copy()
            if len(comparable) < min_peers:
                continue
            peer_excess = (
                comparable["_ordered"].astype(float)
                - comparable["_recommended"].astype(float)
            ).clip(lower=0)
            if float(peer_excess.median()) > 0:
                continue
            positive_peers = comparable[comparable["_recommended"] > 0]
            positive_factors = pd.to_numeric(
                positive_peers["_factor"],
                errors="coerce",
            )
            positive_factors = positive_factors.loc[_finite_mask(positive_factors)]
            peer_median = (
                float(positive_factors.median())
                if not positive_factors.empty
                else None
            )
            results.append(
                _build_result(
                    row,
                    direction="MUY POR ENCIMA",
                    factor=None,
                    peer_median=peer_median,
                    peer_order_median=float(comparable["_ordered"].median()),
                    peer_recommendation_median=float(comparable["_recommended"].median()),
                    peer_mad=None,
                    modified_z_score=None,
                    peer_count=len(comparable),
                    method=(
                        "Recomendación cero con pedido positivo y mediana de exceso cero "
                        "en sucursales pares"
                    ),
                )
            )

    if not results:
        return _empty_result()
    result = pd.DataFrame(results, columns=OUTPUT_COLUMNS)
    _assert_unique_lines(result, "El resultado del benchmarking")
    result["_severity_rank"] = result["severidad"].map(SEVERITY_ORDER).fillna(99)
    result = result.sort_values(
        ["_severity_rank", "magnitud_relativa", "sucursal", "ingrediente"],
        ascending=[True, False, True, True],
    ).drop(columns="_severity_rank")
    return result.reset_index(drop=True)

