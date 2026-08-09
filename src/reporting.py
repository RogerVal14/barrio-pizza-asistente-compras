"""Reportes Excel orientados a la revisión humana de órdenes de compra."""

from __future__ import annotations

from datetime import date
from io import BytesIO
from typing import Any

import pandas as pd
import xlsxwriter

from src.alerts import purchase_format_phrase


INK = "#231F20"
RED = "#CF2F2C"
CREAM = "#F5EBDD"
BONE = "#FFFDF9"
MUTED = "#6E6863"
LINE = "#DED4C9"
GREEN = "#3F7652"
ORANGE = "#E65D32"
GOLD = "#D98E2B"
PURPLE = "#765A92"

SEVERITY_RANK = {"Crítica": 0, "Alta": 1, "Media": 2, "Baja": 3}
ALERT_LABELS = {
    "OMITIDO": "Producto omitido",
    "FALTANTE": "Riesgo de quiebre",
    "SOBREPEDIDO": "Sobrepedido",
}
STATE_LABELS = {
    "OMITIDO": "Agregar producto omitido",
    "FALTANTE": "Aumentar cantidad",
    "SOBREPEDIDO": "Reducir cantidad",
    "DATO INCOMPLETO": "Revisar datos",
    "CORRECTO": "Sin cambios",
    "SIN NECESIDAD": "Sin cambios",
}


def _clean_value(value: object) -> object:
    if value is None or pd.isna(value):
        return ""
    if isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


def _integer(value: object) -> int | None:
    if value is None or pd.isna(value):
        return None
    return int(round(float(value)))


def _purchase_phrase(value: object, format_name: object) -> str:
    quantity = _integer(value)
    if quantity is None:
        return "No calculable"
    return purchase_format_phrase(format_name, quantity)


def _difference_phrase(value: object, format_name: object) -> str:
    difference = _integer(value)
    if difference is None:
        return "No calculable"
    if difference < 0:
        return f"Faltan {_purchase_phrase(abs(difference), format_name)}"
    if difference > 0:
        return f"Sobran {_purchase_phrase(difference, format_name)}"
    return "Sin diferencia"


def _percentage_phrase(value: object) -> str | None:
    """Convierte un factor, por ejemplo 1.25, en un porcentaje legible."""

    if value is None or pd.isna(value) or isinstance(value, bool):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not pd.notna(numeric):
        return None
    formatted = f"{numeric * 100:,.0f}".replace(",", ".")
    return f"{formatted}%"


def _behavior_comparison_phrase(row: object) -> str:
    """Explica la referencia entre sucursales sin depender de ratios técnicos."""

    peer_count = _integer(getattr(row, "cantidad_pares", None)) or 0
    branch_percentage = _percentage_phrase(getattr(row, "factor_vs_recomendacion", None))
    peer_percentage = _percentage_phrase(getattr(row, "mediana_factor_pares", None))
    if branch_percentage is not None and peer_percentage is not None:
        return (
            f"Esta sucursal cubre {branch_percentage} de su recomendación; "
            f"las otras {peer_count} cubren cerca de {peer_percentage}."
        )
    return (
        "La recomendación de esta sucursal es cero. La comparación revisa el exceso "
        f"en formatos frente a {peer_count} sucursales."
    )


