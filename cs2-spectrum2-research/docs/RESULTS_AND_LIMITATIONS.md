# Results and limitations

**Data freeze:** October 5, 2026 pipeline snapshot. The full individual-skin window is **2023-09-29 to 2026-09-28**. All benchmark and High/Low buy-and-hold returns below use the **common 2023-09-29 to 2026-09-15 period**. These dates must not be conflated.

## Cross-sectional relationships

Correlations below compare the three pre-specified image factors against skin-level **total returns** (N = 17). The winsorized columns use **synthetically compounded returns from capped one-day returns**.

| Visual characteristic | Raw Pearson | Raw Spearman | Winsorized Pearson | Winsorized Spearman |
| --- | ---: | ---: | ---: | ---: |
| Mean saturation | +0.605 | +0.179 | +0.437 | +0.355 |
| Mean brightness | +0.286 | +0.083 | +0.392 | +0.257 |
| Color diversity | -0.174 | -0.108 | -0.115 | +0.066 |

Saturation has the largest **raw Pearson** association with return, but its much smaller raw Spearman coefficient indicates that the linear association is sensitive to the magnitude of high-return observations. The saturation Pearson coefficient weakens under winsorization. Brightness is modest and changes under the robustness specification; color diversity shows little stable evidence. None of these correlations is a causal estimate or a demonstrated predictive factor.

## Observed-price characteristic portfolios

The portfolios are initially equal-weighted, then held without rebalancing. The High and Low legs within each characteristic and the all-skin benchmark use the same start/end dates. **Sharpe estimates use each portfolio's available valid one-day observations and therefore are not fully matched-calendar estimates.**

| Portfolio | Cumulative return | Sharpe | Valid one-day observations |
| --- | ---: | ---: | ---: |
| Spectrum 2 Benchmark | +428.6% | 0.666 | 527 |
| High Saturation | +592.6% | 0.988 | 574 |
| Low Saturation | +244.0% | 0.990 | 945 |
| High Brightness | +601.0% | 0.928 | 926 |
| Low Brightness | +234.5% | 1.285 | 579 |
| High Color Diversity | +396.3% | 0.305 | 529 |
| Low Color Diversity | +464.8% | 1.043 | 1,062 |


The High Saturation leg appreciates much more than Low Saturation, but **the two raw Sharpe ratios are nearly identical**; there is no supported risk-adjusted advantage. High Brightness has the largest raw cumulative appreciation of the six legs, yet Low Brightness has the higher Sharpe. Low Color Diversity exceeds High Color Diversity in both cumulative return and raw Sharpe for the matched endpoints; this **does not** establish a general low-diversity factor, especially given weak cross-sectional correlations and observation-set differences.

The descriptive High-minus-Low daily spread rows are **not** shortable portfolios and should not be compared to compounded long-only cumulative returns as if the return definitions were identical.

## Risk robustness

Of **17,707** valid one-day returns, **356** (**2.01%**) were capped by pooled 1%/99% winsorization. The caps are approximately **-29.59%** and **41.02%**. A small fraction of extreme observations materially changes several volatility and Sharpe estimates. Winsorized portfolio cumulative returns are **synthetic robustness values**, not realized observed-price returns.

## Starting-price diagnostic

Start price vs. total return: Pearson **-0.145**, Spearman **-0.248**. Start price vs. saturation: Pearson **+0.347**, Spearman **+0.431**. The simple low-entry-price explanation is not directly supported by these bivariate signs, but the diagnostic **does not control for** rarity, liquidity, or other confounders.

## Limitations

- **Small universe:** 17 skins in one collection and wear grade; limited statistical power, outlier sensitivity, and no out-of-sample test.
- **Market and confounders:** rarity, starting price, liquidity, item-specific float/pattern, stickers, platform events, and broader market conditions are not fully controlled.
- **Unequal intermediate samples:** common portfolio endpoints make cumulative returns comparable over time, but daily volatility/Sharpe estimates use different sets of constituent-complete one-day observations.
- **Data interpretation:** OpenSkin-reported Steam historical aggregates are not guaranteed executable bid/ask or security-style closing prices; missing observations are not imputed.
- **Frictions:** no marketplace fees, bid-ask spread, slippage, price impact, taxes, or liquidity-constrained execution; fractional holdings are theoretical.
- **Image measurement:** standardized current artwork renders are treated as fixed over time; palette RGB distances are not perceptually uniform.
- **Multiple comparisons:** reported correlations are descriptive, not proof of alpha, causality, or universal price predictability.
