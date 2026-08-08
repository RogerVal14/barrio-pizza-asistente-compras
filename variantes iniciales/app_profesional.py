"""Centro ejecutivo de compras de Barrio Pizza.

Variante visual independiente de ``app.py``. Reutiliza los mismos módulos de
validación, proyección, compras, alertas y benchmarking; únicamente cambia la
arquitectura de información y la presentación del producto.

Ejecución::

    streamlit run app_profesional.py
"""

from __future__ import annotations

from datetime import date
from html import escape
from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.alerts import (
    build_anomaly_alerts,
    build_purchase_alerts,
    build_quality_alerts,
    format_number,
    purchase_format_phrase,
)
from src.benchmarking import (
    detect_cross_branch_order_anomalies,
    scope_cross_branch_behaviors,
    summarize_attention_overlap,
)
from src.data_loader import DataBundle, load_data, read_order_upload
from src.forecasting import forecast_all, week_number
from src.purchasing import build_purchase_review, corrected_order, unknown_order_lines
from src.reporting import build_alerts_excel, build_branch_excel
from src.ui_helpers import answer_local_question, dataframe_to_csv_bytes, friendly_review_table
from src.validation import validate_data


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "datos"
SEVERITY_ORDER = ["Crítica", "Alta", "Media", "Baja"]
STATUS_COLORS = {
    "OMITIDO": "#CF2F2C",
    "FALTANTE": "#E65D32",
    "SOBREPEDIDO": "#D98E2B",
    "CORRECTO": "#3F7652",
    "SIN NECESIDAD": "#5C6F7B",
    "DATO INCOMPLETO": "#765A92",
}
STATUS_BUSINESS_LABELS = {
    "CORRECTO": "✅ No necesita cambios",
    "SIN NECESIDAD": "✅ No necesita cambios",
    "FALTANTE": "🟠 Hay que pedir más",
    "OMITIDO": "🔴 No se incluyó en la orden",
    "SOBREPEDIDO": "🟡 Se pidió de más",
    "DATO INCOMPLETO": "⚠️ Faltan datos para decidir",
}
CHART_COLORS = ["#CF2F2C", "#231F20", "#D98E2B", "#3F7652", "#456A80", "#765A92"]


st.set_page_config(
    page_title="Barrio Pizza | Asistente Inteligente de Compras",
    page_icon="🍕",
    layout="wide",
    initial_sidebar_state="auto",
)


