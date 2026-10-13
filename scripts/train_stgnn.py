"""Train and evaluate the DistrictPulse ST-GNN queue forecaster."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np

try:
    import torch
    from torch import nn
except ImportError as exc:
    raise SystemExit("Install PyTorch with: pip install torch") from exc

from districtpulse.stgnn_model import SpatialTemporalNet


def metrics(pred, target):
    error = np.asarray(pred) - np.asarray(target)
    return {"mae": float(np.mean(np.abs(error))),
            "rmse": float(np.sqrt(np.mean(error ** 2)))}


def normalize_adjacency(adjacency):
    a = np.asarray(adjacency, dtype=np.float32)
    a = a + np.eye(a.shape[0], dtype=np.float32)
    degree = np.maximum(a.sum(axis=1, keepdims=True), 1.0)
    return a / degree


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--out", default="models/stgnn.pt")
    parser.add_argument("--train-fraction", type=float, default=0.70)
    parser.add_argument("--val-fraction", type=float, default=0.15)
    parser.add_argument("--patience", type=int, default=12)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.epochs < 1 or args.patience < 1:
        raise SystemExit("--epochs and --patience must be positive.")
    if not 0.5 <= args.train_fraction < 0.9:
        raise SystemExit("--train-fraction must be in [0.5, 0.9).")
    if not 0.05 <= args.val_fraction < 0.3:
        raise SystemExit("--val-fraction must be in [0.05, 0.3).")
    if args.train_fraction + args.val_fraction >= 1.0:
        raise SystemExit("train-fraction + val-fraction must be less than 1.")

    torch.set_num_threads(1)
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    data = np.load(args.dataset, allow_pickle=False)
    X, y = data["X"].astype(np.float32), data["y"].astype(np.float32)
    if X.ndim != 4 or y.ndim != 3:
        raise SystemExit(f"Expected X=[samples,time,nodes,features], y=[samples,nodes,1]; got {X.shape}, {y.shape}")
    n = len(X)
    train_end = int(n * args.train_fraction)
    val_end = int(n * (args.train_fraction + args.val_fraction))
    if train_end < 2 or val_end <= train_end or val_end >= n:
        raise SystemExit(f"Only {n} windows; need enough chronological samples for non-empty train/validation/test splits. "
                         "Collect a longer simulation or reduce window/horizon.")

    # Splits remain chronological. Validation/test targets are never used for fitting.
    X_train, y_train = X[:train_end], y[:train_end]
    X_val, y_val = X[train_end:val_end], y[train_end:val_end]
    X_test, y_test = X[val_end:], y[val_end:]
    mean = X_train.mean(axis=(0, 1, 2), keepdims=True).reshape(-1)
    std = X_train.std(axis=(0, 1, 2), keepdims=True).reshape(-1)
    std[std < 1e-6] = 1.0

    def scale(values):
        return (values - mean[None, None, None, :]) / std[None, None, None, :]

    X_train, X_val, X_test = scale(X_train), scale(X_val), scale(X_test)
    adjacency = normalize_adjacency(data["A"])
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    A_t = torch.tensor(adjacency, dtype=torch.float32, device=device)
    model = SpatialTemporalNet(features=X.shape[-1]).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    loss_fn = nn.MSELoss()
    xt = torch.tensor(X_train, dtype=torch.float32, device=device)
    yt = torch.tensor(y_train, dtype=torch.float32, device=device)
    xv = torch.tensor(X_val, dtype=torch.float32, device=device)
    yv = torch.tensor(y_val, dtype=torch.float32, device=device)
    best_val, best_state, stale = float("inf"), None, 0

    for epoch in range(1, args.epochs + 1):
        model.train()
        permutation = torch.randperm(len(xt), device=device)
        batch_losses = []
        for ids in permutation.split(8):
            optimizer.zero_grad()
            pred = model(xt[ids], A_t)
            loss = loss_fn(pred, yt[ids])
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 2.0)
            optimizer.step()
            batch_losses.append(float(loss.item()))
        model.eval()
        with torch.no_grad():
            val_loss = float(loss_fn(model(xv, A_t), yv).item())
        if val_loss < best_val:
            best_val = val_loss
            best_state = {key: value.detach().cpu().clone()
                          for key, value in model.state_dict().items()}
            stale = 0
        else:
            stale += 1
        if epoch == 1 or epoch % 5 == 0:
            print(f"epoch={epoch:03d} train_mse={np.mean(batch_losses):.4f} val_mse={val_loss:.4f}")
        if stale >= args.patience:
            print(f"Early stopping at epoch {epoch}.")
            break

    if best_state is None:
        raise SystemExit("Training failed to produce a valid checkpoint.")
    model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        pred_val = model(xv, A_t).cpu().numpy()
        pred_test = model(torch.tensor(X_test, dtype=torch.float32, device=device), A_t).cpu().numpy()

    # Persistence and moving-average baselines predict future queue from recent observed queues.
    raw_test = X[val_end:]
    target_test = y_test
    last_queue = raw_test[:, -1, :, 0:1]
    average_queue = raw_test[:, -min(3, raw_test.shape[1]):, :, 0:1].mean(axis=1)
    report = {
        "dataset": str(Path(args.dataset)),
        "samples": int(n), "train_samples": int(len(X_train)),
        "validation_samples": int(len(X_val)), "test_samples": int(len(X_test)),
        "split": "chronological", "window": int(data["window"]),
        "horizon": int(data["horizon"]), "features": [str(x) for x in data["feature_names"]],
        "best_validation_mse": float(best_val),
        "validation": {
            "stgnn": metrics(pred_val, y_val),
            "persistence": metrics(X[train_end:val_end, -1, :, 0:1], y_val),
            "moving_average_3": metrics(X[train_end:val_end, -min(3, X.shape[1]):, :, 0:1].mean(axis=1), y_val),
        },
        "test": {
            "stgnn": metrics(pred_test, target_test),
            "persistence": metrics(last_queue, target_test),
            "moving_average_3": metrics(average_queue, target_test),
        },
        "note": "Use forecast-pressure only if held-out test metrics justify the model versus simple baselines."
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        "state_dict": model.state_dict(),
        "node_ids": [str(x) for x in data["node_ids"].tolist()],
        "features": int(X.shape[-1]), "hidden": 32, "window": int(data["window"]),
        "horizon": int(data["horizon"]), "input_mean": mean.astype(np.float32),
        "input_std": std.astype(np.float32), "adjacency": adjacency,
        "architecture": "DistrictPulseSpatialTemporalNet-v2",
    }, out)
    report_path = out.with_suffix(".metrics.json")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Saved checkpoint: {out}")
    print(f"Saved metrics: {report_path}")


if __name__ == "__main__":
    main()
