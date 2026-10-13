import argparse, os, subprocess, sys
from pathlib import Path

def main():
    p=argparse.ArgumentParser(); p.add_argument('--net',required=True); p.add_argument('--out',required=True); p.add_argument('--period',type=float,default=3.0); p.add_argument('--end',type=int,default=1800); p.add_argument('--seed',type=int,default=42); a=p.parse_args()
    home=os.environ.get('SUMO_HOME')
    if not home: raise SystemExit('Set SUMO_HOME first.')
    out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True)
    trips=Path(str(out)+'.trips.xml'); routes=Path(str(out)+'.rou.xml')
    tool=Path(home)/'tools'/'randomTrips.py'
    subprocess.run([sys.executable,str(tool),'-n',a.net,'-o',str(trips),'--seed',str(a.seed),'--period',str(a.period),'--end',str(a.end),'--binomial','3','--validate'],check=True)
    subprocess.run(['duarouter','-n',a.net,'-t',trips,'-o',routes,'--ignore-errors','--seed',str(a.seed)],check=True)
    cfg=Path(str(out)+'.sumocfg')
    cfg.write_text(f'<configuration><input><net-file value="{Path(a.net).name}"/><route-files value="{routes.name}"/></input><time><begin value="0"/><end value="{a.end}"/><step-length value="1"/></time><processing><time-to-teleport value="-1"/></processing></configuration>',encoding='utf-8')
    print(f'Generated synthetic demand {routes}; this is not observed Mysuru traffic data.')
if __name__=='__main__': main()
