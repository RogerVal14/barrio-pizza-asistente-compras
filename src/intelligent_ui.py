"""Interfaz Streamlit del asistente opcional con Gemini."""

from __future__ import annotations

import os

import streamlit as st

from src.gemini_assistant import (
    GEMINI_MODEL,
    answer_with_fallback,
    build_evidence_frame,
    google_genai_available,
    load_gemini_api_key,
)
from src.ui_helpers import answer_local_question


MODE_GEMINI = "IA generativa"
MODE_LOCAL = "Asistente local"


def _local_answer(question: str, pipeline: dict[str, object]) -> str:
    return answer_local_question(
        question,
        pipeline["review"],
        pipeline["purchase_alerts"],
        pipeline["quality"],
        pipeline["forecasts"],
        pipeline["behaviors"],
    )


def _suggested_questions(pipeline: dict[str, object]) -> list[tuple[str, str]]:
    alerts = pipeline["purchase_alerts"]
    review = pipeline["review"]
    overorders = alerts[alerts["tipo_alerta"] == "SOBREPEDIDO"].sort_values(
        "diferencia_formatos", ascending=False
    )
    ingredient = (
        str(overorders.iloc[0]["ingrediente"])
        if not overorders.empty
        else str(review["nombre"].dropna().iloc[0])
    )
    supplier_totals = (
        review[review["formatos_recomendados"].notna()]
        .groupby("proveedor")["formatos_recomendados"]
        .sum()
        .sort_values(ascending=False)
    )
    supplier = str(supplier_totals.index[0]) if not supplier_totals.empty else "el proveedor"
    return [
        ("Mayor riesgo de quiebre", "¿Qué sucursal tiene más riesgos de quiebre?"),
        (f"Exceso de {ingredient}", f"¿Quién está pidiendo demasiado {ingredient}?"),
        ("Productos omitidos", "¿Qué productos fueron omitidos?"),
        (f"Pedido a {supplier}", f"¿Qué debo pedirle a {supplier}?"),
        (
            "Sobrepedidos perecederos",
            "¿Cuáles sobrepedidos corresponden a productos perecederos?",
        ),
        ("Errores antes de aprobar", "¿Qué datos debo corregir antes de aprobar?"),
    ]


def _render_history(gemini_ready: bool) -> None:
    for message in st.session_state.intelligent_chat_history:
        avatar = "👤" if message["role"] == "user" else "🤖"
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                mode = str(message.get("mode", MODE_LOCAL))
                evidences = message.get("evidences") or []
                source_count = len(evidences)
                source_label = (
                    f" · {source_count} evidencia{'s' if source_count != 1 else ''}"
                    if source_count
                    else ""
                )
                mode_icon = "✨" if mode == MODE_GEMINI else "🧭"
                st.caption(f"{mode_icon} {mode}{source_label}")

                warning = str(message.get("warning") or "").strip()
                if gemini_ready and "no está configurado" in warning.lower():
                    warning = "Esta respuesta anterior se generó con el respaldo local."
                if evidences or warning:
                    detail_label = "Fuentes y detalles"
                    if warning:
                        detail_label = "⚠️ Fuentes y limitaciones"
                    with st.expander(detail_label, expanded=False):
                        if evidences:
                            st.markdown("**Evidencias:** " + ", ".join(evidences))
                        if warning:
                            st.caption(warning)


