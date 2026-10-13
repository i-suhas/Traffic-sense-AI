import argparse
from pathlib import Path
import numpy as np

try:
 import torch
 from torch import nn
except ImportError: raise SystemExit('Install PyTorch with: pip install torch')

class SpatialTemporalNet(nn.Module):
    """Lightweight graph aggregation followed by GRU; input [B,T,N,F], output [B,N,1]."""
    def __init__(self, features=1, hidden=32):
        super().__init__(); self.spatial=nn.Linear(features,hidden); self.gru=nn.GRU(hidden,hidden,batch_first=True); self.head=nn.Sequential(nn.Linear(hidden,hidden),nn.ReLU(),nn.Linear(hidden,1))
    def forward(self,x,A):
        # Aggregate each node's own features with normalized one-hop neighbors.
        h=torch.relu(self.spatial(x)); h=torch.einsum('ij,btjh->btih',A,h)
        b,t,n,hid=h.shape; z=h.permute(0,2,1,3).reshape(b*n,t,hid); out,_=self.gru(z); last=out[:,-1,:]
        return self.head(last).reshape(b,n,1)

def main():
 p=argparse.ArgumentParser(); p.add_argument('--dataset',required=True); p.add_argument('--epochs',type=int,default=40); p.add_argument('--lr',type=float,default=1e-3); p.add_argument('--out',default='models/stgnn.pt'); a=p.parse_args()
 d=np.load(a.dataset,allow_pickle=True); X=d['X']; y=d['y']; A=d['A']
 # Chronological split prevents random-window leakage.
 split=max(1,int(len(X)*0.8)); Xtr,Xv=X[:split],X[split:]; ytr,yv=y[:split],y[split:]
 xt=torch.tensor(Xtr,dtype=torch.float32); yt=torch.tensor(ytr,dtype=torch.float32); xv=torch.tensor(Xv,dtype=torch.float32); yv_t=torch.tensor(yv,dtype=torch.float32)
 A=A.astype(np.float32); A=A+np.eye(A.shape[0],dtype=np.float32); deg=A.sum(1); A=(A/np.maximum(deg[:,None],1)).astype(np.float32); At=torch.tensor(A,dtype=torch.float32)
 model=SpatialTemporalNet(X.shape[-1]); opt=torch.optim.Adam(model.parameters(),lr=a.lr); loss_fn=nn.MSELoss()
 for epoch in range(a.epochs):
  model.train(); opt.zero_grad(); pred=model(xt,At); loss=loss_fn(pred,yt); loss.backward(); opt.step()
  model.eval()
  with torch.no_grad(): val=float(loss_fn(model(xv,At),yv_t).item()) if len(xv) else float('nan')
  if (epoch+1)%5==0 or epoch==0: print(f'epoch={epoch+1:03d} train_mse={loss.item():.4f} validation_mse={val:.4f}')
 out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True); torch.save({'state_dict':model.state_dict(),'nodes':d['node_ids'].tolist(),'features':X.shape[-1],'architecture':'SpatialTemporalNet-v1'},out); print('Saved',out)
if __name__=='__main__': main()
