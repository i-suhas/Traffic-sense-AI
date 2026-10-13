import argparse, urllib.parse, urllib.request
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description='Download a small OSM extract through Overpass API')
    p.add_argument('--bbox', default='76.625,12.285,76.685,12.335', help='west,south,east,north')
    p.add_argument('--out', default='data/mysuru.osm.xml'); a=p.parse_args()
    west,south,east,north=map(float,a.bbox.split(','))
    query=f'[out:xml][timeout:90];(way["highway"]({south},{west},{north},{east});>;);out body;'
    url='https://overpass-api.de/api/interpreter?'+urllib.parse.urlencode({'data':query})
    req=urllib.request.Request(url, headers={'User-Agent':'DistrictPulseResearchMVP/1.0 (educational research)'})
    print('Downloading OSM extract; large areas may be rate-limited...')
    with urllib.request.urlopen(req, timeout=120) as r: data=r.read()
    out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True); out.write_bytes(data)
    print(f'Wrote {len(data):,} bytes to {out}. Validate the area and OSM terms before publishing.')
if __name__=='__main__': main()
