"""
frontend/components/charts.py
=============================
Plotly interactive chart builders styled with modern enterprise SaaS aesthetics.
Features robust sizing, automatic margin handling, formatted date axes,
prevented label overlaps, and accessible high-contrast color palettes.
"""

from datetime import datetime
from typing import Any, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Enterprise SaaS Color System
# ---------------------------------------------------------------------------
COLOR_PRIMARY = "#2563EB"       # Enterprise Blue
COLOR_SUCCESS = "#10B981"       # Emerald
COLOR_WARNING = "#F59E0B"       # Amber
COLOR_DANGER = "#DC2626"        # Crimson
COLOR_PURPLE = "#8B5CF6"        # Violet
COLOR_INDIGO = "#6366F1"        # Indigo
COLOR_SLATE = "#64748B"         # Slate Grey

PALETTE = [
    "#2563EB", "#10B981", "#8B5CF6", "#F59E0B", "#EC4899",
    "#06B6D4", "#6366F1", "#14B8A6", "#F97316", "#84CC16"
]

RULE_LABELS = {
    "A01": "A01 – Candidate Experience",
    "A02": "A02 – Duplicate Applications",
    "A03": "A03 – Interview Assignment",
    "A04": "A04 – Interview Scheduling",
    "A05": "A05 – Scorecard Integrity",
    "A06": "A06 – Offer Approvals",
    "A07": "A07 – Offer Lifecycle Dates",
    "A08": "A08 – Salary Boundary Deviations",
    "A09": "A09 – Workflow Transitions",
    "A10": "A10 – Recruitment Process Consistency",
}

LAYOUT_DEFAULTS = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, system-ui, -apple-system, sans-serif", color="#1E293B", size=12),
)


def _format_month(month_str: str) -> str:
    """Format 'YYYY-MM' or ISO date to 'Mon YYYY' (e.g. 'Jan 2025')."""
    if not month_str:
        return ""
    try:
        clean = str(month_str)[:7]
        dt = datetime.strptime(clean, "%Y-%m")
        return dt.strftime("%b %Y")
    except Exception:
        return str(month_str)


# ---------------------------------------------------------------------------
# 1. Pipeline Funnel Chart
# ---------------------------------------------------------------------------

def chart_stage_funnel(stage_counts: dict[str, int]) -> go.Figure:
    """Funnel chart displaying candidate flow across hiring stages."""
    preferred_order = [
        "applied", "screening", "interview", "assessment", "offer", "hired"
    ]
    stages = [s for s in preferred_order if s in stage_counts]
    for s in stage_counts:
        if s not in stages and s != "rejected":
            stages.append(s)

    counts = [stage_counts.get(s, 0) for s in stages]
    labels = [s.replace("_", " ").title() for s in stages]

    funnel_colors = [
        "#3B82F6", "#2563EB", "#6366F1", "#8B5CF6", "#10B981", "#059669"
    ][:len(stages)]

    fig = go.Figure(go.Funnel(
        y=labels,
        x=counts,
        textinfo="value+percent initial",
        marker=dict(color=funnel_colors),
        connector=dict(line=dict(color="#CBD5E1", width=1.5)),
        hovertemplate="<b>%{y}</b><br>Candidates: %{x:,}<br>Yield from Applied: %{percentInitial:.1%}<extra></extra>",
    ))

    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title=dict(
            text="<b>Application Pipeline Funnel</b>",
            font=dict(size=14, color="#0F172A"),
            x=0.02,
        ),
        margin=dict(l=40, r=40, t=55, b=30),
        height=380,
    )
    return fig


# ---------------------------------------------------------------------------
# 2. Recruitment Source Distribution Donut Chart
# ---------------------------------------------------------------------------

def chart_source_distribution(source_counts: dict[str, int]) -> go.Figure:
    """Donut chart showing applications by recruitment channel without label collisions."""
    if not source_counts:
        fig = go.Figure()
        fig.update_layout(**LAYOUT_DEFAULTS, title="No recruitment source data available")
        return fig

    df = pd.DataFrame(list(source_counts.items()), columns=["Source", "Applications"])
    df = df.sort_values(by="Applications", ascending=False)

    fig = px.pie(
        df,
        names="Source",
        values="Applications",
        hole=0.60,
        color_discrete_sequence=PALETTE,
    )
    fig.update_traces(
        textposition="auto",
        textinfo="percent",
        hovertemplate="<b>%{label}</b><br>Applications: %{value:,}<br>Share: %{percent}<extra></extra>",
        marker=dict(line=dict(color="#FFFFFF", width=2)),
    )
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title=dict(
            text="<b>Applications by Recruitment Source</b>",
            font=dict(size=14, color="#0F172A"),
            x=0.02,
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.25,
            xanchor="center",
            x=0.5,
            font=dict(size=11),
        ),
        margin=dict(l=20, r=20, t=55, b=65),
        height=380,
    )
    return fig


# ---------------------------------------------------------------------------
# 3. Monthly Hiring Trends Chart (Clean Date Formatting & Dual Axis)
# ---------------------------------------------------------------------------

