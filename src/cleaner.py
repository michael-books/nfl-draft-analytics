"""
cleaner.py — Normalize, deduplicate, and type-cast raw PFR data.
"""
from __future__ import annotations

import re
import pathlib
import pandas as pd

POSITION_MAP = {
    "OLB": "LB",
    "ILB": "LB",
    "MLB": "LB",
    "FB": "RB",
    "FS": "S",
    "SS": "S",
    "LT": "OT",
    "RT": "OT",
    "LG": "OG",
    "RG": "OG",
    "NT": "DT",
}

_SUFFIX_RE = re.compile(
    r"\b(jr|sr|ii|iii|iv|hof)\b",
    re.IGNORECASE,
)
_PUNCT_RE = re.compile(r"[^\w\s]")  # remove apostrophes, periods, etc.
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_name(name: str) -> str:
    """Lowercase, strip suffixes and punctuation, collapse whitespace."""
    name = name.lower().strip()
    name = _SUFFIX_RE.sub("", name)
    name = _PUNCT_RE.sub("", name)
    name = _WHITESPACE_RE.sub(" ", name).strip()
    return name


def load_from_excel(
    excel_path: str | pathlib.Path,
    output_dir: str | pathlib.Path,
) -> pd.DataFrame:
    """
    Read the combined NFL Draft Excel file (which already contains AP1 counts)
    and produce both the cleaned draft CSV and the merged dataset CSV in one
    step — no scraping required.

    The Excel file is expected to have PFR's multi-level header structure with
    columns including:
        Unnamed: 0_level_0_Rnd, Unnamed: 1_level_0_Pick, Unnamed: 2_level_0_Tm,
        Unnamed: 3_level_0_Player, Unnamed: 4_level_0_Pos, Unnamed: 5_level_0_Age,
        Misc_AP1, Unnamed: 27_level_0_College/Univ, Year

    Returns the merged DataFrame with is_allpro flag.
    """
    excel_path = pathlib.Path(excel_path)
    output_dir = pathlib.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_excel(excel_path)

    # Rename columns to our standard schema
    col_map = {
        "Unnamed: 0_level_0_Rnd": "round",
        "Unnamed: 1_level_0_Pick": "pick",
        "Unnamed: 2_level_0_Tm": "team",
        "Unnamed: 3_level_0_Player": "player_name",
        "Unnamed: 4_level_0_Pos": "position",
        "Unnamed: 5_level_0_Age": "age",
        "Misc_AP1": "ap1_count",
        "Misc_PB": "pro_bowls",
        "Approx Val_wAV": "wAV",
        "Unnamed: 27_level_0_College/Univ": "college",
        "Year": "year",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    # Drop repeated PFR header rows (where round == 'Rnd')
    df = df[df["round"] != "Rnd"].copy()

    # Drop rows without a player name
    df = df.dropna(subset=["player_name"])
    df = df[df["player_name"].str.strip() != ""]

    # Cast numeric columns
    for col in ["round", "pick", "year"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["round", "pick", "year"])
    df["round"] = df["round"].astype(int)
    df["pick"] = df["pick"].astype(int)
    df["year"] = df["year"].astype(int)

    # ap1_count: coerce to numeric (header rows leave string 'AP1')
    df["ap1_count"] = pd.to_numeric(df["ap1_count"], errors="coerce").fillna(0).astype(int)

    # is_allpro flag: 1 if player earned at least one First-Team All-Pro
    df["is_allpro"] = (df["ap1_count"] > 0).astype(int)

    # Normalize positions
    df["position"] = df["position"].str.strip().map(
        lambda p: POSITION_MAP.get(p, p)
    )

    # Normalize player names
    df["player_name_norm"] = df["player_name"].apply(normalize_name)

    # Save cleaned draft CSV
    draft_out = output_dir / "draft_cleaned.csv"
    df.to_csv(draft_out, index=False)
    print(f"Saved cleaned draft data → {draft_out}  ({len(df):,} rows)")

    # Save merged dataset (already has is_allpro)
    merged_out = output_dir / "merged_dataset.csv"
    df.to_csv(merged_out, index=False)
    print(f"Saved merged dataset    → {merged_out}  ({len(df):,} rows)")
    print(f"  All-Pro players: {df['is_allpro'].sum()} / {len(df)}")

    return df


def clean_draft_data(
    raw_dir: str | pathlib.Path, output_path: str | pathlib.Path
) -> pd.DataFrame:
    """
    Concatenate all draft_YYYY.csv files in *raw_dir*, clean, and save.

    Returns the cleaned DataFrame.
    """
    raw_dir = pathlib.Path(raw_dir)
    csv_files = sorted(raw_dir.glob("draft_*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No draft CSV files found in {raw_dir}")

    frames = [pd.read_csv(f, dtype=str) for f in csv_files]
    df = pd.concat(frames, ignore_index=True)

    # Drop PFR repeated header rows
    df = df[df["round"] != "Rnd"].copy()

    # Drop rows with missing essential fields
    df = df.dropna(subset=["round", "pick", "player_name"])
    df = df[df["player_name"].str.strip() != ""]

    # Cast numeric columns
    df["round"] = pd.to_numeric(df["round"], errors="coerce")
    df["pick"] = pd.to_numeric(df["pick"], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df.dropna(subset=["round", "pick", "year"])
    df["round"] = df["round"].astype(int)
    df["pick"] = df["pick"].astype(int)
    df["year"] = df["year"].astype(int)

    # Normalize positions
    df["position"] = df["position"].str.strip().map(
        lambda p: POSITION_MAP.get(p, p)
    )

    # Normalize player names
    df["player_name_norm"] = df["player_name"].apply(normalize_name)

    output_path = pathlib.Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Saved cleaned draft data → {output_path}  ({len(df):,} rows)")
    return df


def clean_allpro_data(
    raw_dir: str | pathlib.Path, output_path: str | pathlib.Path
) -> pd.DataFrame:
    """
    Concatenate all allpro_YYYY.csv files in *raw_dir*, clean, and save.

    Returns the cleaned DataFrame.
    """
    raw_dir = pathlib.Path(raw_dir)
    csv_files = sorted(raw_dir.glob("allpro_*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No allpro CSV files found in {raw_dir}")

    frames = [pd.read_csv(f, dtype=str) for f in csv_files]
    df = pd.concat(frames, ignore_index=True)

    # Drop rows with missing player names
    df = df.dropna(subset=["player_name"])
    df = df[df["player_name"].str.strip() != ""]

    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")

    # Normalize player names
    df["player_name_norm"] = df["player_name"].apply(normalize_name)

    # Deduplicate on normalized name + year
    df = df.drop_duplicates(subset=["player_name_norm", "year"])

    output_path = pathlib.Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Saved cleaned All-Pro data → {output_path}  ({len(df):,} rows)")
    return df
