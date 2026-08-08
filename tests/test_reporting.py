"""Pruebas de los reportes Excel orientados a usuarios de negocio."""

from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile

import pandas as pd

from src.reporting import build_alerts_excel, build_branch_excel


def _xlsx_text(content: bytes) -> str:
    """Devuelve el XML del libro para validar estructura y textos sin Excel."""

    with ZipFile(BytesIO(content)) as workbook:
        return "\n".join(
            workbook.read(name).decode("utf-8")
            for name in workbook.namelist()
            if name.endswith(".xml")
        )


def test_alerts_report_is_a_valid_friendly_workbook() -> None:
    alerts = pd.DataFrame(
        [
            {
                "alerta_id": "EV-COMPRA-001",
                "severidad": "Alta",
                "tipo_alerta": "FALTANTE",
                "sucursal": "Costa del Este",
                "ingrediente": "Harina 00",
                "formato_compra": "Saco 25 kg",
                "formatos_ordenados": 6,
                "formatos_recomendados": 13,
                "diferencia_formatos": -7,
                "proveedor": "Molinos Central",
                "es_perecedero": "No",
                "razon": "La orden no cubre la necesidad proyectada.",
                "accion_recomendada": "Agregar 7 sacos de 25 kg antes de aprobar.",
            }
        ]
    )

    content = build_alerts_excel(alerts)
    xml = _xlsx_text(content)

    assert content.startswith(b"PK")
    assert "Resumen" in xml
    assert "Alertas prioritarias" in xml
    assert "Todas las alertas" in xml
    assert "6 sacos de 25 kg" in xml
    assert "13 sacos de 25 kg" in xml
    assert "Faltan 7 sacos de 25 kg" in xml
    assert "EV-COMPRA-001" in xml


def test_branch_report_separates_actions_detail_and_calculation_data() -> None:
    decisions = pd.DataFrame(
        [
            {
                "_prioridad": 0,
                "_estado": "OMITIDO",
                "Qué ocurre": "Producto omitido",
                "Ingrediente": "Mozzarella",
                "Pedido actual": "0 cajas de 10 kg",
                "Recomendación": "18 cajas de 10 kg",
                "Cambio sugerido": "Agregar 18 cajas de 10 kg",
                "Formato de compra": "Caja 10 kg",
                "Proveedor": "Distribuidora Láctea",
                "Perecedero": "Sí",
            },
            {
                "_prioridad": 4,
                "_estado": "CORRECTO",
                "Qué ocurre": "Cantidad adecuada",
                "Ingrediente": "Pepperoni",
                "Pedido actual": "5 cajas de 5 kg",
                "Recomendación": "5 cajas de 5 kg",
                "Cambio sugerido": "Dejar la orden como está",
                "Formato de compra": "Caja 5 kg",
                "Proveedor": "Distribuidora Láctea",
                "Perecedero": "Sí",
            },
        ]
    )
    technical = pd.DataFrame(
        [
            {
                "Ingrediente": "Mozzarella",
                "Inventario actual": "5 kg",
                "Consumo esperado": "180 kg",
                "Método": "Promedio robusto",
            }
        ]
    )

    content = build_branch_excel(
        "Brisas del Golf",
        decisions,
        technical,
        safety_margin=0.0,
    )
    xml = _xlsx_text(content)

    assert content.startswith(b"PK")
    assert "Resumen" in xml
    assert "Acciones antes de aprobar" in xml
    assert "Detalle completo" in xml
    assert "Datos de cálculo" in xml
    assert "Brisas del Golf" in xml
    assert "Agregar 18 cajas de 10 kg" in xml
    assert "Dejar la orden como está" in xml
    assert "Margen de seguridad: 0%" in xml


def test_empty_alerts_still_produce_an_openable_report() -> None:
    empty_alerts = pd.DataFrame(
        columns=[
            "alerta_id",
            "severidad",
            "tipo_alerta",
            "sucursal",
            "ingrediente",
        ]
    )

    content = build_alerts_excel(empty_alerts)
    xml = _xlsx_text(content)

    assert content.startswith(b"PK")
    assert "No hay registros para mostrar." in xml