def _workbook_formats(workbook: xlsxwriter.Workbook) -> dict[str, Any]:
    return {
        "title": workbook.add_format(
            {"bold": True, "font_size": 22, "font_color": BONE, "bg_color": INK, "valign": "vcenter"}
        ),
        "subtitle": workbook.add_format(
            {"font_size": 10, "font_color": BONE, "bg_color": INK, "valign": "vcenter"}
        ),
        "section": workbook.add_format(
            {"bold": True, "font_size": 12, "font_color": BONE, "bg_color": RED, "valign": "vcenter"}
        ),
        "card_label": workbook.add_format(
            {"bold": True, "font_size": 9, "font_color": MUTED, "bg_color": CREAM, "align": "center", "valign": "vcenter"}
        ),
        "card_value": workbook.add_format(
            {"bold": True, "font_size": 20, "font_color": INK, "bg_color": CREAM, "align": "center", "valign": "vcenter"}
        ),
        "note": workbook.add_format(
            {"font_size": 9, "font_color": MUTED, "bg_color": "#F9F4EC", "text_wrap": True, "valign": "vcenter"}
        ),
        "header": workbook.add_format(
            {"bold": True, "font_color": BONE, "bg_color": INK, "border": 0, "text_wrap": True, "valign": "vcenter"}
        ),
        "body": workbook.add_format(
            {"font_color": INK, "bg_color": BONE, "bottom": 1, "bottom_color": LINE, "valign": "top"}
        ),
        "body_alt": workbook.add_format(
            {"font_color": INK, "bg_color": "#FAF5EE", "bottom": 1, "bottom_color": LINE, "valign": "top"}
        ),
        "body_wrap": workbook.add_format(
            {"font_color": INK, "bg_color": BONE, "bottom": 1, "bottom_color": LINE, "valign": "top", "text_wrap": True}
        ),
        "body_wrap_alt": workbook.add_format(
            {"font_color": INK, "bg_color": "#FAF5EE", "bottom": 1, "bottom_color": LINE, "valign": "top", "text_wrap": True}
        ),
        "critical": workbook.add_format(
            {"bold": True, "font_color": "#FFFFFF", "bg_color": "#B42318", "align": "center", "valign": "vcenter"}
        ),
        "high": workbook.add_format(
            {"bold": True, "font_color": "#FFFFFF", "bg_color": ORANGE, "align": "center", "valign": "vcenter"}
        ),
        "medium": workbook.add_format(
            {"bold": True, "font_color": INK, "bg_color": "#F7C873", "align": "center", "valign": "vcenter"}
        ),
        "low": workbook.add_format(
            {"bold": True, "font_color": INK, "bg_color": "#DDE8F0", "align": "center", "valign": "vcenter"}
        ),
        "change": workbook.add_format(
            {"bold": True, "font_color": "#FFFFFF", "bg_color": RED, "text_wrap": True, "valign": "vcenter"}
        ),
        "correct": workbook.add_format(
            {"bold": True, "font_color": "#FFFFFF", "bg_color": GREEN, "text_wrap": True, "valign": "vcenter"}
        ),
        "incomplete": workbook.add_format(
            {"bold": True, "font_color": "#FFFFFF", "bg_color": PURPLE, "text_wrap": True, "valign": "vcenter"}
        ),
    }


def _setup_sheet(worksheet: Any) -> None:
    worksheet.hide_gridlines(2)
    worksheet.set_landscape()
    worksheet.set_paper(9)
    worksheet.fit_to_pages(1, 0)
    worksheet.set_margins(left=0.25, right=0.25, top=0.55, bottom=0.55)
    worksheet.set_footer("&LGenerado por Barrio Pizza | Asistente Inteligente de Compras&C&P de &N&RRevisión humana requerida")


def _write_title(
    worksheet: Any,
    formats: dict[str, Any],
    title: str,
    subtitle: str,
    *,
    last_column: int,
) -> None:
    worksheet.merge_range(0, 0, 1, last_column, title, formats["title"])
    worksheet.merge_range(2, 0, 2, last_column, subtitle, formats["subtitle"])
    worksheet.set_row(0, 24)
    worksheet.set_row(1, 24)
    worksheet.set_row(2, 22)


def _write_cards(
    worksheet: Any,
    formats: dict[str, Any],
    cards: list[tuple[str, object]],
    *,
    row: int = 4,
) -> None:
    for index, (label, value) in enumerate(cards):
        start_col = index * 3
        worksheet.merge_range(row, start_col, row, start_col + 1, label, formats["card_label"])
        worksheet.merge_range(row + 1, start_col, row + 2, start_col + 1, _clean_value(value), formats["card_value"])
        worksheet.set_column(start_col, start_col + 1, 13)
    worksheet.set_row(row + 1, 24)
    worksheet.set_row(row + 2, 24)


