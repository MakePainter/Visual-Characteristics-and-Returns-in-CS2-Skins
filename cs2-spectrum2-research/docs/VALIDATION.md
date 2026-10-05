# Validation notes

## Scope and freeze

These checks describe the **October 5, 2026** frozen CSV snapshot, rather than earlier pipeline runs. The individual-skin price window is **2023-09-29 to 2026-09-28**. The frozen individual-skin history contains **18,110** unique skin-date price records for **17** skins. Both correlation tables have **65** visual/financial combinations (13 features × 5 financial metrics). There are **10** rows per portfolio table (benchmark, six long-only characteristic legs, and three descriptive High-minus-Low spreads).

## Confirmed checks

1. **Universe and integrity:** 17 unique skins; no duplicated skin-date observations in the supplied latest historical price file. The raw individual-skin start/end total returns agree with observed first/last prices.
2. **Common portfolio endpoints:** the benchmark and all six long-only legs have start **2023-09-29** and end **2026-09-15** in **both** raw and winsorized portfolio tables. Intermediate valid one-day observations differ across portfolios by design. High-minus-Low spread rows start at the first valid return date, **2023-09-30**.
3. **Portfolio figures:** the final cumulative-return and Sharpe plots correspond to the October 5 raw portfolio CSV, including High Brightness **+601.0%**, High Saturation **+592.6%**, Low Saturation **+244.0%**, and Low Color Diversity **+464.8%**.
4. **Correlations:** the frozen raw Pearson saturation/return coefficient is **+0.605**; the winsorized value is **+0.437**. The figure's brightness and diversity coefficients also agree with the latest CSV.
5. **Outlier robustness:** **17,707** valid one-day returns; **356** capped (**2.01%**), with bounds **-0.295923** and **0.410219**. Raw prices and returns remain preserved separately.
6. **Starting-price diagnostic:** the separate presentation script writes `data/processed/starting_price_diagnostic.csv`; its three relationships agree with the raw master dataset. The portfolio-endpoint change does not alter this skin-level diagnostic.
7. **Architecture:** the main script generates analytical CSVs and cached image assets; `generate_figures.py` produces the seven figures and one starting-price diagnostic CSV from the frozen `data/processed` snapshot.

## Reproducibility boundary

A full clean-environment **live API rerun is not established by these checks**. Provider revisions, network access, and image availability can affect later results. To avoid mixing runs, the 17 analytical CSVs should be frozen together, then the diagnostic and figures regenerated from that snapshot. All findings are gross of trading frictions and descriptive rather than predictive.
