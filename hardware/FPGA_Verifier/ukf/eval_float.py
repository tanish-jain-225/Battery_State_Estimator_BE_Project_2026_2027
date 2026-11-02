import sys, os, json
from collections import OrderedDict
import numpy as np
H=os.path.dirname(os.path.abspath(__file__))
sys.path[:0]=[H, os.path.join(H,"../ekf"), os.path.join(H,"../repo_fixed/hardware/FPGA_Verifier")]
from real_nasa_dataset import generate_nasa_battery_dataset
from real_ekf_baseline import fit_ekf_baseline, run_ekf_on_cycle
from ukf_float import run_ukf_on_cycle
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
m=lambda y,p: dict(mae=round(float(mean_absolute_error(y,p)),4), rmse=round(float(np.sqrt(mean_squared_error(y,p))),4), r2=round(float(r2_score(y,p)),4))
rows,meta=generate_nasa_battery_dataset(); cyc=OrderedDict()
for r in rows: cyc.setdefault((r["battery"],r["cycle"]),[]).append(r)
Y,E,U={},{},{}
for tc in ["B0005","B0006","B0007","B0018"]:
    p=fit_ekf_baseline([r for r in rows if r["battery"]!=tc]); cap=meta[tc]["cap_nominal"]
    ks=[k for k in cyc if k[0]==tc]
    Y[tc]=[r["soc_true"] for k in ks for r in cyc[k]]
    E[tc]=np.concatenate([run_ekf_on_cycle(cyc[k],p,capacity_ah=cap) for k in ks])
    U[tc]=np.concatenate([run_ukf_on_cycle(cyc[k],p,capacity_ah=cap) for k in ks])
    print(tc,"EKF",m(Y[tc],E[tc]),"UKF",m(Y[tc],U[tc]))
ya=sum(Y.values(),[]); print("pooled EKF",m(ya,np.concatenate(list(E.values()))),"UKF",m(ya,np.concatenate(list(U.values()))))
