import html
import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from src.triage import process_batch

# =========================================================
# CONFIG
# =========================================================

st.set_page_config(
    page_title="Caregene Support Intelligence",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="collapsed",  # sidebar was empty, so keep it out of the way
)

RESULTS_PATH = Path("results/results.json")
PAGE_SIZE = 10

URGENCY_ORDER = ["Critical", "High", "Medium", "Low"]
SENTIMENT_ORDER = ["Angry", "Frustrated", "Neutral", "Happy"]
URGENCY_RANK = {v: i for i, v in enumerate(URGENCY_ORDER)}
SENTIMENT_RANK = {v: i for i, v in enumerate(SENTIMENT_ORDER)}

# One palette drives the badges AND the charts, so colours always agree.
# value -> (badge bg, badge text, badge border, solid accent)
PALETTE = {
    "Critical":   ("#fef2f2", "#b91c1c", "#fecaca", "#dc2626"),
    "High":       ("#fff7ed", "#c2410c", "#fed7aa", "#ea580c"),
    "Medium":     ("#fffbeb", "#a16207", "#fde68a", "#ca8a04"),
    "Low":        ("#f0fdf4", "#15803d", "#bbf7d0", "#16a34a"),
    "Angry":      ("#fef2f2", "#b91c1c", "#fecaca", "#dc2626"),
    "Frustrated": ("#fff7ed", "#c2410c", "#fed7aa", "#ea580c"),
    "Neutral":    ("#f3f4f6", "#4b5563", "#d1d5db", "#6b7280"),
    "Happy":      ("#f0fdf4", "#15803d", "#bbf7d0", "#16a34a"),
    "Unknown":    ("#f3f4f6", "#4b5563", "#d1d5db", "#9ca3af"),
    "Incomplete": ("#fffbeb", "#a16207", "#fde68a", "#ca8a04"),
}
CATEGORY_COLORS = ("#eff6ff", "#1d4ed8", "#bfdbfe", "#3b82f6")
FALLBACK_COLORS = PALETTE["Neutral"]



# =========================================================
# STYLING
# =========================================================

