"""The strain id is a cross-repo contract; pin it.

`format_final_linelist` builds the Nextstrain `strain` column. The genetic
painter builds the same string independently, as its FASTA headers, and ncov
joins sequences to metadata on it -- so a one-character disagreement empties
the tree, sometimes without an error.

This test runs the real construction over a fixture table that PhyloGAS also
pins (`PhyloGAS/tests/test_strain_id_contract.py`, same JSON). Change either
formula and at least one of the two tests fails.

`test_data/strain_ids.json` is a copy of PhyloGAS's fixture, deliberately --
TwinSampler must stay runnable with PhyloGAS absent. Keep them in step.
"""

import json
from pathlib import Path

import pandas as pd
import pytest

from simulate_linelist import format_final_linelist

FIXTURE = Path(__file__).parent / "test_data" / "strain_ids.json"


def _fixture():
    d = json.loads(FIXTURE.read_text())
    return d, d["cases"]


def _linelist_frame(cases, start_date, start_tick):
    """Build the minimal frame format_final_linelist needs for these columns."""
    rows = []
    for c in cases:
        exposure_date = pd.to_datetime(start_date) + pd.Timedelta(
            days=c["tick"] - start_tick)
        rows.append({
            "pid": c["pid"],
            "exposure_tick": c["tick"],
            "exposure_date": exposure_date,
            "date": exposure_date,
            # format_final_linelist derives asymptomatic/test_prob from these
            "symptom_severity": "mild",
            "ascertainment_prob": 0.5,
        })
    return pd.DataFrame(rows)


@pytest.mark.parametrize("abbr", ["VA", "WA", "GA"])
def test_strain_matches_fixture_for_each_geography(abbr):
    d, cases = _fixture()
    subset = [c for c in cases if c["divisionAbbr"] == abbr]
    if not subset:
        pytest.skip(f"fixture has no {abbr} cases")

    df = _linelist_frame(subset, d["start_date"], d["start_tick"])
    out = format_final_linelist(df, country=subset[0]["country"],
                                divisionAbbr=abbr)
    assert list(out["strain"]) == [c["strain"] for c in subset]


def test_geography_is_not_hardcoded():
    """A non-Virginia run must change the strain id.

    This is the regression that mattered: country/division/divisionAbbr used
    to be hardcoded Python defaults here while the painter read them from
    config, so a Washington run produced VA strains against WA FASTA headers.
    """
    d, cases = _fixture()
    df = _linelist_frame(cases[:1], d["start_date"], d["start_tick"])

    va = format_final_linelist(df.copy(), divisionAbbr="VA")["strain"].iloc[0]
    wa = format_final_linelist(df.copy(), divisionAbbr="WA")["strain"].iloc[0]
    assert va != wa
    assert "-EHip-" in va and va.startswith("USA/VA")
    assert wa.startswith("USA/WA")
