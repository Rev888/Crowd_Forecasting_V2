import numpy as np
import pandas as pd

from lib import predictor


def predict_as_of(target_date):
    """
    Simulate making a prediction for target_date using ONLY information
    that would have been available before target_date.

    The actual value on target_date is NEVER included in the feature history.
    """

    target = pd.Timestamp(target_date).normalize()

    actuals = predictor.actual_series()

    # CRITICAL: only data strictly BEFORE the target date
    history = actuals[actuals.index < target].copy()

    if history.empty:
        return None

    # Build the exact 77-feature row expected by the Optuna model
    row = predictor.build_feature_row(
        target.date(),
        history,
        actuals,
    )

    # Run the real CatBoost model
    return predictor._predict_row(row)


def main():
    actuals = predictor.actual_series()

    if actuals.empty:
        raise RuntimeError("No actual pilgrim data found.")

    dates = actuals.index.sort_values()

    print("=" * 80)
    print("TIRUMALA OPTUNA MODEL - FULL CHRONOLOGICAL BACKTEST")
    print("=" * 80)
    print(f"Available actual dates: {len(dates):,}")
    print()

    results = []
    errors = []

    for i, target in enumerate(dates, start=1):

        target_date = target.date()
        actual = float(actuals.loc[target])

        try:
            prediction = predict_as_of(target_date)

            if prediction is None:
                continue

            error = prediction - actual
            abs_error = abs(error)

            ape = (
                abs_error / actual * 100
                if actual != 0
                else np.nan
            )

            results.append(
                {
                    "date": target_date,
                    "actual": actual,
                    "prediction": prediction,
                    "error": error,
                    "abs_error": abs_error,
                    "ape_percent": ape,
                }
            )

        except Exception as exc:
            errors.append((target_date, str(exc)))
            print(f"[ERROR] {target_date}: {exc}")

        # Progress every 25 dates
        if i % 25 == 0:
            print(
                f"Processed {i:,}/{len(dates):,} "
                f"| successful: {len(results):,}"
            )

    df = pd.DataFrame(results)

    if df.empty:
        raise RuntimeError(
            "No successful backtest predictions were produced."
        )

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    mae = df["abs_error"].mean()

    rmse = np.sqrt(
        np.mean(df["error"] ** 2)
    )

    mape = df["ape_percent"].mean()

    within_5k = (
        (df["abs_error"] <= 5000).mean() * 100
    )

    within_10k = (
        (df["abs_error"] <= 10000).mean() * 100
    )

    # ------------------------------------------------------------------
    # Print results
    # ------------------------------------------------------------------

    print()
    print("=" * 80)
    print("BACKTEST RESULTS")
    print("=" * 80)

    print(f"Dates tested : {len(df):,}")
    print(f"MAE          : {mae:,.0f}")
    print(f"RMSE         : {rmse:,.0f}")
    print(f"MAPE         : {mape:.2f}%")
    print(f"Within ±5K   : {within_5k:.1f}%")
    print(f"Within ±10K  : {within_10k:.1f}%")
    print(f"Errors       : {len(errors):,}")

    # ------------------------------------------------------------------
    # Worst predictions
    # ------------------------------------------------------------------

    print()
    print("=" * 80)
    print("WORST 20 PREDICTIONS")
    print("=" * 80)

    worst = (
        df.sort_values(
            "abs_error",
            ascending=False,
        )
        .head(20)
    )

    print(
        worst.to_string(
            index=False,
            formatters={
                "actual": lambda x: f"{x:,.0f}",
                "prediction": lambda x: f"{x:,.0f}",
                "error": lambda x: f"{x:,.0f}",
                "abs_error": lambda x: f"{x:,.0f}",
                "ape_percent": lambda x: f"{x:.2f}%",
            },
        )
    )

    # ------------------------------------------------------------------
    # Save complete results
    # ------------------------------------------------------------------

    output_path = "optuna_full_backtest.csv"

    df.to_csv(
        output_path,
        index=False,
    )

    print()
    print("=" * 80)
    print(f"Saved detailed results to: {output_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()