def chart_monthly_trends(trend_data: list[dict[str, Any]]) -> go.Figure:
    """
    Grouped bar & line chart displaying application volume and hiring trends.
    Applies clean 'Mon YYYY' date formatting to prevent raw date overlap.
    """
    if not trend_data:
        fig = go.Figure()
        fig.update_layout(**LAYOUT_DEFAULTS, title="No trend data available")
        return fig

    raw_months = [t.get("month", "") for t in trend_data]
    formatted_months = [_format_month(m) for m in raw_months]
    apps = [t.get("applications", 0) for t in trend_data]
    hires = [t.get("hires", 0) for t in trend_data]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=formatted_months,
        y=apps,
        name="Applications",
        marker=dict(
            color="#93C5FD",
            line=dict(color="#3B82F6", width=1),
        ),
        opacity=0.85,
        hovertemplate="<b>%{x}</b><br>Applications: %{y:,}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=formatted_months,
        y=hires,
        name="Hires",
        mode="lines+markers",
        line=dict(color=COLOR_SUCCESS, width=3.5),
        marker=dict(size=8, symbol="circle", color="#065F46", line=dict(color="#FFFFFF", width=1.5)),
        yaxis="y2",
        hovertemplate="<b>%{x}</b><br>Hires: %{y:,}<extra></extra>",
    ))

    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title=dict(
            text="<b>Recruitment Velocity & Hiring Trends</b>",
            font=dict(size=14, color="#0F172A"),
            x=0.02,
        ),
        xaxis=dict(
            showgrid=False,
            title=None,
            type="category",
            categoryorder="array",
            categoryarray=formatted_months,
            tickangle=-25,
            automargin=True,
        ),
        yaxis=dict(
            title="Applications",
            showgrid=True,
            gridcolor="#F1F5F9",
            automargin=True,
        ),
        yaxis2=dict(
            title="Hires",
            overlaying="y",
            side="right",
            showgrid=False,
            automargin=True,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.04,
            xanchor="right",
            x=1.0,
            font=dict(size=11),
        ),
        margin=dict(l=45, r=45, t=60, b=55),
        height=380,
    )
    return fig


# ---------------------------------------------------------------------------
# 4. Department Requisitions Stacked Bar Chart
# ---------------------------------------------------------------------------

def chart_department_requisitions(dept_data: list[dict[str, Any]]) -> go.Figure:
    """Horizontal stacked bar chart showing open vs filled positions by department."""
    if not dept_data:
        fig = go.Figure()
        fig.update_layout(**LAYOUT_DEFAULTS, title="No department requisition data")
        return fig

    departments = [d.get("department_name", "") for d in dept_data]
    open_reqs = [d.get("open_requisitions", 0) for d in dept_data]
    total_reqs = [d.get("total_requisitions", 0) for d in dept_data]
    filled_reqs = [max(0, tot - op) for tot, op in zip(total_reqs, open_reqs)]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=departments,
        x=open_reqs,
        name="Open Positions",
        orientation="h",
        marker=dict(color=COLOR_PRIMARY),
        hovertemplate="<b>%{y}</b><br>Open Positions: %{x:,}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        y=departments,
        x=filled_reqs,
        name="Filled / Inactive",
        orientation="h",
        marker=dict(color="#CBD5E1"),
        hovertemplate="<b>%{y}</b><br>Filled / Inactive: %{x:,}<extra></extra>",
    ))

    fig.update_layout(
        **LAYOUT_DEFAULTS,
        barmode="stack",
        title=dict(
            text="<b>Requisitions by Department</b>",
            font=dict(size=14, color="#0F172A"),
            x=0.02,
        ),
        xaxis=dict(title="Position Count", showgrid=True, gridcolor="#F1F5F9", automargin=True),
        yaxis=dict(autorange="reversed", automargin=True),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.04,
            xanchor="right",
            x=1.0,
            font=dict(size=11),
        ),
        margin=dict(l=140, r=30, t=60, b=40),
        height=380,
    )
    return fig


# ---------------------------------------------------------------------------
# 5. Interview Outcomes Donut Chart
# ---------------------------------------------------------------------------

def chart_interview_outcomes(outcomes: dict[str, int]) -> go.Figure:
    """Donut chart for interviewer evaluation recommendations."""
    if not outcomes:
        fig = go.Figure()
        fig.update_layout(**LAYOUT_DEFAULTS, title="No interview scorecard data")
        return fig

    outcome_colors = {
        "Strong Hire": "#059669",
        "Hire": "#10B981",
        "Hold": "#F59E0B",
        "No Hire": "#EF4444",
    }
    labels = [k.replace("_", " ").title() for k in outcomes.keys()]
    values = list(outcomes.values())

    fig = px.pie(
        names=labels,
        values=values,
        hole=0.60,
        color=labels,
        color_discrete_map=outcome_colors,
    )
    fig.update_traces(
        textposition="auto",
        textinfo="percent",
        hovertemplate="<b>%{label}</b><br>Evaluations: %{value:,}<br>Share: %{percent}<extra></extra>",
        marker=dict(line=dict(color="#FFFFFF", width=2)),
    )
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title=dict(
            text="<b>Interviewer Evaluation Outcomes</b>",
            font=dict(size=14, color="#0F172A"),
            x=0.02,
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.25,
            xanchor="center",
            x=0.5,
            font=dict(size=11),
        ),
        margin=dict(l=20, r=20, t=55, b=65),
        height=380,
    )
    return fig


