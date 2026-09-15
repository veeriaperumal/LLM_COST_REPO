# ---------------------------------------------------------------------------
# styles.py — Shared CSS and layout helpers for the Streamlit dashboard
# ---------------------------------------------------------------------------

# -- Color palette -------------------------------------------------------------
COLORS = {
    "primary": "#3b82f6",
    "success": "#22c55e",
    "warning": "#f59e0b",
    "danger": "#ef4444",
    "info": "#06b6d4",
    "muted": "#6b7280",
    "bg": "#f8fafc",
    "card": "#ffffff",
}

STATUS_COLORS = {
    "ok": COLORS["success"],
    "down": COLORS["danger"],
    "skipped": COLORS["muted"],
    "accept": COLORS["success"],
    "revise": COLORS["warning"],
    "escalate": COLORS["danger"],
    "pending": COLORS["muted"],
}

PROVIDER_COLORS = {
    "openai": "#10a37f",
    "anthropic": "#d97706",
}

# -- CSS ----------------------------------------------------------------------

PAGE_CSS = """
<style>
/* Wide layout */
.block-container { padding-top: 1rem; }

/* KPI cards */
.kpi-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 0.75rem;
    padding: 1.25rem;
    text-align: center;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.kpi-card h2 {
    margin: 0;
    font-size: 2rem;
    font-weight: 700;
    color: #1e293b;
}
.kpi-card p {
    margin: 0.25rem 0 0;
    font-size: 0.85rem;
    color: #64748b;
}

/* Status badges */
.badge {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
    color: #fff;
}
.badge-success { background: #22c55e; }
.badge-warning { background: #f59e0b; }
.badge-danger  { background: #ef4444; }
.badge-muted   { background: #6b728b; }

/* Pipeline step */
.step {
    display: inline-block;
    padding: 0.4rem 1rem;
    border-radius: 0.5rem;
    font-size: 0.8rem;
    font-weight: 600;
    margin: 0.2rem;
    background: #e0e7ff;
    color: #3730a3;
}
.step-done { background: #dcfce7; color: #166534; }
.step-active { background: #dbeafe; color: #1e40af; border: 2px solid #3b82f6; }
.step-error { background: #fee2e2; color: #991b1b; }
</style>
"""


def inject_css() -> None:
    """Inject custom CSS into the Streamlit page."""
    import streamlit as st
    st.markdown(PAGE_CSS, unsafe_allow_html=True)


def kpi_card(label: str, value: str, delta: str | None = None) -> None:
    """Render a KPI metric card."""
    import streamlit as st
    delta_html = f'<p style="color:{"#22c55e" if not delta.startswith("-") else "#ef4444"}">{delta}</p>' if delta else ""
    st.markdown(
        f'<div class="kpi-card"><h2>{value}</h2><p>{label}</p>{delta_html}</div>',
        unsafe_allow_html=True,
    )


def status_badge(status: str) -> str:
    """Return an HTML status badge."""
    color = STATUS_COLORS.get(status, COLORS["muted"])
    return f'<span class="badge" style="background:{color}">{status}</span>'


def pipeline_steps(steps: list[str], completed: list[str] | None = None) -> str:
    """Render a horizontal pipeline visualization."""
    completed = completed or []
    html = '<div style="display:flex;flex-wrap:wrap;gap:0.25rem;margin:0.5rem 0">'
    for step in steps:
        if step in completed:
            cls = "step step-done"
        else:
            cls = "step"
        html += f'<span class="{cls}">{step}</span>'
    html += "</div>"
    return html
