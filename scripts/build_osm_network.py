import argparse, subprocess
from pathlib import Path

def main():
    p=argparse.ArgumentParser(); p.add_argument('--osm', default='data/mysuru.osm.xml'); p.add_argument('--out', default='data/mysuru_pilot'); a=p.parse_args()
    osm=Path(a.osm); base=Path(a.out); base.parent.mkdir(parents=True,exist_ok=True)
    log=base.with_suffix('.netconvert.log')
    cmd=['netconvert','--osm-files',str(osm),'--output-file',str(base)+'.net.xml','--tls.guess','--junctions.join','--geometry.remove','--roundabouts.guess','--ramps.guess']
    print('+',' '.join(cmd))
    with log.open('w',encoding='utf-8') as f: subprocess.run(cmd,check=True,stdout=f,stderr=subprocess.STDOUT)
    print(f'Created {base}.net.xml; log: {log}')
if __name__=='__main__': main()
