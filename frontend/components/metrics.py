"""
frontend/components/metrics.py
==============================
Reusable enterprise KPI metric cards and summary widgets for Streamlit.
Crafted with zero leading markdown indentation to guarantee flawless HTML rendering.
"""

from typing import Optional
import streamlit as st


def render_kpi_card(
    title: str,
    value: str | int | float,
    subtitle: Optional[str] = None,
    badge: Optional[str] = None,
    badge_type: str = "neutral",
    border_accent: str = "#2563EB",
    icon: Optional[str] = None,
) -> None:
    """
    Renders a styled enterprise KPI card with consistent typography,
    accent border, and semantic pill badges.
    
    Guarantees that all HTML tags are unindented so CommonMark never
    mistakes HTML elements for preformatted code blocks.
    """
    badge_colors = {
        "success": ("#DEF7EC", "#03543F"),
        "warning": ("#FEF3C7", "#92400E"),
        "danger": ("#FDE8E8", "#9B1C1C"),
        "info": ("#E1EFFE", "#1E429F"),
        "purple": ("#EDE9FE", "#5B21B6"),
        "neutral": ("#F1F5F9", "#334155"),
    }
    bg_color, text_color = badge_colors.get(badge_type.lower(), badge_colors["neutral"])

    badge_tag = ""
    if badge:
        badge_tag = (
            f'<span style="background-color: {bg_color}; color: {text_color}; '
            f'padding: 3px 10px; border-radius: 9999px; font-size: 0.72rem; '
            f'font-weight: 700; letter-spacing: 0.03em; display: inline-block;">'
            f'{badge}</span>'
        )

    subtitle_tag = ""
    if subtitle:
        subtitle_tag = (
            f'<div style="font-size: 0.80rem; color: #64748B; margin-top: 6px; '
            f'font-weight: 500; line-height: 1.3;">{subtitle}</div>'
        )

    icon_prefix = f'<span style="margin-right: 6px; font-size: 0.95rem;">{icon}</span>' if icon else ""

    card_html = (
        f'<div style="background: #FFFFFF; border: 1px solid #E2E8F0; '
        f'border-left: 4px solid {border_accent}; border-radius: 10px; '
        f'padding: 16px 18px; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05); '
        f'margin-bottom: 12px; height: 100%; min-height: 110px; box-sizing: border-box;">'
        f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">'
        f'<span style="font-size: 0.75rem; font-weight: 700; text-transform: uppercase; '
        f'letter-spacing: 0.06em; color: #64748B;">{icon_prefix}{title}</span>'
        f'{badge_tag}'
        f'</div>'
        f'<div style="font-size: 1.85rem; font-weight: 800; color: #0F172A; line-height: 1.15; '
        f'letter-spacing: -0.02em;">{value}</div>'
        f'{subtitle_tag}'
        f'</div>'
    )

    st.markdown(card_html, unsafe_allow_html=True)


def render_metric_row(cards: list[dict]) -> None:
    """
    Renders a row of KPI cards evenly spaced in responsive Streamlit columns.
    cards: list of kwargs for render_kpi_card.
    """
    if not cards:
        return
    cols = st.columns(len(cards))
    for col, card in zip(cols, cards):
        with col:
            render_kpi_card(**card)
