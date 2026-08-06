"""Pruebas del sistema visual alternativo."""

from pathlib import Path

import plotly.io as pio

from src.design_system import BARRIO_TOKENS, build_barrio_css, register_plotly_theme


def test_design_tokens_are_present_in_css() -> None:
    css = build_barrio_css()

    assert BARRIO_TOKENS.ink in css
    assert BARRIO_TOKENS.red in css
    assert BARRIO_TOKENS.cream in css
    assert BARRIO_TOKENS.bone in css
    assert "prefers-reduced-motion" in css
    assert "focus-visible" in css


def test_design_system_has_no_external_runtime_dependency() -> None:
    css = build_barrio_css().lower()

    assert "http://" not in css
    assert "https://" not in css
    assert "@import" not in css


def test_plotly_theme_can_be_registered() -> None:
    template_name = register_plotly_theme(template_name="barrio_dashboard_test")

    assert template_name in pio.templates
    assert pio.templates[template_name].layout.paper_bgcolor == BARRIO_TOKENS.white


def test_styled_entrypoint_reuses_the_base_dashboard() -> None:
    source = Path("variantes iniciales/app_barrio_style.py").read_text(encoding="utf-8")

    assert 'with_name("app.py")' in source
    assert "apply_barrio_design" in source
    assert "register_plotly_theme" in source


def test_professional_dashboard_uses_barrio_brand_system() -> None:
    source = Path("variantes iniciales/app_profesional.py").read_text(encoding="utf-8")

    assert "--ops-ink: #231f20" in source
    assert "--ops-red: #cf2f2c" in source
    assert "ops-brand__word" in source
    assert "ops-header::after" in source
    assert "ops-accent" in source
    assert 'data-testid="stButtonGroup"' in source
    assert 'data-testid="stExpandSidebarButton"' in source
    assert '[data-testid="stToolbar"] { visibility: hidden; }' not in source
    assert "--ops-pizza-cursor" in source
    assert ") 2 2, default;" in source
    assert ".stApp, .stApp *" in source
    assert "if chart_title:" in source
    assert "prefers-reduced-motion" in source
    assert "https://barriopizza.com" not in source


def test_intelligent_assistant_inherits_brand_hierarchy() -> None:
    source = Path("src/intelligent_ui.py").read_text(encoding="utf-8")

    assert "ops-chat-intro" in source
    assert "ops-chat-accent" in source
    assert 'label_visibility="collapsed"' in source
