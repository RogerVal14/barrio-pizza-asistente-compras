"""Pruebas unitarias de la proyección robusta."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.forecasting import detect_mad_outliers, forecast_group


def make_history(values: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "sucursal": ["Prueba"] * len(values),
            "ingrediente_id": ["producto"] * len(values),
            "semana": [f"S{index}" for index in range(1, len(values) + 1)],
            "consumo_unidad_base": values,
        }
    )


def test_mad_zero_does_not_mark_outliers() -> None:
    mask, median, mad, modified_z = detect_mad_outliers([10, 10, 10, 10, 10, 10])
    assert median == 10
    assert mad == 0
    assert not mask.any()
    assert np.all(modified_z == 0)


def test_detects_and_excludes_outlier_when_four_values_remain() -> None:
    result, outliers = forecast_group(make_history([28, 30, 150, 29, 31, 27]))
    assert len(outliers) == 1
    assert outliers.iloc[0]["semana"] == "S3"
    assert bool(outliers.iloc[0]["excluido_proyeccion"])
    assert result["cantidad_atipicos"] == 1
    assert result["consumo_proyectado"] == pytest.approx(29.0)
    assert result["metodo_proyeccion"] == "Promedio robusto"


def test_detects_strong_linear_trend() -> None:
    result, _ = forecast_group(make_history([240, 255, 268, 284, 300, 316]))
    assert result["metodo_proyeccion"] == "Tendencia lineal"
    assert result["r2"] >= 0.80
    assert result["consumo_proyectado"] == pytest.approx(330.2666666667)


def test_projection_cannot_be_negative() -> None:
    result, _ = forecast_group(make_history([5, 4, 3, 2, 1, 0]))
    assert result["metodo_proyeccion"] == "Tendencia lineal"
    assert result["consumo_proyectado"] == 0


@pytest.mark.parametrize("values", [[8], [8, 10]])
def test_one_or_two_weeks_produce_low_confidence_basic_projection(values: list[float]) -> None:
    result, _ = forecast_group(make_history(values))
    assert result["nivel_confianza"] == "Baja"
    assert result["metodo_proyeccion"] == "Proyección básica"
    assert pd.notna(result["consumo_proyectado"])


def test_no_history_does_not_fabricate_projection() -> None:
    result, _ = forecast_group(
        pd.DataFrame(columns=["sucursal", "ingrediente_id", "semana", "consumo_unidad_base"])
    )
    assert result["metodo_proyeccion"] == "Sin histórico"
    assert pd.isna(result["consumo_proyectado"])