st.markdown(
    """
    <style>
    .stApp { background-color: #f8fafc; }
    .block-container { padding-top: 4rem; padding-bottom: 3rem; max-width: 1300px; }

    .dashboard-title { font-size: 2rem; font-weight: 700; color: #111827;
                       letter-spacing: -0.02em; line-height: 1.2; }
    .dashboard-subtitle { font-size: 0.95rem; color: #6b7280; margin-bottom: 1.5rem; }

    .ai-status { display: inline-flex; align-items: center; gap: 7px; background: #f0fdf4;
                 border: 1px solid #bbf7d0; color: #166534; border-radius: 999px;
                 padding: 6px 12px; font-size: 0.78rem; font-weight: 600; }
    .ai-dot { width: 7px; height: 7px; background: #22c55e; border-radius: 50%;
              animation: pulse 2s infinite; }
    @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: .35; } }
    @media (prefers-reduced-motion: reduce) { .ai-dot { animation: none; } }

    .kpi-card, .sentiment-card { background: white; border: 1px solid #e5e7eb;
        border-radius: 12px; padding: 1rem 1.25rem; border-top-width: 3px; }
    .kpi-label, .sentiment-label { font-size: 0.8rem; color: #6b7280; margin-bottom: 0.25rem; }
    .kpi-value, .sentiment-value { font-size: 1.8rem; font-weight: 700; color: #111827; line-height: 1.15; }
    .kpi-sub { font-size: 0.75rem; color: #9ca3af; margin-top: 0.15rem; }

    .section-title { font-size: 1.05rem; font-weight: 650; color: #111827;
                     margin: 2rem 0 0.8rem 0; }
    .section-description { font-size: 0.85rem; color: #6b7280; margin: -0.5rem 0 1rem 0; }
    .chart-title { font-size: 0.9rem; font-weight: 600; color: #374151; }

    .badge { display: inline-block; padding: 4px 10px; border-radius: 999px;
             font-size: 0.72rem; font-weight: 650; margin-right: 6px; line-height: 1.2;
             border: 1px solid transparent; }

    .ticket-id { font-size: 0.95rem; font-weight: 700; color: #374151; }
    .ticket-message { font-size: 0.9rem; color: #4b5563; line-height: 1.5; margin-top: 0.4rem; }

    .detail-ticket-id { font-size: 1.65rem; font-weight: 700; color: #111827; }
    .detail-label { font-size: 0.75rem; color: #6b7280; margin-bottom: 0.4rem; }
    .message-box { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 10px;
                   padding: 1rem 1.1rem; color: #374151; font-size: 0.95rem; line-height: 1.65; }

    .stButton > button { border-radius: 8px; font-weight: 600; font-size: 0.82rem; }

    /* Keep alert text readable: the page background is always light, so the
       text must be dark even when the browser/Streamlit theme is dark. */
    [data-testid="stAlert"] p, [data-testid="stAlert"] li,
    [data-testid="stAlert"] strong { color: #1f2937 !important; }

    .empty-state { background: white; border: 1px dashed #cbd5e1; border-radius: 12px;
                   padding: 3.5rem 1.5rem; text-align: center; margin-top: 1rem; }
    .empty-icon { font-size: 2.2rem; margin-bottom: 0.6rem; }
    .empty-title { font-size: 1.15rem; font-weight: 650; color: #111827; }
    .empty-text { font-size: 0.92rem; color: #6b7280; margin-top: 0.35rem; }
    [data-testid="stSpinner"] * { color: #374151 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# DATA
# =========================================================

REQUIRED_FIELDS = ["ticket_id", "message", "urgency", "category", "sentiment", "suggested_reply"]
PLACEHOLDERS = {"message": "(no message)", "urgency": "Unknown", "category": "Unknown",
                "sentiment": "Unknown", "suggested_reply": ""}


def is_blank(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


@st.cache_data(show_spinner=False)
def load_results(path: str, mtime: float):
    """Load and validate results.json. `mtime` busts the cache whenever the file changes.

    Returns (DataFrame, status, skipped). status is one of:
    ok | unreadable | not_list | empty.
    `skipped` counts entries that were unusable (not an object, or no ticket_id).
    Rows missing any other required field are kept, filled with placeholders, and
    flagged in the `_missing` column.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return pd.DataFrame(), "unreadable", 0

    if not isinstance(raw, list):
        return pd.DataFrame(), "not_list", 0

    rows, skipped = [], 0
    for item in raw:
        if not isinstance(item, dict) or is_blank(item.get("ticket_id")):
            skipped += 1
            continue
        missing = [f for f in REQUIRED_FIELDS if is_blank(item.get(f))]
        row = {f: item.get(f) for f in REQUIRED_FIELDS}
        for f in missing:
            row[f] = PLACEHOLDERS.get(f, row[f])
        row["_missing"] = missing
        rows.append(row)

    df = pd.DataFrame(rows, columns=REQUIRED_FIELDS + ["_missing"])

    # Normalise casing so "critical" / "CRITICAL" / "Critical" all match.
    for col in ["urgency", "sentiment", "category"]:
        df[col] = df[col].astype(str).str.strip().str.title()
    return df, ("ok" if len(df) else "empty"), skipped


def render_header(show_status: bool = True):
    left, right = st.columns([5, 1.2], vertical_alignment="center")
    with left:
        st.markdown(
            '<div class="dashboard-title">Caregene Support Intelligence</div>'
            '<div class="dashboard-subtitle">AI-powered support ticket triage dashboard</div>',
            unsafe_allow_html=True,
        )
    if show_status:
        with right:
            st.markdown(
                '<div style="text-align:right"><span class="ai-status">'
                '<span class="ai-dot"></span>AI triage active</span></div>',
                unsafe_allow_html=True,
            )


def render_empty_state():
    """Show the empty dashboard and stop execution."""
    render_header(show_status=False)

    st.markdown(
        '<div class="empty-state">'
        '<div class="empty-icon">📭</div>'
        '<div class="empty-title">No tickets have been processed yet</div>'
        '<div class="empty-text">'
        'Run AI triage to process the support-ticket batch and populate the dashboard.'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.write("")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        if st.button(
            "▶ Process Unprocessed Tickets",
            type="primary",
            use_container_width=True,
            key="process_empty_state",
        ):
            if run_ticket_processing():
                st.rerun()

    st.stop()


ALERT_STYLES = {  # kind -> (background, text, border, accent, icon)
    "warning": ("#fffbeb", "#78350f", "#fde68a", "#f59e0b", "⚠️"),
    "error":   ("#fef2f2", "#7f1d1d", "#fecaca", "#dc2626", "⛔"),
}


def alert(text: str, kind: str = "warning", title: str = ""):
    """Banner with fixed colours, so the message stays readable in light AND dark themes."""
    bg, fg, border, bar, icon = ALERT_STYLES[kind]
    heading = f'<div style="font-weight:700;margin-bottom:2px">{html.escape(title)}</div>' if title else ""
    st.markdown(
        f'<div style="display:flex;gap:10px;align-items:flex-start;background:{bg};color:{fg};'
        f'border:1px solid {border};border-left:4px solid {bar};border-radius:10px;'
        f'padding:0.85rem 1rem;margin:0 0 1rem 0;font-size:0.92rem;line-height:1.5">'
        f'<div>{icon}</div><div>{heading}{html.escape(text)}</div></div>',
        unsafe_allow_html=True,
    )


def load_tickets():
    """Load the fixed support-ticket batch."""
    tickets_path = Path("data/tickets.json")

    try:
        with open(tickets_path, "r", encoding="utf-8") as file:
            tickets = json.load(file)

        if not isinstance(tickets, list):
            return None, "data/tickets.json must contain a JSON list."

        return tickets, None

    except FileNotFoundError:
        return None, "data/tickets.json was not found."

    except json.JSONDecodeError:
        return None, "data/tickets.json is not valid JSON."

    except OSError as error:
        return None, f"Could not read data/tickets.json: {error}"


def run_ticket_processing(
    reset_results=False,
    ticket_ids_to_process=None,
):
    """Run AI triage from the Streamlit server."""
    tickets, error_message = load_tickets()

    if error_message:
        st.error(error_message)
        return False

    if reset_results and RESULTS_PATH.exists():
        try:
            RESULTS_PATH.unlink()
        except OSError as error:
            st.error(f"Could not reset results/results.json: {error}")
            return False

        load_results.clear()

    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(completed, total, ticket_id):
        progress_bar.progress(completed / total if total else 1.0)
        status_text.markdown(
            f'<span style="color:#374151">Processing Ticket #{ticket_id} ({completed}/{total})</span>',
            unsafe_allow_html=True,
        )

    try:
        with st.spinner("Running AI triage..."):
            process_batch(
                tickets,
                progress_callback=update_progress,
                ticket_ids_to_process=ticket_ids_to_process,
            )

    except Exception as error:
        progress_bar.empty()
        status_text.empty()
        st.error(f"Ticket processing failed: {error}")
        return False

    progress_bar.progress(1.0)
    status_text.success("AI triage completed successfully.")

    load_results.clear()
    return True


if not RESULTS_PATH.exists():
    df, status, skipped = pd.DataFrame(), "missing", 0
else:
    df, status, skipped = load_results(
        str(RESULTS_PATH),
        RESULTS_PATH.stat().st_mtime,
    )


# =========================================================
# SINGLE RESULT-STATE HANDLER
# =========================================================
#
# Keep all result-file state handling here.
# In particular, [] means "empty" with skipped == 0 and must
# stop after rendering the empty state.
# =========================================================

if status == "missing":
    render_empty_state()

elif status == "empty" and skipped == 0:
    render_empty_state()

elif status == "unreadable":
    render_header(show_status=False)

    alert(
        "The saved results file is corrupted or contains invalid JSON. "
        "You can reset it and run the AI triage again.",
        "error",
        "Couldn't read results/results.json",
    )

    st.write("")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        if st.button(
            "▶ Reset & Process Tickets",
            type="primary",
            use_container_width=True,
            key="reset_invalid_results",
        ):
            if run_ticket_processing(reset_results=True):
                st.rerun()

    st.stop()

elif status == "not_list":
    render_header(show_status=False)

    alert(
        "The saved results file should contain a JSON list of ticket results.",
        "error",
        "Unexpected results format",
    )

    st.stop()

elif status == "empty" and skipped > 0:
    render_header(show_status=False)

    alert(
        f"All {skipped} entries were missing a ticket ID or were not valid "
        "ticket objects. Reset the saved results and run AI triage again.",
        "error",
        "No usable tickets",
    )

    st.write("")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        if st.button(
            "▶ Reset & Process Tickets",
            type="primary",
            use_container_width=True,
            key="reset_skipped_results",
        ):
            if run_ticket_processing(reset_results=True):
                st.rerun()

    st.caption(
        "This will discard the invalid saved results and regenerate the "
        "ticket triage from data/tickets.json."
    )

    st.stop()


incomplete_df = df[df["_missing"].map(len) > 0]

# =========================================================
# HELPERS
# =========================================================

def badge(value, kind="level") -> str:
    """HTML pill. kind='category' uses the blue category style."""
    value = str(value)
    bg, fg, border, _ = CATEGORY_COLORS if kind == "category" else PALETTE.get(value, FALLBACK_COLORS)
    return (
        f'<span class="badge" style="background:{bg};color:{fg};border-color:{border}">'
        f"{html.escape(value)}</span>"
    )


def accent(value) -> str:
    return PALETTE.get(str(value), FALLBACK_COLORS)[3]


def safe_text(value) -> str:
    """Escape user-supplied text before putting it inside HTML."""
    return html.escape(str(value)).replace("\n", "<br>")


def bar_chart(counts: pd.Series, order=None, colors=None):
    """Horizontal bar chart with a value label on each bar."""
    data = counts.rename_axis("label").reset_index(name="count")
    sort = order if order else "-x"
    x_max = max(int(data["count"].max()), 1) * 1.18  # headroom so value labels never clip
    base = alt.Chart(data).encode(
        y=alt.Y(
            "label:N", sort=sort, title=None,
            axis=alt.Axis(labelLimit=220, labelFontSize=13, labelPadding=12, ticks=False, domain=False),
        ),
        x=alt.X(
            "count:Q", title=None, scale=alt.Scale(domain=[0, x_max]),
            axis=alt.Axis(tickMinStep=1, grid=True, gridColor="#eef0f3", domain=False,
                          labelFontSize=12, labelPadding=8),
        ),
    )
    bars = base.mark_bar(cornerRadiusEnd=6, size=30).encode(
        color=(
            alt.Color("label:N", legend=None,
                      scale=alt.Scale(domain=list(colors), range=list(colors.values())))
            if colors else alt.value(CATEGORY_COLORS[3])
        ),
        tooltip=["label", "count"],
    )
    labels = base.mark_text(align="left", dx=8, fontSize=14, color="#111827", fontWeight="bold").encode(
        text="count:Q"
    )
    st.altair_chart(
        (bars + labels)
        .properties(height=max(260, 66 * len(data)), padding={"left": 8, "right": 16, "top": 12, "bottom": 8})
        .configure_view(strokeWidth=0),
        use_container_width=True,
    )


def sort_frame(d: pd.DataFrame, option: str) -> pd.DataFrame:
    if option == "Most urgent first":
        return d.sort_values("urgency", key=lambda s: s.map(URGENCY_RANK).fillna(99), kind="stable")
    if option == "Angriest first":
        return d.sort_values("sentiment", key=lambda s: s.map(SENTIMENT_RANK).fillna(99), kind="stable")
    if option == "Category (A–Z)":
        return d.sort_values("category", kind="stable")
    return d


# =========================================================
# SESSION STATE
# =========================================================

st.session_state.setdefault("selected_ticket", None)
st.session_state.setdefault("visible_ids", df["ticket_id"].astype(str).tolist())
st.session_state.setdefault("shown", PAGE_SIZE)


def open_ticket(ticket_id):
    st.session_state.selected_ticket = str(ticket_id)


def close_ticket():
    st.session_state.selected_ticket = None


# =========================================================
# DETAIL VIEW
# =========================================================

if st.session_state.selected_ticket is not None:
    selected_id = st.session_state.selected_ticket
    rows = df[df["ticket_id"].astype(str) == selected_id]

    if rows.empty:
        close_ticket()
        st.rerun()

    ticket = rows.iloc[0]
    ids = st.session_state.visible_ids
    pos = ids.index(selected_id) if selected_id in ids else None

    nav_back, _, nav_prev, nav_next = st.columns([1.5, 4, 1, 1])
    nav_back.button("← Back to tickets", on_click=close_ticket)
    if pos is not None:
        nav_prev.button("‹ Previous", disabled=pos == 0, on_click=open_ticket,
                        args=(ids[pos - 1] if pos > 0 else selected_id,), use_container_width=True)
        nav_next.button("Next ›", disabled=pos >= len(ids) - 1, on_click=open_ticket,
                        args=(ids[pos + 1] if pos < len(ids) - 1 else selected_id,), use_container_width=True)

    st.markdown(
        f'<div style="display:flex;align-items:center;justify-content:space-between;margin:1rem 0">'
        f'<div class="detail-ticket-id">Ticket #{safe_text(ticket["ticket_id"])}</div>'
        f'<div>{badge(ticket["urgency"])}</div></div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    for col, label, content in [
        (c1, "Urgency", badge(ticket["urgency"])),
        (c2, "Category", badge(ticket["category"], "category")),
        (c3, "Sentiment", badge(ticket["sentiment"])),
    ]:
        with col, st.container(border=True):
            st.markdown(f'<div class="detail-label">{label}</div>{content}', unsafe_allow_html=True)

    if ticket["_missing"]:
        alert(f"This result is incomplete (missing: {', '.join(ticket['_missing'])}). "
              "Please regenerate it.")

    st.markdown('<div class="section-title">Customer message</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="message-box">{safe_text(ticket["message"])}</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">Suggested reply</div>', unsafe_allow_html=True)
    reply = str(ticket["suggested_reply"]).strip()
    if reply:
        # st.code has a built-in copy button (top right, on hover): no custom JS needed.
        st.code(reply, language=None, wrap_lines=True)
        st.caption("Use the copy icon in the top-right of the box, then send it from your support system.")
    else:
        st.info("No suggested reply was generated for this ticket.")

    st.markdown(
        '<div class="section-title">Ticket actions</div>',
        unsafe_allow_html=True,
    )

    action_col, _ = st.columns([2, 5])

    with action_col:
        if st.button(
            "↻ Regenerate AI Result",
            type="secondary",
            use_container_width=True,
            key=f"regenerate_{selected_id}",
        ):
            if run_ticket_processing(
                ticket_ids_to_process={selected_id}
            ):
                st.session_state.selected_ticket = selected_id
                st.rerun()

    st.stop()


# =========================================================
# MAIN DASHBOARD
# =========================================================

render_header()

process_col, status_col = st.columns([2, 5])

with process_col:
    if st.button(
        "▶ Process Unprocessed Tickets",
        type="primary",
        use_container_width=True,
        key="process_unprocessed",
    ):
        if run_ticket_processing():
            st.rerun()

with status_col:
    st.caption(
        "Runs AI triage only for tickets that do not already have saved results."
    )

if len(incomplete_df) or skipped:
    alert("Some ticket results are incomplete. Please regenerate the affected results.")
    with st.expander(f"See details ({len(incomplete_df)} incomplete, {skipped} skipped)"):
        for _, r in incomplete_df.iterrows():
            st.markdown(f"- Ticket #{r['ticket_id']}: missing {', '.join(r['_missing'])}")
        if skipped:
            st.markdown(
                f"- {skipped} entr{'y' if skipped == 1 else 'ies'} had no ticket ID "
                "or weren't ticket objects, so they were left out."
            )

# ---------- KPIs ----------

total = len(df)
critical = int((df["urgency"] == "Critical").sum())
angry = int((df["sentiment"] == "Angry").sum())
technical = int((df["category"] == "Technical").sum())


def pct(n):
    return f"{n / total:.0%} of all tickets" if total else ""


kpis = [
    ("Total tickets", total, "#3b82f6", "Processed by AI triage"),
    ("Critical", critical, accent("Critical"), pct(critical)),
    ("Angry customers", angry, accent("Angry"), pct(angry)),
    ("Technical", technical, CATEGORY_COLORS[3], pct(technical)),
]
for col, (label, value, color, sub) in zip(st.columns(4), kpis):
    col.markdown(
        f'<div class="kpi-card" style="border-top-color:{color}">'
        f'<div class="kpi-label">{label}</div><div class="kpi-value">{value}</div>'
        f'<div class="kpi-sub">{sub}</div></div>',
        unsafe_allow_html=True,
    )

# ---------- Charts ----------

st.markdown('<div class="section-title">Ticket distribution</div>', unsafe_allow_html=True)
left, right = st.columns(2)

with left, st.container(border=True):
    st.markdown('<div class="chart-title">Tickets by urgency</div>', unsafe_allow_html=True)
    urg_order = URGENCY_ORDER + (["Unknown"] if (df["urgency"] == "Unknown").any() else [])
    counts = df["urgency"].value_counts().reindex(urg_order, fill_value=0)
    bar_chart(counts, order=urg_order, colors={u: accent(u) for u in urg_order})

with right, st.container(border=True):
    st.markdown('<div class="chart-title">Tickets by category</div>', unsafe_allow_html=True)
    bar_chart(df["category"].value_counts())

# ---------- Sentiment ----------

st.markdown('<div class="section-title">Sentiment overview</div>', unsafe_allow_html=True)
SENTIMENT_ICONS = {"Angry": "😠", "Frustrated": "😤", "Neutral": "😐", "Happy": "😊"}

for col, s in zip(st.columns(4), SENTIMENT_ORDER):
    n = int((df["sentiment"] == s).sum())
    share = n / total if total else 0
    bg, fg, border, solid = PALETTE[s]
    col.markdown(
        f'<div class="sentiment-card" style="background:{bg};border-color:{border};'
        f'border-top-color:{solid};padding:1.1rem 1.25rem">'
        f'<div style="display:flex;justify-content:space-between;align-items:center">'
        f'<div class="sentiment-label" style="color:{fg};font-weight:600;font-size:0.9rem">{s}</div>'
        f'<div style="font-size:1.3rem">{SENTIMENT_ICONS[s]}</div></div>'
        f'<div class="sentiment-value" style="color:{fg}">{n}</div>'
        f'<div style="height:6px;background:rgba(255,255,255,0.75);border-radius:999px;margin:0.6rem 0 0.35rem">'
        f'<div style="width:{share * 100:.0f}%;height:100%;background:{solid};border-radius:999px"></div></div>'
        f'<div class="kpi-sub" style="color:{fg};opacity:0.8">{share:.0%} of tickets</div></div>',
        unsafe_allow_html=True,
    )

# ---------- Filters ----------

st.markdown('<div class="section-title">Tickets</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-description">Review and prioritize incoming support requests.</div>',
    unsafe_allow_html=True,
)

f_search, f_urg, f_cat, f_sent, f_sort = st.columns([2, 1, 1, 1, 1.2])
query = f_search.text_input("Search", placeholder="Search message or ticket #")
sel_urgency = f_urg.selectbox("Urgency", ["All"] + [u for u in URGENCY_ORDER + ["Unknown"] if u in set(df["urgency"])])
sel_category = f_cat.selectbox("Category", ["All"] + sorted(df["category"].unique()))
sel_sentiment = f_sent.selectbox("Sentiment", ["All"] + [s for s in SENTIMENT_ORDER + ["Unknown"] if s in set(df["sentiment"])])
sort_option = f_sort.selectbox("Sort by", ["Most urgent first", "Angriest first", "Category (A–Z)", "Original order"])

view = df
if sel_urgency != "All":
    view = view[view["urgency"] == sel_urgency]
if sel_category != "All":
    view = view[view["category"] == sel_category]
if sel_sentiment != "All":
    view = view[view["sentiment"] == sel_sentiment]
if query.strip():
    q = query.strip().lower()
    view = view[
        view["message"].astype(str).str.lower().str.contains(q, regex=False)
        | view["ticket_id"].astype(str).str.lower().str.contains(q, regex=False)
    ]
view = sort_frame(view, sort_option)

# Remember the order so the detail page can step through it with Previous / Next.
st.session_state.visible_ids = view["ticket_id"].astype(str).tolist()

filter_signature = (
    query,
    sel_urgency,
    sel_category,
    sel_sentiment,
    sort_option,
)

if st.session_state.get("filter_signature") != filter_signature:
    st.session_state.filter_signature = filter_signature
    st.session_state.shown = PAGE_SIZE

# ---------- Ticket list ----------

st.caption(f"Showing {min(st.session_state.shown, len(view))} of {len(view)} tickets")

if view.empty:
    st.info("No tickets match these filters. Clear a filter or search term to see more.")
else:
    for _, t in view.head(st.session_state.shown).iterrows():
        message = str(t["message"])
        preview = safe_text(message[:160] + ("…" if len(message) > 160 else ""))
        flag = badge("Incomplete") if t["_missing"] else ""

        with st.container(border=True):
            info, action = st.columns([6, 1], vertical_alignment="center")
            info.markdown(
                f'<span class="ticket-id">#{safe_text(t["ticket_id"])}</span>&nbsp;&nbsp;'
                f'{badge(t["urgency"])}{badge(t["category"], "category")}{badge(t["sentiment"])}{flag}'
                f'<div class="ticket-message">{preview}</div>',
                unsafe_allow_html=True,
            )
            action.button(
                "Open",
                key=f"open_{t['ticket_id']}",
                on_click=open_ticket,
                args=(t["ticket_id"],),
                use_container_width=True,
            )

    if len(view) > st.session_state.shown:
        if st.button("Show more tickets"):
            st.session_state.shown += PAGE_SIZE
            st.rerun()