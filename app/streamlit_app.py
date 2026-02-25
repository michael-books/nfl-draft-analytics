"""
streamlit_app.py — Interactive NFL Draft Analytics Dashboard.

Run with:
    streamlit run app/streamlit_app.py
"""

import sys
import pathlib

# Allow imports from src/ when running from the project root
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import streamlit as st
import pandas as pd

from src.analyzer import (
    compute_hit_rates_by_round,
    compute_hit_rates_by_position,
    compute_hit_rates_by_round_and_position,
    compute_hit_rate_by_pick_number,
    compute_value_table,
)
from src.charts import (
    bar_chart_by_round,
    bar_chart_by_position,
    heatmap_position_round,
    scatter_by_pick_number,
    value_table_chart,
)

PROCESSED_DIR = pathlib.Path(__file__).parent.parent / "data" / "processed"
MERGED_CSV = PROCESSED_DIR / "merged_dataset.csv"

st.set_page_config(
    page_title="NFL Draft Analytics",
    page_icon="🏈",
    layout="wide",
)


@st.cache_data
def load_data() -> pd.DataFrame:
    if not MERGED_CSV.exists():
        st.error(
            f"Merged dataset not found at `{MERGED_CSV}`.  "
            "Please run the data pipeline first (see README)."
        )
        st.stop()
    df = pd.read_csv(MERGED_CSV)
    df["round"] = pd.to_numeric(df["round"], errors="coerce")
    df["pick"] = pd.to_numeric(df["pick"], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["is_allpro"] = pd.to_numeric(df["is_allpro"], errors="coerce").fillna(0).astype(int)
    return df


# ── Load ──────────────────────────────────────────────────────────────────────
df_full = load_data()

# ── Sidebar filters ───────────────────────────────────────────────────────────
st.sidebar.header("Filters")

year_min, year_max = int(df_full["year"].min()), int(df_full["year"].max())
year_range = st.sidebar.slider(
    "Draft year range",
    min_value=year_min,
    max_value=year_max,
    value=(year_min, year_max),
)

GENERIC_POSITIONS = {"OL", "DL", "DB"}
all_positions = sorted(
    p for p in df_full["position"].dropna().unique() if p not in GENERIC_POSITIONS
)
selected_positions = st.sidebar.multiselect(
    "Positions",
    options=all_positions,
    default=all_positions,
    help="Filter to specific positions",
)

min_players = st.sidebar.slider(
    "Min players per position (for position charts)",
    min_value=5,
    max_value=50,
    value=20,
    step=5,
)

# ── Apply filters ─────────────────────────────────────────────────────────────
df = df_full[
    (df_full["year"] >= year_range[0])
    & (df_full["year"] <= year_range[1])
    & (df_full["position"].isin(selected_positions))
].copy()

if df.empty:
    st.info("No data matches the current filters. Adjust the sidebar settings.")
    st.stop()

# ── KPI metrics ───────────────────────────────────────────────────────────────
total_allpros = int(df["is_allpro"].sum())
total_players = len(df)

r1_df = df[df["round"] == 1]
r1_rate = r1_df["is_allpro"].mean() if len(r1_df) > 0 else 0.0

pos_df = compute_hit_rates_by_position(df, min_players=min_players)
best_position = pos_df.iloc[0]["position"] if not pos_df.empty else "N/A"
best_position_rate = pos_df.iloc[0]["hit_rate"] if not pos_df.empty else 0.0

st.title("🏈 NFL Draft Analytics: Who Actually Becomes Elite?")
st.caption(
    f"Draft classes {year_range[0]}–{year_range[1]}  |  "
    f"{total_players:,} players  |  "
    f"First-Team All-Pro selections through 2024"
)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total All-Pros", total_allpros)
col2.metric("Round 1 Hit Rate", f"{r1_rate:.1%}")
col3.metric("Best Position", best_position)
col4.metric(f"{best_position} Hit Rate", f"{best_position_rate:.1%}")

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_round, tab_pos, tab_heat, tab_pick, tab_value = st.tabs(
    ["By Round", "By Position", "Heatmap", "By Pick #", "Value Table"]
)

# Tab 1 — By Round
with tab_round:
    round_df = compute_hit_rates_by_round(df)
    if round_df.empty:
        st.info("No data available for the current filters.")
    else:
        fig = bar_chart_by_round(round_df)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(
            """
            **Key takeaway:** Round 1 picks produce All-Pros at a dramatically
            higher rate than later rounds.  The hit rate drops sharply after
            Round 2, and rounds 6–7 are near-zero.
            """
        )
        with st.expander("Raw data"):
            st.dataframe(
                round_df.assign(hit_rate=round_df["hit_rate"].map(lambda x: f"{x:.2%}")),
                use_container_width=True,
            )

# Tab 2 — By Position
with tab_pos:
    if pos_df.empty:
        st.info("No positions meet the minimum player threshold. Try lowering it in the sidebar.")
    else:
        fig = bar_chart_by_position(pos_df)
        st.plotly_chart(fig, use_container_width=True)
        top3 = ", ".join(
            f"{row['position']} ({row['hit_rate']:.1%})"
            for _, row in pos_df.head(3).iterrows()
        )
        st.markdown(
            f"**Key takeaway:** The three positions with the highest All-Pro hit rates are **{top3}**."
        )
        with st.expander("Raw data"):
            st.dataframe(
                pos_df.assign(hit_rate=pos_df["hit_rate"].map(lambda x: f"{x:.2%}")),
                use_container_width=True,
            )

# Tab 3 — Heatmap
with tab_heat:
    pivot = compute_hit_rates_by_round_and_position(df)
    if pivot.empty:
        st.info("Not enough data to build a heatmap for the current filters.")
    else:
        fig = heatmap_position_round(pivot)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(
            """
            **Gray cells** indicate fewer than 10 players were drafted at that
            position-round combination, making the rate unreliable.
            """
        )

# Tab 4 — By Pick Number
with tab_pick:
    pick_df = compute_hit_rate_by_pick_number(df)
    if pick_df.empty:
        st.info("No data available for the current filters.")
    else:
        fig = scatter_by_pick_number(pick_df)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(
            """
            **Key takeaway:** There is a clear downward trend in All-Pro
            probability as pick number increases.  The smoothed line reveals
            a sharp cliff after the first ~32 picks (end of Round 1).
            """
        )

# Tab 5 — Value Table
with tab_value:
    value_df = compute_value_table(df)
    if value_df.empty:
        st.info("Not enough data to compute value ratios for the current filters.")
    else:
        fig = value_table_chart(value_df)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(
            """
            **Key takeaway:** Positions with a high Late/R1 Ratio are where
            late-round picks overperform relative to expectations — these
            represent the best value opportunities in the mid-rounds.
            """
        )

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "Data source: [Pro Football Reference](https://www.pro-football-reference.com) | "
    "First-Team All-Pro selections only | Draft years 2010–2021 for analysis cohort"
)
