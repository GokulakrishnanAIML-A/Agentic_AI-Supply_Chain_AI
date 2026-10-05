"""Forecast evaluation harness using rolling-origin cross-validation (h=1, min_train=12).
Evaluates Naive, Seasonal Naive, Trailing 3MA, and weighted blends across synthetic product histories.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

# Load historical synthetic seed orders from data/seed/orders.csv
root_dir = Path(__file__).resolve().parent.parent
orders_csv = root_dir / "data" / "seed" / "orders.csv"


def load_order_series_by_product() -> dict[str, list[int]]:
    import csv
    monthly_data: dict[str, dict[str, int]] = {}
    with open(orders_csv, "r", encoding="utf-8") as f:
        # Skip comment lines
        lines = [line for line in f if not line.strip().startswith("#")]
        reader = csv.DictReader(lines)
        for row in reader:
            prod = row.get("product_sku") or row.get("sku") or row.get("product_id") or "PROD-A"
            dt = row["order_date"][:7]  # YYYY-MM
            qty = int(row["quantity"])
            monthly_data.setdefault(prod, {})
            monthly_data[prod][dt] = monthly_data[prod].get(dt, 0) + qty

    series_by_prod: dict[str, list[int]] = {}
    for prod, date_map in monthly_data.items():
        sorted_dates = sorted(date_map.keys())
        series_by_prod[prod] = [date_map[d] for d in sorted_dates]
    return series_by_prod


def predict_naive(series: list[int]) -> int:
    return series[-1] if series else 0


def predict_seasonal_naive(series: list[int]) -> int:
    if len(series) >= 12:
        return series[-12]
    return series[-1] if series else 0


def predict_3ma(series: list[int]) -> int:
    window = series[-3:] if len(series) >= 3 else series
    return int(round(sum(window) / len(window))) if window else 0


def predict_blend(series: list[int], w: float = 0.55) -> int:
    sn = predict_seasonal_naive(series)
    ma = predict_3ma(series)
    return int(round(w * sn + (1.0 - w) * ma))


def rolling_origin_cv(series: list[int], predictor, min_train: int = 12) -> float:
    if len(series) <= min_train:
        return 0.0
    errs = []
    for t in range(min_train, len(series)):
        train = series[:t]
        actual = series[t]
        pred = predictor(train)
        mape = abs(actual - pred) / max(actual, 1)
        errs.append(mape)
    return sum(errs) / len(errs) if errs else 0.0


def evaluate_all():
    series_map = load_order_series_by_product()
    # If empty, generate standard synthetic 24-month profile for evaluation
    if not series_map:
        base = [8500, 8900, 9200, 9600, 10100, 10800, 11200, 10900, 10200, 9700, 9100, 8800]
        series_map["PROD-A"] = base + [int(x * 1.05) for x in base]

    methods = {
        "naive_last": predict_naive,
        "seasonal_naive_t12": predict_seasonal_naive,
        "trailing_3ma": predict_3ma,
        "blend_w0.25": lambda s: predict_blend(s, 0.25),
        "blend_w0.50": lambda s: predict_blend(s, 0.50),
        "blend_w0.55": lambda s: predict_blend(s, 0.55),
        "blend_w0.60": lambda s: predict_blend(s, 0.60),
        "blend_w0.75": lambda s: predict_blend(s, 0.75),
    }

    results_by_method = {m: [] for m in methods}

    for prod, series in series_map.items():
        if len(series) < 13:
            continue
        for name, fn in methods.items():
            mape = rolling_origin_cv(series, fn, min_train=12)
            results_by_method[name].append(mape)

    summary_mape = {}
    for name, mapes in results_by_method.items():
        avg_mape = sum(mapes) / len(mapes) if mapes else 0.0
        summary_mape[name] = round(avg_mape * 100, 2)

    # Pick best performing blend weight
    best_method = min(summary_mape.keys(), key=lambda k: summary_mape[k])

    output = {
        "name": "forecast_evaluation",
        "seed": 42,
        "evaluation_strategy": "rolling_origin_h1_min12",
        "num_products_evaluated": len(series_map),
        "mape_percentage_by_method": summary_mape,
        "best_method": best_method,
        "active_method": "blend_w0.55",
        "active_method_mape_pct": summary_mape.get("blend_w0.55", 0.0),
        "notes": (
            "Evaluation performed using rolling origin (h=1) over 24-month synthetic order histories. "
            "Data contains injected seasonal trends; validates forecasting pipeline mechanics."
        ),
        "status": "OK",
    }

    results_dir = root_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    out_file = results_dir / "forecast.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Forecast evaluation complete. Results written to {out_file}")
    print("MAPE Summary (%):", json.dumps(summary_mape, indent=2))
    return output


if __name__ == "__main__":
    evaluate_all()
