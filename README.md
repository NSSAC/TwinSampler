# TwinSampler

**Turn an agent-based epidemic simulation into a realistic public health line
list — and keep the ground truth.**

An ABM knows exactly who infected whom. A health department does not. It sees
only the cases that happened to get tested and reported, filtered through
testing access, symptom severity, and demographic inequity.

TwinSampler applies that filter. It reads raw EpiHiper output and produces two
things:

* **a line list** — the biased, incomplete record a surveillance system would
  actually have
* **the full transmission graph** — every infection, including the ones nobody
  ever saw

Having both is the point. You can hand the line list to a surveillance method,
then score its answers against truth the method never had access to.

---

## Install

```bash
pip install -e .
```

Needs pandas, numpy, scipy, networkx, scikit-learn, pyyaml. `pyarrow` is
optional but worth having — it substantially speeds up reading the large
EpiHiper and persontrait files:

```bash
pip install -e ".[fast]"
```

---

## Usage

```bash
simulate-linelist \
    --epihiper   output.csv.gz \
    --people     va_persontrait_epihiper.txt \
    --households va_household.csv \
    --rucc       Ruralurbancontinuumcodes2023.csv \
    --ascertain  scripts/linelist_generation/ascertainment_parameters.yaml \
    --start_date 2021-04-07 \
    --start_tick 128 \
    --stop_tick  428 \
    --schedule_input Virginia_importation_schedule.csv \
    --variant_mode variant_bipartite \
    --out        results/linelist.csv \
    --output_all_events \
    --seed 42
```

### Required inputs

| flag | what it is |
|---|---|
| `--epihiper` | raw ABM event log: `tick,pid,exit_state,contact_pid,location_id` |
| `--people` | synthetic population persontrait file |
| `--households` | household table, linking people to residences |
| `--rucc` | USDA rural-urban continuum codes, for the geography modifier |
| `--ascertain` | YAML defining the detection-probability model |

### Common options

| flag | effect |
|---|---|
| `--start_tick` / `--stop_tick` | restrict to a tick window |
| `--start_date` | calendar date corresponding to `--start_tick` |
| `--output_all_events` | also write the full transmission graph (needed for benchmarking) |
| `--seed`, `--n_seeds` | reproducibility; `--n_seeds > 1` emits several independently-ascertained line lists from one simulation |
| `--variant_mode` | `variant_bipartite` (default), `variant_temporal`, or `just_components` |
| `--schedule_input` | variant importation schedule; required unless `--variant_mode just_components` |
| `--prefix_override` | which exit-state prefixes count as a case, e.g. `'["A2","P2","I2","dM2","hM2"]'` |
| `--target_variant` | restrict output to one variant |

### Outputs

Given `--out results/linelist.csv`:

| file | contents |
|---|---|
| `linelist.csv.xz` | **the observable record** — only ascertained cases |
| `linelist_allevents.csv.xz` | **the ground truth** — one row per infection, with `--output_all_events` |
| `linelist_mugration.json` | true geographic transition matrix, for benchmarking |

With `--n_seeds N`, line lists are suffixed `_seed0`, `_seed1`, … so one
simulation yields several independent realisations of surveillance.

Both tables share a schema, including `alias_pid` and `alias_contact` — the
reinfection-safe identifiers that make the transmission graph reconstructable
— plus demographics, `ses_category`, `rucc_code`, `variant_label`,
`component_id`, and the per-row `test_prob` that produced the ascertainment
draw.

#### Identifiers and dates

| column | meaning |
|---|---|
| `alias_pid` | the **infection** id, `"{pid}.{exposure_tick}"`. 1:1 with `strain` downstream. A person infected twice has two. |
| `alias_contact` | the infector's infection id |
| `sim_pid` | the **person** in the synthetic population |
| `sim_tick`, `date` | onset of the clinical state that row records (the earliest one, in `allevents`) |
| `exposure_tick`, `exposure_date` | when the infection was acquired |

`date` is an **onset** date, not a collection or report date: no reporting
delay is modelled. Downstream tools that treat it as a sampling date are off
by the specimen-to-report lag a real system would add.

`allevents` holds one row per infection — the earliest ascertainable state
(A/P/I/dM/hM by default) — restricted to infections whose state onset falls in
`--start_tick`…`--stop_tick`. Earlier releases wrote one row per state
(about 1.7 rows per infection); consumers that counted rows as infections
over-counted. Regenerate older `allevents` files, or de-duplicate on
`alias_pid`.

---

## How ascertainment works

Detection probability is multiplicative:

```
P(detection) = P_base × M_age × M_ses × M_geography × M_comorbidity
```

`P_base` comes from clinical severity, which is derived from the ABM exit
state — asymptomatic infections are far less likely to be caught than
hospitalised ones. The multipliers then skew detection by age, socioeconomic
status, rural/urban access, and comorbidity.

Every value in `ascertainment_parameters.yaml` is sourced to the COVID-19
epidemiological literature, with inline citations. Edit that file to model a
different surveillance regime; nothing is hard-coded.

The model evaluates each infection's states **chronologically** and records
the *first* ascertained event, so someone detected while presymptomatic is not
double-counted when they later become severe. Detection is keyed on the
infection (`alias_pid`), not the person: a reinfection is a new chance to be
detected. (Releases before this fix keyed on `pid`, which silently dropped
every reinfection after a person's first detection.)

---

## What makes the output realistic

* **State-dependent detection.** Severity drives the base rate, so the line
  list is biased toward serious illness exactly as real surveillance is.
* **Demographic bias.** Age, SES, and geographic access all shift detection,
  producing the systematic under-representation real programs contend with.
* **Reinfection-safe graph reconstruction.** Transmission links are rebuilt
  with time-aware merging (`pandas.merge_asof`), so a person infected twice
  gets two distinct infection identities rather than a collapsed one.
* **Variant labelling.** Real importation schedules are overlaid onto
  transmission components, so variants enter the simulated epidemic on
  plausible dates.

---

## Components

| file | role |
|---|---|
| `simulate_linelist.py` | orchestrator: filter, link, ascertain, write |
| `ascertainment_module.py` | maps ABM exit states to severity and computes per-row detection probability |
| `demographics_module.py` | `DemographicsLoader` — reads persontrait/household files, normalises schema drift, maps FIPS to county names |
| `label_components.py` | connected components of the transmission graph, and variant assignment |
| `place_resolver.py`, `rucc_utils.py` | geography: FIPS, rural-urban codes |
| `testing_prob.py` | the probability calculation itself |
| `calc_re.py` | effective reproduction number from the event log |

`twinsampler-label-components` is also installed, for running the component
and variant labelling independently of a full line list build.

Running the scripts directly still works:

```bash
python scripts/linelist_generation/simulate_linelist.py --help
```

---

## Where this fits

```
EpiHiper ABM
     │
     ▼
TwinSampler ──────► linelist.csv.xz ──────► BeyondBaseline
     │                                       (which cases to sequence?)
     └───────────► linelist_allevents.csv.xz
                   linelist_mugration.json
                              │
                              ▼
                          PhyloGAS
                   (how well did the method do?)
```

* [BeyondBaseline](https://github.com/NSSAC/BeyondBaseline) — chooses which
  cases to sequence, under a budget
* [PhyloGAS](https://github.com/NSSAC/PhyloGAS) — paints viral genomes onto
  the transmission graph and benchmarks surveillance methods against the
  ground truth produced here

TwinSampler is useful on its own: anywhere you need a realistically biased
line list paired with the truth behind it.
