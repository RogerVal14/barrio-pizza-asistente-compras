"""Rediseño alternativo en Shiny para Python del asistente de compras.

Esta aplicación conserva la lógica de negocio probada en ``src/`` y ofrece una
segunda interfaz. La aplicación Streamlit original permanece en ``app.py``.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
import re
import unicodedata
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from shiny import App, Inputs, Outputs, Session, reactive, render, ui
from shinywidgets import output_widget, render_plotly

from src.alerts import (
    build_anomaly_alerts,
    build_purchase_alerts,
    build_quality_alerts,
    format_number,
)
from src.data_loader import DataBundle, load_data, read_order_upload
from src.forecasting import forecast_all, week_number
from src.purchasing import build_purchase_review, corrected_order, unknown_order_lines
from src.ui_helpers import (
    answer_local_question,
    dataframe_to_csv_bytes,
    filter_rows,
    friendly_review_table,
)
from src.validation import validate_data


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "datos"
PLOT_COLORS = ["#C65D3A", "#E4A13B", "#708A65", "#57748E", "#8A6D60"]
SEVERITY_COLORS = {
    "Crítica": "#A93535",
    "Alta": "#D9692F",
    "Media": "#D69A32",
    "Baja": "#57748E",
}
SEVERITY_ICONS = {
    "Crítica": "●",
    "Alta": "▲",
    "Media": "◆",
    "Baja": "●",
}
SEVERITY_ORDER = {"Crítica": 0, "Alta": 1, "Media": 2, "Baja": 3}


APP_CSS = """
:root {
  --bp-ink: #2d2925;
  --bp-muted: #6f665f;
  --bp-paper: #fffaf4;
  --bp-panel: #ffffff;
  --bp-soft: #f7eee4;
  --bp-line: #ead9ca;
  --bp-terracotta: #c65d3a;
  --bp-terracotta-dark: #98432c;
  --bp-gold: #dca043;
  --bp-green: #708a65;
  --bp-blue: #57748e;
  --bp-danger: #a93535;
}

