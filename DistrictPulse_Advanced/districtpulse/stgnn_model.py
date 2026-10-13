"""Small graph-aggregation + GRU model for intersection-level queue forecasting."""
try:
    import torch
    from torch import nn
except ImportError as exc:
    raise ImportError("PyTorch is required for ST-GNN features. Install it with pip install torch.") from exc


class SpatialTemporalNet(nn.Module):
    """Input [batch, time, nodes, features], output [batch, nodes, predicted queue]."""
    def __init__(self, features=4, hidden=32):
        super().__init__()
        self.spatial = nn.Linear(features, hidden)
        self.gru = nn.GRU(hidden, hidden, batch_first=True)
        self.head = nn.Sequential(nn.Linear(hidden, hidden), nn.ReLU(), nn.Linear(hidden, 1))

    def forward(self, x, adjacency):
        h = torch.relu(self.spatial(x))
        h = torch.einsum("ij,btjh->btih", adjacency, h)
        batch, steps, nodes, hidden = h.shape
        z = h.permute(0, 2, 1, 3).reshape(batch * nodes, steps, hidden)
        z, _ = self.gru(z)
        return self.head(z[:, -1, :]).reshape(batch, nodes, 1)
