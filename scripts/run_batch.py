import argparse, subprocess, sys
from pathlib import Path

def main():
    p=argparse.ArgumentParser(); p.add_argument('--scenario',default='data/demo'); p.add_argument('--controllers',nargs='+',default=['fixed','density','smdp']); p.add_argument('--seeds',nargs='+',type=int,default=[11,22,33]); p.add_argument('--end',type=int,default=None); a=p.parse_args()
    root=Path(__file__).resolve().parents[1]
    for seed in a.seeds:
        for controller in a.controllers:
            cmd=[sys.executable,str(root/'scripts'/'run_experiment.py'),'--scenario',a.scenario,'--controller',controller,'--seed',str(seed)]
            if a.end: cmd += ['--end',str(a.end)]
            subprocess.run(cmd,check=True)
if __name__=='__main__': main()
