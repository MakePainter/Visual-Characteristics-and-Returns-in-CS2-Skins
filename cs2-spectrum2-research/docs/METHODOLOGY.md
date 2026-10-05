# Methodology

## Universe and research design

The cross-section consists of all 17 Spectrum 2 Factory New skins, excluding StatTrak and Souvenir. The three **pre-specified** visual sorting factors are mean saturation, mean brightness, and palette color diversity. The exercise is exploratory; the collection and wear restrictions reduce heterogeneity but do not eliminate rarity, starting-price, liquidity, or market-condition confounding.

## Market data and individual-skin returns

OpenSkin-reported Steam daily price history covers **2023-09-29 to 2026-09-28** in the frozen October 5 snapshot (**18,110** valid skin-date price records). These are provider-reported historical aggregates, not guaranteed executable closing quotes. Each skin's total return is `last observed price / first observed price - 1`; annualized return uses the elapsed calendar days. Individual-skin price histories need not contain all dates. A one-day return is valid only if consecutive observations are exactly one calendar day apart; there is **no price forward-fill** and no assumption that missing days earn zero return.

Annualized volatility is sample standard deviation of valid one-day returns times `sqrt(365)`. Sharpe ratios annualize the mean daily excess return over its sample standard deviation, with `sqrt(365)`. Historical three-month U.S. Treasury par yields (`BC_3MONTH`) are converted from percentage to decimal, divided by 365, and matched backward to the most recently available publication date. Maximum drawdown for individual skins uses the compounded series of valid one-day returns; it is not identical to drawdown from an uninterrupted daily price series when observations are missing.

## Image-derived features

Steam/OpenSkin PNG images are standardized and converted to RGBA. Fully transparent pixels (alpha = 0) are excluded; all visible pixels are retained, including non-painted metal, wood, shadows, and highlights. Mean saturation and brightness use HSV values for visible pixels. Edge density counts differences between adjacent visible pixels only; luminance and RGB statistics also exclude the transparent canvas. ColorThief is given only visible RGB pixels for its six-color palette and dominant color. Color diversity is the mean pairwise Euclidean RGB distance among palette colors, an exploratory proxy rather than a perceptually uniform color metric. Images are treated as static characteristics for the historical period.

## Median-sorted buy-and-hold portfolios

For each factor, skins with values **greater than or equal to** the cross-sectional median enter High; skins below the median enter Low. Portfolio members are equally weighted **at inception**, using theoretical fractional units; holdings are then fixed, with no rebalancing. The all-17 benchmark follows the same rule.

The program first constructs the price panel from **one downloaded history dataset**, then determines the first and last dates on which **all 17 skins** have observed prices. In the frozen sample, these common endpoints are **2023-09-29** and **2026-09-15**. Every long-only factor portfolio and the benchmark must have valid prices on both endpoints. Between endpoints, each portfolio is valued only on dates when **all its own constituents** have prices. Consequently, intermediate price/valid-one-day-return counts differ across portfolios. This retains more actual observations than an all-17 complete-case calendar, without imputing prices. All cumulative returns and annualized buy-and-hold appreciation cover the same elapsed investment period, but risk estimates are **not based on identical intermediate daily samples**.

Portfolio daily returns are used for volatility and Sharpe **only when consecutive portfolio valuations are one calendar day apart**. Portfolio maximum drawdown is calculated from the observed portfolio value path, not an imputed daily path. The High-minus-Low series subtracts simultaneous valid one-day High and Low returns, and reports an arithmetic mean spread annualized by 365. This is descriptive; it is not an investable short portfolio, and its `Annualized_Return` is not a compounded long-short return. Spread dates begin with a return observation rather than the initial portfolio valuation date.

## Outlier robustness

All valid individual-skin one-day returns are pooled and capped at the 1st and 99th percentiles. The frozen run caps **356 of 17,707 returns (2.01%)** with bounds **-0.295923** and **0.410219**. No observations are deleted. Raw return results are primary. Synthetic winsorized price indices are constructed from capped returns and separately evaluated using the same common-endpoint logic. Synthetic compounded returns must **not** be interpreted as observed start/end price returns. Robustness correlations use winsorized skin-level compounded return metrics, not a winsorization of the raw cross-sectional return column.

## Starting-price diagnostic

The separate `generate_figures.py` presentation script produces `data/processed/starting_price_diagnostic.csv` from the committed raw master CSV. The frozen Pearson/Spearman correlations are: starting price vs total return **-0.145/-0.248**, starting price vs mean saturation **+0.347/+0.431**, and saturation vs total return **+0.605/+0.179**. These are bivariate descriptions and cannot rule out confounding or establish causal independence.

## Market frictions and generalizability

All results exclude fees, spreads, slippage, taxes, and price impact. Aggregate series do not control for exact item float, patterns, stickers, or transaction-specific details. Sample-specific high returns do not demonstrate scalable executable investment returns. There are only 17 assets and no out-of-sample validation; multiple explored visual metrics and outlier sensitivity limit inference.