def _write_dataframe(
    worksheet: Any,
    formats: dict[str, Any],
    frame: pd.DataFrame,
    *,
    start_row: int,
    widths: dict[str, float] | None = None,
    severity_column: str | None = None,
    state_column: str | None = None,
) -> int:
    widths = widths or {}
    columns = [str(column) for column in frame.columns]
    for column_index, column in enumerate(columns):
        worksheet.write(start_row, column_index, column, formats["header"])
        calculated_width = min(max(len(column) + 2, widths.get(column, 14)), 48)
        worksheet.set_column(column_index, column_index, calculated_width)
    worksheet.set_row(start_row, 30)

    for row_offset, values in enumerate(frame.itertuples(index=False, name=None), start=1):
        excel_row = start_row + row_offset
        alternate = row_offset % 2 == 0
        worksheet.set_row(excel_row, 38)
        for column_index, value in enumerate(values):
            column = columns[column_index]
            is_long_text = widths.get(column, 14) >= 28
            body_key = "body_wrap_alt" if alternate and is_long_text else "body_wrap" if is_long_text else "body_alt" if alternate else "body"
            cell_format = formats[body_key]
            if severity_column == column:
                cell_format = {
                    "Crítica": formats["critical"],
                    "Alta": formats["high"],
                    "Media": formats["medium"],
                    "Baja": formats["low"],
                }.get(str(value), cell_format)
            if state_column == column:
                state_text = str(value)
                if "Sin cambios" in state_text:
                    cell_format = formats["correct"]
                elif "Revisar datos" in state_text:
                    cell_format = formats["incomplete"]
                else:
                    cell_format = formats["change"]
            worksheet.write(excel_row, column_index, _clean_value(value), cell_format)

    last_row = start_row + max(len(frame), 1)
    if not frame.empty:
        worksheet.autofilter(start_row, 0, start_row + len(frame), len(columns) - 1)
    else:
        worksheet.merge_range(start_row + 1, 0, start_row + 2, max(len(columns) - 1, 0), "No hay registros para mostrar.", formats["note"])
    worksheet.freeze_panes(start_row + 1, 0)
    worksheet.print_area(0, 0, last_row, max(len(columns) - 1, 0))
    return last_row


