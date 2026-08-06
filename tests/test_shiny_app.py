"""Pruebas de integración de la interfaz alternativa Shiny."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


pytest.importorskip("shiny")

SHINY_APP_PATH = Path("variantes iniciales/app_shiny.py")
SHINY_SPEC = importlib.util.spec_from_file_location("app_shiny", SHINY_APP_PATH)
assert SHINY_SPEC is not None and SHINY_SPEC.loader is not None
app_shiny = importlib.util.module_from_spec(SHINY_SPEC)
sys.modules[SHINY_SPEC.name] = app_shiny
SHINY_SPEC.loader.exec_module(app_shiny)


def test_shiny_app_loads_default_pipeline() -> None:
    """La alternativa debe iniciar con los mismos resultados verificados."""

    review = app_shiny.INITIAL_PIPELINE["review"]
    alerts = app_shiny.INITIAL_PIPELINE["purchase_alerts"]

    assert app_shiny.app is not None
    assert len(review) == 88
    assert int((alerts["tipo_alerta"] == "OMITIDO").sum()) == 1
    assert int((alerts["tipo_alerta"] == "FALTANTE").sum()) == 1
    assert int((alerts["tipo_alerta"] == "SOBREPEDIDO").sum()) == 2


def test_shiny_simulator_recalculates_after_quantity_change() -> None:
    """Editar formatos debe actualizar la recomendación sin otra lógica paralela."""

    order = app_shiny.DEFAULT_ORDER.copy()
    mask = (order["sucursal"] == "Costa del Este") & (order["ingrediente_id"] == "harina")
    order.loc[mask, "cantidad_formatos"] = 13

    recalculated = app_shiny.run_pipeline(app_shiny.BUNDLE, order, 0.0)
    alerts = recalculated["purchase_alerts"]
    flour_shortage = alerts[
        (alerts["sucursal"] == "Costa del Este")
        & (alerts["ingrediente_id"] == "harina")
        & (alerts["tipo_alerta"] == "FALTANTE")
    ]

    assert flour_shortage.empty
