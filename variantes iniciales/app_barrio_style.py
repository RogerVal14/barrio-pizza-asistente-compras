"""Variante Streamlit del dashboard con el sistema visual Barrio.

La aplicación reutiliza íntegramente la lógica y las pantallas de ``app.py``.
Solo sustituye la capa de estilos y el tema de gráficos, por lo que las reglas
de validación, proyección y compra permanecen en una única implementación.

Ejecución::

    streamlit run app_barrio_style.py
"""

from __future__ import annotations

from pathlib import Path

from src import ui_helpers
from src.design_system import apply_barrio_design, register_plotly_theme


register_plotly_theme()
ui_helpers.inject_app_css = apply_barrio_design

_SOURCE_APP = Path(__file__).with_name("app.py")
if not _SOURCE_APP.exists():
    raise FileNotFoundError(f"No se encontró el dashboard base: {_SOURCE_APP.name}")

exec(
    compile(_SOURCE_APP.read_text(encoding="utf-8"), str(_SOURCE_APP), "exec"),
    globals(),
    globals(),
)

