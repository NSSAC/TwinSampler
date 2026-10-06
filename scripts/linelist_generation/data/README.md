# Bundled data

Small reference tables shipped inside the `linelist_generation` package
(declared as package data in `pyproject.toml`), so they are present in every
install, not only in a checkout.

| file | size | source |
|---|---|---|
| `Ruralurbancontinuumcodes2023.csv` | 629 KB | USDA Economic Research Service |
| `county_fips.csv` | 57 KB | derived from the US Census county table |

---

## Ruralurbancontinuumcodes2023.csv

USDA Rural-Urban Continuum Codes, 2023 edition. Classifies every US county on
a 1-9 scale from "metro, 1 million+" to "completely rural, not adjacent to a
metro area".

Used by TwinSampler's ascertainment model as the geographic-access modifier:
rural counties get a lower detection probability, reflecting reduced testing
access.

**Source**
<https://www.ers.usda.gov/data-products/rural-urban-continuum-codes>

Direct download (what this copy came from, retrieved 2026-10-01):
```
https://www.ers.usda.gov/media/5768/2023-rural-urban-continuum-codes.csv?v=27068
```

**Rights.** Produced by the USDA Economic Research Service, an agency of the
United States federal government. Works of the US government are not subject
to domestic copyright protection (17 U.S.C. 105) and are in the public domain.
Redistributed here unmodified for reproducibility; please credit USDA ERS.

**Shape.** Long format, one row per county per attribute:

```
FIPS,State,County_Name,Attribute,Value
01001,AL,Autauga County,Population_2020,58805
01001,AL,Autauga County,RUCC_2023,2
```

9,703 rows covering 3,235 counties. `rucc_utils.load_and_pivot_rucc()` pivots
this to wide and renames `RUCC_2023` to `rucc_code`.

**Refreshing.** The copy here is pinned so that results stay reproducible.
`simulate-linelist` uses it unless `--rucc` names another file, so to use a
newer edition download it from the URL above and pass it explicitly
(PhyloGAS: set `population.rucc_file`; `phylogas fetch-data --with-rucc`
downloads it for you).

Note that RUCC is revised roughly every decade (2003, 2013, 2023), and county
FIPS codes do change — Connecticut replaced its counties with planning regions
in 2022, for instance. Re-running an old analysis against a new RUCC file may
not reproduce.
