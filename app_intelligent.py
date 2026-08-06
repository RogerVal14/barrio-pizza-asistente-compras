"""Variante profesional con chat opcional de Gemini.

Reutiliza íntegramente ``app_profesional.py`` y sustituye únicamente la página
del asistente. Si Gemini no está configurado, continúa con el analizador local.

Ejecución::

    streamlit run app_intelligent.py
"""

from __future__ import annotations

from pathlib import Path

from src.intelligent_ui import render_intelligent_assistant


ASSISTANT_PAGE_LABEL = "Asistente inteligente"
ASSISTANT_RENDERER = render_intelligent_assistant
SIDEBAR_OPERATION_STATUS = "4 archivos CSV · cálculos locales · Gemini opcional."

_WRAPPER_FILE = Path(__file__).resolve()
_SOURCE_APP = _WRAPPER_FILE.parent / "variantes iniciales" / "app_profesional.py"
if not _SOURCE_APP.exists():
    raise FileNotFoundError(f"No se encontró el dashboard profesional: {_SOURCE_APP}")

try:
    globals()["__file__"] = str(_SOURCE_APP)
    exec(
        compile(_SOURCE_APP.read_text(encoding="utf-8"), str(_SOURCE_APP), "exec"),
        globals(),
        globals(),
    )
finally:
    globals()["__file__"] = str(_WRAPPER_FILE)
