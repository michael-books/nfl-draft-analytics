"""
charts.py — Plotly figure factory.  All functions return go.Figure.
No side effects — works in both Jupyter (fig.show()) and Streamlit
(st.plotly_chart(fig)).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Round boundary pick numbers (approximate, 32-team era)
ROUND_BOUNDARIES = [32, 64, 96, 128, 160, 192, 224, 256]


def bar_chart_by_round(df: pd.DataFrame) -> go.Figure:
    """
    Bar chart: All-Pro hit rate by draft round.

    df must have columns: round, hit_rate, allpro_count, total_players
    """
    fig = px.bar(
        df,
        x="round",
        y="hit_rate",
        color="hit_rate",
        color_continuous_scale="Blues",
        labels={"round": "Draft Round", "hit_rate": "All-Pro Hit Rate"},
        title="All-Pro Hit Rate by Draft Round (2010–2021 Draft Classes)",
        custom_data=["allpro_count", "total_players"],
    )
    fig.update_traces(
        hovertemplate=(
            "Round %{x}<br>"
            "Hit Rate: %{y:.1%}<br>"
            "All-Pros: %{customdata[0]}<br>"
            "Total Players: %{customdata[1]}<extra></extra>"
        )
    )
    fig.update_yaxes(tickformat=".0%")
    fig.update_layout(coloraxis_showscale=False, xaxis=dict(tickmode="linear", dtick=1))
    return fig


def bar_chart_by_position(df: pd.DataFrame) -> go.Figure:
    """
    Horizontal bar chart: All-Pro hit rate by position, sorted descending.

    df must have columns: position, hit_rate, allpro_count, total_players
    """
    df_sorted = df.sort_values("hit_rate", ascending=True)
    fig = px.bar(
        df_sorted,
        x="hit_rate",
        y="position",
        orientation="h",
        color="hit_rate",
        color_continuous_scale="Teal",
        labels={"position": "Position", "hit_rate": "All-Pro Hit Rate"},
        title="All-Pro Hit Rate by Position (min. 20 drafted players, 2010–2021)",
        custom_data=["allpro_count", "total_players"],
    )
    fig.update_traces(
        hovertemplate=(
            "%{y}<br>"
            "Hit Rate: %{x:.1%}<br>"
            "All-Pros: %{customdata[0]}<br>"
            "Total Players: %{customdata[1]}<extra></extra>"
        )
    )
    fig.update_xaxes(tickformat=".0%")
    fig.update_layout(coloraxis_showscale=False, height=max(400, len(df_sorted) * 28))
    return fig


def heatmap_position_round(pivot: pd.DataFrame) -> go.Figure:
    """
    Heatmap: position × round hit rates.

    *pivot* is the output of compute_hit_rates_by_round_and_position().
    NaN cells (n < 10) are shown in light gray with "n<10" annotation.
    """
    z = pivot.values
    positions = list(pivot.index)
    rounds = [int(c) for c in pivot.columns]

    # Build annotation text
    text = []
    for row in z:
        text_row = []
        for val in row:
            if np.isnan(val):
                text_row.append("n<10")
            else:
                text_row.append(f"{val:.1%}")
        text.append(text_row)

    # Replace NaN with -1 for colorscale purposes
    z_display = np.where(np.isnan(z), -1.0, z)

    # Custom colorscale: -1 → gray, 0 → white, max → dark blue
    max_val = float(np.nanmax(z)) if not np.all(np.isnan(z)) else 0.3
    colorscale = [
        [0.0, "rgb(220,220,220)"],           # gray for n<10 sentinel
        [1e-6 / (max_val + 1e-6), "rgb(255,255,255)"],  # near-zero → white
        [1.0, "rgb(8, 48, 107)"],             # max → dark blue
    ]

    fig = go.Figure(
        data=go.Heatmap(
            z=z_display,
            x=rounds,
            y=positions,
            text=text,
            texttemplate="%{text}",
            colorscale=colorscale,
            zmin=-1,
            zmax=max_val,
            showscale=True,
            colorbar=dict(
                title="Hit Rate",
                tickformat=".0%",
                tickvals=[0, max_val * 0.5, max_val],
                ticktext=["0%", f"{max_val * 50:.0f}%", f"{max_val * 100:.0f}%"],
            ),
            hovertemplate=(
                "Position: %{y}<br>Round: %{x}<br>Hit Rate: %{text}<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        title="All-Pro Hit Rate Heatmap: Position × Round",
        xaxis=dict(title="Draft Round", tickmode="linear", dtick=1),
        yaxis=dict(title="Position"),
        height=max(500, len(positions) * 30 + 100),
    )
    return fig


def scatter_by_pick_number(df: pd.DataFrame) -> go.Figure:
    """
    Scatter + smoothed line: hit rate by overall pick number.

    df must have columns: pick, hit_rate, rolling_hit_rate
    """
    fig = go.Figure()

    # Faint raw dots
    fig.add_trace(
        go.Scatter(
            x=df["pick"],
            y=df["hit_rate"],
            mode="markers",
            marker=dict(color="steelblue", opacity=0.3, size=5),
            name="Per-pick rate",
            hovertemplate="Pick %{x}: %{y:.1%}<extra></extra>",
        )
    )

    # Smoothed line
    fig.add_trace(
        go.Scatter(
            x=df["pick"],
            y=df["rolling_hit_rate"],
            mode="lines",
            line=dict(color="darkblue", width=2.5),
            name="10-pick rolling avg",
            hovertemplate="Pick %{x}: %{y:.1%}<extra></extra>",
        )
    )

    # Vertical dashed lines at round boundaries
    for boundary in ROUND_BOUNDARIES:
        if boundary <= df["pick"].max():
            fig.add_vline(
                x=boundary,
                line_dash="dash",
                line_color="gray",
                line_width=1,
                annotation_text=f"R{ROUND_BOUNDARIES.index(boundary) + 2}",
                annotation_position="top",
            )

    fig.update_yaxes(tickformat=".0%")
    fig.update_layout(
        title="All-Pro Hit Rate by Overall Pick Number (10-pick rolling avg)",
        xaxis_title="Overall Pick Number",
        yaxis_title="All-Pro Hit Rate",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def value_table_chart(df: pd.DataFrame) -> go.Figure:
    """
    Table: best-value positions (late-round relative overperformers).

    df must be output of compute_value_table().
    """
    # Alternate row colors
    n = len(df)
    fill_colors = [
        ["#f0f4f8" if i % 2 == 0 else "white" for i in range(n)]
    ] * len(df.columns)

    fig = go.Figure(
        data=go.Table(
            header=dict(
                values=[
                    "Position",
                    "Round 1 Hit Rate",
                    "Rounds 3–5 Hit Rate",
                    "Late/R1 Ratio",
                    "R3–5 Drafted",
                    "R1 Drafted",
                ],
                fill_color="#08306b",
                font=dict(color="white", size=12),
                align="center",
                height=32,
            ),
            cells=dict(
                values=[
                    df["position"],
                    df["r1_rate"].map(lambda x: f"{x:.1%}"),
                    df["r35_rate"].map(lambda x: f"{x:.1%}"),
                    df["late_round_to_r1_ratio"].map(
                        lambda x: f"{x:.2f}x" if pd.notna(x) else "N/A"
                    ),
                    df["r35_count"],
                    df["r1_count"],
                ],
                fill_color=fill_colors,
                align="center",
                height=28,
                font=dict(size=11),
            ),
        )
    )
    fig.update_layout(
        title="Best-Value Positions: Rounds 3–5 vs Round 1 All-Pro Rate",
        height=max(300, n * 32 + 100),
    )
    return fig
