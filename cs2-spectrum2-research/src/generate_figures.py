"""Generate the final figures and diagnostics from committed processed CSVs.

This script changes presentation/labels only. It does not alter the underlying
research methodology or the source CSV data.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed"
FIGURE_DIR = ROOT / "figures"


def short_skin_name(market_name):
    """Remove the wear suffix from chart labels."""
    return str(market_name).replace(" (Factory New)", "")


def make_volatility_chart():
    """Compare observed and winsorized annualized volatility."""
    raw = pd.read_csv(DATA_DIR / "spectrum2_financial_metrics.csv")
    robust = pd.read_csv(
        DATA_DIR / "spectrum2_financial_metrics_winsorized.csv"
    )

    data = raw[
        ["Market_Name", "Annualized_Volatility"]
    ].merge(
        robust[["Market_Name", "Annualized_Volatility"]],
        on="Market_Name",
        suffixes=("_Raw", "_Winsorized"),
    )

    data["Skin"] = data["Market_Name"].map(short_skin_name)

    # Stored volatility values are decimals; display them as percentages.
    data["Annualized_Volatility_Raw"] *= 100.0
    data["Annualized_Volatility_Winsorized"] *= 100.0

    data = data.sort_values("Annualized_Volatility_Raw")

    y = np.arange(len(data))
    height = 0.38

    fig, ax = plt.subplots(figsize=(10.5, 7.5))

    ax.barh(
        y - height / 2,
        data["Annualized_Volatility_Raw"],
        height,
        label="Observed returns",
    )
    ax.barh(
        y + height / 2,
        data["Annualized_Volatility_Winsorized"],
        height,
        label="Winsorized daily returns",
    )

    ax.set_yticks(y)
    ax.set_yticklabels(data["Skin"])
    ax.set_xlabel("Annualized volatility (%)")
    ax.set_title(
        "Effect of 1%/99% Winsorization on Annualized Volatility"
    )
    ax.grid(axis="x", alpha=0.20)
    ax.legend(frameon=False)

    fig.tight_layout()
    fig.savefig(
        FIGURE_DIR / "raw_vs_winsorized_volatility.png",
        dpi=250,
        bbox_inches="tight",
    )
    plt.close(fig)


def make_factor_correlation_chart():
    """Compare raw and winsorized Pearson return correlations."""
    raw = pd.read_csv(DATA_DIR / "spectrum2_correlations.csv")
    robust = pd.read_csv(
        DATA_DIR / "spectrum2_correlations_winsorized.csv"
    )

    features = [
        "Mean_Saturation",
        "Mean_Brightness",
        "Color_Diversity",
    ]
    labels = [
        "Saturation",
        "Brightness",
        "Color diversity",
    ]

    def select(data):
        subset = data[
            (data["Visual_Feature"].isin(features))
            & (data["Financial_Metric"] == "Total_Return")
        ]
        series = subset.set_index(
            "Visual_Feature"
        )["Pearson_Correlation"]
        return series.loc[features]

    raw_values = select(raw)
    robust_values = select(robust)

    x = np.arange(len(features))
    width = 0.40

    fig, ax = plt.subplots(figsize=(9, 5.5))

    ax.bar(
        x - width / 2,
        raw_values.to_numpy(),
        width,
        label="Observed returns",
    )
    ax.bar(
        x + width / 2,
        robust_values.to_numpy(),
        width,
        label="Winsorized daily returns",
    )

    ax.axhline(0, linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel(
        "Pearson correlation with sample-period total return"
    )
    ax.set_title(
        "Pre-Specified Visual Factors: Return Correlations"
    )
    ax.grid(axis="y", alpha=0.20)
    ax.legend(frameon=False)

    fig.tight_layout()
    fig.savefig(
        FIGURE_DIR
        / "factor_correlations_raw_vs_winsorized.png",
        dpi=250,
        bbox_inches="tight",
    )
    plt.close(fig)


def make_portfolio_return_chart():
    """Plot observed total returns for characteristic-sorted portfolios."""
    data = pd.read_csv(DATA_DIR / "spectrum2_portfolios.csv")

    data = data[
        data["Portfolio"].str.startswith(
            ("High ", "Low "),
            na=False,
        )
    ].copy()

    data["Label"] = (
        data["Portfolio"]
        .str.replace("Mean_", "", regex=False)
        .str.replace("_", " ", regex=False)
    )

    data["Total_Return_Percent"] = (
        pd.to_numeric(data["Total_Return"], errors="coerce")
        * 100.0
    )

    data = (
        data
        .dropna(subset=["Total_Return_Percent"])
        .sort_values("Total_Return_Percent")
    )

    fig, ax = plt.subplots(figsize=(9.5, 5.5))

    ax.barh(
        data["Label"],
        data["Total_Return_Percent"],
    )

    ax.set_xlabel(
        "Observed sample-period total return (%)"
    )
    ax.set_title(
        "Characteristic-Sorted Buy-and-Hold Portfolios"
    )
    ax.grid(axis="x", alpha=0.20)

    fig.tight_layout()
    fig.savefig(
        FIGURE_DIR / "portfolio_total_returns.png",
        dpi=250,
        bbox_inches="tight",
    )
    plt.close(fig)


def make_normalized_price_chart():
    """Plot observed Steam price history normalized to 100."""
    history = pd.read_csv(
        DATA_DIR / "spectrum2_daily_prices.csv"
    )

    history["Date"] = pd.to_datetime(
        history["Date"],
        errors="coerce",
    )
    history["Price"] = pd.to_numeric(
        history["Price"],
        errors="coerce",
    )

    history = history.dropna(
        subset=["Date", "Price", "Market_Name"]
    )

    fig, ax = plt.subplots(figsize=(12, 7))

    for item_name, group in history.groupby("Market_Name"):
        group = group.sort_values("Date")
        group = group[group["Price"] > 0].copy()

        if group.empty:
            continue

        normalized = (
            group["Price"]
            / group["Price"].iloc[0]
            * 100.0
        )

        ax.plot(
            group["Date"],
            normalized,
            label=short_skin_name(item_name),
            linewidth=1.35,
        )

    ax.set_title(
        "Spectrum 2: Normalized Steam Price History"
    )
    ax.set_xlabel("Date")
    ax.set_ylabel(
        "Price Index (Start = 100, log scale)"
    )
    ax.set_yscale("log")
    ax.grid(True, which="both", alpha=0.20)
    ax.legend(
        fontsize=7,
        ncol=2,
        frameon=False,
    )

    fig.tight_layout()
    fig.savefig(
        FIGURE_DIR / "normalized_price_paths_log.png",
        dpi=250,
        bbox_inches="tight",
    )
    plt.close(fig)


def make_saturation_return_chart():
    """Plot saturation against observed sample-period total return."""
    master = pd.read_csv(
        DATA_DIR / "spectrum2_master.csv"
    )

    data = master[
        [
            "Mean_Saturation",
            "Total_Return",
            "Market_Name",
        ]
    ].copy()

    data["Mean_Saturation"] = pd.to_numeric(
        data["Mean_Saturation"],
        errors="coerce",
    )
    data["Total_Return"] = pd.to_numeric(
        data["Total_Return"],
        errors="coerce",
    )

    data = data.dropna()

    if len(data) < 2:
        return

    data["Return_Percent"] = (
        data["Total_Return"] * 100.0
    )

    fig, ax = plt.subplots(figsize=(10, 7))

    ax.scatter(
        data["Mean_Saturation"],
        data["Return_Percent"],
        s=55,
        alpha=0.85,
    )

    # Label only the two largest observed returns. These are the
    # influential observations most useful to identify visually.
    label_rows = data.nlargest(
        2,
        "Return_Percent",
    )

    for _, row in label_rows.iterrows():
        ax.annotate(
            short_skin_name(row["Market_Name"]),
            (
                row["Mean_Saturation"],
                row["Return_Percent"],
            ),
            fontsize=8,
            xytext=(6, 5),
            textcoords="offset points",
        )

    ax.set_title(
        "Spectrum 2: Mean Saturation vs. Sample-Period Return"
    )
    ax.set_xlabel(
        "Mean Image Saturation (0-1)"
    )
    ax.set_ylabel(
        "Observed sample-period total return (%)"
    )
    ax.grid(True, alpha=0.20)

    fig.tight_layout()
    fig.savefig(
        FIGURE_DIR / "saturation_vs_return.png",
        dpi=250,
        bbox_inches="tight",
    )
    plt.close(fig)


def make_individual_sharpe_chart():
    """Plot observed individual-skin annualized Sharpe ratios."""
    master = pd.read_csv(
        DATA_DIR / "spectrum2_master.csv"
    )

    data = master[
        ["Market_Name", "Sharpe_Ratio"]
    ].copy()

    data["Sharpe_Ratio"] = pd.to_numeric(
        data["Sharpe_Ratio"],
        errors="coerce",
    )
    data = data.dropna()

    if data.empty:
        return

    data["Skin"] = data["Market_Name"].map(
        short_skin_name
    )
    data = data.sort_values("Sharpe_Ratio")

    fig_height = max(
        6.5,
        0.36 * len(data) + 1.5,
    )

    fig, ax = plt.subplots(
        figsize=(10.5, fig_height)
    )

    ax.barh(
        data["Skin"],
        data["Sharpe_Ratio"],
    )

    ax.axvline(0, linewidth=0.8)
    ax.set_title(
        "Spectrum 2: Individual-Skin Sharpe Ratios"
    )
    ax.set_xlabel(
        "Annualized Sharpe Ratio (observed returns)"
    )
    ax.set_ylabel("")
    ax.grid(axis="x", alpha=0.20)

    fig.tight_layout()
    fig.savefig(
        FIGURE_DIR / "skin_sharpe_ratios.png",
        dpi=250,
        bbox_inches="tight",
    )
    plt.close(fig)


def make_portfolio_sharpe_chart():
    """Plot observed Sharpe ratios for high/low portfolios."""
    portfolios = pd.read_csv(
        DATA_DIR / "spectrum2_portfolios.csv"
    )

    data = portfolios[
        portfolios["Portfolio"].str.startswith(
            ("High ", "Low "),
            na=False,
        )
    ][
        ["Portfolio", "Sharpe_Ratio"]
    ].copy()

    data["Sharpe_Ratio"] = pd.to_numeric(
        data["Sharpe_Ratio"],
        errors="coerce",
    )
    data = data.dropna()

    if data.empty:
        return

    data["Portfolio"] = (
        data["Portfolio"]
        .str.replace("Mean_", "", regex=False)
        .str.replace("_", " ", regex=False)
    )

    data = data.sort_values("Sharpe_Ratio")

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.barh(
        data["Portfolio"],
        data["Sharpe_Ratio"],
    )

    ax.axvline(0, linewidth=0.8)
    ax.set_title(
        "Spectrum 2: Characteristic Portfolio Sharpe Ratios"
    )
    ax.set_xlabel(
        "Annualized Sharpe Ratio (observed returns)"
    )
    ax.set_ylabel("")
    ax.grid(axis="x", alpha=0.20)

    fig.tight_layout()
    fig.savefig(
        FIGURE_DIR / "factor_portfolio_sharpe.png",
        dpi=250,
        bbox_inches="tight",
    )
    plt.close(fig)


def make_starting_price_diagnostic():
    """Write starting-price Pearson and rank correlations."""
    master = pd.read_csv(
        DATA_DIR / "spectrum2_master.csv"
    )

    required = [
        "Start_Price",
        "Total_Return",
        "Mean_Saturation",
    ]

    for column in required:
        master[column] = pd.to_numeric(
            master[column],
            errors="coerce",
        )

    def correlations(left, right):
        pair = master[
            [left, right]
        ].dropna()

        if len(pair) < 2:
            return np.nan, np.nan

        pearson = pair[left].corr(
            pair[right]
        )

        # Spearman correlation is Pearson correlation of ranks.
        left_rank = pair[left].rank(
            method="average"
        )
        right_rank = pair[right].rank(
            method="average"
        )
        spearman = left_rank.corr(
            right_rank
        )

        return pearson, spearman

    rows = []

    relationships = [
        (
            "Start price vs total return",
            "Start_Price",
            "Total_Return",
        ),
        (
            "Start price vs mean saturation",
            "Start_Price",
            "Mean_Saturation",
        ),
        (
            "Mean saturation vs total return",
            "Mean_Saturation",
            "Total_Return",
        ),
    ]

    for label, left, right in relationships:
        pearson, spearman = correlations(
            left,
            right,
        )

        rows.append(
            {
                "Relationship": label,
                "Pearson": pearson,
                "Spearman": spearman,
            }
        )

    pd.DataFrame(rows).to_csv(
        DATA_DIR / "starting_price_diagnostic.csv",
        index=False,
    )


def main():
    FIGURE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    make_volatility_chart()
    make_factor_correlation_chart()
    make_portfolio_return_chart()
    make_normalized_price_chart()
    make_saturation_return_chart()
    make_individual_sharpe_chart()
    make_portfolio_sharpe_chart()
    make_starting_price_diagnostic()

    print("All figures and diagnostics created.")


if __name__ == "__main__":
    main()
