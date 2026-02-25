"""
merger.py — Join draft + All-Pro data and add the is_allpro flag.
"""
from __future__ import annotations

import pandas as pd

# Players who earned at least one First-Team All-Pro selection.
# Used for post-merge validation.
KNOWN_ALLPROS = {
    # name (as it appears normalized), draft_year
    ("aaron donald", 2014),
    ("patrick mahomes", 2017),
    ("davante adams", 2014),
    ("travis kelce", 2013),
    ("tyreek hill", 2016),
    ("lamar jackson", 2018),
    ("joey bosa", 2016),
    ("myles garrett", 2017),
    ("nick bosa", 2019),
    ("micah parsons", 2021),
    ("justin jefferson", 2020),
    ("jamarr chase", 2021),
    ("trent williams", 2010),
    ("bobby wagner", 2012),
    ("richard sherman", 2011),
    ("earl thomas", 2010),
    ("calvin johnson", 2007),
    ("cam newton", 2011),
    ("luke kuechly", 2012),
    ("drew brees", 2001),
}


def merge_datasets(draft_df: pd.DataFrame, allpro_df: pd.DataFrame) -> pd.DataFrame:
    """
    Add a binary ``is_allpro`` column to *draft_df*.

    A player is flagged as 1 if their normalized name appears anywhere in the
    All-Pro dataset (across any year).  This intentionally ignores the year of
    the All-Pro selection — we only care whether the drafted player *ever*
    made an All-Pro team.
    """
    allpro_names = set(allpro_df["player_name_norm"].dropna().unique())
    draft_df = draft_df.copy()
    draft_df["is_allpro"] = draft_df["player_name_norm"].isin(allpro_names).astype(int)
    return draft_df


def filter_analysis_cohort(df: pd.DataFrame) -> pd.DataFrame:
    """
    Keep only draft classes from 2010–2021.

    Players drafted through 2021 have had at least 3 full seasons by end of
    2024, giving them a fair chance to earn All-Pro honors.
    """
    return df[(df["year"] >= 2010) & (df["year"] <= 2021)].copy()


def validate_known_allpros(df: pd.DataFrame) -> None:
    """
    Print a quick sanity-check table for ~20 known All-Pro players.

    Warns if any expected All-Pro has is_allpro == 0.
    """
    print("\n=== Known All-Pro Validation ===")
    issues = []
    for name_norm, draft_year in sorted(KNOWN_ALLPROS):
        subset = df[
            (df["player_name_norm"] == name_norm) & (df["year"] == draft_year)
        ]
        if subset.empty:
            status = "NOT IN DRAFT DATA"
            issues.append(name_norm)
        elif subset["is_allpro"].iloc[0] == 1:
            status = "OK ✓"
        else:
            status = "MISSING is_allpro flag ✗"
            issues.append(name_norm)
        print(f"  {name_norm:<30} ({draft_year})  {status}")

    if issues:
        print(f"\nWARNING: {len(issues)} player(s) may have name-matching issues: {issues}")
    else:
        print("\nAll known All-Pros validated successfully.")