PROFESSIONAL_CSS = """
<style>
:root {
  --ops-ink: #231f20;
  --ops-muted: #706a65;
  --ops-line: #d8d0c7;
  --ops-paper: #fffdf9;
  --ops-canvas: #f2ece5;
  --ops-red: #cf2f2c;
  --ops-red-soft: #fbe8e5;
  --ops-amber: #d98e2b;
  --ops-green: #3f7652;
  --ops-blue: #456a80;
  --ops-purple: #765a92;
  --ops-radius: 18px;
  --ops-shadow: 0 18px 44px rgba(35, 31, 32, .09);
  --ops-font-display: "Arial Narrow", "Roboto Condensed", Impact, sans-serif;
  --ops-font-body: "Aptos", "Segoe UI", Arial, sans-serif;
  --ops-pizza-cursor: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='32' height='32' viewBox='0 0 32 32'%3E%3Cpath d='M2.5 2.5 L29 11.5 Q25 23 12 29 Z' fill='%23F5C451' stroke='%236B351D' stroke-width='2' stroke-linejoin='round'/%3E%3Cpath d='M29 11.5 Q25 23 12 29' fill='none' stroke='%23C96A2B' stroke-width='5' stroke-linecap='round'/%3E%3Ccircle cx='13' cy='11' r='2.6' fill='%23CF2F2C' stroke='%239E211F' stroke-width='.7'/%3E%3Ccircle cx='20' cy='16' r='3' fill='%23CF2F2C' stroke='%239E211F' stroke-width='.7'/%3E%3Ccircle cx='13.5' cy='21' r='2.5' fill='%23CF2F2C' stroke='%239E211F' stroke-width='.7'/%3E%3Ccircle cx='18.8' cy='15' r='.55' fill='%237A1818'/%3E%3Ccircle cx='21.2' cy='16.7' r='.55' fill='%237A1818'/%3E%3Cpath d='M6 6 L12 10 M7 9 L10 12' stroke='%23FFF1B8' stroke-width='1.25' stroke-linecap='round' opacity='.9'/%3E%3C/svg%3E") 2 2, default;
}

html, body, [class*="css"] {
  font-family: var(--ops-font-body);
}

.stApp, .stApp * {
  cursor: var(--ops-pizza-cursor) !important;
}

.stApp {
  color: var(--ops-ink);
  background:
    radial-gradient(circle at 100% 0, rgba(207, 47, 44, .09), transparent 32rem),
    linear-gradient(90deg, rgba(35, 31, 32, .025) 1px, transparent 1px),
    var(--ops-canvas);
  background-size: auto, 36px 36px, auto;
}

[data-testid="stAppViewContainer"] > .main .block-container {
  max-width: 1560px;
  padding: 1.25rem 2rem 5rem;
}

[data-testid="stHeader"] {
  background: rgba(242, 236, 229, .88);
  border-bottom: 1px solid rgba(23, 21, 19, .07);
  backdrop-filter: blur(16px);
}
[data-testid="stToolbar"] {
  visibility: visible;
  background: transparent;
}
[data-testid="stAppDeployButton"],
[data-testid="stToolbarActions"],
[data-testid="stMainMenu"] {
  display: none;
}
[data-testid="stExpandSidebarButton"] {
  visibility: visible !important;
  display: inline-flex;
  align-items: center;
  gap: .35rem;
  width: auto;
  height: 2.5rem;
  padding: 0 .85rem;
  color: #fff;
  background: var(--ops-red);
  border: 1px solid var(--ops-red);
  border-radius: 999px;
  box-shadow: 0 8px 20px rgba(35,31,32,.18);
}
[data-testid="stExpandSidebarButton"]::after {
  content: "Filtros";
  color: #fff;
  font-family: var(--ops-font-body);
  font-size: .64rem;
  font-weight: 850;
  letter-spacing: .08em;
  text-transform: uppercase;
}
[data-testid="stExpandSidebarButton"] span,
[data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"] {
  color: #fff !important;
}
[data-testid="stSidebarCollapseButton"] {
  visibility: visible !important;
}
[data-testid="stSidebarCollapseButton"] button span,
[data-testid="stSidebarCollapseButton"] button [data-testid="stIconMaterial"] {
  color: rgba(255,255,255,.82) !important;
}

[data-testid="stSidebar"] {
  background:
    radial-gradient(circle at 20% 4%, rgba(207, 47, 44, .22), transparent 12rem),
    var(--ops-ink);
  border-right: 1px solid rgba(255, 255, 255, .08);
}

[data-testid="stSidebar"] * { color: #fffdf9; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { color: rgba(255,255,255,.58); }
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.12); }
[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] [data-baseweb="input"] > div,
[data-testid="stSidebar"] input {
  color: #fffdf9;
  background: rgba(255,255,255,.07);
  border-color: rgba(255,255,255,.16);
}

.ops-brand {
  position: relative;
  margin: .2rem 0 1.5rem;
  padding: .25rem 0 1.25rem;
  border-bottom: 1px solid rgba(255,255,255,.12);
}
.ops-brand::after {
  content: "";
  position: absolute;
  right: 0;
  bottom: -2px;
  width: 54px;
  height: 3px;
  background: var(--ops-red);
}
.ops-brand__word {
  display: block;
  color: #fff;
  font-family: var(--ops-font-display);
  font-size: 1.95rem;
  font-weight: 900;
  letter-spacing: .01em;
  line-height: .9;
  text-transform: uppercase;
}
.ops-brand__meta {
  display: block;
  margin-top: .65rem;
  color: rgba(255,255,255,.58);
  font-size: .63rem;
  font-weight: 700;
  letter-spacing: .18em;
  text-transform: uppercase;
}

.ops-side-note {
  padding: .85rem .9rem;
  color: rgba(255,255,255,.72);
  background: rgba(255,255,255,.055);
  border: 1px solid rgba(255,255,255,.1);
  border-radius: 11px;
  font-size: .76rem;
  line-height: 1.45;
}
.ops-side-note b { color: #fff; }
.ops-live {
  display: inline-block;
  width: 8px;
  height: 8px;
  margin-right: .45rem;
  background: #4bc38a;
  border-radius: 50%;
  box-shadow: 0 0 0 4px rgba(75,195,138,.12);
}

.ops-header {
  isolation: isolate;
  position: relative;
  overflow: hidden;
  display: flex;
  gap: 1.5rem;
  align-items: center;
  justify-content: space-between;
  min-height: 250px;
  margin: .25rem 0 1rem;
  padding: 1.75rem clamp(1.5rem, 3.4vw, 2.75rem);
  color: #fff;
  background:
    linear-gradient(112deg, rgba(35,31,32,.99) 0%, rgba(35,31,32,.96) 58%, rgba(63,35,26,.94) 100%),
    repeating-linear-gradient(-20deg, transparent 0 18px, rgba(255,255,255,.04) 18px 20px);
  border: 1px solid rgba(255,255,255,.08);
  border-radius: 22px;
  box-shadow: 0 24px 60px rgba(35,31,32,.18);
}
.ops-header::before {
  content: "";
  position: absolute;
  z-index: -1;
  right: -68px;
  bottom: -125px;
  width: 275px;
  height: 275px;
  border: 42px solid var(--ops-red);
  border-radius: 50%;
}
.ops-header::after {
  content: "BARRIO";
  position: absolute;
  z-index: -1;
  top: -.35rem;
  right: .75rem;
  color: rgba(255,255,255,.035);
  font-family: var(--ops-font-display);
  font-size: clamp(6rem, 14vw, 12rem);
  font-weight: 900;
  letter-spacing: -.055em;
  line-height: 1;
}
.ops-eyebrow {
  margin-bottom: .45rem;
  color: var(--ops-red);
  font-size: .72rem;
  font-weight: 850;
  letter-spacing: .2em;
  text-transform: uppercase;
}
.ops-header h1 {
  max-width: 820px;
  margin: 0;
  padding: 0;
  color: #fff;
  font-family: var(--ops-font-display);
  font-size: clamp(2.7rem, 4.4vw, 4.4rem);
  font-weight: 900;
  letter-spacing: -.025em;
  line-height: .88;
  text-transform: uppercase;
}
.ops-header h1 .ops-accent {
  color: var(--ops-red);
}
.ops-header p {
  max-width: 680px;
  margin: 1rem 0 0;
  color: rgba(255,255,255,.72);
  font-size: .95rem;
  line-height: 1.55;
}
.ops-review {
  min-width: 280px;
  max-width: 330px;
  padding: 1.05rem 1.1rem;
  background: rgba(255,255,255,.08);
  border: 1px solid rgba(255,255,255,.18);
  border-radius: 16px;
  box-shadow: none;
  backdrop-filter: blur(10px);
}
.ops-review__label {
  color: rgba(255,255,255,.58);
  font-size: .66rem;
  font-weight: 800;
  letter-spacing: .14em;
  text-transform: uppercase;
}
.ops-review__value { margin-top: .35rem; color: #fff; font-size: .92rem; font-weight: 760; line-height: 1.45; }
.ops-review__human {
  margin-top: .75rem;
  padding-top: .7rem;
  color: #fff;
  border-top: 1px solid rgba(255,255,255,.14);
  font-size: .7rem;
  font-weight: 760;
}
.ops-review__human::first-letter { color: var(--ops-red); }

.ops-section-head {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 1rem;
  margin: 2rem 0 1rem;
}
.ops-section-head h2 {
  margin: 0;
  padding: 0;
  color: var(--ops-ink);
  font-family: var(--ops-font-display);
  font-size: clamp(1.9rem, 3vw, 2.65rem);
  font-weight: 900;
  letter-spacing: -.015em;
  line-height: .95;
  text-transform: uppercase;
}
.ops-section-head p { max-width: 760px; margin: .45rem 0 0; color: var(--ops-muted); font-size: .84rem; }
.ops-kicker {
  color: var(--ops-red);
  font-size: .65rem;
  font-weight: 820;
  letter-spacing: .19em;
  text-transform: uppercase;
}

.ops-metric {
  position: relative;
  overflow: hidden;
  min-height: 132px;
  padding: 1.1rem 1.15rem 1.15rem;
  background: var(--ops-paper);
  border: 1px solid rgba(35,31,32,.14);
  border-radius: var(--ops-radius);
  box-shadow: 0 10px 26px rgba(35,31,32,.055);
}
.ops-metric::after {
  content: "";
  position: absolute;
  right: -18px;
  bottom: -27px;
  width: 72px;
  height: 72px;
  border: 12px solid var(--tone-color, var(--ops-blue));
  border-radius: 50%;
  opacity: .12;
}
.ops-metric[data-tone="danger"] { --tone-color: var(--ops-red); }
.ops-metric[data-tone="warning"] { --tone-color: var(--ops-amber); }
.ops-metric[data-tone="success"] { --tone-color: var(--ops-green); }
.ops-metric[data-tone="neutral"] { --tone-color: var(--ops-blue); }
.ops-metric__label {
  color: var(--ops-muted);
  font-size: .67rem;
  font-weight: 820;
  letter-spacing: .12em;
  text-transform: uppercase;
}
.ops-metric__value {
  margin: .5rem 0 .25rem;
  color: var(--ops-ink);
  font-family: var(--ops-font-display);
  font-size: 2.55rem;
  font-weight: 900;
  letter-spacing: -.055em;
  line-height: 1;
}
.ops-metric__note { color: var(--ops-muted); font-size: .72rem; line-height: 1.35; }

.ops-purchase-facts {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 1rem;
  margin: 1rem 0 .8rem;
}
.ops-purchase-fact {
  min-width: 0;
  padding: .9rem 0;
  border-bottom: 2px solid rgba(35,31,32,.12);
}
.ops-purchase-fact span {
  display: block;
  margin-bottom: .45rem;
  color: var(--ops-muted);
  font-size: .78rem;
  line-height: 1.25;
}
.ops-purchase-fact b {
  display: block;
  color: var(--ops-ink);
  font-family: var(--ops-font-body);
  font-size: clamp(1.65rem, 2.45vw, 2.65rem);
  font-weight: 400;
  letter-spacing: -.035em;
  line-height: 1.08;
  overflow-wrap: anywhere;
  white-space: normal;
}
.ops-purchase-fact[data-kind="purchase"] b {
  font-size: clamp(1.35rem, 1.9vw, 2rem);
  line-height: 1.12;
}

.ops-panel {
  padding: 1.1rem 1.15rem;
  background: var(--ops-paper);
  border: 1px solid rgba(35,31,32,.13);
  border-radius: var(--ops-radius);
  box-shadow: 0 12px 32px rgba(35,31,32,.055);
}
.ops-panel-title { margin: 0 0 .2rem; font-family: var(--ops-font-display); font-size: 1.25rem; font-weight: 900; letter-spacing: -.025em; text-transform: uppercase; }
.ops-panel-subtitle { margin: 0 0 .9rem; color: var(--ops-muted); font-size: .75rem; }

.ops-alert {
  margin: 0 0 .75rem;
  padding: 1rem 1.05rem;
  background: var(--ops-paper);
  border: 1px solid var(--ops-line);
  border-left: 5px solid var(--severity-color, var(--ops-red));
  border-radius: 12px;
  box-shadow: 0 6px 16px rgba(30,24,18,.04);
}
.ops-alert[data-severity="Crítica"] { --severity-color: #cf2f2c; }
.ops-alert[data-severity="Alta"] { --severity-color: #e65d32; }
.ops-alert[data-severity="Media"] { --severity-color: #d98e2b; }
.ops-alert[data-severity="Baja"] { --severity-color: #456a80; }
.ops-alert__top { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
.ops-alert__title { color: var(--ops-ink); font-size: .9rem; font-weight: 800; }
.ops-badge {
  display: inline-flex;
  align-items: center;
  padding: .28rem .52rem;
  color: var(--severity-color, var(--ops-red));
  background: color-mix(in srgb, var(--severity-color, var(--ops-red)) 10%, white);
  border: 1px solid color-mix(in srgb, var(--severity-color, var(--ops-red)) 24%, white);
  border-radius: 999px;
  font-size: .62rem;
  font-weight: 850;
  letter-spacing: .07em;
  text-transform: uppercase;
  white-space: nowrap;
}
.ops-alert__message { margin: .65rem 0; color: #393531; font-size: .8rem; line-height: 1.48; }
.ops-alert__facts {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: .45rem;
  margin: .7rem 0;
}
.ops-fact { padding: .5rem .55rem; background: #f7f4ef; border-radius: 8px; }
.ops-fact span { display: block; color: var(--ops-muted); font-size: .59rem; font-weight: 760; text-transform: uppercase; }
.ops-fact b { display: block; margin-top: .15rem; color: var(--ops-ink); font-size: .77rem; }
.ops-alert__action {
  padding-top: .65rem;
  color: var(--ops-ink);
  border-top: 1px solid var(--ops-line);
  font-size: .76rem;
}
.ops-alert__action b { color: var(--ops-red); }
.ops-alert__comparison {
  margin: .75rem 0;
  padding: .75rem .8rem;
  color: #393531;
  background: #f2eee8;
  border-radius: 9px;
  font-size: .78rem;
  line-height: 1.5;
}
.ops-alert__comparison b { color: var(--ops-ink); }
.ops-tech {
  margin-top: .7rem;
  padding-top: .65rem;
  color: var(--ops-muted);
  border-top: 1px dashed #d7d0c7;
  font-size: .7rem;
}
.ops-tech summary {
  color: var(--ops-muted);
  cursor: pointer;
  font-weight: 760;
}
.ops-tech div { margin-top: .55rem; line-height: 1.55; }

.ops-note {
  padding: .9rem 1rem;
  color: #3d3934;
  background: #eee9e2;
  border: 1px solid #d8d0c7;
  border-radius: 11px;
  font-size: .78rem;
  line-height: 1.5;
}
.ops-note--human { background: var(--ops-red-soft); border-color: #efc7c2; }
.ops-note b { color: var(--ops-ink); }

div[data-testid="stButtonGroup"] {
  margin: 1.05rem 0 .25rem;
  padding: .36rem;
  background: var(--ops-ink);
  border: 1px solid var(--ops-ink);
  border-radius: 999px;
  box-shadow: 0 10px 26px rgba(35,31,32,.14);
}
div[data-testid="stButtonGroup"] div[role="radiogroup"] {
  gap: .2rem;
}
div[data-testid="stButtonGroup"] button[data-variant="segmented_control"] {
  min-height: 2.75rem;
  color: rgba(255,255,255,.72);
  background: transparent;
  border-color: transparent;
  border-radius: 999px;
  font-size: .69rem;
  font-weight: 820;
  letter-spacing: .045em;
  text-transform: uppercase;
}
div[data-testid="stButtonGroup"] button[data-variant="segmented_control"][data-selected="true"] {
  color: #fff;
  background: var(--ops-red);
}
div[data-testid="stButtonGroup"] button[data-variant="segmented_control"] p {
  color: inherit;
}

div[data-baseweb="tab-list"] {
  gap: .4rem;
  padding: .3rem;
  background: rgba(35,31,32,.06);
  border-bottom: 1px solid var(--ops-line);
  border-radius: 12px 12px 0 0;
}
button[data-baseweb="tab"] { border-radius: 9px; font-size: .72rem; font-weight: 800; letter-spacing: .035em; text-transform: uppercase; }
button[data-baseweb="tab"][aria-selected="true"] { color: #fff; background: var(--ops-red); }

[data-testid="stDataFrame"], [data-testid="stDataEditor"], [data-testid="stPlotlyChart"] {
  overflow: hidden;
  background: var(--ops-paper);
  border: 1px solid var(--ops-line);
  border-radius: var(--ops-radius);
  box-shadow: 0 7px 20px rgba(30,24,18,.04);
}
[data-testid="stExpander"] {
  background: var(--ops-paper);
  border: 1px solid var(--ops-line);
  border-radius: 11px;
}
[data-testid="stFileUploaderDropzone"] {
  background: var(--ops-paper);
  border-color: #c9c1b7;
  border-radius: 12px;
}

div.stButton > button, div.stDownloadButton > button, [data-testid="stFileUploaderDropzone"] button {
  min-height: 2.65rem;
  color: #fff;
  background: var(--ops-red);
  border: 1px solid var(--ops-red);
  border-radius: 999px;
  font-size: .69rem;
  font-weight: 820;
  letter-spacing: .055em;
  text-transform: uppercase;
  transition: transform .16s ease, box-shadow .16s ease, background .16s ease;
}
div.stButton > button:hover, div.stDownloadButton > button:hover,
[data-testid="stFileUploaderDropzone"] button:hover {
  color: #fff;
  background: var(--ops-ink);
  border-color: var(--ops-ink);
  box-shadow: 0 8px 20px rgba(35,31,32,.2);
  transform: translateY(-1px);
}

.ops-footer {
  margin-top: 2.5rem;
  padding-top: 1rem;
  color: var(--ops-muted);
  border-top: 1px solid var(--ops-line);
  font-size: .7rem;
}

@media (max-width: 900px) {
  [data-testid="stAppViewContainer"] > .main .block-container { padding-inline: 1rem; }
  .ops-header { align-items: flex-start; flex-direction: column; padding: 1.65rem; border-radius: 18px; }
  .ops-review { width: 100%; }
  .ops-alert__facts { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  div[data-testid="stButtonGroup"] { overflow-x: auto; border-radius: 16px; }
  div[data-testid="stButtonGroup"] div[role="radiogroup"] {
    display: flex !important;
    flex-wrap: nowrap !important;
    width: max-content !important;
    min-width: max-content !important;
  }
  div[data-testid="stButtonGroup"] button[data-variant="segmented_control"] {
    flex: 0 0 auto !important;
    min-width: 145px;
  }
  .ops-purchase-facts { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 560px) {
  .ops-alert__facts { grid-template-columns: 1fr; }
  .ops-header { min-height: 0; padding: 1.35rem 1.15rem; }
  .ops-header h1 { font-size: 2.6rem; line-height: .9; }
  .ops-header p { font-size: .86rem; }
  .ops-review { min-width: 0; }
  .ops-section-head h2 { font-size: 2rem; }
  .ops-purchase-facts { grid-template-columns: 1fr; gap: .35rem; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { transition: none !important; scroll-behavior: auto !important; }
}
</style>
"""


