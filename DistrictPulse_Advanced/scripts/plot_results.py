"""Plot controller metrics from summarize_results.py output."""
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="results/comparison.csv")
    parser.add_argument("--out", default="results/controller_comparison.png")
    args = parser.parse_args()
    df = pd.read_csv(args.csv)
    candidates = [
        "mean_ordinary_trip_duration_s",
        "mean_ordinary_trip_waiting_s",
        "mean_emergency_trip_duration_s",
        "mean_emergency_trip_waiting_s",
        "mean_trip_time_loss_s",
        "mean_halting_vehicles",
    ]
    metrics = [metric for metric in candidates
               if metric in df.columns and pd.to_numeric(df[metric], errors="coerce").notna().any()]
    if not metrics:
        raise SystemExit("No recognized non-empty metrics in CSV.")
    if "controller" not in df:
        raise SystemExit("CSV must contain a controller column.")
    fig, axes = plt.subplots(1, len(metrics), figsize=(5 * len(metrics), 4))
    if len(metrics) == 1:
        axes = [axes]
    for ax, metric in zip(axes, metrics):
        subset = df[["controller", metric]].copy()
        subset[metric] = pd.to_numeric(subset[metric], errors="coerce")
        subset = subset.dropna()
        if subset.empty:
            ax.set_visible(False)
            continue
        subset.boxplot(column=metric, by="controller", ax=ax)
        ax.set_title(metric.replace("_", " "))
        ax.set_xlabel("controller")
        ax.set_ylabel("seconds" if "duration" in metric or "waiting" in metric or "time_loss" in metric else "vehicles")
    fig.suptitle("DistrictPulse matched-seed controller comparison")
    fig.tight_layout()
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=160)
    print("Saved", output)


if __name__ == "__main__":
    main()
