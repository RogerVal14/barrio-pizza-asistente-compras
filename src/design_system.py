"""Sistema visual inspirado en la experiencia pública de Barrio Pizza.

El módulo concentra tokens, estilos de Streamlit y el tema de Plotly. No
descarga fuentes ni imágenes: la aplicación conserva su funcionamiento sin
internet y usa alternativas tipográficas instaladas en el sistema.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import plotly.graph_objects as go
import plotly.io as pio


class StreamlitMarkdown(Protocol):
    """Contrato mínimo requerido para inyectar el sistema visual."""

    def markdown(self, body: str, *, unsafe_allow_html: bool = False) -> object:
        """Renderiza contenido Markdown o HTML."""


@dataclass(frozen=True, slots=True)
class BarrioDesignTokens:
    """Tokens reutilizables derivados de la identidad observada en el sitio."""

    ink: str = "#231F20"
    brown: str = "#3F231A"
    red: str = "#CF2F2C"
    cream: str = "#F0E8E0"
    bone: str = "#F9F7F4"
    white: str = "#FFFFFF"
    amber: str = "#D98E2B"
    green: str = "#3F7652"
    blue: str = "#456A80"
    font_display: str = '"Arial Narrow", "Roboto Condensed", Impact, sans-serif'
    font_body: str = '"Aptos", "Segoe UI", Arial, sans-serif'
    radius_small: str = "10px"
    radius_medium: str = "16px"
    radius_pill: str = "999px"
    shadow: str = "0 12px 30px rgba(35, 31, 32, 0.10)"


BARRIO_TOKENS = BarrioDesignTokens()


_BASE_CSS = r"""
html, body, [class*="css"] {
  font-family: var(--bp-font-body);
}