st.markdown(PROFESSIONAL_CSS, unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def load_default_data() -> DataBundle:
    """Carga las cuatro fuentes locales sin depender de servicios externos."""

    return load_data(DATA_DIR)


def run_pipeline(bundle: DataBundle, order: pd.DataFrame, safety_margin: float) -> dict[str, object]:
    """Ejecuta la misma cadena de negocio utilizada por el dashboard principal."""

    validated = validate_data(bundle.catalogo, bundle.historico, bundle.inventario, order)
    forecasts, outliers = forecast_all(validated.historico, validated.combinaciones)
    review = build_purchase_review(validated, forecasts, safety_margin=safety_margin)
    purchase_alerts = build_purchase_alerts(review)
    behaviors = detect_cross_branch_order_anomalies(
        review,
        catalog_ingredient_ids=validated.catalogo["ingrediente_id"],
    )
    quality = build_quality_alerts(validated.incidencias)
    historical_anomalies = build_anomaly_alerts(outliers, validated.catalogo)
    return {
        "validated": validated,
        "forecasts": forecasts,
        "outliers": outliers,
        "review": review,
        "purchase_alerts": purchase_alerts,
        "behaviors": behaviors,
        "quality": quality,
        "historical_anomalies": historical_anomalies,
        "unknown_order": unknown_order_lines(validated),
        "corrected": corrected_order(review),
    }


def section_header(kicker: str, title: str, description: str) -> None:
    """Presenta una cabecera consistente para cada bloque de decisión."""

    st.markdown(
        f"""
        <div class="ops-section-head">
          <div>
            <div class="ops-kicker">{escape(kicker)}</div>
            <h2>{escape(title)}</h2>
            <p>{escape(description)}</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: object, note: str, tone: str = "neutral") -> None:
    """Muestra un KPI compacto con texto que no depende únicamente del color."""

    st.markdown(
        f"""
        <div class="ops-metric" data-tone="{escape(tone)}">
          <div class="ops-metric__label">{escape(label)}</div>
          <div class="ops-metric__value">{escape(str(value))}</div>
          <div class="ops-metric__note">{escape(note)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def safe_integer(value: object) -> str:
    """Presenta formatos enteros y conserva un guion para valores no calculables."""

    if value is None or pd.isna(value):
        return "—"
    return str(int(round(float(value))))


def signed_integer(value: object) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{int(round(float(value))):+d}"


def purchase_quantity_phrase(value: object, format_name: object) -> str:
    """Presenta una cantidad con el empaque real del proveedor."""

    if value is None or pd.isna(value):
        return "No calculable"
    return purchase_format_phrase(format_name, int(round(float(value))))


def format_table(frame: pd.DataFrame) -> pd.DataFrame:
    """Evita sufijos decimales en columnas expresadas como formatos."""

    result = frame.copy()
    for column in result.columns:
        if "formato" in str(column).lower():
            numeric = pd.to_numeric(result[column], errors="coerce")
            if numeric.notna().any():
                result[column] = numeric.round().astype("Int64")
    return result


def chart_layout(figure: go.Figure, *, height: int = 360) -> go.Figure:
    """Aplica una presentación sobria y consistente a los gráficos."""

    chart_title = figure.layout.title.text if figure.layout.title else None
    layout_options: dict[str, object] = dict(
        height=height,
        margin=dict(l=20, r=20, t=55, b=30),
        paper_bgcolor="#fffdf9",
        plot_bgcolor="#fffdf9",
        font=dict(family="Aptos, Segoe UI, Arial", color="#393531", size=12),
        legend=dict(title=None, orientation="h", y=-0.18),
        colorway=CHART_COLORS,
        hoverlabel=dict(bgcolor="#231f20", bordercolor="#cf2f2c", font_color="#fffdf9"),
    )
    if chart_title:
        layout_options["title_font"] = dict(
            family="Arial Narrow, Impact, sans-serif",
            size=18,
            color="#231f20",
        )
    figure.update_layout(**layout_options)
    figure.update_xaxes(gridcolor="rgba(35,31,32,.08)", linecolor="rgba(35,31,32,.15)")
    figure.update_yaxes(gridcolor="rgba(35,31,32,.08)", linecolor="rgba(35,31,32,.15)")
    return figure


def alert_card(row: object) -> None:
    """Renderiza una alerta completa como unidad de decisión."""

    format_name = getattr(row, "formato_compra")
    ordered = purchase_quantity_phrase(getattr(row, "formatos_ordenados"), format_name)
    recommended = purchase_quantity_phrase(getattr(row, "formatos_recomendados"), format_name)
    difference_value = getattr(row, "diferencia_formatos")
    if difference_value is None or pd.isna(difference_value):
        difference = "No calculable"
    elif float(difference_value) < 0:
        difference = f"Faltan {purchase_quantity_phrase(abs(float(difference_value)), format_name)}"
    elif float(difference_value) > 0:
        difference = f"Sobran {purchase_quantity_phrase(float(difference_value), format_name)}"
    else:
        difference = "Sin diferencia"
    perishable = str(getattr(row, "es_perecedero"))
    st.markdown(
        f"""
        <article class="ops-alert" data-severity="{escape(str(row.severidad))}">
          <div class="ops-alert__top">
            <div class="ops-alert__title">{escape(str(row.sucursal))} · {escape(str(row.ingrediente))}</div>
            <span class="ops-badge">{escape(str(row.severidad))} · {escape(str(row.tipo_alerta))}</span>
          </div>
          <div class="ops-alert__message">{escape(str(row.mensaje))}</div>
          <div class="ops-alert__facts">
            <div class="ops-fact"><span>Orden</span><b>{escape(ordered)}</b></div>
            <div class="ops-fact"><span>Recomendación</span><b>{escape(recommended)}</b></div>
            <div class="ops-fact"><span>Diferencia</span><b>{escape(difference)}</b></div>
            <div class="ops-fact"><span>Condición</span><b>{'Perecedero' if perishable == 'Sí' else 'No perecedero'}</b></div>
          </div>
          <div class="ops-alert__action"><b>Decisión sugerida:</b> {escape(str(row.accion_recomendada))}
          &nbsp; · &nbsp; <b>Proveedor:</b> {escape(str(row.proveedor))}</div>
        </article>
        """,
        unsafe_allow_html=True,
    )


def behavior_card(row: object) -> None:
    """Traduce el benchmarking a una explicación útil para compras."""

    ordered = int(round(float(row.formatos_ordenados)))
    recommended = int(round(float(row.formatos_recomendados)))
    difference = int(round(float(row.diferencia_formatos)))
    ordered_phrase = purchase_format_phrase(row.formato_compra, ordered)
    recommended_phrase = purchase_format_phrase(row.formato_compra, recommended)
    adjustment_phrase = purchase_format_phrase(row.formato_compra, abs(difference))
    peer_count = int(row.cantidad_pares)
    primary = str(row.diagnostico_principal)

    if primary == "Producto omitido":
        title = f"{row.sucursal} no incluyó {row.ingrediente}"
        summary = (
            f"La orden no contiene este producto. Según el consumo proyectado y el inventario, "
            f"se recomiendan {recommended_phrase}."
        )
    elif difference < 0:
        title = f"{row.sucursal} pidió menos {row.ingrediente} de lo recomendado"
        summary = (
            f"Pidió {ordered_phrase}, pero la recomendación es {recommended_phrase}. "
            f"Faltan {adjustment_phrase}."
        )
    else:
        title = f"{row.sucursal} pidió más {row.ingrediente} de lo recomendado"
        summary = (
            f"Pidió {ordered_phrase}, pero la recomendación es {recommended_phrase}. "
            f"Hay {adjustment_phrase} adicionales."
        )

    adjustment = (
        f"Faltan {adjustment_phrase}"
        if difference < 0
        else f"Sobran {adjustment_phrase}"
        if difference > 0
        else "No requiere ajuste"
    )
    direction_text = "más baja" if difference < 0 else "más alta"
    branch_factor = row.factor_vs_recomendacion
    peer_factor = row.mediana_factor_pares
    if pd.notna(branch_factor) and pd.notna(peer_factor):
        branch_percentage = format_number(float(branch_factor) * 100, decimals=0)
        peer_percentage = format_number(float(peer_factor) * 100, decimals=0)
        comparison = (
            f"La orden de esta sucursal cubre aproximadamente el {branch_percentage}% de su recomendación. "
            f"Las otras {peer_count} sucursales cubren cerca del {peer_percentage}% de la suya. "
            f"Por eso esta orden se ve mucho {direction_text} de lo habitual."
        )
    else:
        comparison = (
            f"La recomendación es cero y no se calcula un porcentaje. Aun así, la cantidad pedida "
            f"es muy distinta de las otras {peer_count} sucursales."
        )

    st.markdown(
        f"""
        <article class="ops-alert" data-severity="{escape(str(row.severidad))}">
          <div class="ops-alert__top">
            <div class="ops-alert__title">{escape(title)}</div>
            <span class="ops-badge">Revisar comparación</span>
          </div>
          <div class="ops-alert__message">{escape(summary)}</div>
          <div class="ops-alert__facts">
            <div class="ops-fact"><span>Esta sucursal pidió</span><b>{escape(ordered_phrase)}</b></div>
            <div class="ops-fact"><span>Se recomienda</span><b>{escape(recommended_phrase)}</b></div>
            <div class="ops-fact"><span>Ajuste de la orden</span><b>{escape(adjustment)}</b></div>
            <div class="ops-fact"><span>Qué tan confiable es</span><b>{escape(str(row.nivel_confianza))} · {peer_count} sucursales comparadas</b></div>
          </div>
          <div class="ops-alert__comparison"><b>¿Por qué aparece esta señal?</b><br>{escape(comparison)}</div>
          <div class="ops-alert__action"><b>Qué debería revisar:</b> {escape(str(row.accion_recomendada))}</div>
          <details class="ops-tech">
            <summary>Ver detalle técnico del cálculo</summary>
            <div><b>Ratio de la sucursal:</b> {escape(str(row.ratio_sucursal))} ·
            <b>Mediana de las otras sucursales:</b> {escape(str(row.ratio_mediana_pares))} ·
            <b>Diferencia:</b> {signed_integer(row.diferencia_formatos)} formatos ·
            <b>Método:</b> {escape(str(row.metodo_deteccion))} ·
            <b>Confianza:</b> {escape(str(row.nivel_confianza))}</div>
          </details>
        </article>
        """,
        unsafe_allow_html=True,
    )


def scoped_frames(
    pipeline: dict[str, object],
    branches: list[str],
    suppliers: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Aplica el alcance global sin multiplicar filas mediante merges."""

    review = pipeline["review"].copy()
    if branches:
        review = review[review["sucursal"].isin(branches)]
    if suppliers:
        review = review[review["proveedor"].isin(suppliers)]

    alerts = pipeline["purchase_alerts"].copy()
    if branches:
        alerts = alerts[alerts["sucursal"].isin(branches)]
    if suppliers:
        alerts = alerts[alerts["proveedor"].isin(suppliers)]

    behaviors = scope_cross_branch_behaviors(pipeline["behaviors"], review)
    quality = pipeline["quality"].copy()
    if branches and not quality.empty:
        quality = quality[quality["sucursal"].isna() | quality["sucursal"].isin(branches)]
    return review, alerts, behaviors, quality


def branch_decision_table(review: pd.DataFrame) -> pd.DataFrame:
    """Convierte el detalle técnico de una sucursal en acciones de compra."""

    rows: list[dict[str, object]] = []
    priority = {
        "OMITIDO": 0,
        "FALTANTE": 1,
        "SOBREPEDIDO": 2,
        "DATO INCOMPLETO": 3,
        "CORRECTO": 4,
        "SIN NECESIDAD": 4,
    }
    for row in review.itertuples(index=False):
        state = str(row.estado)
        format_name = row.formato_compra
        ordered = None if pd.isna(row.formatos_ordenados) else int(round(float(row.formatos_ordenados)))
        recommended = (
            None
            if pd.isna(row.formatos_recomendados)
            else int(round(float(row.formatos_recomendados)))
        )
        difference = (
            None if pd.isna(row.diferencia_formatos) else int(round(float(row.diferencia_formatos)))
        )

        ordered_text = (
            "No disponible"
            if ordered is None
            else purchase_format_phrase(format_name, ordered)
        )
        recommended_text = (
            "No se puede calcular"
            if recommended is None
            else "No pedir"
            if recommended == 0
            else purchase_format_phrase(format_name, recommended)
        )
        if state in {"OMITIDO", "FALTANTE"} and difference is not None:
            change = f"Agregar {purchase_format_phrase(format_name, abs(difference))}"
        elif state == "SOBREPEDIDO" and difference is not None:
            change = f"Retirar {purchase_format_phrase(format_name, difference)}"
        elif state == "DATO INCOMPLETO":
            change = "Revisar los datos antes de comprar"
        else:
            change = "Dejar la orden como está"

        rows.append(
            {
                "_prioridad": priority.get(state, 9),
                "_estado": state,
                "Qué ocurre": STATUS_BUSINESS_LABELS.get(state, state),
                "Ingrediente": row.nombre,
                "Pedido actual": ordered_text,
                "Recomendación": recommended_text,
                "Cambio sugerido": change,
                "Formato de compra": format_name,
                "Proveedor": row.proveedor,
                "Perecedero": "Sí" if bool(row.es_perecedero_bool) else "No",
            }
        )
    return pd.DataFrame(rows).sort_values(["_prioridad", "Ingrediente"], na_position="last")


def render_executive(
    review: pd.DataFrame,
    alerts: pd.DataFrame,
    behaviors: pd.DataFrame,
    quality: pd.DataFrame,
) -> None:
    section_header(
        "Pulso semanal",
        "Vista ejecutiva",
        "Qué requiere decisión antes de aprobar la orden y dónde concentrar la revisión.",
    )
    correct = int(review["estado"].isin(["CORRECTO", "SIN NECESIDAD"]).sum())
    incomplete = int((review["estado"] == "DATO INCOMPLETO").sum())
    percentage = 100 * correct / len(review) if len(review) else 0.0
    risks = int(alerts["tipo_alerta"].isin(["FALTANTE", "OMITIDO"]).sum()) if not alerts.empty else 0
    overorders = int((alerts["tipo_alerta"] == "SOBREPEDIDO").sum()) if not alerts.empty else 0
    errors = int((quality["nivel"] == "Error").sum()) if not quality.empty else 0

    kpis = st.columns(5)
    with kpis[0]:
        metric_card("Líneas revisadas", len(review), "Combinaciones sucursal–ingrediente", "neutral")
    with kpis[1]:
        metric_card("Sin ajuste", f"{percentage:.1f}%", f"{correct} líneas correctas", "success")
    with kpis[2]:
        metric_card("Riesgo de quiebre", risks, "Faltantes y omisiones", "danger")
    with kpis[3]:
        metric_card("Sobrepedidos", overorders, "Formatos completos adicionales", "warning")
    with kpis[4]:
        metric_card("Errores de datos", errors, f"{incomplete} líneas no calculables", "neutral")

    overlap = summarize_attention_overlap(alerts, behaviors)
    st.markdown(
        f"""
        <div class="ops-note ops-note--human"><b>Lectura correcta del total:</b>
        existen {overlap['lineas_unicas']} líneas únicas con atención. Las {overlap['comportamientos_inusuales']}
        señales entre sucursales son contexto comparativo y {overlap['superposicion']} coinciden con una alerta
        principal; no se suman como productos adicionales. Toda recomendación requiere aprobación humana.</div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.08, .92], gap="large")
    with left:
        section_header("Prioridad", "Cola de decisiones", "Primero se muestran los casos de mayor severidad.")
        if alerts.empty:
            st.success("No hay alertas de compra para el alcance seleccionado.")
        else:
            for row in alerts.head(4).itertuples(index=False):
                alert_card(row)
    with right:
        section_header("Cobertura", "Estado de las líneas", "Diagnósticos mutuamente excluyentes de la revisión.")
        status_counts = review["estado"].value_counts().rename_axis("estado").reset_index(name="líneas")
        figure = px.pie(
            status_counts,
            names="estado",
            values="líneas",
            hole=.68,
            color="estado",
            color_discrete_map=STATUS_COLORS,
        )
        figure.update_traces(textinfo="label+value", hovertemplate="%{label}: %{value} líneas<extra></extra>")
        figure.add_annotation(
            text=f"<b>{len(review)}</b><br><span style='font-size:11px'>líneas</span>",
            showarrow=False,
            font=dict(size=22, color="#171513"),
        )
        st.plotly_chart(chart_layout(figure, height=390), width="stretch")

    charts = st.columns(2, gap="large")
    with charts[0]:
        if alerts.empty:
            st.info("Sin alertas para graficar por sucursal.")
        else:
            by_branch = alerts.groupby(["sucursal", "tipo_alerta"], as_index=False).size()
            figure = px.bar(
                by_branch,
                x="sucursal",
                y="size",
                color="tipo_alerta",
                text="size",
                barmode="stack",
                title="Decisiones pendientes por sucursal",
                labels={"sucursal": "Sucursal", "size": "Líneas", "tipo_alerta": "Diagnóstico"},
                color_discrete_map={"OMITIDO": "#B42318", "FALTANTE": "#E04F16", "SOBREPEDIDO": "#D28B16"},
            )
            figure.update_traces(textposition="inside")
            st.plotly_chart(chart_layout(figure), width="stretch")
    with charts[1]:
        if alerts.empty:
            st.info("Sin decisiones pendientes por proveedor.")
        else:
            by_supplier = alerts.groupby(["proveedor", "tipo_alerta"], as_index=False).size()
            figure = px.bar(
                by_supplier,
                x="size",
                y="proveedor",
                color="tipo_alerta",
                text="size",
                orientation="h",
                title="Líneas que requieren ajuste por proveedor",
                labels={"proveedor": "Proveedor", "size": "Líneas", "tipo_alerta": "Diagnóstico"},
                color_discrete_map={"OMITIDO": "#B42318", "FALTANTE": "#E04F16", "SOBREPEDIDO": "#D28B16"},
            )
            st.plotly_chart(chart_layout(figure), width="stretch")


def render_alert_center(alerts: pd.DataFrame, behaviors: pd.DataFrame) -> None:
    section_header(
        "Decisiones",
        "Centro de alertas",
        "Filtra, revisa y descarga únicamente las líneas que necesitan una acción.",
    )
    purchase_tab, behavior_tab = st.tabs(
        ["Alertas de compra", "Comportamiento inusual entre sucursales"]
    )
    with purchase_tab:
        filter_columns = st.columns([1, 1, 1, 1, .8])
        severities = filter_columns[0].multiselect(
            "Severidad",
            [value for value in SEVERITY_ORDER if value in set(alerts.get("severidad", []))],
            placeholder="Todas",
            key="pro_alert_severity",
        )
        alert_types = filter_columns[1].multiselect(
            "Diagnóstico",
            sorted(alerts["tipo_alerta"].dropna().unique()) if not alerts.empty else [],
            placeholder="Todos",
            key="pro_alert_type",
        )
        branches = filter_columns[2].multiselect(
            "Sucursal",
            sorted(alerts["sucursal"].dropna().unique()) if not alerts.empty else [],
            placeholder="Todas",
            key="pro_alert_branch",
        )
        suppliers = filter_columns[3].multiselect(
            "Proveedor",
            sorted(alerts["proveedor"].dropna().unique()) if not alerts.empty else [],
            placeholder="Todos",
            key="pro_alert_supplier",
        )
        perishability = filter_columns[4].selectbox(
            "Perecedero",
            ["Todos", "Sí", "No"],
            key="pro_alert_perishable",
        )

        visible = alerts.copy()
        for column, selected in [
            ("severidad", severities),
            ("tipo_alerta", alert_types),
            ("sucursal", branches),
            ("proveedor", suppliers),
        ]:
            if selected:
                visible = visible[visible[column].isin(selected)]
        if perishability != "Todos":
            visible = visible[visible["es_perecedero"] == perishability]

        controls = st.columns([1, 1, 3])
        controls[0].metric("Resultados", len(visible))
        controls[1].metric("Críticos", int((visible["severidad"] == "Crítica").sum()) if not visible.empty else 0)
        controls[2].caption("Los filtros vacíos equivalen a mostrar todos los valores de esa dimensión.")
        if visible.empty:
            st.success("No hay alertas con la combinación de filtros seleccionada.")
        else:
            for row in visible.itertuples(index=False):
                alert_card(row)

        table_columns = [
            "severidad", "tipo_alerta", "sucursal", "ingrediente", "proveedor",
            "es_perecedero", "formato_compra", "formatos_ordenados",
            "formatos_recomendados", "diferencia_formatos", "razon", "accion_recomendada",
        ]
        table = visible[table_columns].copy() if not visible.empty else pd.DataFrame(columns=table_columns)
        with st.expander("Ver tabla consolidada", expanded=False):
            st.dataframe(format_table(table), width="stretch", hide_index=True)
        st.markdown(
            "<div class='ops-note'><b>Reporte listo para compartir.</b> Incluye un resumen, "
            "las decisiones prioritarias y el detalle completo en hojas separadas. Se abre en "
            "Excel con colores, filtros y cantidades expresadas en sacos, cajas o paquetes.</div>",
            unsafe_allow_html=True,
        )
        st.download_button(
            "📊 Descargar reporte visual de alertas (Excel)",
            build_alerts_excel(visible),
            file_name="reporte_visual_alertas_compra.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
            type="primary",
            key="pro_download_alerts_excel",
        )
        with st.expander("Opciones avanzadas de descarga"):
            st.caption(
                "El CSV conserva datos simples para análisis técnico. Para una revisión gerencial, "
                "recomendamos el reporte Excel anterior."
            )
            st.download_button(
                "Descargar alertas visibles en CSV",
                dataframe_to_csv_bytes(table),
                file_name="alertas_compra_revision.csv",
                mime="text/csv",
                width="stretch",
                key="pro_download_alerts_csv",
            )

    with behavior_tab:
        st.markdown(
            "<div class='ops-note'><b>¿Qué significa esta sección?</b> La herramienta revisa si una sucursal "
            "está pidiendo mucho más o mucho menos de un ingrediente que las demás, teniendo en cuenta que "
            "cada sucursal puede consumir cantidades diferentes. Es una invitación a revisar la orden, no una "
            "confirmación de que exista un error.</div>",
            unsafe_allow_html=True,
        )
        if behaviors.empty:
            st.success("No se detectó comportamiento inusual para el alcance actual.")
        else:
            for row in behaviors.itertuples(index=False):
                behavior_card(row)
            behavior_columns = [
                "diagnostico_principal", "sucursal", "ingrediente", "proveedor",
                "formatos_ordenados", "formatos_recomendados", "diferencia_formatos",
                "ratio_sucursal", "ratio_mediana_pares", "cantidad_pares",
                "metodo_deteccion", "nivel_confianza", "accion_recomendada",
            ]
            table = behaviors[behavior_columns].copy()
            st.download_button(
                "Descargar comparación entre sucursales",
                dataframe_to_csv_bytes(table),
                file_name="comportamiento_inusual_sucursales.csv",
                mime="text/csv",
                width="stretch",
            )


def render_branch_workspace(
    pipeline: dict[str, object],
    review: pd.DataFrame,
    safety_margin: float,
) -> None:
    section_header(
        "Exploración",
        "Revisión de una sucursal",
        "Te mostramos qué productos debes cambiar antes de aprobar su orden.",
    )
    validated = pipeline["validated"]
    available_branches = sorted(review["sucursal"].dropna().unique())
    if not available_branches:
        st.warning("No hay sucursales dentro del alcance seleccionado.")
        return

    selector, explanation = st.columns([.75, 2.25])
    with selector:
        branch = st.selectbox("Sucursal", available_branches, key="pro_branch")
    with explanation:
        st.markdown(
            f"""
            <div class="ops-note"><b>Estás revisando {escape(branch)}.</b> Primero verás los productos
            que necesitan aumentar, reducir o agregarse. Los productos que están bien pueden mostrarse
            de forma opcional.</div>
            """,
            unsafe_allow_html=True,
        )
    branch_review = review[review["sucursal"] == branch].copy()
    alert_count = int(branch_review["estado"].isin(["OMITIDO", "FALTANTE", "SOBREPEDIDO"]).sum())
    correct_count = int(branch_review["estado"].isin(["CORRECTO", "SIN NECESIDAD"]).sum())
    incomplete_count = int((branch_review["estado"] == "DATO INCOMPLETO").sum())
    columns = st.columns(4)
    with columns[0]:
        metric_card("Productos revisados", len(branch_review), "Todos los ingredientes de la sucursal", "neutral")
    with columns[1]:
        metric_card("Debes cambiar", alert_count, "Agregar, aumentar o reducir cantidades", "danger")
    with columns[2]:
        metric_card("No debes cambiar", correct_count, "La cantidad pedida ya es adecuada", "success")
    with columns[3]:
        metric_card("Revisar datos", incomplete_count, "No se puede recomendar con seguridad", "warning")

    if safety_margin:
        st.warning(
            f"Simulación activa: se agregó {safety_margin:.0%} de margen de seguridad al consumo esperado. "
            "Esto puede aumentar la cantidad recomendada frente a la fórmula original."
        )

    overview_tab, analysis_tab = st.tabs(
        ["Qué debes cambiar", "Ver historial de un ingrediente"]
    )
    with overview_tab:
        omitted_count = int((branch_review["estado"] == "OMITIDO").sum())
        missing_count = int((branch_review["estado"] == "FALTANTE").sum())
        over_count = int((branch_review["estado"] == "SOBREPEDIDO").sum())
        action_parts = []
        if omitted_count:
            omitted_label = f"{omitted_count} producto" if omitted_count == 1 else f"{omitted_count} productos"
            omitted_verb = "no aparece" if omitted_count == 1 else "no aparecen"
            action_parts.append(f"agregar {omitted_label} que {omitted_verb} en la orden")
        if missing_count:
            missing_label = f"{missing_count} producto" if missing_count == 1 else f"{missing_count} productos"
            action_parts.append(f"aumentar la cantidad de {missing_label}")
        if over_count:
            over_label = f"{over_count} producto" if over_count == 1 else f"{over_count} productos"
            action_parts.append(f"reducir la cantidad de {over_label}")
        if incomplete_count:
            incomplete_label = f"{incomplete_count} producto" if incomplete_count == 1 else f"{incomplete_count} productos"
            action_parts.append(f"corregir los datos de {incomplete_label}")
        if action_parts:
            st.warning("Antes de aprobar debes " + "; ".join(action_parts) + ".")
        else:
            st.success("La orden de esta sucursal no necesita cambios.")

        status_counts = (
            branch_review.assign(
                situacion=branch_review["estado"].map(STATUS_BUSINESS_LABELS)
            )["situacion"]
            .value_counts()
            .rename_axis("Qué debes hacer")
            .reset_index(name="Productos")
        )
        business_colors = {
            "✅ No necesita cambios": "#27845B",
            "🟠 Hay que pedir más": "#E04F16",
            "🔴 No se incluyó en la orden": "#B42318",
            "🟡 Se pidió de más": "#D28B16",
            "⚠️ Faltan datos para decidir": "#7A5AF8",
        }
        figure = px.bar(
            status_counts,
            x="Productos",
            y="Qué debes hacer",
            orientation="h",
            color="Qué debes hacer",
            text="Productos",
            color_discrete_map=business_colors,
            title=f"Resumen fácil de la orden · {branch}",
            labels={"Productos": "Cantidad de productos"},
        )
        figure.update_layout(showlegend=False)
        figure.update_traces(texttemplate="%{text} productos", textposition="inside")
        st.plotly_chart(chart_layout(figure, height=330), width="stretch")

        show_all = st.toggle(
            "Mostrar también los productos que no necesitan cambios",
            value=False,
            key="pro_show_all_branch_lines",
        )
        all_decisions = branch_decision_table(branch_review)
        decisions = all_decisions.copy()
        if not show_all:
            decisions = decisions[
                decisions["_estado"].isin(["OMITIDO", "FALTANTE", "SOBREPEDIDO", "DATO INCOMPLETO"])
            ]
        visible_decisions = decisions.drop(columns=["_prioridad", "_estado"])
        technical = friendly_review_table(branch_review)
        for column in ["Inventario actual", "Proyección", "Necesidad"]:
            if column in technical:
                technical[column] = pd.to_numeric(technical[column], errors="coerce").round(2)
        st.caption(
            f"Mostrando {len(visible_decisions)} de {len(branch_review)} productos de {branch}."
        )
        st.dataframe(
            visible_decisions,
            width="stretch",
            hide_index=True,
        )
        st.markdown(
            f"<div class='ops-note'><b>Reporte de {escape(branch)} listo para compartir.</b> "
            "Incluye el resumen de la sucursal, qué debes cambiar antes de aprobar, la orden "
            "completa y una hoja separada con los datos del cálculo.</div>",
            unsafe_allow_html=True,
        )
        st.download_button(
            f"📊 Descargar revisión visual de {branch} (Excel)",
            build_branch_excel(
                branch,
                all_decisions,
                technical,
                safety_margin=safety_margin,
            ),
            file_name=f"revision_visual_{branch.lower().replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
            type="primary",
            key="pro_download_branch_excel",
        )
        with st.expander("Opciones avanzadas de descarga"):
            st.caption(
                "El CSV contiene exactamente las filas visibles en pantalla y es útil para análisis técnico."
            )
            st.download_button(
                "Descargar filas visibles en CSV",
                dataframe_to_csv_bytes(visible_decisions),
                file_name=f"revision_{branch.lower().replace(' ', '_')}.csv",
                mime="text/csv",
                width="stretch",
                key="pro_download_branch_csv",
            )

        with st.expander("Ver datos usados para los cálculos"):
            st.caption(
                "Esta tabla contiene inventario, proyección y método. Se conserva para auditoría, "
                "pero no necesitas leerla para saber qué cambiar."
            )
            st.dataframe(format_table(technical), width="stretch", hide_index=True)

    with analysis_tab:
        names = branch_review["nombre"].dropna().sort_values().unique().tolist()
        if not names:
            st.info("No hay ingredientes conocidos para analizar.")
            return
        ingredient_name = st.selectbox(
            "Producto que quieres revisar",
            names,
            key="pro_ingredient",
        )
        selected = branch_review[branch_review["nombre"] == ingredient_name].iloc[0]
        ingredient_id = selected["ingrediente_id"]
        history = validated.historico[
            (validated.historico["sucursal"] == branch)
            & (validated.historico["ingrediente_id"] == ingredient_id)
        ].copy()
        history["semana_numero"] = history["semana"].map(week_number)
        history["consumo_numerico"] = pd.to_numeric(history["consumo_unidad_base"], errors="coerce")
        history = history.sort_values("semana_numero")

        forecast_rows = pipeline["forecasts"]
        forecast_rows = forecast_rows[
            (forecast_rows["sucursal"] == branch)
            & (forecast_rows["ingrediente_id"] == ingredient_id)
        ]
        selected_forecast = forecast_rows.iloc[0] if not forecast_rows.empty else None

        format_example = purchase_quantity_phrase(1, selected["formato_compra"])
        st.markdown(
            f"""
            <div class="ops-note" style="margin:.7rem 0 1rem">
              <b>¿Qué significa “formato”?</b> Es la presentación completa e indivisible que vende el proveedor.
              Para {escape(str(ingredient_name))}, <b>1 formato equivale a {escape(format_example)}</b>.
              Como no se compran fracciones de un empaque, la recomendación siempre se redondea hacia arriba.
            </div>
            """,
            unsafe_allow_html=True,
        )

        figure = go.Figure()
        figure.add_trace(
            go.Scatter(
                x=history["semana"],
                y=history["consumo_numerico"],
                mode="lines+markers",
                name="Consumo observado",
                line=dict(color="#3E6F88", width=3),
                marker=dict(size=9),
            )
        )
        selected_outliers = pipeline["outliers"]
        selected_outliers = selected_outliers[
            (selected_outliers["sucursal"] == branch)
            & (selected_outliers["ingrediente_id"] == ingredient_id)
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
                    marker=dict(size=14, symbol="x", color="#B42318"),
                )
            )
        if selected_forecast is not None and pd.notna(selected_forecast["consumo_proyectado"]):
            projected_week = f"S{int(selected_forecast['semana_proyectada_numero'])}"
            figure.add_trace(
                go.Scatter(
                    x=[projected_week],
                    y=[selected_forecast["consumo_proyectado"]],
                    mode="markers+text",
                    text=["Proyección"],
                    textposition="top center",
                    name="Proyección robusta",
                    marker=dict(size=15, symbol="diamond", color="#E04F16"),
                )
            )
        figure.update_layout(
            title=f"Cuánto se consumió y cuánto se espera consumir · {ingredient_name}",
            xaxis_title="Semana",
            yaxis_title=f"Consumo ({selected['unidad_base']})",
            hovermode="x unified",
        )
        st.plotly_chart(chart_layout(figure, height=430), width="stretch")

        purchase_facts = (
            ("Disponible ahora", f"{format_number(selected['inventario_actual'])} {selected['unidad_base']}", "base"),
            ("Consumo esperado", f"{format_number(selected['consumo_proyectado'])} {selected['unidad_base']}", "base"),
            ("Falta cubrir", f"{format_number(selected['necesidad_base'])} {selected['unidad_base']}", "base"),
            (
                "Se pidió",
                purchase_quantity_phrase(selected["formatos_ordenados"], selected["formato_compra"]),
                "purchase",
            ),
            (
                "Se recomienda",
                purchase_quantity_phrase(selected["formatos_recomendados"], selected["formato_compra"]),
                "purchase",
            ),
        )
        purchase_facts_html = "".join(
            f'<div class="ops-purchase-fact" data-kind="{kind}">'
            f'<span class="ops-purchase-fact__label">{escape(label)}</span>'
            f'<b class="ops-purchase-fact__value">{escape(value)}</b>'
            "</div>"
            for label, value, kind in purchase_facts
        )
        st.html(f'<div class="ops-purchase-facts">{purchase_facts_html}</div>')
        if selected_forecast is None:
            st.warning("No existe una proyección válida para esta combinación.")
        else:
            with st.expander("¿Cómo se calculó el consumo esperado?"):
                st.markdown(
                    f"**Método:** {escape(str(selected_forecast['metodo_proyeccion']))}  \n"
                    f"**Confianza:** {escape(str(selected_forecast['nivel_confianza']))}  \n"
                    f"{escape(str(selected_forecast['explicacion_metodo']))}"
                )


def render_order_workbench(bundle: DataBundle, pipeline: dict[str, object]) -> None:
    section_header(
        "Ejecución",
        "Mesa de compra",
        "Edita la orden, valida cambios y prepara archivos separados por proveedor.",
    )
    simulation_tab, corrected_tab, supplier_tab = st.tabs(
        ["Simulador", "Orden corregida", "Paquetes por proveedor"]
    )

    with simulation_tab:
        upload_column, status_column = st.columns([1.45, .55], gap="large")
        with upload_column:
            uploaded = st.file_uploader(
                "Cargar orden_compra_semana.csv",
                type=["csv"],
                key="pro_order_upload",
            )
            if uploaded is not None:
                try:
                    candidate = read_order_upload(BytesIO(uploaded.getvalue()))
                    preview_validation = validate_data(
                        bundle.catalogo,
                        bundle.historico,
                        bundle.inventario,
                        candidate,
                    )
                    missing_schema = preview_validation.incidencias[
                        preview_validation.incidencias["codigo"] == "COLUMNA_AUSENTE"
                    ]
                    if not missing_schema.empty:
                        st.error("El archivo no puede utilizarse: faltan columnas obligatorias.")
                        st.dataframe(missing_schema, width="stretch", hide_index=True)
                    else:
                        error_count = int((preview_validation.incidencias["nivel"] == "Error").sum())
                        if error_count:
                            st.warning(f"El archivo conserva {error_count} errores visibles para corrección.")
                        else:
                            st.success("El esquema es válido y no contiene errores bloqueantes.")
                        if st.button("Usar archivo cargado", key="pro_use_upload", width="stretch"):
                            current = candidate.copy()
                            numeric = pd.to_numeric(current["cantidad_formatos"], errors="coerce")
                            current["cantidad_formatos"] = numeric.where(numeric.notna(), current["cantidad_formatos"])
                            st.session_state.pro_working_order = current
                            st.session_state.pro_editor_version += 1
                            st.rerun()
                except Exception as exc:
                    st.error(f"No fue posible leer el archivo: {exc}")
        with status_column:
            errors = pipeline["quality"]
            errors = errors[errors["nivel"] == "Error"] if not errors.empty else errors
            metric_card(
                "Estado del archivo",
                "Revisar" if len(errors) else "Listo",
                f"{len(errors)} errores de datos conservados",
                "danger" if len(errors) else "success",
            )

        controls = st.columns([1, 1, 3])
        if controls[0].button("Restablecer orden original", key="pro_reset", width="stretch"):
            original = bundle.orden.copy()
            original["cantidad_formatos"] = pd.to_numeric(original["cantidad_formatos"], errors="coerce")
            st.session_state.pro_working_order = original
            st.session_state.pro_editor_version += 1
            st.rerun()
        controls[1].metric("Líneas actuales", len(st.session_state.pro_working_order))
        controls[2].caption("Los cambios recalculan proyección, necesidad, recomendación y alertas. No se eliminan filas problemáticas.")

        current = st.session_state.pro_working_order
        quantities = pd.to_numeric(current["cantidad_formatos"], errors="coerce")
        has_invalid = bool(current["cantidad_formatos"].notna().any() and quantities.isna().any())
        quantity_config = (
            st.column_config.TextColumn("Cantidad de formatos", required=True)
            if has_invalid
            else st.column_config.NumberColumn(
                "Cantidad de formatos", min_value=0.0, step=1.0, required=True
            )
        )
        edited = st.data_editor(
            current,
            num_rows="dynamic",
            width="stretch",
            hide_index=True,
            key=f"pro_order_editor_{st.session_state.pro_editor_version}",
            column_config={
                "sucursal": st.column_config.TextColumn("Sucursal", required=True),
                "ingrediente_id": st.column_config.TextColumn("Ingrediente ID", required=True),
                "cantidad_formatos": quantity_config,
            },
        )
        if not edited.reset_index(drop=True).equals(current.reset_index(drop=True)):
            st.session_state.pro_working_order = edited.reset_index(drop=True)
            st.rerun()

    corrected = pipeline["corrected"].copy()
    for column in [
        "cantidad_formatos_original",
        "cantidad_formatos_corregida",
        "diferencia_formatos_corregir",
    ]:
        corrected[column] = pd.to_numeric(corrected[column], errors="coerce").round().astype("Int64")

    with corrected_tab:
        st.markdown(
            "<div class='ops-note'><b>Regla:</b> la orden corregida incluye todo el catálogo conocido. "
            "Las cantidades no calculables permanecen vacías para revisión humana.</div>",
            unsafe_allow_html=True,
        )
        st.download_button(
            "Descargar orden corregida completa",
            dataframe_to_csv_bytes(corrected),
            file_name="orden_corregida_completa.csv",
            mime="text/csv",
            width="stretch",
        )
        st.dataframe(corrected, width="stretch", hide_index=True)
        unknown = pipeline["unknown_order"]
        if not unknown.empty:
            st.error("Ingredientes desconocidos excluidos de las órdenes a proveedores.")
            st.dataframe(format_table(unknown), width="stretch", hide_index=True)

    with supplier_tab:
        suppliers = corrected["proveedor"].dropna().sort_values().unique().tolist()
        if not suppliers:
            st.info("No hay proveedores con líneas calculables.")
        for supplier in suppliers:
            supplier_order = corrected[corrected["proveedor"] == supplier]
            with st.expander(f"{supplier} · {len(supplier_order)} líneas", expanded=False):
                st.dataframe(supplier_order, width="stretch", hide_index=True)
                safe_name = "".join(
                    character.lower() if character.isalnum() else "_" for character in supplier
                ).strip("_")
                st.download_button(
                    f"Descargar orden de {supplier}",
                    dataframe_to_csv_bytes(supplier_order),
                    file_name=f"orden_{safe_name}.csv",
                    mime="text/csv",
                    key=f"pro_supplier_{safe_name}",
                    width="stretch",
                )


def quality_issue_card(row: object, ingredient_names: dict[str, str]) -> None:
    """Explica una incidencia sin exponer códigos internos como contenido principal."""

    code = str(row.codigo)
    ingredient_id = "" if pd.isna(row.ingrediente_id) else str(row.ingrediente_id)
    ingredient = ingredient_names.get(ingredient_id, ingredient_id or "No identificado")
    branch = "Todas las sucursales" if pd.isna(row.sucursal) else str(row.sucursal)
    source_labels = {
        "orden": "Orden semanal",
        "catalogo": "Catálogo de ingredientes",
        "historico": "Histórico de consumo",
        "inventario": "Inventario actual",
    }
    source = source_labels.get(str(row.archivo), str(row.archivo))
    line = "No aplica" if pd.isna(row.fila) else str(int(float(row.fila)))

    if code == "INGREDIENTE_DESCONOCIDO":
        title = "La orden contiene un producto que no existe en el catálogo"
        explanation = (
            f"{branch} incluyó “{ingredient_id}”, pero el sistema no encuentra ese código en el catálogo."
        )
        why = "Sin catálogo no se conoce el proveedor, la unidad ni el tamaño de compra. Esta línea no puede recomendarse ni enviarse a un proveedor."
        action = "Confirmar el código. Si el producto es válido, agregarlo al catálogo; si fue un error, corregirlo o retirarlo de la orden."
        badge = "Debe corregirse"
    elif code == "PRODUCTO_OMITIDO_ORDEN":
        title = "Un producto del catálogo no fue incluido en la orden"
        explanation = f"{branch} no incluyó {ingredient} en su orden semanal."
        why = "El sistema lo interpreta como 0 formatos pedidos para comprobar si hace falta agregarlo."
        action = "Revisar la alerta de compra y agregar la cantidad recomendada si la gerente la aprueba."
        badge = "Revisar antes de aprobar"
    elif code == "INVENTARIO_FALTANTE":
        title = "Falta el inventario actual de un producto"
        explanation = f"No hay una cantidad de inventario confiable para {ingredient} en {branch}."
        why = "Sin inventario no se puede saber cuánto falta realmente y no se asume que el stock sea cero."
        action = "Registrar o corregir el inventario antes de calcular la compra."
        badge = "No se puede calcular"
    elif code in {"HISTORICO_FALTANTE", "HISTORICO_INCOMPLETO"}:
        title = "Falta historial suficiente para estimar el consumo"
        explanation = f"{ingredient} en {branch} no tiene todas las semanas esperadas."
        why = "Con menos información la estimación puede ser menos confiable; sin histórico no se fabrica una proyección."
        action = "Revisar y completar el histórico disponible antes de aprobar la recomendación."
        badge = "Revisar historial"
    else:
        title = "Hay un dato que necesita revisión"
        explanation = str(row.detalle)
        why = str(row.por_que_importa)
        action = "Corregir el dato en el archivo de origen y volver a ejecutar la revisión."
        badge = "Error" if str(row.nivel) == "Error" else "Advertencia"

    severity = "Crítica" if str(row.nivel) == "Error" else "Baja"
    st.markdown(
        f"""
        <article class="ops-alert" data-severity="{severity}">
          <div class="ops-alert__top">
            <div class="ops-alert__title">{escape(title)}</div>
            <span class="ops-badge">{escape(badge)}</span>
          </div>
          <div class="ops-alert__message">{escape(explanation)}</div>
          <div class="ops-alert__facts">
            <div class="ops-fact"><span>Sucursal</span><b>{escape(branch)}</b></div>
            <div class="ops-fact"><span>Producto o código</span><b>{escape(ingredient)}</b></div>
            <div class="ops-fact"><span>Archivo donde aparece</span><b>{escape(source)}</b></div>
            <div class="ops-fact"><span>Fila del archivo</span><b>{escape(line)}</b></div>
          </div>
          <div class="ops-alert__comparison"><b>¿Por qué importa?</b><br>{escape(why)}</div>
          <div class="ops-alert__action"><b>Qué debes hacer:</b> {escape(action)}</div>
        </article>
        """,
        unsafe_allow_html=True,
    )


def historical_anomaly_card(row: object) -> None:
    """Explica un consumo extremo conservando el dato y su tratamiento."""

    value = f"{format_number(row.consumo_unidad_base)} {row.unidad_base}"
    usual = f"{format_number(row.mediana)} {row.unidad_base}"
    treatment = (
        "No se utilizó para calcular la próxima semana, para evitar que una semana excepcional distorsione la compra."
        if bool(row.excluido_proyeccion)
        else "Se conservó dentro del cálculo porque no había suficientes semanas válidas para excluirlo."
    )
    st.markdown(
        f"""
        <article class="ops-alert" data-severity="Baja">
          <div class="ops-alert__top">
            <div class="ops-alert__title">Consumo inusual de {escape(str(row.nombre))} en {escape(str(row.sucursal))}</div>
            <span class="ops-badge">Comprobar registro</span>
          </div>
          <div class="ops-alert__message">En {escape(str(row.semana))} se registraron {escape(value)}.
          Las semanas normales están alrededor de {escape(usual)}.</div>
          <div class="ops-alert__comparison"><b>¿Cómo se trató?</b><br>{escape(treatment)}
          El valor original permanece guardado y visible.</div>
          <div class="ops-alert__action"><b>Qué debes hacer:</b> Confirmar si fue un consumo extraordinario real
          o un error de captura. No es una alerta para comprar más por sí sola.</div>
          <details class="ops-tech"><summary>Ver detalle técnico</summary>
          <div><b>MAD:</b> {escape(format_number(row.mad))} ·
          <b>Modified z-score:</b> {escape(format_number(row.modified_z_score))}</div></details>
        </article>
        """,
        unsafe_allow_html=True,
    )


def render_data_and_method(pipeline: dict[str, object], safety_margin: float) -> None:
    section_header(
        "Gobierno",
        "¿Podemos confiar en los datos?",
        "Primero te mostramos qué debes corregir; los cálculos técnicos quedan como información opcional.",
    )
    issues = pipeline["quality"]
    anomalies = pipeline["historical_anomalies"]
    errors = issues[issues["nivel"] == "Error"] if not issues.empty else issues
    warnings = issues[issues["nivel"] == "Advertencia"] if not issues.empty else issues
    unknown_count = (
        int((issues["codigo"] == "INGREDIENTE_DESCONOCIDO").sum())
        if not issues.empty
        else 0
    )
    metrics = st.columns(4)
    with metrics[0]:
        metric_card("Debes corregir", len(errors), "Impiden confiar en una o más líneas", "danger")
    with metrics[1]:
        metric_card("Debes revisar", len(warnings), "No bloquean todo el cálculo", "warning")
    with metrics[2]:
        metric_card("Fuera del catálogo", unknown_count, "No se enviarán a un proveedor", "danger")
    with metrics[3]:
        metric_card("Consumos inusuales", len(anomalies), "Semanas que conviene comprobar", "neutral")
    st.markdown(
        "<div class='ops-note'><b>Importante:</b> esta sección no indica cuánto comprar. "
        "Solo señala datos que podrían estar equivocados, incompletos o fuera de lo habitual. "
        "Nada se borra ni se corrige automáticamente.</div>",
        unsafe_allow_html=True,
    )

    catalog = pipeline["validated"].catalogo
    ingredient_names = dict(
        catalog.dropna(subset=["ingrediente_id"])
        .drop_duplicates("ingrediente_id", keep=False)
        .set_index("ingrediente_id")["nombre"]
    )

    problem_tab, anomaly_tab, forecast_tab, method_tab = st.tabs(
        [
            "Problemas que debes corregir",
            "Consumos inusuales",
            "Consumo esperado",
            "Cómo calculamos",
        ]
    )

    with problem_tab:
        st.markdown("#### Qué debes corregir antes de aprobar")
        st.caption("Cada tarjeta indica dónde está el problema, por qué importa y la acción recomendada.")
        if issues.empty:
            st.success("No se detectaron problemas de datos.")
        else:
            for row in issues.itertuples(index=False):
                quality_issue_card(row, ingredient_names)
        with st.expander("Ver reporte técnico con códigos y filas"):
            st.caption("Este reporte sirve para auditoría o para quien vaya a corregir los CSV.")
            st.dataframe(issues, width="stretch", hide_index=True)

    with anomaly_tab:
        st.markdown("#### Semanas que se ven muy diferentes de lo normal")
        st.caption(
            "Una semana inusual no significa automáticamente que el dato esté mal ni que debas comprar más."
        )
        if anomalies.empty:
            st.success("No se encontraron consumos históricos inusuales.")
        else:
            for row in anomalies.itertuples(index=False):
                historical_anomaly_card(row)
        with st.expander("Ver reporte técnico de valores inusuales"):
            st.dataframe(anomalies, width="stretch", hide_index=True)

    with forecast_tab:
        forecasts = pipeline["forecasts"].copy()
        method_labels = {
            "Promedio robusto": "Consumo estable: usamos semanas representativas",
            "Tendencia lineal": "Cambio claro: seguimos la tendencia",
        }
        forecasts["Explicación sencilla"] = (
            forecasts["metodo_proyeccion"]
            .map(method_labels)
            .fillna("No había datos suficientes para estimar")
        )
        method_counts = (
            forecasts["Explicación sencilla"]
            .value_counts()
            .rename_axis("Cómo se estimó")
            .reset_index(name="Productos por sucursal")
        )
        stable_count = int((forecasts["metodo_proyeccion"] == "Promedio robusto").sum())
        trend_count = int((forecasts["metodo_proyeccion"] == "Tendencia lineal").sum())
        unavailable_count = int(forecasts["consumo_proyectado"].isna().sum())
        forecast_metrics = st.columns(3)
        forecast_metrics[0].metric("Consumo estable", stable_count)
        forecast_metrics[1].metric("Con cambio claro", trend_count)
        forecast_metrics[2].metric("Sin estimación", unavailable_count)
        st.markdown(
            "<div class='ops-note'><b>En palabras simples:</b> si el consumo se mantiene parecido, "
            "usamos un promedio que ignora semanas muy extrañas. Si existe un crecimiento o descenso "
            "claro y consistente, seguimos esa dirección.</div>",
            unsafe_allow_html=True,
        )
        figure = px.bar(
            method_counts,
            x="Productos por sucursal",
            y="Cómo se estimó",
            orientation="h",
            text="Productos por sucursal",
            color="Cómo se estimó",
            color_discrete_sequence=CHART_COLORS,
            title="Cómo estimamos el consumo de la próxima semana",
        )
        figure.update_layout(showlegend=False)
        st.plotly_chart(chart_layout(figure, height=350), width="stretch")
        trend_rows = forecasts[forecasts["metodo_proyeccion"] == "Tendencia lineal"].copy()
        st.markdown("#### Productos cuyo consumo está cambiando claramente")
        if trend_rows.empty:
            st.info("No encontramos crecimientos o descensos suficientemente claros.")
        else:
            metadata = catalog[
                ["ingrediente_id", "nombre", "unidad_base"]
            ].drop_duplicates("ingrediente_id", keep=False)
            trend_display = trend_rows.merge(
                metadata,
                on="ingrediente_id",
                how="left",
                validate="many_to_one",
            )
            trend_display["consumo_proyectado"] = pd.to_numeric(
                trend_display["consumo_proyectado"], errors="coerce"
            ).round(2)
            trend_display = trend_display[
                [
                    "sucursal",
                    "nombre",
                    "consumo_proyectado",
                    "unidad_base",
                    "nivel_confianza",
                    "explicacion_metodo",
                ]
            ].rename(
                columns={
                    "sucursal": "Sucursal",
                    "nombre": "Producto",
                    "consumo_proyectado": "Consumo esperado",
                    "unidad_base": "Unidad",
                    "nivel_confianza": "Confianza",
                    "explicacion_metodo": "Por qué se siguió la tendencia",
                }
            )
            st.dataframe(trend_display, width="stretch", hide_index=True)
        with st.expander("Ver cálculos técnicos de las proyecciones"):
            st.dataframe(forecasts, width="stretch", hide_index=True)

    with method_tab:
        st.markdown("### Cómo llegamos a una recomendación de compra")
        st.markdown(
            """
            1. **Estimamos cuánto se consumirá la próxima semana** usando el histórico reciente.
            2. **Restamos lo que ya existe en inventario.** Si alcanza, no recomendamos comprar.
            3. **Convertimos lo que falta al formato real del proveedor:** sacos, cajas, latas o paquetes.
            4. **Redondeamos hacia arriba**, porque no se puede comprar medio saco o media caja.
            5. **Comparamos la recomendación con la orden actual** para indicar qué agregar, retirar o dejar igual.

            El pequeño excedente que queda dentro del último formato es normal. Solo hay sobrepedido cuando
            se solicitó por lo menos un formato completo adicional.
            """
        )
        st.markdown(
            "<div class='ops-note'><b>Definición de formato:</b> es la unidad completa en la que el proveedor "
            "vende un ingrediente, por ejemplo un saco de 25 kg, una caja de 10 kg o un paquete de 250 g. "
            "No representa una unidad de peso genérica y no se permiten fracciones del empaque.</div>",
            unsafe_allow_html=True,
        )
        review = pipeline["review"]
        examples = review[
            review["estado"].isin(["FALTANTE", "OMITIDO"])
            & review["formatos_recomendados"].notna()
        ]
        if not examples.empty:
            example = examples.iloc[0]
            ordered = int(round(float(example["formatos_ordenados"])))
            recommended = int(round(float(example["formatos_recomendados"])))
            st.markdown(
                f"""
                <div class="ops-panel">
                  <div class="ops-kicker">Ejemplo con los datos actuales</div>
                  <div style="margin-top:.55rem;line-height:1.6;font-size:.86rem">
                  Para <b>{escape(str(example['nombre']))}</b> en <b>{escape(str(example['sucursal']))}</b>,
                  se esperan {escape(format_number(example['consumo_proyectado_ajustado']))} {escape(str(example['unidad_base']))}
                  y existen {escape(format_number(example['inventario_actual']))} {escape(str(example['unidad_base']))} en inventario.
                  Después de restar el inventario faltan {escape(format_number(example['necesidad_base']))} {escape(str(example['unidad_base']))}.
                  Por el tamaño de compra, se recomiendan <b>{escape(purchase_format_phrase(example['formato_compra'], recommended))}</b>.
                  La orden actual tiene <b>{escape(purchase_format_phrase(example['formato_compra'], ordered))}</b>.
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        if safety_margin:
            st.warning(
                f"Simulación activa: se agregó {safety_margin:.0%} al consumo esperado antes de calcular la compra. "
                "Este ajuste es opcional y no forma parte de la fórmula original."
            )
        else:
            st.info("La simulación está en 0%: se está utilizando la fórmula original.")
        st.markdown(
            "<div class='ops-note'><b>Lo que esta herramienta no puede calcular:</b> los archivos no "
            "contienen precios, ventas, clientes, tiempos de entrega ni niveles de servicio. Por eso no "
            "mostramos ahorro monetario, días de inventario ni demanda por cliente.</div>",
            unsafe_allow_html=True,
        )
        with st.expander("Ver fórmulas y criterios técnicos exactos"):
            st.markdown(
                r"""
                `necesidad_base = max(consumo_proyectado - inventario_actual, 0)`

                `formatos_recomendados = ceil(necesidad_base / unidad_base_por_formato)`

                `cantidad_ordenada_base = formatos_ordenados × unidad_base_por_formato`

                `diferencia_formatos = formatos_ordenados - formatos_recomendados`

                Para detectar valores extremos se usa MAD y modified z-score > 3.5. Solo se excluye un
                valor si quedan al menos cuatro observaciones. Se sigue una tendencia lineal únicamente con
                R² ≥ 0.80 y un cambio estimado de al menos 15% del promedio limpio.
                """
            )


def render_assistant(pipeline: dict[str, object]) -> None:
    section_header(
        "Consulta local",
        "Pregúntale a tus datos",
        "Respuestas derivadas de los DataFrames procesados, sin API keys ni envío de información.",
    )
    st.markdown(
        "<div class='ops-note'><b>Descripción honesta:</b> es un analizador local basado en reglas, no un "
        "modelo generativo. Reconoce preguntas frecuentes en español y responde con los resultados actuales.</div>",
        unsafe_allow_html=True,
    )
    alerts = pipeline["purchase_alerts"]
    review = pipeline["review"]
    overorders = alerts[alerts["tipo_alerta"] == "SOBREPEDIDO"].sort_values(
        "diferencia_formatos", ascending=False
    )
    example_ingredient = (
        overorders.iloc[0]["ingrediente"]
        if not overorders.empty
        else review["nombre"].dropna().iloc[0]
    )
    supplier_totals = (
        review[review["formatos_recomendados"].notna()]
        .groupby("proveedor")["formatos_recomendados"]
        .sum()
        .sort_values(ascending=False)
    )
    example_supplier = supplier_totals.index[0] if not supplier_totals.empty else "el proveedor"
    suggestions = [
        "¿Qué sucursal tiene más riesgos de quiebre?",
        f"¿Quién está pidiendo demasiado {example_ingredient}?",
        "¿Qué productos fueron omitidos?",
        "¿Cuáles sobrepedidos son perecederos?",
        f"¿Qué debo pedirle a {example_supplier}?",
        "¿Qué comportamientos inusuales hay entre sucursales?",
        "¿Qué ingredientes presentan tendencias?",
        "¿Qué datos tienen errores?",
    ]
    st.markdown("##### Preguntas sugeridas")
    for start in range(0, len(suggestions), 4):
        columns = st.columns(4)
        for column, suggestion in zip(columns, suggestions[start : start + 4]):
            column.button(
                suggestion,
                key=f"pro_suggestion_{start}_{suggestion}",
                width="stretch",
                on_click=lambda value=suggestion: st.session_state.update(
                    pro_assistant_question=value
                ),
            )

    question = st.text_input(
        "Escribe tu pregunta",
        placeholder="Ejemplo: ¿Qué productos fueron omitidos?",
        key="pro_assistant_question",
    )
    if question:
        answer = answer_local_question(
            question,
            pipeline["review"],
            pipeline["purchase_alerts"],
            pipeline["quality"],
            pipeline["forecasts"],
            pipeline["behaviors"],
        )
        st.markdown(
            f"""
            <div class="ops-panel" style="margin-top:1rem">
              <div class="ops-kicker">Respuesta basada en los datos actuales</div>
              <div style="margin-top:.55rem;line-height:1.6;font-size:.9rem">{escape(answer)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


try:
    bundle = load_default_data()
except Exception as exc:
    st.error(f"No fue posible cargar los archivos locales: {exc}")
    st.stop()

if "pro_working_order" not in st.session_state:
    initial_order = bundle.orden.copy()
    initial_order["cantidad_formatos"] = pd.to_numeric(
        initial_order["cantidad_formatos"], errors="coerce"
    )
    st.session_state.pro_working_order = initial_order
if "pro_editor_version" not in st.session_state:
    st.session_state.pro_editor_version = 0

weeks = bundle.historico.get("semana", pd.Series(dtype="object")).dropna().astype(str)
last_week = max(weeks, key=week_number) if not weeks.empty else "sin semana"

with st.sidebar:
    st.markdown(
        """
        <div class="ops-brand">
          <span class="ops-brand__word">Barrio</span>
          <span class="ops-brand__meta">Inteligencia de compras</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.subheader("Alcance de revisión")
    st.caption(f"Ciclo posterior a {last_week} · {date.today().strftime('%d/%m/%Y')}")
    safety_margin_percent = st.slider(
        "Margen de seguridad simulado",
        min_value=0,
        max_value=20,
        value=0,
        step=1,
        help="Simulación opcional; no forma parte de la fórmula original.",
        key="pro_safety_margin",
    )

pipeline = run_pipeline(
    bundle,
    st.session_state.pro_working_order,
    safety_margin_percent / 100,
)
review_all = pipeline["review"]
sidebar_operation_status = str(
    globals().get(
        "SIDEBAR_OPERATION_STATUS",
        "4 archivos CSV · sin API keys · sin conexión externa.",
    )
)

with st.sidebar:
    branches = st.multiselect(
        "Sucursales",
        sorted(review_all["sucursal"].dropna().unique()),
        placeholder="Todas las sucursales",
        key="pro_global_branches",
    )
    suppliers = st.multiselect(
        "Proveedores",
        sorted(review_all["proveedor"].dropna().unique()),
        placeholder="Todos los proveedores",
        key="pro_global_suppliers",
    )
    st.caption("Sin selección se incluyen todos los valores.")
    st.divider()
    st.markdown(
        f"""
        <div class="ops-side-note"><span class="ops-live"></span><b>Operación local</b><br>
        {escape(sidebar_operation_status)}<br><br>
        Las recomendaciones son apoyo para la gerente y requieren aprobación antes de emitir compras.</div>
        """,
        unsafe_allow_html=True,
    )

review, alerts, behaviors, quality = scoped_frames(pipeline, branches, suppliers)

st.markdown(
    f"""
    <header class="ops-header">
      <div>
        <div class="ops-eyebrow">Barrio Pizza · abastecimiento semanal</div>
        <h1>Asistente <span class="ops-accent">inteligente</span><br>de compras</h1>
        <p>Del dato a la decisión: consumo, inventario y órdenes convertidos en acciones claras por sucursal, ingrediente y proveedor.</p>
      </div>
      <div class="ops-review">
        <div class="ops-review__label">Revisión activa</div>
        <div class="ops-review__value">Próxima semana después de {escape(last_week)} · {date.today().strftime('%d/%m/%Y')}</div>
        <div class="ops-review__human">● Pendiente de aprobación humana</div>
      </div>
    </header>
    """,
    unsafe_allow_html=True,
)

assistant_page_label = str(globals().get("ASSISTANT_PAGE_LABEL", "Asistente local"))
page_options = [
    "Vista ejecutiva",
    "Alertas",
    "Sucursales",
    "Mesa de compra",
    "Datos y método",
    assistant_page_label,
]
page = st.segmented_control(
    "Navegación principal",
    page_options,
    default=page_options[0],
    selection_mode="single",
    label_visibility="collapsed",
    width="stretch",
    key="pro_navigation",
)

if page == "Vista ejecutiva":
    render_executive(review, alerts, behaviors, quality)
elif page == "Alertas":
    render_alert_center(alerts, behaviors)
elif page == "Sucursales":
    render_branch_workspace(pipeline, review, safety_margin_percent / 100)
elif page == "Mesa de compra":
    render_order_workbench(bundle, pipeline)
elif page == "Datos y método":
    render_data_and_method(pipeline, safety_margin_percent / 100)
elif page == assistant_page_label:
    assistant_renderer = globals().get("ASSISTANT_RENDERER", render_assistant)
    assistant_renderer(pipeline)

st.markdown(
    """
    <footer class="ops-footer">Barrio Pizza · Prototipo local de apoyo a compras ·
    resultados derivados de los CSV cargados · ninguna orden se confirma automáticamente.</footer>
    """,
    unsafe_allow_html=True,
)
