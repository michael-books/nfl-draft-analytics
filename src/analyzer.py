"""
analyzer.py — Hit-rate aggregations (pure pandas).
"""
from __future__ import annotations

import pandas as pd


def compute_hit_rates_by_round(df: pd.DataFrame) -> pd.DataFrame:
    """
    Group by round and compute All-Pro hit rate.

    Returns DataFrame with columns:
        round, hit_rate, allpro_count, total_players
    """
    grouped = df.groupby("round")["is_allpro"].agg(
        allpro_count="sum",
        total_players="count",
    ).reset_index()
    grouped["hit_rate"] = grouped["allpro_count"] / grouped["total_players"]
    return grouped.sort_values("round")


def compute_hit_rates_by_position(
    df: pd.DataFrame, min_players: int = 20
) -> pd.DataFrame:
    """
    Group by position, filter small samples, sort descending by hit rate.

    Returns DataFrame with columns:
        position, hit_rate, allpro_count, total_players
    """
    grouped = df.groupby("position")["is_allpro"].agg(
        allpro_count="sum",
        total_players="count",
    ).reset_index()
    grouped["hit_rate"] = grouped["allpro_count"] / grouped["total_players"]
    grouped = grouped[grouped["total_players"] >= min_players]
    return grouped.sort_values("hit_rate", ascending=False).reset_index(drop=True)


def compute_hit_rates_by_round_and_position(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pivot table: rows = position, columns = round.

    Cell values are hit_rate (float).  Positions with fewer than 10 players
    in a given round are NaN (handled in charts.py for gray-out display).
    """
    grouped = df.groupby(["position", "round"])["is_allpro"].agg(
        allpro_count="sum",
        total_players="count",
    ).reset_index()
    grouped["hit_rate"] = grouped["allpro_count"] / grouped["total_players"]

    # Mask cells with n < 10
    grouped.loc[grouped["total_players"] < 10, "hit_rate"] = float("nan")

    pivot = grouped.pivot(index="position", columns="round", values="hit_rate")
    pivot.columns.name = "round"
    return pivot


def compute_hit_rate_by_pick_number(df: pd.DataFrame) -> pd.DataFrame:
    """
    Group by overall pick number and add a rolling average (window=10).

    Returns DataFrame with columns:
        pick, hit_rate, allpro_count, total_players, rolling_hit_rate
    """
    grouped = df.groupby("pick")["is_allpro"].agg(
        allpro_count="sum",
        total_players="count",
    ).reset_index()
    grouped["hit_rate"] = grouped["allpro_count"] / grouped["total_players"]
    grouped = grouped.sort_values("pick").reset_index(drop=True)
    grouped["rolling_hit_rate"] = (
        grouped["hit_rate"].rolling(window=10, min_periods=1, center=True).mean()
    )
    return grouped


def compute_value_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Identify positions where rounds 3–5 are high relative to round 1.

    Returns a DataFrame sorted by the late_round_to_r1_ratio descending,
    with columns: position, r1_rate, r35_rate, late_round_to_r1_ratio,
    r35_count, r1_count
    """
    r1 = df[df["round"] == 1].groupby("position")["is_allpro"].agg(
        r1_allpro="sum",
        r1_count="count",
    ).reset_index()
    r1["r1_rate"] = r1["r1_allpro"] / r1["r1_count"]

    r35 = df[df["round"].between(3, 5)].groupby("position")["is_allpro"].agg(
        r35_allpro="sum",
        r35_count="count",
    ).reset_index()
    r35["r35_rate"] = r35["r35_allpro"] / r35["r35_count"]

    merged = r1.merge(r35, on="position", how="inner")
    merged = merged[(merged["r1_count"] >= 5) & (merged["r35_count"] >= 10)]
    merged["late_round_to_r1_ratio"] = merged.apply(
        lambda row: row["r35_rate"] / row["r1_rate"] if row["r1_rate"] > 0 else float("nan"),
        axis=1,
    )
    return (
        merged[["position", "r1_rate", "r35_rate", "late_round_to_r1_ratio", "r35_count", "r1_count"]]
        .sort_values("late_round_to_r1_ratio", ascending=False)
        .reset_index(drop=True)
    )
