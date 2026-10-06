# Unapplied patches

## 0002-ascertain-per-infection.patch

`simulate()`'s first-detection set is keyed on `pid`, the person, so once
somebody is ascertained they are excluded for the rest of the run -- including
for later, entirely separate infections.

Measured on the 36-week Delta wave: 1,033,000 of 4,090,940 people (25.3%) have
more than one infection, up to 6, with episodes 39 to 114 days apart. Each is
a distinct `alias_pid` with its own `strain` and its own painted genome. So a
quarter of the population was systematically under-ascertained, and
non-randomly -- being detected early is exactly what disqualified you later.

The patch keys on `alias_pid` and adds a guard, because
`format_final_linelist` silently adds a missing schema column as an empty
string; without the guard a reordering upstream would collapse every infection
onto one key rather than error.

### Why this is not applied

Confirm first that EpiHiper's disease model intends that much waning immunity.
A 39-day reinfection interval is short for SARS-CoV-2, and 25% within 252 days
is high; the `R2` -> susceptible parameterisation lives in
`cfg/exp1/disease.json`, not here. Making those infections detectable is only
the right fix if the model means to produce them.

### Blast radius

Everything downstream. The line list grows, every sampled set changes, and
every benchmark number moves. Give it its own run and note it against any
prior results.

### To apply

    git apply patches/0002-ascertain-per-infection.patch

### Numbering

`0001-surs-seeding.patch` is in BeyondBaseline's `patches/`, since it changes
`run_all_scenarios.py`. The two are independent; the numbering is shared only
so the pair can be discussed in order.
