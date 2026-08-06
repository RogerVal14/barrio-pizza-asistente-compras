"""Proyección robusta, transparente y auditable del consumo semanal."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

import numpy as np
import pandas as pd


FORECAST_COLUMNS = [
    "sucursal",
    "ingrediente_id",
    "consumo_proyectado",
    "metodo_proyeccion",
    "cantidad_atipicos",
    "r2",
    "nivel_confianza",
    "explicacion_metodo",
    "promedio_simple_6s",
    "semanas_validas",
    "semanas_usadas",
    "pendiente",
    "cambio_relativo_tendencia",
    "semana_proyectada_numero",
]

OUTLIER_COLUMNS = [
    "sucursal",
    "ingrediente_id",
    "semana",
    "consumo_unidad_base",
    "mediana",
    "mad",
    "modified_z_score",
    "excluido_proyeccion",
]


def week_number(value: object) -> float:
    """Convierte etiquetas como S1 o S12 en un número ordenable."""

    if pd.isna(value):
        return np.nan
    match = re.fullmatch(r"S(\d+)", str(value).strip(), flags=re.IGNORECASE)
    return float(match.group(1)) if match else np.nan


def detect_mad_outliers(values: Iterable[float]) -> tuple[np.ndarray, float, float, np.ndarray]:
    """Detecta extremos con modified z-score y devuelve máscara, mediana, MAD y z."""

    array = np.asarray(list(values), dtype=float)
    if array.size == 0:
        return np.array([], dtype=bool), np.nan, np.nan, np.array([], dtype=float)

    median = float(np.median(array))
    mad = float(np.median(np.abs(array - median)))
    modified_z = np.zeros(array.size, dtype=float)
    if mad <= 0 or not np.isfinite(mad):
        return np.zeros(array.size, dtype=bool), median, mad, modified_z

    modified_z = 0.6745 * (array - median) / mad
    return np.abs(modified_z) > 3.5, median, mad, modified_z


def _linear_fit(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    slope, intercept = np.polyfit(x, y, 1)
    fitted = intercept + slope * x
    residual = float(np.sum((y - fitted) ** 2))
    total = float(np.sum((y - np.mean(y)) ** 2))
    if np.isclose(total, 0):
        r2 = 1.0 if np.isclose(residual, 0) else 0.0
    else:
        r2 = max(0.0, min(1.0, 1.0 - residual / total))
    return float(slope), float(intercept), float(r2)


def forecast_group(group: pd.DataFrame) -> tuple[dict[str, object], pd.DataFrame]:
    """Proyecta una sola combinación y conserva evidencia de sus atípicos."""

    working = group.copy()
    working["semana_numero"] = working["semana"].map(week_number)
    working["consumo_numerico"] = pd.to_numeric(
        working["consumo_unidad_base"], errors="coerce"
    )
    valid = working[
        working["semana_numero"].notna()
        & working["consumo_numerico"].notna()
        & (working["consumo_numerico"] >= 0)
    ].sort_values("semana_numero")

    # Una semana duplicada no se promedia ni suma implícitamente.
    duplicate_week = valid.duplicated("semana_numero", keep=False)
    valid_for_model = valid.loc[~duplicate_week].copy()
    values = valid_for_model["consumo_numerico"].to_numpy(dtype=float)
    outlier_mask, median, mad, modified_z = detect_mad_outliers(values)
    can_exclude = int((~outlier_mask).sum()) >= 4
    excluded_mask = outlier_mask if can_exclude else np.zeros(len(values), dtype=bool)
    clean = valid_for_model.loc[~excluded_mask].copy()

    outlier_rows: list[dict[str, object]] = []
    for position in np.flatnonzero(outlier_mask):
        row = valid_for_model.iloc[position]
        outlier_rows.append(
            {
                "sucursal": row.get("sucursal"),
                "ingrediente_id": row.get("ingrediente_id"),
                "semana": row["semana"],
                "consumo_unidad_base": float(row["consumo_numerico"]),
                "mediana": median,
                "mad": mad,
                "modified_z_score": float(modified_z[position]),
                "excluido_proyeccion": bool(can_exclude),
            }
        )

    simple_average = (
        float(valid_for_model.tail(6)["consumo_numerico"].mean())
        if not valid_for_model.empty
        else np.nan
    )
    n_valid = len(valid_for_model)
    n_clean = len(clean)
    next_week = (
        int(valid_for_model["semana_numero"].max()) + 1 if n_valid else np.nan
    )

    result: dict[str, object] = {
        "consumo_proyectado": np.nan,
        "metodo_proyeccion": "Sin histórico",
        "cantidad_atipicos": int(outlier_mask.sum()),
        "r2": np.nan,
        "nivel_confianza": "No disponible",
        "explicacion_metodo": "No existen observaciones históricas válidas; no se fabrica una proyección.",
        "promedio_simple_6s": simple_average,
        "semanas_validas": n_valid,
        "semanas_usadas": n_clean,
        "pendiente": np.nan,
        "cambio_relativo_tendencia": np.nan,
        "semana_proyectada_numero": next_week,
    }
    if n_clean == 0:
        return result, pd.DataFrame(outlier_rows, columns=OUTLIER_COLUMNS)

    y = clean["consumo_numerico"].to_numpy(dtype=float)
    x = clean["semana_numero"].to_numpy(dtype=float)
    mean_clean = float(np.mean(y))
    slope = np.nan
    r2 = np.nan
    change_relative = np.nan
    strong_trend = False

    if n_clean >= 2:
        slope, intercept, r2 = _linear_fit(x, y)
        absolute_change = abs(slope * (float(np.max(x)) - float(np.min(x))))
        change_relative = absolute_change / abs(mean_clean) if not np.isclose(mean_clean, 0) else 0.0
        # Dos puntos siempre producen una recta perfecta; no son evidencia suficiente
        # para elevar una referencia básica a tendencia fuerte.
        strong_trend = n_clean >= 3 and r2 >= 0.80 and change_relative >= 0.15
    else:
        intercept = mean_clean

    if strong_trend:
        forecast = intercept + slope * float(next_week)
        method = "Tendencia lineal"
        explanation = (
            f"La regresión presenta R²={r2:.2f} y un cambio estimado de "
            f"{change_relative:.0%}; se proyecta la siguiente semana con la tendencia."
        )
    else:
        forecast = mean_clean
        method = "Promedio robusto" if n_clean >= 3 else "Proyección básica"
        if n_clean == 1:
            explanation = "Solo hay una semana válida; se conserva su consumo como referencia básica."
        elif n_clean == 2:
            explanation = "Solo hay dos semanas válidas; se usa su promedio y se marca confianza baja."
        elif int(outlier_mask.sum()) and can_exclude:
            explanation = (
                f"No hay tendencia fuerte; se usa el promedio de {n_clean} semanas limpias "
                f"después de excluir {int(outlier_mask.sum())} valor atípico."
            )
        else:
            explanation = (
                f"No hay tendencia fuerte; se usa el promedio de {n_clean} semanas válidas."
            )

    if n_clean <= 2:
        confidence = "Baja"
    elif strong_trend and r2 >= 0.90 and n_clean >= 4:
        confidence = "Alta"
    elif n_clean >= 4:
        confidence = "Media"
    else:
        confidence = "Baja"

    result.update(
        {
            "consumo_proyectado": max(float(forecast), 0.0),
            "metodo_proyeccion": method,
            "r2": r2,
            "nivel_confianza": confidence,
            "explicacion_metodo": explanation,
            "pendiente": slope,
            "cambio_relativo_tendencia": change_relative,
        }
    )
    return result, pd.DataFrame(outlier_rows, columns=OUTLIER_COLUMNS)


def forecast_all(
    historical: pd.DataFrame, combinations: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Proyecta toda la cuadrícula sucursal–ingrediente, incluso si falta histórico."""

    rows: list[dict[str, object]] = []
    outlier_frames: list[pd.DataFrame] = []
    grouped = {
        (str(branch), str(ingredient)): group
        for (branch, ingredient), group in historical.groupby(
            ["sucursal", "ingrediente_id"], dropna=False
        )
    }

    for combo in combinations.itertuples(index=False):
        key = (str(combo.sucursal), str(combo.ingrediente_id))
        group = grouped.get(
            key,
            pd.DataFrame(
                columns=["sucursal", "ingrediente_id", "semana", "consumo_unidad_base"]
            ),
        )
        result, outliers = forecast_group(group)
        rows.append(
            {"sucursal": combo.sucursal, "ingrediente_id": combo.ingrediente_id, **result}
        )
        if not outliers.empty:
            outlier_frames.append(outliers)

    forecasts = pd.DataFrame(rows, columns=FORECAST_COLUMNS)
    forecasts = combinations.merge(
        forecasts,
        on=["sucursal", "ingrediente_id"],
        how="left",
        validate="one_to_one",
    )
    outliers = (
        pd.concat(outlier_frames, ignore_index=True)
        if outlier_frames
        else pd.DataFrame(columns=OUTLIER_COLUMNS)
    )
    return forecasts, outliers