def _inject_chat_css() -> None:
    st.markdown(
        """
        <style>
        .ops-chat-status {
            display:flex; flex-wrap:wrap; gap:.45rem 1rem; align-items:center;
            margin:.35rem 0 .75rem; padding:.65rem .85rem; border:1px solid #ded6cc;
            border-radius:12px; background:rgba(255,255,255,.58); color:#5f574f;
            font-size:.88rem;
        }
        .ops-chat-status strong { color:#25211e; }
        .ops-chat-dot { width:.55rem; height:.55rem; border-radius:50%; background:#2a9362; }
        .ops-chat-dot--local { background:#d58a24; }
        div[data-testid="stChatMessage"] {
            padding:.7rem .9rem; margin-bottom:.55rem; border:1px solid #e4ded7;
            border-radius:14px; background:rgba(255,255,255,.62);
        }
        div[data-testid="stChatMessage"] p { margin-bottom:.35rem; }
        div[data-testid="stExpander"] { margin-top:.2rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_intelligent_assistant(pipeline: dict[str, object]) -> None:
    """Presenta Gemini de forma opcional y mantiene siempre el respaldo local."""

    _inject_chat_css()
    st.markdown("### 💬 Pregúntale a tus datos")
    st.caption(
        "Las cifras fueron calculadas previamente por Python. La IA solo interpreta y redacta "
        "respuestas a partir de un subconjunto de esos resultados."
    )

    try:
        api_key = load_gemini_api_key(st.secrets, os.environ)
    except Exception:
        api_key = load_gemini_api_key(None, os.environ)
    sdk_ready = google_genai_available()
    gemini_ready = bool(api_key and sdk_ready)

    if "intelligent_chat_history" not in st.session_state:
        st.session_state.intelligent_chat_history = []
    if "intelligent_chat_mode" not in st.session_state:
        st.session_state.intelligent_chat_mode = MODE_GEMINI if gemini_ready else MODE_LOCAL
    if not gemini_ready:
        st.session_state.intelligent_chat_mode = MODE_LOCAL

    top = st.columns([1.55, .45])
    with top[0]:
        selected_mode = st.segmented_control(
            "Modo de respuesta",
            [MODE_GEMINI, MODE_LOCAL],
            key="intelligent_chat_mode",
            width="stretch",
        )
    with top[1]:
        st.write("")
        if st.button("🗑️ Limpiar", key="clear_intelligent_chat", width="stretch"):
            st.session_state.intelligent_chat_history = []
            st.session_state.pop("intelligent_pending_question", None)
            st.rerun()

    if gemini_ready:
        status_html = (
            "<span class='ops-chat-dot'></span><strong>Gemini activo</strong>"
            f"<span>{GEMINI_MODEL}</span>"
        )
    else:
        reasons = []
        if not api_key:
            reasons.append("no se encontró GEMINI_API_KEY")
        if not sdk_ready:
            reasons.append("google-genai no está instalado")
        status_html = (
            "<span class='ops-chat-dot ops-chat-dot--local'></span>"
            "<strong>Respaldo local activo</strong><span>"
            + " y ".join(reasons)
            + "</span>"
        )
        selected_mode = MODE_LOCAL

    st.markdown(
        "<div class='ops-chat-status'>"
        + status_html
        + "<span>·</span><span>Las cifras las calcula Python</span>"
        "<span>·</span><span><strong>Verificar antes de aprobar</strong></span></div>",
        unsafe_allow_html=True,
    )

    suggestions = _suggested_questions(pipeline)
    history_is_empty = not st.session_state.intelligent_chat_history
    with st.expander("Preguntas sugeridas", expanded=history_is_empty):
        for start in range(0, len(suggestions), 3):
            columns = st.columns(3)
            for column, (label, question_value) in zip(
                columns, suggestions[start : start + 3]
            ):
                column.button(
                    label,
                    key=f"intelligent_suggestion_{start}_{label}",
                    width="stretch",
                    on_click=lambda value=question_value: st.session_state.update(
                        intelligent_pending_question=value
                    ),
                )

    _render_history(gemini_ready)
    pending = st.session_state.pop("intelligent_pending_question", None)
    typed = st.chat_input("Escribe una pregunta sobre compras, alertas o proveedores")
    question = pending or typed
    if not question:
        return

    st.session_state.intelligent_chat_history.append(
        {"role": "user", "content": str(question)}
    )
    evidence = build_evidence_frame(
        pipeline["review"],
        pipeline["purchase_alerts"],
        pipeline["quality"],
        pipeline["unknown_order"],
    )

    if selected_mode == MODE_GEMINI and gemini_ready:
        with st.spinner("Gemini está redactando una respuesta basada en la evidencia..."):
            result = answer_with_fallback(
                str(question),
                evidence,
                api_key,
                lambda value: _local_answer(value, pipeline),
            )
    else:
        result = answer_with_fallback(
            str(question),
            evidence,
            None,
            lambda value: _local_answer(value, pipeline),
        )

    st.session_state.intelligent_chat_history.append(
        {
            "role": "assistant",
            "content": result.respuesta,
            "mode": result.modo_usado,
            "evidences": list(result.evidencias),
            "warning": result.advertencia,
        }
    )
    st.rerun()
