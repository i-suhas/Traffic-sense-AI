"""Inference wrapper for a validated DistrictPulse ST-GNN checkpoint."""
from pathlib import Path
import numpy as np


class STGNNPredictor:
    def __init__(self, checkpoint_path):
        try:
            import torch
            from districtpulse.stgnn_model import SpatialTemporalNet
        except ImportError as exc:
            raise RuntimeError("Install PyTorch to use --controller forecast-pressure.") from exc
        self.torch = torch
        checkpoint = torch.load(Path(checkpoint_path), map_location="cpu", weights_only=False)
        self.node_ids = [str(x) for x in checkpoint["node_ids"]]
        self.window = int(checkpoint["window"])
        self.mean = np.asarray(checkpoint["input_mean"], dtype=np.float32)
        self.std = np.asarray(checkpoint["input_std"], dtype=np.float32)
        self.adjacency = torch.tensor(checkpoint["adjacency"], dtype=torch.float32)
        self.model = SpatialTemporalNet(features=int(checkpoint["features"]),
                                        hidden=int(checkpoint.get("hidden", 32)))
        self.model.load_state_dict(checkpoint["state_dict"])
        self.model.eval()

    def predict(self, history_by_node):
        """Predict next queue for nodes with a complete chronological feature window."""
        if any(node not in history_by_node or len(history_by_node[node]) < self.window
               for node in self.node_ids):
            return None
        values = np.asarray([
            list(history_by_node[node])[-self.window:] for node in self.node_ids
        ], dtype=np.float32)  # [N,T,F]
        values = np.transpose(values, (1, 0, 2))[None, ...]  # [1,T,N,F]
        values = (values - self.mean[None, None, None, :]) / self.std[None, None, None, :]
        with self.torch.no_grad():
            x = self.torch.tensor(values, dtype=self.torch.float32)
            pred = self.model(x, self.adjacency).cpu().numpy()[0, :, 0]
        return {node: max(0.0, float(value))
                for node, value in zip(self.node_ids, pred)}
