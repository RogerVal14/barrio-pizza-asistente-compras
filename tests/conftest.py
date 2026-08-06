"""Fixtures pequeñas para probar reglas sin depender de los CSV de integración."""

from __future__ import annotations

import pandas as pd
import pytest


@pytest.fixture
def minimal_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    catalog = pd.DataFrame(
        [
            {
                "ingrediente_id": "insumo",
                "nombre": "Insumo de prueba",
                "proveedor": "Proveedor de prueba",
                "unidad_base": "kg",
                "formato_compra": "Caja 5 kg",
                "unidad_base_por_formato": 5,
                "es_perecedero": "No",
            }
        ]
    )
    historical = pd.DataFrame(
        [
            {
                "sucursal": "Sucursal nueva",
                "ingrediente_id": "insumo",
                "semana": f"S{week}",
                "consumo_unidad_base": 10,
            }
            for week in range(1, 7)
        ]
    )
    inventory = pd.DataFrame(
        [{"sucursal": "Sucursal nueva", "ingrediente_id": "insumo", "stock_actual_unidad_base": 0}]
    )
    order = pd.DataFrame(
        [{"sucursal": "Sucursal nueva", "ingrediente_id": "insumo", "cantidad_formatos": 2}]
    )
    return catalog, historical, inventory, order