body {
  color: var(--bp-ink);
  background: linear-gradient(180deg, #fffaf4 0%, #f8f1e9 100%);
}

.bslib-sidebar-layout > .sidebar {
  background: #2e2723 !important;
  color: #fff7ee;
  border-right: 0 !important;
}

.bslib-sidebar-layout > .sidebar label,
.bslib-sidebar-layout > .sidebar .control-label,
.bslib-sidebar-layout > .sidebar .form-label,
.bslib-sidebar-layout > .sidebar .irs-min,
.bslib-sidebar-layout > .sidebar .irs-max {
  color: #fff7ee !important;
}

.bslib-sidebar-layout > .sidebar .form-text,
.bslib-sidebar-layout > .sidebar small {
  color: #d9cbc0 !important;
}

.bp-side-brand {
  padding: .4rem 0 1rem;
  border-bottom: 1px solid rgba(255,255,255,.13);
  margin-bottom: 1rem;
}

.bp-side-brand .eyebrow {
  color: #e8b56a;
  font-size: .72rem;
  font-weight: 800;
  letter-spacing: .12em;
  text-transform: uppercase;
}

.bp-side-brand h2 {
  margin: .3rem 0 .2rem;
  font-size: 1.3rem;
  color: white;
}

.bp-side-section {
  margin-top: 1rem;
  color: #e8b56a;
  font-size: .75rem;
  font-weight: 800;
  letter-spacing: .1em;
  text-transform: uppercase;
}

.bp-hero {
  position: relative;
  overflow: hidden;
  padding: 1.55rem 1.7rem;
  margin-bottom: 1rem;
  border-radius: 1.25rem;
  color: #fffaf5;
  background:
    radial-gradient(circle at 92% 18%, rgba(228,161,59,.32), transparent 26%),
    linear-gradient(125deg, #332822 0%, #563429 58%, #8f452f 100%);
  box-shadow: 0 18px 44px rgba(74,46,34,.18);
}

.bp-hero::after {
  content: "";
  position: absolute;
  width: 220px;
  height: 220px;
  right: -90px;
  bottom: -120px;
  border: 32px solid rgba(255,255,255,.07);
  border-radius: 50%;
}

.bp-hero .eyebrow {
  color: #f0bd72;
  font-size: .74rem;
  font-weight: 800;
  letter-spacing: .13em;
  text-transform: uppercase;
}

.bp-hero h1 {
  margin: .28rem 0 .38rem;
  font-size: clamp(1.65rem, 3vw, 2.5rem);
  font-weight: 800;
}

.bp-hero p {
  max-width: 820px;
  margin: 0;
  color: #f3e6dc;
  font-size: 1rem;
}

.bp-human {
  display: inline-flex;
  align-items: center;
  gap: .4rem;
  margin-top: .9rem;
  padding: .38rem .68rem;
  border: 1px solid rgba(255,255,255,.25);
  border-radius: 999px;
  background: rgba(255,255,255,.09);
  color: #fff;
  font-size: .8rem;
  font-weight: 700;
}

.bp-source-line {
  margin: -.15rem 0 .9rem;
  color: var(--bp-muted);
  font-size: .82rem;
}

.card, .bslib-card, .value-box {
  border: 1px solid var(--bp-line) !important;
  border-radius: 1rem !important;
  box-shadow: 0 8px 24px rgba(88,62,45,.07) !important;
}

.card-header {
  background: transparent !important;
  border-bottom: 1px solid var(--bp-line) !important;
  color: #4b352d;
  font-weight: 800;
}

.bp-valuebox {
  min-height: 118px;
  background: white !important;
}

.bp-valuebox .value-box-value {
  color: var(--bp-ink);
  font-size: 1.85rem !important;
  font-weight: 850;
}

.bp-valuebox .value-box-title {
  color: var(--bp-muted);
  font-size: .78rem;
  font-weight: 750;
  letter-spacing: .02em;
}

.bp-valuebox .value-box-showcase {
  color: var(--bp-terracotta);
  font-size: 1.35rem;
}

.bp-vb-good { border-top: 4px solid var(--bp-green) !important; }
.bp-vb-risk { border-top: 4px solid var(--bp-danger) !important; }
.bp-vb-warn { border-top: 4px solid var(--bp-gold) !important; }
.bp-vb-info { border-top: 4px solid var(--bp-blue) !important; }
.bp-vb-main { border-top: 4px solid var(--bp-terracotta) !important; }

.bp-alert-stack {
  display: grid;
  gap: .7rem;
}

.bp-alert {
  padding: .9rem 1rem;
  border: 1px solid var(--bp-line);
  border-left: 5px solid var(--bp-blue);
  border-radius: .85rem;
  background: #fff;
}

.bp-alert-critical { border-left-color: var(--bp-danger); background: #fff7f5; }
.bp-alert-high { border-left-color: #d9692f; }
.bp-alert-medium { border-left-color: var(--bp-gold); }
.bp-alert-low { border-left-color: var(--bp-blue); }

.bp-alert-head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: .4rem;
  margin-bottom: .35rem;
  font-weight: 800;
}

.bp-alert-meta {
  margin-top: .45rem;
  color: var(--bp-muted);
  font-size: .82rem;
}

.bp-note, .bp-status {
  padding: .85rem 1rem;
  border: 1px solid var(--bp-line);
  border-left: 4px solid var(--bp-terracotta);
  border-radius: .75rem;
  background: #fff8f0;
}

.bp-status-good { border-left-color: var(--bp-green); background: #f4f8f2; }
.bp-status-warning { border-left-color: var(--bp-gold); background: #fffaee; }
.bp-status-error { border-left-color: var(--bp-danger); background: #fff5f3; }

.bp-section-intro {
  color: var(--bp-muted);
  margin-top: -.25rem;
  margin-bottom: 1rem;
}

.bp-method-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: .8rem;
  margin: .75rem 0 1rem;
}

.bp-method-step {
  padding: .9rem;
  border: 1px solid var(--bp-line);
  border-radius: .8rem;
  background: #fff;
}

.bp-method-step strong {
  display: block;
  color: var(--bp-terracotta-dark);
  margin-bottom: .25rem;
}

.nav-underline .nav-link.active {
  color: var(--bp-terracotta-dark) !important;
  border-bottom-color: var(--bp-terracotta) !important;
}

.btn-primary {
  --bs-btn-bg: var(--bp-terracotta);
  --bs-btn-border-color: var(--bp-terracotta);
  --bs-btn-hover-bg: var(--bp-terracotta-dark);
  --bs-btn-hover-border-color: var(--bp-terracotta-dark);
}

.shiny-data-grid {
  border-radius: .75rem;
  overflow: hidden;
}

@media (max-width: 768px) {
  .bp-hero { padding: 1.15rem; border-radius: .95rem; }
  .bp-hero h1 { font-size: 1.55rem; }
}
"""


def run_pipeline(
    bundle: DataBundle,
    order: pd.DataFrame,
    safety_margin: float,
) -> dict[str, Any]:
    """Ejecuta el mismo pipeline usado por la aplicación principal."""

    validated = validate_data(bundle.catalogo, bundle.historico, bundle.inventario, order)
    forecasts, outliers = forecast_all(validated.historico, validated.combinaciones)
    review = build_purchase_review(validated, forecasts, safety_margin=safety_margin)
    return {
        "validated": validated,
        "forecasts": forecasts,
        "outliers": outliers,
        "review": review,
        "purchase_alerts": build_purchase_alerts(review),
        "quality": build_quality_alerts(validated.incidencias),
        "anomalies": build_anomaly_alerts(outliers, validated.catalogo),
        "unknown_order": unknown_order_lines(validated),
        "corrected": corrected_order(review),
    }


def selected_values(value: object) -> list[str]:
    """Normaliza el valor de un selector simple o múltiple."""

    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    return [str(item) for item in value if str(item)]


def format_display_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Redondea únicamente la copia de presentación y conserva enteros legibles."""

    result = frame.copy()
    for column in result.columns:
        if pd.api.types.is_bool_dtype(result[column]):
            continue
        numeric = pd.to_numeric(result[column], errors="coerce")
        original_non_null = int(result[column].notna().sum())
        if not numeric.notna().any() or int(numeric.notna().sum()) != original_non_null:
            continue
        if numeric.dropna().map(lambda value: float(value).is_integer()).all():
            result[column] = numeric.round().astype("Int64")
        else:
            result[column] = numeric.round(2)
    return result


def apply_review_filters(review: pd.DataFrame, filters: dict[str, list[str]]) -> pd.DataFrame:
    """Aplica los controles laterales a las líneas de revisión."""

    result = review.copy()
    for column, key in [
        ("sucursal", "branches"),
        ("proveedor", "suppliers"),
        ("nombre", "ingredients"),
        ("metodo_proyeccion", "methods"),
    ]:
        selected = filters[key]
        if selected:
            result = result[result[column].isin(selected)]
    if filters["perishability"]:
        labels = result["es_perecedero_bool"].map({True: "Sí", False: "No"})
        result = result[labels.isin(filters["perishability"])]
    return result


def sort_alerts(alerts: pd.DataFrame) -> pd.DataFrame:
    """Ordena alertas por severidad y magnitud sin modificar los datos fuente."""

    if alerts.empty:
        return alerts.copy()
    result = alerts.copy()
    result["_severity_rank"] = result["severidad"].map(SEVERITY_ORDER).fillna(99)
    result["_difference_rank"] = pd.to_numeric(
        result["diferencia_formatos"], errors="coerce"
    ).abs().fillna(0)
    return result.sort_values(
        ["_severity_rank", "_difference_rank"], ascending=[True, False]
    ).drop(columns=["_severity_rank", "_difference_rank"])


def severity_class(value: object) -> str:
    normalized = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    return normalized.lower().replace(" ", "-")


def safe_slug(value: object) -> str:
    normalized = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", normalized.lower()).strip("_") or "proveedor"


def alert_cards(alerts: pd.DataFrame, limit: int = 8) -> ui.TagChild:
    """Construye tarjetas accesibles con texto, no solo con color."""

    visible = sort_alerts(alerts).head(limit)
    if visible.empty:
        return ui.div(
            ui.strong("✓ Sin alertas de compra"),
            ui.div("La selección actual no requiere ajustes de compra."),
            class_="bp-status bp-status-good",
        )
    cards: list[ui.TagChild] = []
    for row in visible.itertuples():
        icon = SEVERITY_ICONS.get(str(row.severidad), "●")
        cards.append(
            ui.div(
                ui.div(
                    ui.span(f"{icon} {row.severidad} · {row.tipo_alerta}"),
                    ui.span(f"{row.sucursal} · {row.ingrediente}"),
                    class_="bp-alert-head",
                ),
                ui.div(str(row.mensaje)),
                ui.div(
                    ui.strong("Acción: "),
                    str(row.accion_recomendada),
                    " · ",
                    ui.strong("Proveedor: "),
                    str(row.proveedor),
                    class_="bp-alert-meta",
                ),
                class_=f"bp-alert bp-alert-{severity_class(row.severidad)}",
            )
        )
    return ui.div(*cards, class_="bp-alert-stack")


def value_card(
    title: str,
    value: object,
    icon: str,
    variant: str,
    detail: str | None = None,
) -> ui.TagChild:
    children: list[ui.TagChild] = []
    if detail:
        children.append(ui.tags.small(detail))
    return ui.value_box(
        title,
        str(value),
        *children,
        showcase=ui.span(icon, aria_hidden="true"),
        class_=f"bp-valuebox bp-vb-{variant}",
        fill=False,
    )


def empty_figure(message: str) -> go.Figure:
    figure = go.Figure()
    figure.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"size": 15, "color": "#6f665f"},
    )
    figure.update_xaxes(visible=False)
    figure.update_yaxes(visible=False)
    figure.update_layout(height=330, margin=dict(t=20, b=20, l=20, r=20))
    return figure


def style_figure(figure: go.Figure, height: int = 360) -> go.Figure:
    figure.update_layout(
        height=height,
        margin=dict(t=35, b=35, l=35, r=25),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Segoe UI, Arial, sans-serif", "color": "#2d2925"},
        legend_title_text="",
    )
    return figure


def normalize_order_quantities(order: pd.DataFrame) -> pd.DataFrame:
    result = order.copy().reset_index(drop=True)
    if "cantidad_formatos" in result.columns:
        numeric = pd.to_numeric(result["cantidad_formatos"], errors="coerce")
        result["cantidad_formatos"] = numeric.where(numeric.notna(), result["cantidad_formatos"])
    return result


def corrected_for_export(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in [
        "cantidad_formatos_original",
        "cantidad_formatos_corregida",
        "diferencia_formatos_corregir",
    ]:
        if column in result:
            result[column] = pd.to_numeric(result[column], errors="coerce").round().astype("Int64")
    return result


BUNDLE = load_data(DATA_DIR)
DEFAULT_ORDER = normalize_order_quantities(BUNDLE.orden)
INITIAL_PIPELINE = run_pipeline(BUNDLE, DEFAULT_ORDER, 0.0)
INITIAL_REVIEW = INITIAL_PIPELINE["review"]
INITIAL_ALERTS = INITIAL_PIPELINE["purchase_alerts"]

BRANCHES = sorted(str(value) for value in INITIAL_REVIEW["sucursal"].dropna().unique())
SUPPLIERS = sorted(str(value) for value in INITIAL_REVIEW["proveedor"].dropna().unique())
INGREDIENTS = sorted(str(value) for value in INITIAL_REVIEW["nombre"].dropna().unique())
METHODS = sorted(str(value) for value in INITIAL_REVIEW["metodo_proyeccion"].dropna().unique())
ALERT_TYPES = sorted(str(value) for value in INITIAL_ALERTS.get("tipo_alerta", pd.Series(dtype=str)).dropna().unique())
SEVERITIES = [
    level for level in SEVERITY_ORDER if level in set(INITIAL_ALERTS.get("severidad", pd.Series(dtype=str)))
]
HISTORICAL_WEEKS = BUNDLE.historico.get("semana", pd.Series(dtype=object)).dropna().astype(str)
MAX_WEEK = max(HISTORICAL_WEEKS, key=week_number) if not HISTORICAL_WEEKS.empty else "sin semana"

INITIAL_OVERORDERS = INITIAL_ALERTS[INITIAL_ALERTS["tipo_alerta"] == "SOBREPEDIDO"].copy()
if not INITIAL_OVERORDERS.empty:
    INITIAL_OVERORDERS["_abs_diff"] = pd.to_numeric(
        INITIAL_OVERORDERS["diferencia_formatos"], errors="coerce"
    ).abs()
    EXAMPLE_INGREDIENT = str(
        INITIAL_OVERORDERS.sort_values("_abs_diff", ascending=False).iloc[0]["ingrediente"]
    )
else:
    EXAMPLE_INGREDIENT = INGREDIENTS[0] if INGREDIENTS else "el ingrediente"

INITIAL_SUPPLIER_TOTALS = (
    INITIAL_REVIEW[INITIAL_REVIEW["formatos_recomendados"].notna()]
    .groupby("proveedor")["formatos_recomendados"]
    .sum()
    .sort_values(ascending=False)
)
EXAMPLE_SUPPLIER = (
    str(INITIAL_SUPPLIER_TOTALS.index[0])
    if not INITIAL_SUPPLIER_TOTALS.empty
    else "el proveedor"
)


def sidebar_ui() -> ui.Sidebar:
    return ui.sidebar(
        ui.div(
            ui.div("CENTRO DE DECISIONES", class_="eyebrow"),
            ui.h2("Barrio Pizza"),
            ui.tags.small(f"Revisión posterior a {MAX_WEEK} · {date.today().strftime('%d/%m/%Y')}"),
            class_="bp-side-brand",
        ),
        ui.div("Escenario", class_="bp-side-section"),
        ui.input_slider(
            "margin_percent",
            "Margen de seguridad simulado",
            min=0,
            max=20,
            value=0,
            step=1,
            post="%",
        ),
        ui.tags.small("Simulación opcional; no pertenece a la fórmula original."),
        ui.div("Filtros de revisión", class_="bp-side-section"),
        ui.input_selectize("filter_branch", "Sucursal", choices=BRANCHES, multiple=True),
        ui.input_selectize("filter_supplier", "Proveedor", choices=SUPPLIERS, multiple=True),
        ui.input_selectize("filter_ingredient", "Ingrediente", choices=INGREDIENTS, multiple=True),
        ui.input_selectize("filter_alert", "Tipo de alerta", choices=ALERT_TYPES, multiple=True),
        ui.input_selectize("filter_severity", "Severidad", choices=SEVERITIES, multiple=True),
        ui.input_selectize(
            "filter_perishable",
            "Perecedero",
            choices=["Sí", "No"],
            multiple=True,
        ),
        ui.input_selectize("filter_method", "Método de proyección", choices=METHODS, multiple=True),
        ui.input_action_button("clear_filters", "Limpiar filtros", class_="btn-outline-light w-100"),
        width=310,
        open="desktop",
        resizable=True,
    )


def methodology_ui() -> ui.TagChild:
    return ui.TagList(
        ui.h3("Metodología transparente"),
        ui.p(
            "La lógica es la misma que en la aplicación principal: robusta, explicable y sin datos inventados.",
            class_="bp-section-intro",
        ),
        ui.div(
            ui.div(ui.strong("1 · Proyección"), "Ordenar S1, S2… y conservar la evidencia original.", class_="bp-method-step"),
            ui.div(ui.strong("2 · Atípicos"), "Mediana, MAD y modified z-score absoluto mayor que 3.5.", class_="bp-method-step"),
            ui.div(ui.strong("3 · Tendencia"), "Regresión lineal solo con R² ≥ 0.80 y cambio relativo ≥ 15%.", class_="bp-method-step"),
            ui.div(ui.strong("4 · Compra"), "Necesidad no negativa y conversión a formatos completos con ceil.", class_="bp-method-step"),
            class_="bp-method-grid",
        ),
        ui.layout_columns(
            ui.card(
                ui.card_header("Fórmulas de compra"),
                ui.tags.ol(
                    ui.tags.li(ui.tags.code("necesidad_base = max(consumo_proyectado - inventario_actual, 0)")),
                    ui.tags.li(ui.tags.code("formatos_recomendados = ceil(necesidad_base / unidad_base_por_formato)")),
                    ui.tags.li(ui.tags.code("cantidad_ordenada_base = formatos_ordenados × unidad_base_por_formato")),
                    ui.tags.li(ui.tags.code("diferencia_formatos = formatos_ordenados - formatos_recomendados")),
                ),
                ui.p("El excedente inevitable dentro del último formato no se clasifica como sobrepedido."),
            ),
            ui.card(
                ui.card_header("Reglas de seguridad"),
                ui.tags.ul(
                    ui.tags.li("Sin inventario, la línea queda como DATO INCOMPLETO."),
                    ui.tags.li("Con una o dos semanas, la confianza es baja."),
                    ui.tags.li("Sin histórico válido, no se fabrica una proyección."),
                    ui.tags.li("Las recomendaciones siempre requieren aprobación humana."),
                ),
            ),
            col_widths=[6, 6],
        ),
        ui.output_ui("margin_method_note"),
        ui.card(
            ui.card_header("Limitaciones conocidas"),
            ui.p(
                "Los archivos no contienen precios, ventas, clientes, lead times ni niveles de servicio. "
                "Esta versión no calcula ahorro monetario, días de inventario o demanda por cliente, y no está conectada a Odoo."
            ),
        ),
    )


app_ui = ui.page_sidebar(
    sidebar_ui(),
    ui.head_content(
        ui.tags.meta(name="viewport", content="width=device-width, initial-scale=1"),
        ui.tags.style(APP_CSS),
    ),
    ui.div(
        ui.div("REVISIÓN SEMANAL DE ABASTECIMIENTO", class_="eyebrow"),
        ui.h1("Barrio Pizza | Asistente Inteligente de Compras"),
        ui.p(
            "Una segunda experiencia construida con Shiny para Python para priorizar decisiones, "
            "investigar excepciones y corregir la orden sin perder trazabilidad."
        ),
        ui.span("◎ Recomendaciones sujetas a aprobación humana", class_="bp-human"),
        class_="bp-hero",
    ),
    ui.div(
        f"Fuente: 4 CSV locales · {len(BRANCHES)} sucursales · "
        f"{BUNDLE.catalogo['ingrediente_id'].nunique()} ingredientes de catálogo · sin API keys",
        class_="bp-source-line",
    ),
    ui.navset_card_underline(
        ui.nav_panel(
            "Resumen ejecutivo",
            ui.output_ui("kpis"),
            ui.layout_columns(
                ui.card(
                    ui.card_header("Alertas por sucursal"),
                    output_widget("alerts_by_branch"),
                    full_screen=True,
                ),
                ui.card(
                    ui.card_header("Alertas por tipo"),
                    output_widget("alerts_by_type"),
                    full_screen=True,
                ),
                col_widths=[7, 5],
            ),
            ui.layout_columns(
                ui.card(
                    ui.card_header("Prioridad para la gerente"),
                    ui.output_ui("priority_alerts"),
                ),
                ui.card(
                    ui.card_header("Líneas sin ajuste requerido"),
                    output_widget("correct_gauge"),
                ),
                col_widths=[8, 4],
            ),
        ),
        ui.nav_panel(
            "Alertas",
            ui.layout_columns(
                ui.div(
                    ui.h3("Alertas accionables"),
                    ui.p("Ordenadas por severidad y magnitud del ajuste.", class_="bp-section-intro"),
                ),
                ui.input_switch("critical_only", "Mostrar solo críticas", False),
                col_widths=[9, 3],
            ),
            ui.output_ui("all_alert_cards"),
            ui.card(
                ui.card_header("Tabla filtrable"),
                ui.output_data_frame("alerts_table"),
                ui.card_footer(
                    ui.download_button("download_alerts", "Descargar alertas filtradas", class_="btn-primary")
                ),
                full_screen=True,
            ),
        ),
        ui.nav_panel(
            "Detalle por sucursal",
            ui.layout_columns(
                ui.input_selectize(
                    "detail_branch",
                    "Sucursal",
                    choices=BRANCHES,
                    selected=BRANCHES[0] if BRANCHES else None,
                ),
                ui.output_ui("detail_ingredient_control"),
                ui.input_switch("compare_simple", "Comparar promedio simple", False),
                col_widths=[4, 5, 3],
            ),
            ui.output_ui("branch_kpis"),
            ui.card(
                ui.card_header("Ingredientes de la sucursal"),
                ui.output_data_frame("branch_review_table"),
                full_screen=True,
            ),
            ui.card(
                ui.card_header("Histórico y proyección"),
                output_widget("history_projection"),
                full_screen=True,
            ),
            ui.output_ui("detail_metrics"),
            ui.output_ui("forecast_method_note"),
        ),
        ui.nav_panel(
            "Simulador de orden",
            ui.h3("Simulador reactivo"),
            ui.p(
                "Carga una orden o edita cantidades. Cada cambio vuelve a ejecutar las validaciones y fórmulas.",
                class_="bp-section-intro",
            ),
            ui.layout_columns(
                ui.card(
                    ui.card_header("Cargar CSV"),
                    ui.input_file(
                        "order_upload",
                        "Nuevo orden_compra_semana.csv",
                        accept=[".csv", "text/csv"],
                        multiple=False,
                        button_label="Seleccionar archivo",
                        placeholder="Ningún archivo seleccionado",
                    ),
                    ui.output_ui("upload_validation"),
                    ui.input_action_button("apply_upload", "Usar esta orden", class_="btn-primary"),
                ),
                ui.card(
                    ui.card_header("Controles"),
                    ui.p("Solo la columna cantidad_formatos puede editarse directamente."),
                    ui.input_action_button("reset_order", "Restablecer orden original", class_="btn-outline-secondary"),
                    ui.output_ui("simulator_status"),
                ),
                col_widths=[7, 5],
            ),
            ui.card(
                ui.card_header("Orden de trabajo"),
                ui.output_data_frame("simulator_grid"),
                ui.card_footer("Doble clic en una celda de cantidad_formatos para editarla."),
                full_screen=True,
            ),
        ),
        ui.nav_panel(
            "Orden corregida",
            ui.h3("Orden corregida por proveedor"),
            ui.p(
                "Incluye el catálogo conocido. Las cantidades no calculables permanecen vacías para revisión humana.",
                class_="bp-section-intro",
            ),
            ui.download_button("download_corrected", "Descargar orden corregida completa", class_="btn-primary"),
            ui.card(
                ui.card_header("Orden completa"),
                ui.output_data_frame("corrected_table"),
                full_screen=True,
            ),
            ui.card(
                ui.card_header("Descargas por proveedor"),
                ui.output_ui("supplier_downloads"),
            ),
            ui.card(
                ui.card_header("Datos pendientes por corregir"),
                ui.output_ui("unknown_note"),
                ui.output_data_frame("unknown_table"),
            ),
        ),
        ui.nav_panel(
            "Calidad de datos",
            ui.h3("Calidad y trazabilidad"),
            ui.p(
                "Las incidencias de datos, las alertas de compra y las anomalías históricas se presentan por separado.",
                class_="bp-section-intro",
            ),
            ui.output_ui("quality_kpis"),
            ui.div(
                ui.strong("Por qué importa: "),
                "una incidencia requiere corrección del dato; una alerta compara orden y recomendación; "
                "una anomalía informa un valor extremo conservando el original.",
                class_="bp-note",
            ),
            ui.accordion(
                ui.accordion_panel("Errores", ui.output_data_frame("quality_errors")),
                ui.accordion_panel("Advertencias y omisiones", ui.output_data_frame("quality_warnings")),
                ui.accordion_panel("Históricos incompletos", ui.output_data_frame("quality_incomplete")),
                ui.accordion_panel("Valores atípicos", ui.output_data_frame("quality_outliers")),
                multiple=True,
                open=["Errores", "Valores atípicos"],
            ),
        ),
        ui.nav_panel("Metodología", methodology_ui()),
        id="main_navigation",
        selected="Resumen ejecutivo",
        full_screen=False,
    ),
    ui.card(
        ui.card_header("Pregúntale a tus datos"),
        ui.p(
            "Asistente local basado en reglas. No es un modelo generativo y no envía información a servicios externos.",
            class_="bp-section-intro",
        ),
        ui.layout_column_wrap(
            ui.input_action_button("suggest_risks", "¿Qué sucursal tiene más riesgos?", class_="btn-outline-secondary"),
            ui.input_action_button("suggest_overorder", f"¿Quién pide demasiado {EXAMPLE_INGREDIENT}?", class_="btn-outline-secondary"),
            ui.input_action_button("suggest_omitted", "¿Qué productos fueron omitidos?", class_="btn-outline-secondary"),
            ui.input_action_button("suggest_supplier", f"¿Qué debo pedirle a {EXAMPLE_SUPPLIER}?", class_="btn-outline-secondary"),
            width="250px",
        ),
        ui.input_text(
            "assistant_question",
            "Pregunta",
            placeholder="Ejemplo: ¿Cuáles sobrepedidos son perecederos?",
        ),
        ui.output_ui("assistant_answer"),
    ),
    title=None,
    window_title="Barrio Pizza | Asistente Inteligente de Compras · Shiny",
    lang="es",
    fillable=False,
)


def server(input: Inputs, output: Outputs, session: Session) -> None:
    working_order = reactive.value(DEFAULT_ORDER.copy())

    def current_filters() -> dict[str, list[str]]:
        return {
            "branches": selected_values(input.filter_branch()),
            "suppliers": selected_values(input.filter_supplier()),
            "ingredients": selected_values(input.filter_ingredient()),
            "alert_types": selected_values(input.filter_alert()),
            "severities": selected_values(input.filter_severity()),
            "perishability": selected_values(input.filter_perishable()),
            "methods": selected_values(input.filter_method()),
        }

    @reactive.calc
    def pipeline() -> dict[str, Any]:
        return run_pipeline(
            BUNDLE,
            working_order(),
            float(input.margin_percent() or 0) / 100.0,
        )

    @reactive.calc
    def filtered_review() -> pd.DataFrame:
        filters = current_filters()
        return apply_review_filters(pipeline()["review"], filters)

    @reactive.calc
    def filtered_alerts() -> pd.DataFrame:
        filters = current_filters()
        return filter_rows(
            pipeline()["purchase_alerts"],
            branches=filters["branches"],
            suppliers=filters["suppliers"],
            ingredients=filters["ingredients"],
            alert_types=filters["alert_types"],
            severities=filters["severities"],
            perishability=filters["perishability"],
            methods=filters["methods"],
        )

    @reactive.calc
    def filtered_quality() -> pd.DataFrame:
        result = pipeline()["quality"].copy()
        branches = current_filters()["branches"]
        if branches and not result.empty:
            result = result[result["sucursal"].isna() | result["sucursal"].isin(branches)]
        return result

    @reactive.effect
    @reactive.event(input.clear_filters)
    def _clear_filters() -> None:
        for control in [
            "filter_branch",
            "filter_supplier",
            "filter_ingredient",
            "filter_alert",
            "filter_severity",
            "filter_perishable",
            "filter_method",
        ]:
            ui.update_selectize(control, selected=[])

    @render.ui
    def kpis() -> ui.TagChild:
        review = filtered_review()
        alerts = filtered_alerts()
        quality = filtered_quality()
        correct = int(review["estado"].isin(["CORRECTO", "SIN NECESIDAD"]).sum())
        risks = int((alerts["tipo_alerta"] == "FALTANTE").sum()) if not alerts.empty else 0
        omitted = int((alerts["tipo_alerta"] == "OMITIDO").sum()) if not alerts.empty else 0
        overorders = int((alerts["tipo_alerta"] == "SOBREPEDIDO").sum()) if not alerts.empty else 0
        errors = int((quality["nivel"] == "Error").sum()) if not quality.empty else 0
        affected = set(alerts["sucursal"].dropna()) if not alerts.empty else set()
        if not quality.empty:
            affected.update(quality.loc[quality["nivel"] == "Error", "sucursal"].dropna())
        return ui.layout_column_wrap(
            value_card("Líneas revisadas", len(review), "▤", "main"),
            value_card("Líneas correctas", correct, "✓", "good"),
            value_card("Riesgos de quiebre", risks, "!", "risk"),
            value_card("Productos omitidos", omitted, "∅", "risk"),
            value_card("Sobrepedidos", overorders, "↗", "warn"),
            value_card("Errores de datos", errors, "?", "info"),
            value_card("Sucursales afectadas", len(affected), "⌂", "info"),
            width="190px",
        )

    @render_plotly
    def alerts_by_branch() -> go.Figure | None:
        if input.main_navigation() != "Resumen ejecutivo":
            return None
        alerts = filtered_alerts()
        if alerts.empty:
            return empty_figure("No hay alertas para graficar")
        counts = alerts.groupby(["sucursal", "severidad"], as_index=False).size()
        figure = px.bar(
            counts,
            x="sucursal",
            y="size",
            color="severidad",
            text="size",
            labels={"sucursal": "Sucursal", "size": "Alertas", "severidad": "Severidad"},
            color_discrete_map=SEVERITY_COLORS,
            category_orders={"severidad": list(SEVERITY_ORDER)},
        )
        figure.update_traces(textposition="outside")
        return style_figure(figure)

    @render_plotly
    def alerts_by_type() -> go.Figure | None:
        if input.main_navigation() != "Resumen ejecutivo":
            return None
        alerts = filtered_alerts()
        if alerts.empty:
            return empty_figure("No hay alertas para graficar")
        counts = alerts["tipo_alerta"].value_counts().rename_axis("tipo").reset_index(name="cantidad")
        figure = px.pie(
            counts,
            names="tipo",
            values="cantidad",
            hole=0.58,
            color_discrete_sequence=PLOT_COLORS,
        )
        figure.update_traces(textinfo="label+value")
        return style_figure(figure)

    @render_plotly
    def correct_gauge() -> go.Figure | None:
        if input.main_navigation() != "Resumen ejecutivo":
            return None
        review = filtered_review()
        correct = int(review["estado"].isin(["CORRECTO", "SIN NECESIDAD"]).sum())
        percentage = 100.0 * correct / len(review) if len(review) else 0.0
        figure = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=percentage,
                number={"suffix": "%", "valueformat": ".1f"},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": "#708a65"},
                    "steps": [
                        {"range": [0, 60], "color": "#f5d6cf"},
                        {"range": [60, 85], "color": "#fbe8bf"},
                        {"range": [85, 100], "color": "#dde8d9"},
                    ],
                },
            )
        )
        return style_figure(figure, height=305)

    @render.ui
    def priority_alerts() -> ui.TagChild:
        return alert_cards(filtered_alerts(), limit=5)

    @reactive.calc
    def visible_alerts() -> pd.DataFrame:
        alerts = filtered_alerts()
        if input.critical_only():
            alerts = alerts[alerts["severidad"] == "Crítica"]
        return sort_alerts(alerts)

    @render.ui
    def all_alert_cards() -> ui.TagChild:
        return alert_cards(visible_alerts(), limit=20)

    @render.data_frame
    def alerts_table() -> render.DataGrid:
        columns = [
            "severidad",
            "tipo_alerta",
            "sucursal",
            "ingrediente",
            "proveedor",
            "es_perecedero",
            "formato_compra",
            "formatos_ordenados",
            "cantidad_ordenada_base",
            "formatos_recomendados",
            "cantidad_recomendada_base",
            "diferencia_formatos",
            "unidad_base",
            "razon",
            "accion_recomendada",
        ]
        alerts = visible_alerts()
        table = alerts[columns].copy() if not alerts.empty else pd.DataFrame(columns=columns)
        return render.DataGrid(
            format_display_frame(table),
            width="100%",
            height="500px",
            filters=True,
            summary="Viendo filas {start} a {end} de {total}",
        )

    @render.download_button(filename="alertas_compra_filtradas.csv", media_type="text/csv")
    def download_alerts():
        yield dataframe_to_csv_bytes(visible_alerts())

    @render.ui
    def detail_ingredient_control() -> ui.TagChild:
        review = pipeline()["review"]
        branch = input.detail_branch()
        names = (
            review.loc[review["sucursal"] == branch, "nombre"]
            .dropna()
            .sort_values()
            .astype(str)
            .unique()
            .tolist()
        )
        return ui.input_selectize(
            "detail_ingredient",
            "Ingrediente para analizar",
            choices=names,
            selected=names[0] if names else None,
        )

    @reactive.calc
    def detail_context() -> tuple[pd.Series | None, pd.Series | None]:
        review = pipeline()["review"]
        forecasts = pipeline()["forecasts"]
        rows = review[
            (review["sucursal"] == input.detail_branch())
            & (review["nombre"] == input.detail_ingredient())
        ]
        if rows.empty:
            return None, None
        selected = rows.iloc[0]
        forecast_rows = forecasts[
            (forecasts["sucursal"] == selected["sucursal"])
            & (forecasts["ingrediente_id"] == selected["ingrediente_id"])
        ]
        return selected, forecast_rows.iloc[0] if not forecast_rows.empty else None

    @render.ui
    def branch_kpis() -> ui.TagChild:
        review = pipeline()["review"]
        branch_review = review[review["sucursal"] == input.detail_branch()]
        alerts_count = int(branch_review["estado"].isin(["OMITIDO", "FALTANTE", "SOBREPEDIDO"]).sum())
        return ui.layout_column_wrap(
            value_card("Ingredientes revisados", len(branch_review), "▤", "main"),
            value_card("Alertas de compra", alerts_count, "!", "risk"),
            value_card(
                "Líneas correctas",
                int(branch_review["estado"].isin(["CORRECTO", "SIN NECESIDAD"]).sum()),
                "✓",
                "good",
            ),
            value_card("Datos incompletos", int((branch_review["estado"] == "DATO INCOMPLETO").sum()), "?", "info"),
            width="230px",
        )

    @render.data_frame
    def branch_review_table() -> render.DataGrid:
        review = pipeline()["review"]
        branch_review = review[review["sucursal"] == input.detail_branch()]
        return render.DataGrid(
            format_display_frame(friendly_review_table(branch_review)),
            width="100%",
            height="420px",
            filters=True,
            summary="Viendo filas {start} a {end} de {total}",
        )

    @render_plotly
    def history_projection() -> go.Figure | None:
        if input.main_navigation() != "Detalle por sucursal":
            return None
        selected, forecast = detail_context()
        if selected is None or forecast is None:
            return empty_figure("Selecciona una sucursal y un ingrediente")
        validated = pipeline()["validated"]
        history = validated.historico[
            (validated.historico["sucursal"] == selected["sucursal"])
            & (validated.historico["ingrediente_id"] == selected["ingrediente_id"])
        ].copy()
        history["semana_numero"] = history["semana"].map(week_number)
        history["consumo_numerico"] = pd.to_numeric(history["consumo_unidad_base"], errors="coerce")
        history = history.sort_values("semana_numero")
        figure = go.Figure()
        figure.add_trace(
            go.Scatter(
                x=history["semana"],
                y=history["consumo_numerico"],
                mode="lines+markers",
                name="Consumo observado",
                line={"color": "#57748e", "width": 3},
                marker={"size": 9},
                hovertemplate="%{x}: %{y}<extra></extra>",
            )
        )
        outliers = pipeline()["outliers"]
        selected_outliers = outliers[
            (outliers["sucursal"] == selected["sucursal"])
            & (outliers["ingrediente_id"] == selected["ingrediente_id"])
        ]
        if not selected_outliers.empty:
            figure.add_trace(
                go.Scatter(
                    x=selected_outliers["semana"],
                    y=selected_outliers["consumo_unidad_base"],
                    mode="markers+text",
                    text=["Atípico"] * len(selected_outliers),
                    textposition="top center",
                    name="Valor atípico",
                    marker={"size": 15, "symbol": "x", "color": "#a93535"},
                )
            )
        if pd.notna(forecast["consumo_proyectado"]):
            next_week = f"S{int(forecast['semana_proyectada_numero'])}"
            figure.add_trace(
                go.Scatter(
                    x=[next_week],
                    y=[forecast["consumo_proyectado"]],
                    mode="markers+text",
                    text=["Proyección"],
                    textposition="top center",
                    name="Proyección robusta",
                    marker={"size": 15, "symbol": "diamond", "color": "#c65d3a"},
                )
            )
        if input.compare_simple() and pd.notna(forecast["promedio_simple_6s"]):
            simple = float(forecast["promedio_simple_6s"])
            figure.add_hline(
                y=simple,
                line_dash="dot",
                line_color="#dca043",
                annotation_text=f"Promedio simple: {format_number(simple)}",
            )
        figure.update_layout(
            xaxis_title="Semana",
            yaxis_title=f"Consumo ({selected['unidad_base']})",
            hovermode="x unified",
        )
        return style_figure(figure, height=445)

    @render.ui
    def detail_metrics() -> ui.TagChild:
        selected, _ = detail_context()
        if selected is None:
            return ui.div("No hay una línea seleccionada.", class_="bp-status bp-status-warning")
        unit = str(selected["unidad_base"])
        ordered = int(selected["formatos_ordenados"]) if pd.notna(selected["formatos_ordenados"]) else "—"
        recommended = int(selected["formatos_recomendados"]) if pd.notna(selected["formatos_recomendados"]) else "—"
        return ui.layout_column_wrap(
            value_card("Inventario", f"{format_number(selected['inventario_actual'])} {unit}", "I", "info"),
            value_card("Proyección", f"{format_number(selected['consumo_proyectado'])} {unit}", "P", "main"),
            value_card("Necesidad", f"{format_number(selected['necesidad_base'])} {unit}", "N", "warn"),
            value_card("Orden", f"{ordered} formatos", "O", "info"),
            value_card("Recomendación", f"{recommended} formatos", "R", "good"),
            width="200px",
        )

    @render.ui
    def forecast_method_note() -> ui.TagChild:
        _, forecast = detail_context()
        if forecast is None:
            return ui.div()
        return ui.div(
            ui.strong(f"Método: {forecast['metodo_proyeccion']} · Confianza: {forecast['nivel_confianza']}"),
            ui.br(),
            str(forecast["explicacion_metodo"]),
            class_="bp-note",
        )

    @reactive.calc
    def uploaded_order_result() -> tuple[pd.DataFrame | None, str | None]:
        files = input.order_upload()
        if not files:
            return None, None
        try:
            with Path(files[0]["datapath"]).open("rb") as uploaded:
                return read_order_upload(uploaded), None
        except Exception as exc:  # El mensaje se presenta en la interfaz.
            return None, str(exc)

    @render.ui
    def upload_validation() -> ui.TagChild:
        order, error = uploaded_order_result()
        if error:
            return ui.div(f"No fue posible leer el archivo: {error}", class_="bp-status bp-status-error")
        if order is None:
            return ui.div("Selecciona un CSV para validarlo antes de usarlo.", class_="bp-status")
        validated = validate_data(BUNDLE.catalogo, BUNDLE.historico, BUNDLE.inventario, order)
        schema_errors = validated.incidencias[validated.incidencias["codigo"] == "COLUMNA_AUSENTE"]
        if not schema_errors.empty:
            return ui.div("Faltan columnas obligatorias; el archivo no puede usarse.", class_="bp-status bp-status-error")
        errors = int((validated.incidencias["nivel"] == "Error").sum())
        if errors:
            return ui.div(
                f"Esquema válido con {errors} incidencias. Las líneas afectadas se conservarán como datos pendientes.",
                class_="bp-status bp-status-warning",
            )
        return ui.div(f"Archivo válido: {len(order)} líneas listas para simular.", class_="bp-status bp-status-good")

    @reactive.effect
    @reactive.event(input.apply_upload)
    def _apply_uploaded_order() -> None:
        order, error = uploaded_order_result()
        if error or order is None:
            ui.notification_show("Primero selecciona un CSV válido.", type="error")
            return
        validated = validate_data(BUNDLE.catalogo, BUNDLE.historico, BUNDLE.inventario, order)
        if (validated.incidencias["codigo"] == "COLUMNA_AUSENTE").any():
            ui.notification_show("El archivo no puede usarse: faltan columnas obligatorias.", type="error")
            return
        working_order.set(normalize_order_quantities(order))
        ui.notification_show("La orden cargada ya está activa en el simulador.", type="message")

    @reactive.effect
    @reactive.event(input.reset_order)
    def _reset_order() -> None:
        working_order.set(DEFAULT_ORDER.copy())
        ui.notification_show("Se restauró la orden original.", type="message")

    @render.data_frame
    def simulator_grid() -> render.DataGrid:
        return render.DataGrid(
            working_order(),
            width="100%",
            height="560px",
            filters=True,
            editable=True,
            summary="Viendo filas {start} a {end} de {total}",
        )

    @simulator_grid.set_patch_fn
    def _simulator_patch(*, patch: render.CellPatch):
        current = working_order().copy()
        row_index = int(patch["row_index"])
        column_index = int(patch["column_index"])
        column = str(current.columns[column_index])
        previous = current.iat[row_index, column_index]
        if column != "cantidad_formatos":
            ui.notification_show("Solo puede editarse cantidad_formatos.", type="warning")
            return previous
        numeric = pd.to_numeric(pd.Series([patch["value"]]), errors="coerce").iloc[0]
        if pd.isna(numeric) or float(numeric) < 0 or not float(numeric).is_integer():
            ui.notification_show("La cantidad debe ser un entero mayor o igual que cero.", type="error")
            return previous
        value = int(numeric)
        current.iat[row_index, column_index] = value
        working_order.set(current)
        return value

    @render.ui
    def simulator_status() -> ui.TagChild:
        quality = pipeline()["quality"]
        errors = quality[quality["nivel"] == "Error"] if not quality.empty else quality
        alerts = pipeline()["purchase_alerts"]
        if errors.empty:
            return ui.div(
                f"{len(working_order())} líneas · {len(alerts)} alertas de compra · sin errores bloqueantes añadidos.",
                class_="bp-status bp-status-good",
            )
        return ui.div(
            f"{len(errors)} errores de datos permanecen visibles para corrección humana.",
            class_="bp-status bp-status-warning",
        )

    @reactive.calc
    def corrected_data() -> pd.DataFrame:
        return corrected_for_export(pipeline()["corrected"])

    @render.data_frame
    def corrected_table() -> render.DataGrid:
        return render.DataGrid(
            format_display_frame(corrected_data()),
            width="100%",
            height="540px",
            filters=True,
            summary="Viendo filas {start} a {end} de {total}",
        )

    @render.download_button(filename="orden_corregida_completa.csv", media_type="text/csv")
    def download_corrected():
        yield dataframe_to_csv_bytes(corrected_data())

    @render.ui
    def supplier_downloads() -> ui.TagChild:
        corrected = corrected_data()
        buttons = []
        for supplier in sorted(corrected["proveedor"].dropna().astype(str).unique()):
            count = len(corrected[corrected["proveedor"] == supplier])
            buttons.append(
                ui.download_button(
                    f"download_supplier_{safe_slug(supplier)}",
                    f"{supplier} · {count} líneas",
                    class_="btn-outline-secondary",
                )
            )
        return ui.layout_column_wrap(*buttons, width="260px") if buttons else ui.div("No hay proveedores disponibles.")

    def register_supplier_download(supplier: str) -> None:
        download_id = f"download_supplier_{safe_slug(supplier)}"

        @output(id=download_id)
        @render.download_button(
            filename=lambda: f"orden_{safe_slug(supplier)}.csv",
            media_type="text/csv",
        )
        def _download_supplier():
            frame = corrected_data()
            yield dataframe_to_csv_bytes(frame[frame["proveedor"] == supplier])

    for supplier_name in SUPPLIERS:
        register_supplier_download(supplier_name)

    @render.ui
    def unknown_note() -> ui.TagChild:
        unknown = pipeline()["unknown_order"]
        if unknown.empty:
            return ui.div("No hay ingredientes desconocidos pendientes.", class_="bp-status bp-status-good")
        return ui.div(
            "Estas líneas no se incluyen en órdenes a proveedores porque no existe metadata confiable en el catálogo.",
            class_="bp-status bp-status-error",
        )

    @render.data_frame
    def unknown_table() -> render.DataGrid:
        return render.DataGrid(
            format_display_frame(pipeline()["unknown_order"]),
            width="100%",
            filters=False,
            summary="Viendo filas {start} a {end} de {total}",
        )

    @render.ui
    def quality_kpis() -> ui.TagChild:
        issues = filtered_quality()
        anomalies = pipeline()["anomalies"]
        return ui.layout_column_wrap(
            value_card("Errores", int((issues["nivel"] == "Error").sum()) if not issues.empty else 0, "×", "risk"),
            value_card("Advertencias", int((issues["nivel"] == "Advertencia").sum()) if not issues.empty else 0, "!", "warn"),
            value_card(
                "Productos desconocidos",
                int((issues["codigo"] == "INGREDIENTE_DESCONOCIDO").sum()) if not issues.empty else 0,
                "?",
                "info",
            ),
            value_card("Atípicos históricos", len(anomalies), "◇", "info"),
            width="230px",
        )

    def quality_grid(frame: pd.DataFrame, height: str = "360px") -> render.DataGrid:
        return render.DataGrid(
            format_display_frame(frame),
            width="100%",
            height=height,
            filters=True,
            summary="Viendo filas {start} a {end} de {total}",
        )

    @render.data_frame
    def quality_errors() -> render.DataGrid:
        issues = filtered_quality()
        return quality_grid(issues[issues["nivel"] == "Error"] if not issues.empty else issues)

    @render.data_frame
    def quality_warnings() -> render.DataGrid:
        issues = filtered_quality()
        return quality_grid(issues[issues["nivel"] == "Advertencia"] if not issues.empty else issues)

    @render.data_frame
    def quality_incomplete() -> render.DataGrid:
        issues = filtered_quality()
        incomplete = issues[
            issues["codigo"].isin(["HISTORICO_INCOMPLETO", "HISTORICO_FALTANTE"])
        ] if not issues.empty else issues
        return quality_grid(incomplete)

    @render.data_frame
    def quality_outliers() -> render.DataGrid:
        anomalies = pipeline()["anomalies"]
        columns = [
            "sucursal",
            "nombre",
            "semana",
            "consumo_unidad_base",
            "unidad_base",
            "mediana",
            "mad",
            "modified_z_score",
            "excluido_proyeccion",
            "detalle",
        ]
        table = anomalies[columns] if not anomalies.empty else pd.DataFrame(columns=columns)
        return quality_grid(table)

    @render.ui
    def margin_method_note() -> ui.TagChild:
        margin = int(input.margin_percent() or 0)
        if margin:
            return ui.div(
                f"Simulación activa: se aplica +{margin}% sobre la proyección. Este ajuste no forma parte de la fórmula original.",
                class_="bp-status bp-status-warning",
            )
        return ui.div(
            "Margen de seguridad 0%: la simulación coincide con la fórmula original.",
            class_="bp-status bp-status-good",
        )

    suggestions = {
        "suggest_risks": "¿Qué sucursal tiene más riesgos de quiebre?",
        "suggest_overorder": f"¿Quién está pidiendo demasiado {EXAMPLE_INGREDIENT}?",
        "suggest_omitted": "¿Qué productos fueron omitidos?",
        "suggest_supplier": f"¿Qué debo pedirle a {EXAMPLE_SUPPLIER}?",
    }

    def register_suggestion(control: str, question: str) -> None:
        @reactive.effect
        @reactive.event(input[control])
        def _set_question() -> None:
            ui.update_text("assistant_question", value=question)

    for control_id, suggested_question in suggestions.items():
        register_suggestion(control_id, suggested_question)

    @render.ui
    def assistant_answer() -> ui.TagChild:
        question = str(input.assistant_question() or "").strip()
        if not question:
            return ui.div("Escribe una pregunta o usa una de las sugerencias.", class_="bp-status")
        current = pipeline()
        answer = answer_local_question(
            question,
            current["review"],
            current["purchase_alerts"],
            current["quality"],
            current["forecasts"],
        )
        return ui.div(ui.strong("Respuesta: "), answer, class_="bp-note")


app = App(app_ui, server)