# ---------------------------------------------------------------------------
# 6. Offer Lifecycle Status Breakdown Bar Chart
# ---------------------------------------------------------------------------

def chart_offer_status(status_counts: dict[str, int]) -> go.Figure:
    """Bar chart showing candidate offers by lifecycle state."""
    status_order = [
        "draft", "pending_approval", "approved", "released",
        "accepted", "declined", "expired", "rejected"
    ]
    ordered_keys = [s for s in status_order if s in status_counts]
    values = [status_counts.get(s, 0) for s in ordered_keys]
    labels = [s.replace("_", " ").title() for s in ordered_keys]

    color_map = {
        "Draft": "#94A3B8",
        "Pending Approval": "#F59E0B",
        "Approved": "#3B82F6",
        "Released": "#8B5CF6",
        "Accepted": "#10B981",
        "Declined": "#F43F5E",
        "Expired": "#64748B",
        "Rejected": "#EF4444",
    }
    colors = [color_map.get(l, COLOR_PRIMARY) for l in labels]

    fig = go.Figure(go.Bar(
        x=labels,
        y=values,
        marker=dict(
            color=colors,
            line=dict(color="rgba(0,0,0,0.08)", width=1),
        ),
        text=values,
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Offers: %{y:,}<extra></extra>",
    ))
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title=dict(
            text="<b>Offer Lifecycle Status Breakdown</b>",
            font=dict(size=14, color="#0F172A"),
            x=0.02,
        ),
        xaxis=dict(showgrid=False, automargin=True, tickangle=-20),
        yaxis=dict(title="Offers", showgrid=True, gridcolor="#F1F5F9", automargin=True),
        margin=dict(l=45, r=25, t=55, b=55),
        height=380,
    )
    return fig


# ---------------------------------------------------------------------------
# 7. Anomaly Category Breakdown Horizontal Bar (A01 - A10)
# ---------------------------------------------------------------------------

def chart_anomalies_by_category(
    category_counts: dict[str, int],
    descriptions: Optional[dict[str, str]] = None,
) -> go.Figure:
    """
    Horizontal bar chart showing detected compliance anomalies per rule category A01-A10.
    Expanded height and descriptive labels prevent text crowding.
    """
    codes = sorted(category_counts.keys())
    counts = [category_counts[c] for c in codes]
    y_labels = [RULE_LABELS.get(c, c) for c in codes]

    hover_texts = []
    for c in codes:
        desc = descriptions.get(c, "") if descriptions else ""
        hover_texts.append(f"<b>{RULE_LABELS.get(c, c)}</b><br>{desc}<br>Discrepancies Found: <b>{category_counts[c]:,}</b>")

    fig = go.Figure(go.Bar(
        x=counts,
        y=y_labels,
        orientation="h",
        marker=dict(
            color="#DC2626",
            line=dict(color="#991B1B", width=1),
        ),
        hovertext=hover_texts,
        hoverinfo="text",
        text=counts,
        textposition="auto",
    ))
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title=dict(
            text="<b>Anomalies by Rule Category (A01 – A10)</b>",
            font=dict(size=14, color="#0F172A"),
            x=0.02,
        ),
        xaxis=dict(title="Anomalies Found", showgrid=True, gridcolor="#F1F5F9", automargin=True),
        yaxis=dict(autorange="reversed", automargin=True),
        margin=dict(l=220, r=40, t=55, b=45),
        height=440,
    )
    return fig


# ---------------------------------------------------------------------------
# 8. Anomaly Severity Distribution Donut Chart
# ---------------------------------------------------------------------------

def chart_anomalies_by_severity(severity_counts: dict[str, int]) -> go.Figure:
    """Donut chart for anomaly severity classification."""
    colors = {
        "Critical": "#991B1B",
        "High": "#EA580C",
        "Medium": "#EAB308",
        "Low": "#2563EB",
    }
    labels = ["Critical", "High", "Medium", "Low"]
    values = [severity_counts.get(s, 0) for s in labels]

    fig = px.pie(
        names=labels,
        values=values,
        hole=0.60,
        color=labels,
        color_discrete_map=colors,
    )
    fig.update_traces(
        textposition="auto",
        textinfo="percent",
        hovertemplate="<b>%{label} Severity</b><br>Count: %{value:,}<br>Share: %{percent}<extra></extra>",
        marker=dict(line=dict(color="#FFFFFF", width=2)),
    )
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title=dict(
            text="<b>Anomaly Distribution by Severity</b>",
            font=dict(size=14, color="#0F172A"),
            x=0.02,
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.22,
            xanchor="center",
            x=0.5,
            font=dict(size=11),
        ),
        margin=dict(l=20, r=20, t=55, b=65),
        height=440,
    )
    return fig
