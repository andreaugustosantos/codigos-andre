"""Q de Tobin k trimestres antes e depois da menção (Tabela 18, Painel E) e firmas que divulgam em 3 de cada 4 trimestres (Tabela 17, Painel F)."""
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__))); from caminhos import *  # noqa
import importlib.util, sys, warnings, pickle
import numpy as np, pandas as pd, pyfixest as pf
warnings.filterwarnings('ignore')
W=ROOT
spec=importlib.util.spec_from_file_location('e',EST_PY); E=importlib.util.module_from_spec(spec); spec.loader.exec_module(E)
sys.path.insert(0,CODE); import ddd_core as D
TEL='Telecommunications Services'
p=pd.read_pickle(f'{R02}/painel_firma_trimestre.pkl'); p['t']=D.qindex(p['qkey'])
base=E.est_sample(p,'Q_CP','V2'); full=E.est_sample(p,'Q_CP','V1')
R={}
import os
if os.environ.get('SKIP_LAGS'):
    pass
# ---- Q em t+k sobre a menção em t
rows=[]
for var,pn in [('Mineral_RareEarths','US'),('Composite','US'),('Composite','Total'),('Mineral_Copper','US')]:
    b=E.subset(base,pn); b=b[b['TRBC Industry Group Name']!=TEL] if var=='Composite' else b
    fq=E.subset(full,pn)[['RIC','t','qkey','Q','Size','Leverage','ROA']]
    for k in [-3,-2,-1,0,1,2,3]:
        x=b[['RIC','t',var]].copy(); x['t']=x['t']+k
        dd=x.merge(fq,on=['RIC','t'])
        dd['MR']=E.zscore(dd[var].astype(float)); sd=dd[var].astype(float).std(ddof=0)
        f=pf.feols('Q ~ MR + Size + Leverage + ROA | RIC + qkey',data=dd,vcov={'CRV1':'RIC'})
        rows.append(dict(var=var,panel=pn,k=k,b=f.coef()['MR'],se=f.se()['MR'],p=f.pvalue()['MR'],per_mention=f.coef()['MR']/sd,N=f._N))
R['lags']=pd.DataFrame(rows); print(R['lags'].round(4).to_string())
# ---- firmas de divulgação trimestral
fr=full.groupby('RIC').agg(nq=('t','size')); calls=base.groupby('RIC').size().rename('ncall')
fr=fr.join(calls).fillna(0); fr['share']=fr.ncall/fr.nq
qrt=set(fr.index[fr.share>=0.75])
reg=base.drop_duplicates('RIC').set_index('RIC')['Region_HQ']
info=pd.DataFrame({'share':fr.share,'reg':reg.reindex(fr.index)})
R['share_by_region']=info.groupby('reg').share.agg(['mean',lambda s:(s>=0.75).mean(),'size'])
print(R['share_by_region'])
rows=[]
for var in E.MINERALS+['Composite']:
    for pn in E.PANELS:
        b=E.subset(base,pn); b=b[b.RIC.isin(qrt)]
        if var=='Composite': b=b[b['TRBC Industry Group Name']!=TEL]
        b=b.copy(); b['MR']=E.zscore(b[var].astype(float))
        if b.RIC.nunique()<20 or b['MR'].isna().all():
            continue
        try:
            f=pf.feols('Q ~ MR + Size + Leverage + ROA | RIC + qkey',data=b,vcov={'CRV1':'RIC'})
        except BaseException as ex:
            print('skip',var,pn,ex); continue
        rows.append(dict(var=var,panel=pn,b=f.coef()['MR'],se=f.se()['MR'],p=f.pvalue()['MR'],N=f._N,firms=b.RIC.nunique()))
R['quarterly']=pd.DataFrame(rows); print(R['quarterly'].round(4).to_string())
pickle.dump(R,open(f'{RES}/tempo_q.pkl','wb'))
