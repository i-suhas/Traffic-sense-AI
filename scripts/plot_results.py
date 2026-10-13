import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

def main():
 p=argparse.ArgumentParser(); p.add_argument('--csv',default='results/comparison.csv'); p.add_argument('--out',default='results/controller_comparison.png'); a=p.parse_args()
 df=pd.read_csv(a.csv); metrics=[m for m in ['mean_trip_time_loss_s','mean_trip_duration_s','mean_trip_waiting_s','mean_halting_vehicles'] if m in df.columns]
 if not metrics: raise SystemExit('No recognized metrics in CSV')
 fig,axes=plt.subplots(1,len(metrics),figsize=(5*len(metrics),4));
 if len(metrics)==1: axes=[axes]
 for ax,m in zip(axes,metrics): df.boxplot(column=m,by='controller',ax=ax); ax.set_title(m.replace('_',' ')); ax.set_xlabel('controller')
 fig.suptitle('DistrictPulse matched-seed controller comparison'); fig.tight_layout(); out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True); fig.savefig(out,dpi=160); print('Saved',out)
if __name__=='__main__': main()
