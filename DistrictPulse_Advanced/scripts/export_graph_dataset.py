"""Export chronologically ordered graph-temporal windows from states.csv."""
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pandas as pd

FEATURES = ["halting", "vehicles", "waiting", "mean_speed"]


def adjacency_from_network(network_path, node_ids):
    """Build a TLS adjacency matrix from connected incoming/outgoing network edges."""
    root = ET.parse(network_path).getroot()
    incoming, outgoing = {str(n): set() for n in node_ids}, {str(n): set() for n in node_ids}
    for connection in root.findall("connection"):
        tls = connection.get("tl")
        if tls not in incoming:
            continue
        from_edge, to_edge = connection.get("from"), connection.get("to")
        if from_edge:
            incoming[tls].add(from_edge)
        if to_edge:
            outgoing[tls].add(to_edge)
    matrix = np.zeros((len(node_ids), len(node_ids)), dtype=np.float32)
    for i, a in enumerate(node_ids):
        for j, b in enumerate(node_ids):
            if i != j and outgoing[str(a)].intersection(incoming[str(b)]):
                matrix[i, j] = 1.0
                matrix[j, i] = 1.0
    np.fill_diagonal(matrix, 1.0)
    return matrix


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--states", required=True)
    parser.add_argument("--out", default="data/graph_dataset.npz")
    graph = parser.add_mutually_exclusive_group(required=True)
    graph.add_argument("--adjacency", help="Square CSV adjacency matrix in sorted tls_id order.")
    graph.add_argument("--network", help="SUMO .net.xml; derive TLS adjacency from connected edges.")
    parser.add_argument("--window", type=int, default=12)
    parser.add_argument("--horizon", type=int, default=3,
                        help="Number of recorded time steps ahead to predict.")
    args = parser.parse_args()
    if args.window < 2 or args.horizon < 1:
        raise SystemExit("--window must be >=2 and --horizon must be >=1.")

    df = pd.read_csv(args.states)
    required = {"time", "tls_id", *FEATURES}
    missing = required.difference(df.columns)
    if missing:
        raise SystemExit(f"states.csv missing required columns: {sorted(missing)}")
    ids = sorted(df.tls_id.astype(str).unique())
    if args.network:
        adj = adjacency_from_network(args.network, ids)
    else:
        adj = pd.read_csv(args.adjacency, header=None).to_numpy(dtype=np.float32)
    if adj.shape != (len(ids), len(ids)):
        raise SystemExit(f"Adjacency must be {len(ids)}x{len(ids)} for sorted tls ids: {ids}")

    # Each timestamp becomes a [node, feature] matrix. Duplicate rows are aggregated.
    times = sorted(df.time.unique())
    per_feature = []
    for feature in FEATURES:
        pivot = (df.assign(tls_id=df.tls_id.astype(str))
                   .pivot_table(index="time", columns="tls_id", values=feature, aggfunc="mean")
                   .reindex(index=times, columns=ids).fillna(0.0))
        per_feature.append(pivot.to_numpy(dtype=np.float32))
    values = np.stack(per_feature, axis=-1)  # [time, node, feature]
    xs, ys, target_times = [], [], []
    last_start = len(values) - args.window - args.horizon
    for start in range(last_start + 1):
        target = start + args.window + args.horizon - 1
        xs.append(values[start:start + args.window])
        ys.append(values[target, :, 0:1])  # future halting count is the target
        target_times.append(times[target])
    if not xs:
        raise SystemExit("Not enough time steps for the requested window/horizon.")

    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output, X=np.asarray(xs, dtype=np.float32), y=np.asarray(ys, dtype=np.float32),
        A=adj, node_ids=np.asarray(ids, dtype=str), target_times=np.asarray(target_times),
        feature_names=np.asarray(FEATURES, dtype=str),
        window=np.int64(args.window), horizon=np.int64(args.horizon),
    )
    print(f"Saved {len(xs)} chronological windows; nodes={len(ids)}; features={FEATURES}; output={output}")


if __name__ == "__main__":
    main()
