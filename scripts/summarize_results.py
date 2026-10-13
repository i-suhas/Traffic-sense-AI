import argparse, json
from pathlib import Path
import pandas as pd

def main():
    p=argparse.ArgumentParser(); p.add_argument('--results',default='results'); p.add_argument('--out',default='results/comparison.csv'); a=p.parse_args()
    rows=[]
    for path in Path(a.results).glob('*/metrics.json'):
        try:
            m=json.loads(path.read_text(encoding='utf-8')); manifest_path=path.parent/'manifest.json'; manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
            rows.append({'run':path.parent.name,'controller':manifest.get('controller','unknown'),'seed':manifest.get('seed'),**{k:v for k,v in m.items() if k!='run_dir'}})
        except Exception as e: print('Skipping',path,e)
    if not rows: raise SystemExit('No metrics.json files found. Run experiments first.')
    df=pd.DataFrame(rows); out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True); df.to_csv(out,index=False); print(df.to_string(index=False)); print('\nSaved',out)
    numeric=[c for c in ['mean_trip_duration_s','mean_trip_waiting_s','mean_trip_time_loss_s','mean_halting_vehicles'] if c in df.columns]
    if 'controller' in df.columns and numeric:
        print('\nMean by controller:'); print(df.groupby('controller')[numeric].mean(numeric_only=True).round(3).to_string())
if __name__=='__main__': main()
