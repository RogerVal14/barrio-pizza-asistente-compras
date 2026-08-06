"""Pruebas de integración contra los casos de negocio entregados."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.alerts import build_purchase_alerts
from src.data_loader import load_data
from src.forecasting import forecast_all
from src.purchasing import build_purchase_review, unknown_order_lines
from src.validation import validate_data


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def processed() -> tuple[object, object, object, object]:
    bundle = load_data(ROOT / "datos")
    validated = validate_data(bundle.catalogo, bundle.historico, bundle.inventario, bundle.orden)
    forecasts, outliers = forecast_all(validated.historico, validated.combinaciones)
    review = build_purchase_review(validated, forecasts, safety_margin=0)
    alerts = build_purchase_alerts(review)
    return validated, forecasts, outliers, review, alerts


def line(review: object, branch: str, ingredient: str) -> object:
    return review[(review["sucursal"] == branch) & (review["ingrediente_id"] == ingredient)].iloc[0]


def test_brisas_mozzarella_is_omitted_with_18_formats(processed: tuple[object, ...]) -> None:
    _, _, _, review, _ = processed
    result = line(review, "Brisas del Golf", "mozzarella")
    assert result["producto_omitido_orden"]
    assert result["formatos_recomendados"] == 18
    assert result["estado"] == "OMITIDO"


def test_aji_chombo_is_unknown_and_has_no_invented_metadata(
    processed: tuple[object, ...]
) -> None:
    validated, _, _, _, _ = processed
    unknown = unknown_order_lines(validated)
    assert unknown["ingrediente_id"].tolist() == ["aji_chombo"]
    issue = validated.incidencias[
        (validated.incidencias["codigo"] == "INGREDIENTE_DESCONOCIDO")
        & (validated.incidencias["ingrediente_id"] == "aji_chombo")
    ]
    assert len(issue) == 1
    assert "proveedor" not in unknown.columns


def test_costa_flour_trend_and_shortage(processed: tuple[object, ...]) -> None:
    _, _, _, review, _ = processed
    result = line(review, "Costa del Este", "harina")
    assert result["metodo_proyeccion"] == "Tendencia lineal"
    assert result["consumo_proyectado"] == pytest.approx(330.2666666667)
    assert result["formatos_recomendados"] == 13
    assert result["formatos_ordenados"] == 6
    assert result["diferencia_formatos"] == -7
    assert result["estado"] == "FALTANTE"


def test_marbella_pepperoni_outlier_does_not_create_false_shortage(
    processed: tuple[object, ...]
) -> None:
    _, _, outliers, review, _ = processed
    detected = outliers[
        (outliers["sucursal"] == "Marbella") & (outliers["ingrediente_id"] == "pepperoni")
    ]
    assert len(detected) == 1
    assert detected.iloc[0]["semana"] == "S3"
    assert detected.iloc[0]["consumo_unidad_base"] == 150
    assert detected.iloc[0]["excluido_proyeccion"]
    result = line(review, "Marbella", "pepperoni")
    assert result["consumo_proyectado"] == pytest.approx(29)
    assert result["formatos_recomendados"] == 5
    assert result["estado"] == "CORRECTO"


def test_brisas_onion_overorder(processed: tuple[object, ...]) -> None:
    _, _, _, review, _ = processed
    result = line(review, "Brisas del Golf", "cebolla")
    assert result["formatos_recomendados"] == 2
    assert result["formatos_ordenados"] == 5
    assert result["diferencia_formatos"] == 3
    assert result["estado"] == "SOBREPEDIDO"


def test_via_argentina_basil_perishable_overorder(processed: tuple[object, ...]) -> None:
    _, _, _, review, alerts = processed
    result = line(review, "Via Argentina", "albahaca")
    assert result["formatos_recomendados"] == 2
    assert result["formatos_ordenados"] == 20
    assert result["diferencia_formatos"] == 18
    assert result["estado"] == "SOBREPEDIDO"
    assert result["es_perecedero_bool"]
    alert = alerts[
        (alerts["sucursal"] == "Via Argentina") & (alerts["ingrediente_id"] == "albahaca")
    ].iloc[0]
    assert alert["severidad"] == "Media"


def test_minimum_expected_alerts(processed: tuple[object, ...]) -> None:
    validated, _, outliers, _, alerts = processed
    assert (alerts["tipo_alerta"] == "OMITIDO").sum() >= 1
    assert (alerts["tipo_alerta"] == "FALTANTE").sum() >= 1
    assert (alerts["tipo_alerta"] == "SOBREPEDIDO").sum() >= 2
    assert (validated.incidencias["codigo"] == "INGREDIENTE_DESCONOCIDO").sum() >= 1
    assert len(outliers) >= 1
