# 🧬 TwinSampler: Synthetic Epidemic & Ascertainment Engine

**TwinSampler** is a computational epidemiology tool designed to bridge the gap between theoretical Agent-Based Models (ABMs) and observable public health data. It processes raw disease simulation outputs and applies a "Lens of Ascertainment" to generate highly realistic, biased public health line lists paired with complete, hidden ground-truth transmission graphs.

This repository serves as the data-generation backend for adaptive sampling frameworks, enabling researchers to test surveillance strategies against realistic systemic biases.

## 🚀 Key Features

*   **State-Dependent Ascertainment:** Models the "First Ascertained Event" by calculating detection probabilities chronologically across disease states (e.g., Presymptomatic vs. Severe).
*   **Demographic Bias Injection:** Configurable YAML parameters simulate real-world surveillance lag and systemic under-testing based on age, socioeconomic status (SES), and geographic access.
*   **Time-Aware Graph Reconstruction:** Utilizes optimized time-aware merging (`pandas.merge_asof`) to flawlessly reconstruct transmission networks, naturally handling re-infections and bridging disconnected data frames.
*   **Variant "Painting":** Dynamically overlays real-world variant importation schedules onto simulated transmission components.
*   **Ground Truth Preservation:** Outputs both the biased observable line list and the complete, unseen `allevents` transmission tree for downstream algorithmic benchmarking.

## 📂 Core Components

*   `simulate_linelist.py`: The primary orchestrator. Filters raw EpiHiper ABM data, links transmission networks, applies ascertainment probabilities, and generates the final line list CSVs.
*   `ascertainment_module.py`: The probability engine. Translates ABM exit states into clinical severities and calculates row-wise detection probabilities based on `ascertainment_parameters.yaml`.
*   `label_components.py`: The topology engine. Extracts the `alias_pid` transmission graph, detects connected components, and assigns genetic variant labels over time.

## 📊 Inputs & Outputs

**Inputs:** Raw ABM event logs (EpiHiper), synthetic population demographics (Census/Persontrait), and YAML ascertainment configurations.
**Outputs:** 
- `linelist.csv.xz` (The biased, observable public health record)
- `linelist_allevents.csv.xz` (The fully connected, hidden transmission ground truth)
- `abmugration.json` (The baseline geographic transition matrix)

