"""
frontend/components/tables.py
=============================
Table rendering utilities, column formatters, status badges, page headers,
and structured card containers.
"""

from typing import Any, Optional, Sequence
import pandas as pd
import streamlit as st


def render_page_header(title: str, subtitle: str, icon: Optional[str] = None) -> None:
    """
    Renders a unified modern SaaS page header across all dashboard views.
    Unindented to guarantee clean HTML rendering.
    """
    icon_tag = f'<span style="margin-right: 8px;">{icon}</span>' if icon else ""
    header_html = (
        f'<div style="margin-bottom: 22px;">'
        f'<h1 style="font-size: 1.85rem; font-weight: 800; color: #0F172A; '
        f'margin: 0 0 6px 0; letter-spacing: -0.025em; line-height: 1.2;">'
        f'{icon_tag}{title}</h1>'
        f'<p style="color: #64748B; font-size: 0.95rem; margin: 0; font-weight: 400; line-height: 1.4;">'
        f'{subtitle}</p>'
        f'</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)


def render_info_card(
    title: str,
    items: Sequence[tuple[str, Any]],
    subtitle: Optional[str] = None,
    accent_color: str = "#2563EB",
) -> None:
    """
    Renders an enterprise key-value profile/inspection card.
    Perfect for candidate profiles, requisition summaries, and offer audits.
    """
    rows_html = "".join(
        f'<div style="display: flex; justify-content: space-between; align-items: center; '
        f'padding: 7px 0; border-bottom: 1px solid #F1F5F9; font-size: 0.88rem;">'
        f'<span style="color: #64748B; font-weight: 500;">{k}</span>'
        f'<span style="color: #0F172A; font-weight: 600; text-align: right;">{v}</span>'
        f'</div>'
        for k, v in items
    )
    footer_html = (
        f'<div style="font-size: 0.78rem; color: #94A3B8; margin-top: 10px; font-weight: 500;">'
        f'{subtitle}</div>'
        if subtitle
        else ""
    )
    card_html = (
        f'<div style="background: #FFFFFF; border: 1px solid #E2E8F0; '
        f'border-top: 3px solid {accent_color}; border-radius: 8px; padding: 18px 20px; '
        f'box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04); margin-bottom: 14px;">'
        f'<div style="font-size: 0.98rem; font-weight: 700; color: #0F172A; '
        f'margin-bottom: 10px; border-bottom: 2px solid #F8FAFC; padding-bottom: 6px;">'
        f'{title}</div>'
        f'{rows_html}'
        f'{footer_html}'
        f'</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)


def render_status_badge(status_str: str) -> str:
    """
    Returns HTML for a colored pill badge based on entity status.
    Single-line output with zero indentation.
    """
    status_lower = str(status_str).lower().replace(" ", "_")

    badge_styles = {
        # Positive / Completed
        "hired": ("#DEF7EC", "#03543F"),
        "accepted": ("#DEF7EC", "#03543F"),
        "open": ("#DEF7EC", "#03543F"),
        "completed": ("#DEF7EC", "#03543F"),
        "strong_hire": ("#DEF7EC", "#03543F"),
        "hire": ("#DEF7EC", "#03543F"),
        "resolved": ("#DEF7EC", "#03543F"),

        # Info / In Progress
        "screening": ("#E1EFFE", "#1E429F"),
        "interview": ("#E1EFFE", "#1E429F"),
        "scheduled": ("#E1EFFE", "#1E429F"),
        "approved": ("#E1EFFE", "#1E429F"),
        "released": ("#EDE9FE", "#5B21B6"),
        "investigating": ("#E1EFFE", "#1E429F"),

        # Warning / Pending
        "applied": ("#FEF3C7", "#92400E"),
        "assessment": ("#FEF3C7", "#92400E"),
        "draft": ("#F1F5F9", "#475569"),
        "pending_approval": ("#FEF3C7", "#92400E"),
        "hold": ("#FEF3C7", "#92400E"),

        # Danger / Negative
        "rejected": ("#FDE8E8", "#9B1C1C"),
        "declined": ("#FDE8E8", "#9B1C1C"),
        "cancelled": ("#FDE8E8", "#9B1C1C"),
        "no_hire": ("#FDE8E8", "#9B1C1C"),
        "expired": ("#F1F5F9", "#64748B"),
        "closed": ("#F1F5F9", "#64748B"),
        "critical": ("#FDE8E8", "#9B1C1C"),
        "high": ("#FFEDD5", "#C2410C"),
        "medium": ("#FEF3C7", "#92400E"),
        "low": ("#E1EFFE", "#1E429F"),
    }

    bg, fg = badge_styles.get(status_lower, ("#F1F5F9", "#334155"))
    display_text = str(status_str).replace("_", " ").title()

    return (
        f'<span style="background-color: {bg}; color: {fg}; padding: 3px 10px; '
        f'border-radius: 9999px; font-size: 0.75rem; font-weight: 600; '
        f'letter-spacing: 0.02em; display: inline-block;">{display_text}</span>'
    )


def render_empty_state(message: str = "No records found.", action_hint: Optional[str] = None) -> None:
    """Renders a friendly SaaS empty state placeholder with zero leading indentation."""
    action_html = (
        f'<p style="color: #64748B; font-size: 0.85rem; margin-top: 4px;">{action_hint}</p>'
        if action_hint
        else ""
    )
    html = (
        f'<div style="text-align: center; padding: 40px 20px; background: #F8FAFC; '
        f'border: 2px dashed #CBD5E1; border-radius: 8px; margin: 20px 0;">'
        f'<div style="font-size: 2.2rem; margin-bottom: 8px;">📋</div>'
        f'<div style="font-size: 1.05rem; font-weight: 600; color: #1E293B;">{message}</div>'
        f'{action_html}'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def format_currency(val: Any) -> str:
    """Format numeric or Decimal value as standard Indian Rupee (INR) currency string."""
    if val is None:
        return "N/A"
    try:
        amt = float(val)
        return f"INR {amt:,.2f}"
    except (ValueError, TypeError):
        return str(val)
