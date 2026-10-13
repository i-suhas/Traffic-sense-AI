import argparse, os, subprocess, sys
from pathlib import Path

def run(cmd, env=None):
    print('+', ' '.join(map(str, cmd)))
    subprocess.run(list(map(str, cmd)), check=True, env=env)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--seed', type=int, default=42); p.add_argument('--end', type=int, default=1800); p.add_argument('--out', default='data/demo'); a=p.parse_args()
    out=Path(a.out); out.mkdir(parents=True, exist_ok=True)
    net=out/'demo.net.xml'; rou=out/'demo.rou.xml'; cfg=out/'demo.sumocfg'
    run(['netgenerate','--grid','--grid.number','3','--grid.length','250','--grid.attach-length','100','--tls.guess','--tls.guess.threshold','1','--default.speed','13.89','--output-file',net])
    sumo_home=os.environ.get('SUMO_HOME')
    if not sumo_home: raise SystemExit('Set SUMO_HOME to your SUMO installation directory first.')
    trips_tool=Path(sumo_home)/'tools'/'randomTrips.py'
    if not trips_tool.exists(): raise SystemExit(f'Cannot find {trips_tool}. Correct SUMO_HOME.')
    run([sys.executable, trips_tool, '-n', net, '-r', rou, '--seed', a.seed, '--period', '2.0', '--end', a.end, '--binomial', '4', '--validate'])
    cfg.write_text(f"""<configuration>\n <input><net-file value=\"{net.name}\"/><route-files value=\"{rou.name}\"/></input>\n <time><begin value=\"0\"/><end value=\"{a.end}\"/><step-length value=\"1\"/></time>\n <processing><time-to-teleport value=\"-1\"/></processing>\n</configuration>\n""", encoding='utf-8')
    print(f'Demo scenario created at {out.resolve()}')
if __name__=='__main__': main()
