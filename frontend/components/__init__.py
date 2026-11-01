"""
frontend.components package
"""
from frontend.components.metrics import render_kpi_card, render_metric_row
from frontend.components.charts import (
    chart_stage_funnel,
    chart_source_distribution,
    chart_monthly_trends,
    chart_department_requisitions,
    chart_interview_outcomes,
    chart_offer_status,
    chart_anomalies_by_category,
    chart_anomalies_by_severity,
)
from frontend.components.tables import render_status_badge, render_empty_state, format_currency
from frontend.components.sidebar import render_sidebar

