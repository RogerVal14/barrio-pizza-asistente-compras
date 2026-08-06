"""Pruebas unitarias de conversiones y reglas de compra."""

from __future__ import annotations

import pandas as pd
import pytest

from src.forecasting import forecast_all
from src.purchasing import (
    base_to_formats,
    build_purchase_review,
    calculate_need,
    classify_line,
    formats_to_base,
)
from src.validation import validate_data


def test_formats_to_base_conversion() -> None:
    assert formats_to_base(6, 25) == 150


def test_base_to_formats_uses_ceil() -> None:
    assert base_to_formats(25.01, 25) == 2


def test_format_2_55_kg() -> None:
    assert formats_to_base(3, 2.55) == pytest.approx(7.65)
    assert base_to_formats(5.10, 2.55) == 2


def test_format_0_25_kg() -> None:
    assert formats_to_base(7, 0.25) == pytest.approx(1.75)
    assert base_to_formats(1.01, 0.25) == 5


def test_negative_need_is_clamped_to_zero() -> None:
    assert calculate_need(projected=10, inventory=12) == 0
    assert base_to_formats(-4, 5) == 0


def test_inevitable_rounding_is_correct() -> None:
    recommendation = base_to_formats(26, 25)
    assert recommendation == 2
    assert classify_line(2, recommendation) == "CORRECTO"


def test_one_full_extra_format_is_overorder() -> None:
    assert classify_line(3, 2) == "SOBREPEDIDO"


def test_omitted_product_is_labeled() -> None:
    assert classify_line(0, 2, omitted=True) == "OMITIDO"


def test_missing_inventory_is_not_assumed_zero(minimal_frames: tuple[pd.DataFrame, ...]) -> None:
    catalog, historical, inventory, order = minimal_frames
    validated = validate_data(catalog, historical, inventory.iloc[0:0], order)
    forecasts, _ = forecast_all(validated.historico, validated.combinaciones)
    review = build_purchase_review(validated, forecasts)
    assert review.iloc[0]["estado"] == "DATO INCOMPLETO"
    assert pd.isna(review.iloc[0]["inventario_actual"])
    assert pd.isna(review.iloc[0]["formatos_recomendados"])


def test_new_branch_and_ingredient_work_without_hardcoding(
    minimal_frames: tuple[pd.DataFrame, ...]
) -> None:
    catalog, historical, inventory, order = minimal_frames
    validated = validate_data(catalog, historical, inventory, order)
    forecasts, _ = forecast_all(validated.historico, validated.combinaciones)
    review = build_purchase_review(validated, forecasts)
    assert validated.sucursales == ["Sucursal nueva"]
    assert review.iloc[0]["nombre"] == "Insumo de prueba"
    assert review.iloc[0]["formatos_recomendados"] == 2
    assert review.iloc[0]["estado"] == "CORRECTO"