.stApp {
  background:
    radial-gradient(circle at 96% 2%, rgba(207, 47, 44, .10), transparent 22rem),
    linear-gradient(180deg, var(--bp-bone) 0%, #ffffff 58%, var(--bp-cream) 100%);
  color: var(--bp-ink);
}

[data-testid="stAppViewContainer"] > .main .block-container {
  max-width: 1480px;
  padding-top: 1.25rem;
  padding-bottom: 4rem;
}

[data-testid="stHeader"] {
  background: rgba(249, 247, 244, .86);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(35, 31, 32, .08);
}

/* Barra lateral: panel operativo oscuro, como la navegación del sitio. */
[data-testid="stSidebar"] {
  background:
    linear-gradient(165deg, rgba(207, 47, 44, .15), transparent 38%),
    var(--bp-ink);
  border-right: 1px solid rgba(255, 255, 255, .08);
}

[data-testid="stSidebar"]::before {
  content: "BARRIO\A COMPRAS";
  white-space: pre;
  display: block;
  padding: 1.6rem 1.4rem .8rem;
  color: var(--bp-white);
  font-family: var(--bp-font-display);
  font-size: 2rem;
  font-weight: 900;
  font-stretch: condensed;
  letter-spacing: -.03em;
  line-height: .84;
}

[data-testid="stSidebar"]::after {
  content: "SI HAY DATOS";
  position: absolute;
  top: 2.05rem;
  right: 1.25rem;
  color: var(--bp-red);
  font-size: .62rem;
  font-weight: 800;
  letter-spacing: .18em;
}

[data-testid="stSidebar"] * {
  color: var(--bp-white);
}

[data-testid="stSidebar"] hr {
  border-color: rgba(255, 255, 255, .14);
}

[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] [data-baseweb="input"] > div,
[data-testid="stSidebar"] input {
  background: rgba(255, 255, 255, .08);
  border-color: rgba(255, 255, 255, .18);
}

[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
  color: rgba(255, 255, 255, .66);
}

h1, h2, h3, .stHeading {
  color: var(--bp-ink);
}

h1, h2, h3 {
  font-family: var(--bp-font-display);
  font-stretch: condensed;
}

h2 {
  text-transform: uppercase;
  letter-spacing: -.02em;
}

/* Hero editorial de alto contraste. */
.bp-hero {
  isolation: isolate;
  position: relative;
  overflow: hidden;
  min-height: 240px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 2rem clamp(1.35rem, 4vw, 3.6rem);
  margin: .25rem 0 1rem;
  color: var(--bp-white);
  background:
    linear-gradient(115deg, rgba(35, 31, 32, .98) 0%, rgba(35, 31, 32, .94) 55%, rgba(63, 35, 26, .91) 100%),
    repeating-linear-gradient(-20deg, transparent 0 18px, rgba(255,255,255,.035) 18px 20px);
  border: 1px solid rgba(255, 255, 255, .08);
  border-radius: var(--bp-radius-md);
  box-shadow: var(--bp-shadow);
}

.bp-hero::before {
  content: "";
  position: absolute;
  z-index: -1;
  width: 290px;
  height: 290px;
  right: -75px;
  bottom: -130px;
  border: 42px solid var(--bp-red);
  border-radius: 50%;
  opacity: .9;
}

.bp-hero::after {
  content: "COMPRAS";
  position: absolute;
  z-index: -1;
  right: 1rem;
  top: -.2rem;
  color: rgba(255, 255, 255, .035);
  font-family: var(--bp-font-display);
  font-size: clamp(6rem, 15vw, 13rem);
  font-weight: 900;
  line-height: 1;
  letter-spacing: -.045em;
}

.bp-hero h1 {
  max-width: 980px;
  margin: 0;
  color: var(--bp-white);
  font-family: var(--bp-font-display);
  font-size: clamp(2.25rem, 5.2vw, 5.4rem);
  font-weight: 900;
  letter-spacing: -.045em;
  line-height: .92;
  text-transform: uppercase;
}

.bp-hero h1::first-line {
  color: var(--bp-white);
}

.bp-hero p {
  max-width: 760px;
  margin: 1rem 0 0;
  color: rgba(255, 255, 255, .76);
  font-size: 1rem;
  letter-spacing: .025em;
}

.bp-human {
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  margin-top: 1.1rem;
  padding: .48rem .85rem;
  color: var(--bp-white);
  background: var(--bp-red);
  border-radius: var(--bp-radius-pill);
  font-size: .76rem;
  font-weight: 800;
  letter-spacing: .055em;
  text-transform: uppercase;
}

/* Tarjetas KPI con jerarquía visual y contraste suficiente. */
[data-testid="stMetric"] {
  position: relative;
  min-height: 126px;
  overflow: hidden;
  padding: 1rem 1.05rem 1.05rem;
  background: rgba(255, 255, 255, .93);
  border: 1px solid rgba(35, 31, 32, .14);
  border-radius: var(--bp-radius-sm);
  box-shadow: 0 8px 20px rgba(35, 31, 32, .06);
}

[data-testid="stMetric"]::before {
  content: "";
  position: absolute;
  inset: 0 auto 0 0;
  width: 6px;
  background: var(--bp-red);
}

[data-testid="stMetricLabel"] p {
  color: rgba(35, 31, 32, .68);
  font-size: .75rem;
  font-weight: 800;
  letter-spacing: .055em;
  line-height: 1.25;
  text-transform: uppercase;
}

[data-testid="stMetricValue"] {
  color: var(--bp-ink);
  font-family: var(--bp-font-display);
  font-size: clamp(1.7rem, 3vw, 2.45rem);
  font-weight: 900;
  letter-spacing: -.02em;
}

/* Alertas: estructura y texto complementan el color. */
.bp-alert {
  position: relative;
  padding: 1.05rem 1.2rem 1.05rem 1.35rem;
  margin: .75rem 0;
  color: var(--bp-ink);
  background: var(--bp-white);
  border: 1px solid rgba(35, 31, 32, .16);
  border-left: 8px solid var(--bp-red);
  border-radius: var(--bp-radius-sm);
  box-shadow: 0 8px 18px rgba(35, 31, 32, .07);
}

.bp-alert strong {
  font-family: var(--bp-font-display);
  font-size: 1.12rem;
  letter-spacing: .02em;
  text-transform: uppercase;
}

.bp-alert small {
  color: rgba(35, 31, 32, .68);
}

.bp-note {
  padding: .95rem 1.05rem;
  color: var(--bp-ink);
  background: var(--bp-cream);
  border: 1px solid rgba(63, 35, 26, .26);
  border-left: 7px solid var(--bp-brown);
  border-radius: var(--bp-radius-sm);
}

/* Botones píldora, inspirados en la llamada a la acción del sitio. */
div.stButton > button,
div.stDownloadButton > button,
[data-testid="stFileUploaderDropzone"] button {
  min-height: 2.65rem;
  padding-inline: 1.15rem;
  color: var(--bp-white);
  background: var(--bp-red);
  border: 1px solid var(--bp-red);
  border-radius: var(--bp-radius-pill);
  font-family: var(--bp-font-body);
  font-size: .78rem;
  font-weight: 800;
  letter-spacing: .075em;
  text-transform: uppercase;
  transition: transform .16s ease, background .16s ease, box-shadow .16s ease;
}

div.stButton > button:hover,
div.stDownloadButton > button:hover,
[data-testid="stFileUploaderDropzone"] button:hover {
  color: var(--bp-white);
  background: var(--bp-ink);
  border-color: var(--bp-ink);
  box-shadow: 0 8px 18px rgba(35, 31, 32, .18);
  transform: translateY(-1px);
}

div.stButton > button:focus-visible,
div.stDownloadButton > button:focus-visible,
button[data-baseweb="tab"]:focus-visible {
  outline: 3px solid var(--bp-amber);
  outline-offset: 3px;
}

/* Navegación de pestañas con lectura de sección activa. */
div[data-baseweb="tab-list"] {
  gap: .2rem;
  padding: .2rem;
  background: var(--bp-ink);
  border-radius: var(--bp-radius-sm);
}

button[data-baseweb="tab"] {
  min-height: 3.25rem;
  color: rgba(255, 255, 255, .72);
  background: transparent;
  border-radius: calc(var(--bp-radius-sm) - 3px);
  font-size: .72rem;
  font-weight: 800;
  letter-spacing: .045em;
  text-transform: uppercase;
}

button[data-baseweb="tab"][aria-selected="true"] {
  color: var(--bp-white);
  background: var(--bp-red);
}

button[data-baseweb="tab"] > div[data-testid="stMarkdownContainer"] p {
  color: inherit;
}

[data-testid="stDataFrame"],
[data-testid="stDataEditor"] {
  overflow: hidden;
  background: var(--bp-white);
  border: 1px solid rgba(35, 31, 32, .14);
  border-radius: var(--bp-radius-sm);
  box-shadow: 0 6px 16px rgba(35, 31, 32, .05);
}

[data-testid="stPlotlyChart"] {
  overflow: hidden;
  background: var(--bp-white);
  border: 1px solid rgba(35, 31, 32, .10);
  border-radius: var(--bp-radius-md);
  box-shadow: 0 8px 22px rgba(35, 31, 32, .05);
}

[data-testid="stExpander"] {
  background: rgba(255, 255, 255, .78);
  border: 1px solid rgba(35, 31, 32, .13);
  border-radius: var(--bp-radius-sm);
}

[data-testid="stFileUploaderDropzone"] {
  background: var(--bp-cream);
  border-color: rgba(63, 35, 26, .35);
  border-radius: var(--bp-radius-sm);
}

[data-testid="stCaptionContainer"] p {
  color: rgba(35, 31, 32, .60);
  font-size: .78rem;
  letter-spacing: .025em;
}

code {
  color: var(--bp-red);
  background: rgba(207, 47, 44, .08);
  border-radius: 5px;
}

a {
  color: var(--bp-red);
}

@media (max-width: 900px) {
  [data-testid="stAppViewContainer"] > .main .block-container {
    padding-inline: 1rem;
  }

  .bp-hero {
    min-height: 220px;
    border-radius: var(--bp-radius-sm);
  }

  .bp-hero::after {
    top: 1.2rem;
    font-size: 6rem;
  }

  div[data-baseweb="tab-list"] {
    overflow-x: auto;
    justify-content: flex-start;
  }

  button[data-baseweb="tab"] {
    flex: 0 0 auto;
    min-width: max-content;
  }
}

@media (max-width: 520px) {
  .bp-hero {
    min-height: 245px;
    padding: 1.5rem 1.15rem;
  }

  .bp-hero h1 {
    font-size: 2.25rem;
  }

  .bp-hero p {
    font-size: .9rem;
  }

  .bp-human {
    font-size: .66rem;
  }

  [data-testid="stMetric"] {
    min-height: 108px;
  }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    scroll-behavior: auto !important;
    transition: none !important;
  }
}
"""


def build_barrio_css(tokens: BarrioDesignTokens = BARRIO_TOKENS) -> str:
    """Construye el bloque CSS autocontenido del sistema de diseño."""

    variables = f"""
    :root {{
      --bp-ink: {tokens.ink};
      --bp-brown: {tokens.brown};
      --bp-red: {tokens.red};
      --bp-cream: {tokens.cream};
      --bp-bone: {tokens.bone};
      --bp-white: {tokens.white};
      --bp-amber: {tokens.amber};
      --bp-green: {tokens.green};
      --bp-blue: {tokens.blue};
      --bp-font-display: {tokens.font_display};
      --bp-font-body: {tokens.font_body};
      --bp-radius-sm: {tokens.radius_small};
      --bp-radius-md: {tokens.radius_medium};
      --bp-radius-pill: {tokens.radius_pill};
      --bp-shadow: {tokens.shadow};
    }}
    """
    return f"<style>{variables}{_BASE_CSS}</style>"


def apply_barrio_design(st_module: StreamlitMarkdown) -> None:
    """Aplica el tema a una aplicación Streamlit compatible."""

    st_module.markdown(build_barrio_css(), unsafe_allow_html=True)


def register_plotly_theme(
    tokens: BarrioDesignTokens = BARRIO_TOKENS,
    template_name: str = "barrio_dashboard",
) -> str:
    """Registra y activa un tema Plotly coherente con los tokens visuales."""

    template = go.layout.Template(
        layout=go.Layout(
            font={"family": tokens.font_body, "color": tokens.ink},
            title={"font": {"family": tokens.font_display, "color": tokens.ink}},
            paper_bgcolor=tokens.white,
            plot_bgcolor=tokens.white,
            colorway=[
                tokens.red,
                tokens.ink,
                tokens.brown,
                tokens.amber,
                tokens.green,
                tokens.blue,
                "#8D6E63",
            ],
            hoverlabel={
                "bgcolor": tokens.ink,
                "bordercolor": tokens.red,
                "font": {"color": tokens.white, "family": tokens.font_body},
            },
            xaxis={
                "gridcolor": "rgba(35,31,32,0.10)",
                "linecolor": "rgba(35,31,32,0.26)",
                "zerolinecolor": "rgba(35,31,32,0.18)",
            },
            yaxis={
                "gridcolor": "rgba(35,31,32,0.10)",
                "linecolor": "rgba(35,31,32,0.26)",
                "zerolinecolor": "rgba(35,31,32,0.18)",
            },
            legend={
                "bgcolor": "rgba(249,247,244,0.84)",
                "bordercolor": "rgba(35,31,32,0.12)",
                "borderwidth": 1,
            },
        )
    )
    pio.templates[template_name] = template
    pio.templates.default = template_name
    return template_name

