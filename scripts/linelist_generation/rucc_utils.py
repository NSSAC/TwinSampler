#!/usr/bin/env python3
"""
rucc_utils.py
Utilities for reading and reshaping USDA RUCC lookup data.
"""

from __future__ import annotations
import os
import pandas as pd

# USDA ERS 2023 rural-urban continuum codes, shipped inside the package so
# --rucc is optional. Public domain (17 U.S.C. 105); provenance in
# data/README.md next to the file.
RUCC_FILENAME = "Ruralurbancontinuumcodes2023.csv"


def bundled_rucc_path() -> str:
    """Absolute path to the bundled RUCC table.

    Same resolution as demographics_module.county_fips_path(): through
    importlib.resources when installed, then beside this file for a checkout
    run as plain scripts.
    """
    try:
        from importlib.resources import files

        cand = files("linelist_generation") / "data" / RUCC_FILENAME
        if cand.is_file():
            return str(cand)
    except (ImportError, ModuleNotFoundError, TypeError, OSError):
        pass        # not importable as a package: running the files directly

    cand = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "data", RUCC_FILENAME)
    if os.path.isfile(cand):
        return cand
    raise FileNotFoundError(
        f"{RUCC_FILENAME} not found. It ships inside the package at "
        f"linelist_generation/data/{RUCC_FILENAME}; pull and reinstall "
        f"TwinSampler, or pass --rucc.")


def load_and_pivot_rucc(rucc_path: str, encoding: str = "latin1") -> pd.DataFrame:
    """
    Load a 'long' RUCC CSV and pivot to wide, returning columns:
        ['FIPS', 'State', 'County_Name', 'rucc_code', ...]
    Expects columns in the input: ['FIPS', 'State', 'County_Name', 'Attribute', 'Value'].
    """
    rucc_long = pd.read_csv(rucc_path, encoding=encoding)
    required_cols = {"FIPS", "State", "County_Name", "Attribute", "Value"}
    missing = required_cols - set(rucc_long.columns)
    if missing:
        raise ValueError(f"RUCC file missing columns: {missing}")

    rucc_wide = (
        rucc_long.pivot_table(
            index=["FIPS", "State", "County_Name"],
            columns="Attribute",
            values="Value",
            aggfunc="first",
        )
        .reset_index()
        .rename_axis(None, axis=1)
    )

    # Normalize types and names
    if "RUCC_2023" in rucc_wide.columns:
        rucc_wide = rucc_wide.rename(columns={"RUCC_2023": "rucc_code"})
    elif "RUCC" in rucc_wide.columns:
        rucc_wide = rucc_wide.rename(columns={"RUCC": "rucc_code"})
    else:
        # If neither exists, keep going but leave rucc_code missing
        rucc_wide["rucc_code"] = pd.NA

    rucc_wide["rucc_code"] = pd.to_numeric(rucc_wide["rucc_code"], errors="coerce")

    # Ensure FIPS is zero-padded 5-char string
    rucc_wide["FIPS"] = rucc_wide["FIPS"].astype(str).str.zfill(5)

    return rucc_wide