def _friendly_alerts(alerts: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    ordered_alerts = alerts.copy()
    if not ordered_alerts.empty:
        ordered_alerts["_orden_severidad"] = ordered_alerts["severidad"].map(SEVERITY_RANK).fillna(99)
        ordered_alerts = ordered_alerts.sort_values(
            ["_orden_severidad", "sucursal", "ingrediente"], na_position="last"
        )
    for row in ordered_alerts.itertuples(index=False):
        format_name = getattr(row, "formato_compra", None)
        rows.append(
            {
                "Severidad": getattr(row, "severidad", ""),
                "Diagnóstico": ALERT_LABELS.get(str(getattr(row, "tipo_alerta", "")), getattr(row, "tipo_alerta", "")),
                "Sucursal": getattr(row, "sucursal", ""),
                "Ingrediente": getattr(row, "ingrediente", ""),
                "Pedido actual": _purchase_phrase(getattr(row, "formatos_ordenados", None), format_name),
                "Recomendación": _purchase_phrase(getattr(row, "formatos_recomendados", None), format_name),
                "Ajuste necesario": _difference_phrase(getattr(row, "diferencia_formatos", None), format_name),
                "Proveedor": getattr(row, "proveedor", ""),
                "Perecedero": getattr(row, "es_perecedero", ""),
                "Por qué importa": getattr(row, "razon", ""),
                "Acción recomendada": getattr(row, "accion_recomendada", ""),
                "Evidencia": getattr(row, "alerta_id", ""),
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "Severidad", "Diagnóstico", "Sucursal", "Ingrediente", "Pedido actual",
            "Recomendación", "Ajuste necesario", "Proveedor", "Perecedero",
            "Por qué importa", "Acción recomendada", "Evidencia",
        ],
    )


def build_alerts_excel(alerts: pd.DataFrame) -> bytes:
    """Construye un reporte visual con las alertas que permanecen después de filtrar."""

    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    workbook.set_properties(
        {
            "title": "Reporte de alertas de compra",
            "subject": "Revisión semanal de órdenes",
            "company": "Barrio Pizza",
            "comments": "Las recomendaciones requieren aprobación humana.",
        }
    )
    formats = _workbook_formats(workbook)
    friendly = _friendly_alerts(alerts)

    summary = workbook.add_worksheet("Resumen")
    _setup_sheet(summary)
    _write_title(
        summary,
        formats,
        "BARRIO PIZZA | REPORTE DE ALERTAS",
        f"Alertas visibles al {date.today().strftime('%d/%m/%Y')} · Las recomendaciones requieren aprobación humana.",
        last_column=8,
    )
    critical_count = int((alerts.get("severidad", pd.Series(dtype="object")) == "Crítica").sum())
    branch_count = int(alerts.get("sucursal", pd.Series(dtype="object")).dropna().nunique())
    _write_cards(
        summary,
        formats,
        [("Alertas visibles", len(alerts)), ("Atención crítica", critical_count), ("Sucursales afectadas", branch_count)],
    )
    summary.merge_range(
        8,
        0,
        9,
        8,
        "Cómo usar este reporte: empieza por las alertas críticas, confirma el inventario y la operación de la sucursal, y aprueba o ajusta cada recomendación. Los colores acompañan etiquetas de texto; no son el único indicador.",
        formats["note"],
    )
    summary.merge_range(11, 0, 11, 8, "DECISIONES PRIORITARIAS", formats["section"])
    priority_summary = friendly.head(6)[
        ["Severidad", "Sucursal", "Ingrediente", "Diagnóstico", "Ajuste necesario", "Acción recomendada"]
    ]
    _write_dataframe(
        summary,
        formats,
        priority_summary,
        start_row=12,
        widths={"Severidad": 13, "Sucursal": 19, "Ingrediente": 22, "Diagnóstico": 20, "Ajuste necesario": 24, "Acción recomendada": 45},
        severity_column="Severidad",
    )

    priority = workbook.add_worksheet("Alertas prioritarias")
    _setup_sheet(priority)
    _write_title(
        priority,
        formats,
        "ALERTAS PRIORITARIAS",
        "Casos de severidad crítica o alta. Revisar antes de aprobar la compra.",
        last_column=11,
    )
    priority_frame = friendly[friendly["Severidad"].isin(["Crítica", "Alta"])]
    _write_dataframe(
        priority,
        formats,
        priority_frame,
        start_row=4,
        widths={"Severidad": 13, "Diagnóstico": 20, "Sucursal": 20, "Ingrediente": 22, "Pedido actual": 24, "Recomendación": 24, "Ajuste necesario": 26, "Proveedor": 24, "Perecedero": 13, "Por qué importa": 42, "Acción recomendada": 48, "Evidencia": 14},
        severity_column="Severidad",
    )

    all_alerts = workbook.add_worksheet("Todas las alertas")
    _setup_sheet(all_alerts)
    _write_title(
        all_alerts,
        formats,
        "TODAS LAS ALERTAS VISIBLES",
        "El contenido respeta los filtros aplicados en el dashboard al momento de descargar.",
        last_column=11,
    )
    _write_dataframe(
        all_alerts,
        formats,
        friendly,
        start_row=4,
        widths={"Severidad": 13, "Diagnóstico": 20, "Sucursal": 20, "Ingrediente": 22, "Pedido actual": 24, "Recomendación": 24, "Ajuste necesario": 26, "Proveedor": 24, "Perecedero": 13, "Por qué importa": 42, "Acción recomendada": 48, "Evidencia": 14},
        severity_column="Severidad",
    )

    workbook.close()
    return output.getvalue()


def _friendly_behaviors(behaviors: pd.DataFrame) -> pd.DataFrame:
    """Traduce la comparación entre sucursales a lenguaje de compras."""

    rows: list[dict[str, object]] = []
    ordered = behaviors.copy()
    if not ordered.empty:
        ordered["_orden_severidad"] = ordered["severidad"].map(SEVERITY_RANK).fillna(99)
        ordered = ordered.sort_values(
            ["_orden_severidad", "sucursal", "ingrediente"],
            na_position="last",
        )

    for row in ordered.itertuples(index=False):
        format_name = getattr(row, "formato_compra", None)
        peer_count = _integer(getattr(row, "cantidad_pares", None)) or 0
        direction = str(getattr(row, "direccion", ""))
        signal = (
            "Pedido mucho mayor que el patrón"
            if direction == "MUY POR ENCIMA"
            else "Pedido mucho menor que el patrón"
        )
        diagnosis = str(getattr(row, "diagnostico_principal", "Revisión de compra"))
        if diagnosis == "Producto omitido":
            signal = "Producto omitido; comparación como contexto"
        rows.append(
            {
                "Diagnóstico principal": diagnosis,
                "Señal comparativa": signal,
                "Sucursal": getattr(row, "sucursal", ""),
                "Ingrediente": getattr(row, "ingrediente", ""),
                "Pedido actual": _purchase_phrase(
                    getattr(row, "formatos_ordenados", None), format_name
                ),
                "Recomendación": _purchase_phrase(
                    getattr(row, "formatos_recomendados", None), format_name
                ),
                "Ajuste de la orden": _difference_phrase(
                    getattr(row, "diferencia_formatos", None), format_name
                ),
                "Comparación sencilla": _behavior_comparison_phrase(row),
                "Qué tan confiable es": (
                    f"{getattr(row, 'nivel_confianza', '')} · "
                    f"{peer_count} sucursales comparadas"
                ),
                "Proveedor": getattr(row, "proveedor", ""),
                "Perecedero": getattr(row, "es_perecedero", ""),
                "Qué debes revisar": getattr(row, "accion_recomendada", ""),
                "Método utilizado": getattr(row, "metodo_deteccion", ""),
            }
        )

    return pd.DataFrame(
        rows,
        columns=[
            "Diagnóstico principal",
            "Señal comparativa",
            "Sucursal",
            "Ingrediente",
            "Pedido actual",
            "Recomendación",
            "Ajuste de la orden",
            "Comparación sencilla",
            "Qué tan confiable es",
            "Proveedor",
            "Perecedero",
            "Qué debes revisar",
            "Método utilizado",
        ],
    )


def _technical_behaviors(behaviors: pd.DataFrame) -> pd.DataFrame:
    """Conserva la evidencia técnica en una hoja secundaria del reporte."""

    columns = {
        "diagnostico_principal": "Diagnóstico principal",
        "direccion": "Dirección comparativa",
        "sucursal": "Sucursal",
        "ingrediente_id": "Ingrediente ID",
        "ingrediente": "Ingrediente",
        "proveedor": "Proveedor",
        "formato_compra": "Formato de compra",
        "unidad_base": "Unidad base",
        "formatos_ordenados": "Formatos ordenados",
        "formatos_recomendados": "Formatos recomendados",
        "diferencia_formatos": "Diferencia de formatos",
        "cantidad_ordenada_base": "Cantidad ordenada base",
        "cantidad_recomendada_base": "Cantidad recomendada base",
        "ratio_sucursal": "Ratio de la sucursal",
        "ratio_mediana_pares": "Mediana de los pares",
        "cantidad_pares": "Sucursales comparadas",
        "metodo_deteccion": "Método utilizado",
        "nivel_confianza": "Nivel de confianza",
        "estado_compra": "Estado de compra",
        "razon": "Razón técnica",
        "accion_recomendada": "Acción recomendada",
    }
    available = [column for column in columns if column in behaviors.columns]
    return behaviors[available].rename(columns=columns).copy()


def build_behaviors_excel(behaviors: pd.DataFrame) -> bytes:
    """Construye un reporte visual de comportamientos inusuales entre sucursales."""

    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    workbook.set_properties(
        {
            "title": "Comportamiento inusual entre sucursales",
            "subject": "Contexto comparativo para revisar órdenes de compra",
            "company": "Barrio Pizza",
            "comments": (
                "Las señales comparativas no confirman un error y requieren revisión humana."
            ),
        }
    )
    formats = _workbook_formats(workbook)
    friendly = _friendly_behaviors(behaviors)

    summary = workbook.add_worksheet("Resumen")
    _setup_sheet(summary)
    _write_title(
        summary,
        formats,
        "BARRIO PIZZA | COMPARACIÓN ENTRE SUCURSALES",
        (
            f"Generado el {date.today().strftime('%d/%m/%Y')} · Estas señales invitan "
            "a revisar; no confirman un error."
        ),
        last_column=10,
    )
    branch_count = int(behaviors.get("sucursal", pd.Series(dtype="object")).dropna().nunique())
    ingredient_count = int(
        behaviors.get("ingrediente", pd.Series(dtype="object")).dropna().nunique()
    )
    moderate_count = int(
        (behaviors.get("nivel_confianza", pd.Series(dtype="object")) == "Moderada").sum()
    )
    _write_cards(
        summary,
        formats,
        [
            ("Casos para revisar", len(behaviors)),
            ("Sucursales involucradas", branch_count),
            ("Ingredientes involucrados", ingredient_count),
            ("Confianza moderada", moderate_count),
        ],
    )
    summary.merge_range(
        8,
        0,
        9,
        10,
        (
            "Lectura correcta: una misma línea puede ser producto omitido, faltante o "
            "sobrepedido y, al mismo tiempo, verse inusual frente a otras sucursales. "
            "Sigue siendo una sola línea de compra y no debe contarse como un producto adicional."
        ),
        formats["note"],
    )
    summary.merge_range(11, 0, 11, 10, "QUÉ DEBES REVISAR", formats["section"])
    summary_columns = [
        "Diagnóstico principal",
        "Sucursal",
        "Ingrediente",
        "Pedido actual",
        "Recomendación",
        "Ajuste de la orden",
        "Comparación sencilla",
        "Qué tan confiable es",
        "Qué debes revisar",
    ]
    _write_dataframe(
        summary,
        formats,
        friendly[summary_columns].head(8),
        start_row=12,
        widths={
            "Diagnóstico principal": 22,
            "Sucursal": 20,
            "Ingrediente": 22,
            "Pedido actual": 25,
            "Recomendación": 25,
            "Ajuste de la orden": 27,
            "Comparación sencilla": 44,
            "Qué tan confiable es": 27,
            "Qué debes revisar": 48,
        },
    )

    cases = workbook.add_worksheet("Casos para revisar")
    _setup_sheet(cases)
    _write_title(
        cases,
        formats,
        "CASOS PARA REVISAR",
        (
            "Primero conserva el diagnóstico de compra; la comparación con otras "
            "sucursales aparece como contexto secundario."
        ),
        last_column=len(friendly.columns) - 1,
    )
    _write_dataframe(
        cases,
        formats,
        friendly,
        start_row=4,
        widths={
            "Diagnóstico principal": 22,
            "Señal comparativa": 34,
            "Sucursal": 20,
            "Ingrediente": 22,
            "Pedido actual": 25,
            "Recomendación": 25,
            "Ajuste de la orden": 27,
            "Comparación sencilla": 45,
            "Qué tan confiable es": 27,
            "Proveedor": 24,
            "Perecedero": 13,
            "Qué debes revisar": 48,
            "Método utilizado": 45,
        },
    )

    technical = _technical_behaviors(behaviors)
    technical_sheet = workbook.add_worksheet("Detalle técnico")
    _setup_sheet(technical_sheet)
    _write_title(
        technical_sheet,
        formats,
        "EVIDENCIA TÉCNICA DE LA COMPARACIÓN",
        (
            "Ratios, cantidad de pares, método y confianza. Esta hoja sirve para "
            "auditar la señal, no para contar alertas adicionales."
        ),
        last_column=max(len(technical.columns) - 1, 0),
    )
    _write_dataframe(
        technical_sheet,
        formats,
        technical,
        start_row=4,
        widths={
            str(column): (
                48
                if column in {"Razón técnica", "Acción recomendada", "Método utilizado"}
                else 25
            )
            for column in technical.columns
        },
    )

    workbook.close()
    return output.getvalue()


def build_branch_excel(
    branch: str,
    decisions: pd.DataFrame,
    technical: pd.DataFrame,
    *,
    safety_margin: float = 0.0,
) -> bytes:
    """Construye un libro completo y legible para una sola sucursal."""

    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    workbook.set_properties(
        {
            "title": f"Revisión de compra · {branch}",
            "subject": "Revisión semanal por sucursal",
            "company": "Barrio Pizza",
            "comments": "Las recomendaciones requieren aprobación humana.",
        }
    )
    formats = _workbook_formats(workbook)

    working = decisions.copy()
    if "_estado" in working:
        working["Decisión"] = working["_estado"].map(STATE_LABELS).fillna(working["_estado"])
    elif "Decisión" not in working:
        working["Decisión"] = "Revisar"
    if "_prioridad" in working:
        working = working.sort_values(["_prioridad", "Ingrediente"], na_position="last")

    states = working.get("_estado", pd.Series(index=working.index, dtype="object"))
    change_mask = states.isin(["OMITIDO", "FALTANTE", "SOBREPEDIDO", "DATO INCOMPLETO"])
    correct_mask = states.isin(["CORRECTO", "SIN NECESIDAD"])
    incomplete_mask = states.eq("DATO INCOMPLETO")
    action_columns = [
        "Decisión", "Ingrediente", "Pedido actual", "Recomendación",
        "Cambio sugerido", "Formato de compra", "Proveedor", "Perecedero",
    ]
    available_action_columns = [column for column in action_columns if column in working.columns]
    actions = working.loc[change_mask, available_action_columns].copy()
    detail = working[[column for column in available_action_columns if column in working.columns]].copy()

    summary = workbook.add_worksheet("Resumen")
    _setup_sheet(summary)
    margin_note = f"Margen de seguridad simulado: {safety_margin:.0%}." if safety_margin else "Margen de seguridad: 0% (fórmula original)."
    _write_title(
        summary,
        formats,
        f"REVISIÓN DE COMPRA | {branch.upper()}",
        f"Generado el {date.today().strftime('%d/%m/%Y')} · {margin_note} · Requiere aprobación humana.",
        last_column=10,
    )
    _write_cards(
        summary,
        formats,
        [
            ("Productos revisados", len(working)),
            ("Debes cambiar", int(change_mask.sum())),
            ("Sin cambios", int(correct_mask.sum())),
            ("Revisar datos", int(incomplete_mask.sum())),
        ],
    )
    summary.merge_range(
        8,
        0,
        9,
        10,
        "Cómo usar este reporte: revisa primero la hoja “Acciones antes de aprobar”. La hoja “Detalle completo” conserva todos los productos y “Datos de cálculo” mantiene la evidencia técnica.",
        formats["note"],
    )
    summary.merge_range(11, 0, 11, 10, "ACCIONES ANTES DE APROBAR", formats["section"])
    _write_dataframe(
        summary,
        formats,
        actions.head(8),
        start_row=12,
        widths={"Decisión": 24, "Ingrediente": 23, "Pedido actual": 25, "Recomendación": 25, "Cambio sugerido": 32, "Formato de compra": 22, "Proveedor": 25, "Perecedero": 13},
        state_column="Decisión",
    )

    actions_sheet = workbook.add_worksheet("Acciones antes de aprobar")
    _setup_sheet(actions_sheet)
    _write_title(
        actions_sheet,
        formats,
        f"QUÉ DEBES CAMBIAR | {branch.upper()}",
        "Solo aparecen productos que deben agregarse, aumentarse, reducirse o revisarse por datos incompletos.",
        last_column=max(len(actions.columns) - 1, 0),
    )
    _write_dataframe(
        actions_sheet,
        formats,
        actions,
        start_row=4,
        widths={"Decisión": 24, "Ingrediente": 23, "Pedido actual": 25, "Recomendación": 25, "Cambio sugerido": 32, "Formato de compra": 22, "Proveedor": 25, "Perecedero": 13},
        state_column="Decisión",
    )

    detail_sheet = workbook.add_worksheet("Detalle completo")
    _setup_sheet(detail_sheet)
    _write_title(
        detail_sheet,
        formats,
        f"ORDEN COMPLETA | {branch.upper()}",
        "Incluye productos que necesitan cambios y productos cuya cantidad ya es adecuada.",
        last_column=max(len(detail.columns) - 1, 0),
    )
    _write_dataframe(
        detail_sheet,
        formats,
        detail,
        start_row=4,
        widths={"Decisión": 24, "Ingrediente": 23, "Pedido actual": 25, "Recomendación": 25, "Cambio sugerido": 32, "Formato de compra": 22, "Proveedor": 25, "Perecedero": 13},
        state_column="Decisión",
    )

    audit_sheet = workbook.add_worksheet("Datos de cálculo")
    _setup_sheet(audit_sheet)
    _write_title(
        audit_sheet,
        formats,
        f"EVIDENCIA TÉCNICA | {branch.upper()}",
        "Inventario, proyección, necesidad y método utilizados. No sustituye la revisión humana.",
        last_column=max(len(technical.columns) - 1, 0),
    )
    _write_dataframe(
        audit_sheet,
        formats,
        technical,
        start_row=4,
        widths={str(column): 22 for column in technical.columns},
    )

    workbook.close()
    return output.getvalue()
