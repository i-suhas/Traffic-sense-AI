"""Create sliding-window graph-temporal data from state logs.
Expected adjacency CSV: square matrix whose rows/columns follow sorted tls_id order.
"""
import argparse
from pathlib import Path
import numpy as np, pandas as pd

def main():
    p=argparse.ArgumentParser(); p.add_argument('--states',required=True); p.add_argument('--out',default='data/graph_dataset.npz'); p.add_argument('--adjacency',required=True); p.add_argument('--window',type=int,default=12); p.add_argument('--horizon',type=int,default=3); a=p.parse_args()
    df=pd.read_csv(a.states); ids=sorted(df.tls_id.unique()); adj=pd.read_csv(a.adjacency,header=None).to_numpy(dtype=np.float32)
    if adj.shape!=(len(ids),len(ids)): raise SystemExit(f'Adjacency must be {len(ids)}x{len(ids)} for tls ids: {ids}')
    # Aggregate by simulation second and tls id; use queue pressure as a simple target.
    pivot=df.pivot_table(index='time',columns='tls_id',values='halting',aggfunc='mean').reindex(columns=ids).fillna(0).sort_index()
    values=pivot.to_numpy(dtype=np.float32); xs=[]; ys=[]
    for i in range(0,len(values)-a.window-a.horizon+1):
        xs.append(values[i:i+a.window,:,None]); ys.append(values[i+a.window+a.horizon-1,:,None])
    if not xs: raise SystemExit('Not enough time steps for requested window/horizon.')
    out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True); np.savez_compressed(out,X=np.asarray(xs),y=np.asarray(ys),A=adj,node_ids=np.asarray(ids),window=a.window,horizon=a.horizon)
    print(f'Saved {len(xs)} windows; nodes={len(ids)}; output={out}')
if __name__=='__main__': main()
