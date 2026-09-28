"""VAL-04 — minimum headway on the real corridor: fixed block on OSRD's generated signals (CV-4) and moving block
(TC-TC-07), both from golsim running profiles on the OSRD-validated corridor.

Fixed block follows OSRD's BAL spacing rule (SpacingResourceGenerator): a detection zone is required from the time
the head reaches the sighting point (400 m, from the RailJSON) of the signal that would show the warning aspect,
i.e. the signal before the block's entry signal, until the tail clears the zone. Minimum headway between identical
trains = longest zone occupation. The train path is rebuilt on the RailJSON track graph from the stop anchors in
the OSRD export (each leg checked against OSRD distances).

Usage: python scripts/val04_headway_real_signals.py   (inputs: OSRD S2 export and lakeshore_topology.json)
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src')); sys.path.insert(0, str(ROOT / 'scripts'))
EXPORT = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / 'data' / 'osrd' / 'osrd_S2_export.csv')
TOPO = sys.argv[2] if len(sys.argv) > 2 else str(ROOT / 'data' / 'osrd' / 'lakeshore_topology.json')
import val03_cross_validation as v
from golsim import railjson_path as rp
topo=rp.load_topology(TOPO)
class G(rp.TrackGraph):
    def __init__(self,t): super().__init__(t); self.op_parts['UNION-7']=('23621505-0',177.0,'Toronto Union Station')
rp.TrackGraph=G
df=v.read_osrd_export(EXPORT); st=v.extract_stops(df)
anchors=[]
for _,s in st.iterrows():
    rows=df[(df.pos_m.round(0)==round(s.pos_m)) & df.op.notna()]
    tn=['UNION-7'] if 'Union' in s['name'] else [x for x in rows.trackName.dropna() if len(x)>20]
    if tn: anchors.append((tn[0], s.pos_m))
segs,checks,err=rp.rebuild_path(topo,anchors)
for c in checks:
    if abs(c[3]-c[2])>2: print('LEG',c)
print('total abs err', round(err,1), 'segments', len(segs))

import numpy as np
from golsim import load_trains, run_time
from golsim.config import CONFIG
from golsim.dynamics import Corridor, buffer_stop_approach_limits
sig=rp.project(segs, topo['signals'], directional=True)
det=rp.project(segs, topo['detectors'], directional=False)
end=segs[-1].path_begin+segs[-1].length
print('path', round(end), 'm; facing signals', len(sig), '; detectors', len(det))
sp=np.array([p for p,_ in sig]); print('block length median', np.median(np.diff(sp)).round(0), 'max', np.diff(sp).max().round(0))
# train timeline on OSRD corridor (S2 proxy: EMU + BAL driver rules), up to Whitby
segl=v.speed_limit_segments(df); L=float(df.pos_m.iloc[-1])
stations=[{"name":s['name'],"position_m":float(s.pos_m),"dwell_s":60 if 0<i<len(st)-1 else 0} for i,(_,s) in enumerate(st.iterrows())]
stations[-1]['position_m']=L
tr=load_trains(CONFIG/'rolling_stock.yaml')['S2_bilevel_emu']
res=run_time(tr,Corridor(stations,segl+buffer_stop_approach_limits(L),[[0,L,0]]),ds=1.0,driver_margins_m=(100,50))
stop_pos=np.array([s['position_m'] for s in stations]); dw=np.array([s['dwell_s'] for s in stations])
def T(x):  # time head first reaches x
    x=min(max(x,0),L); i=int(round(x)); return res.t[i]+dw[stop_pos< x-0.5].sum()
def Tdep(x):
    x=min(max(x,0),L); i=int(round(x)); return res.t[i]+dw[stop_pos<=x+0.5].sum()
bounds=[0.0]+[p for p,_ in det if 0<p<end]+[end]
worst=[]
for a,b in zip(bounds[:-1],bounds[1:]):
    if b-a<1: continue
    k=np.searchsorted(sp, a+0.5)-1          # entry signal of the block containing the zone
    prev=sp[k-1] if k>=1 else 0.0           # signal that would show the warning aspect
    start=T(prev-400.0)
    finish=Tdep(min(b+tr.length_m, end))
    worst.append((finish-start,a,b,prev))
worst.sort(reverse=True)
names=[(s['position_m'],s['name']) for s in stations]
def near(x): return min(names,key=lambda n:abs(n[0]-x))[1]
print('Minimum headway (blocking time, BAL, real signals):', round(worst[0][0]),'s =',round(worst[0][0]/60,1),'min')
for h,a,b,prev in worst[:6]:
    print(f"  zone {a/1000:7.2f}-{b/1000:7.2f} km (near {near(a)}), warning signal at {prev/1000:.2f} km: {h:5.0f} s")

from golsim.braking import permitted_distance
from golsim.config import load_signalling
_,MB=load_signalling()
# Moving block: follower head at x (speed v) needs the leader's tail beyond x + d_P(v) + margin + U_pos + v*staleness.
H=[]
for x in range(0,int(end)-1,10):
    v_=res.v[x]
    need=x+permitted_distance(tr,v_)+MB.safety_margin_m+MB.position_uncertainty_m+v_*MB.reaction_time_s+tr.length_m
    H.append((Tdep(min(need,end))-T(x)+MB.system_processing_s, x))
H.sort(reverse=True)
print('Moving block minimum headway:', round(H[0][0]),'s at', round(H[0][1]/1000,2),'km (near',near(H[0][1]),')')

def fixed_headway(signal_positions, zone_bounds):
    spp=np.array(sorted(signal_positions)); out=[]
    for a,b in zip(zone_bounds[:-1],zone_bounds[1:]):
        if b-a<1: continue
        k=np.searchsorted(spp,a+0.5)-1; prev=spp[k-1] if k>=1 else 0.0
        out.append((Tdep(min(b+tr.length_m,end))-T(prev-400.0),a))
    return max(out)
print('\nSensitivity: uniform block length instead of generated signals')
for blk in (3000,2000,1500,1000):
    pos=list(np.arange(0,end,blk)); h,a=fixed_headway(pos,pos+[end])
    print(f"  {blk:5d} m blocks: H_fixed {h:5.0f} s (near {near(a)}) -> reduction vs moving block {100*(h-H[0][0])/h:4.0f} %")
