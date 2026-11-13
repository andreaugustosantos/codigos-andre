"""Medição de terras raras e mudanças de amostra nos EUA (Tabela 18, linhas 7 a 10)."""
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__))); from caminhos import *  # noqa
import importlib.util, pandas as pd, numpy as np, pyfixest as pf, pickle
spec=importlib.util.spec_from_file_location('e',EST_PY); E=importlib.util.module_from_spec(spec); spec.loader.exec_module(E)
tr=pd.read_pickle(R02 + '/amostra_validacao.pkl')
p=pd.read_pickle(R02 + '/painel_firma_trimestre.pkl')
det=tr[['RIC','qkey','Mineral_RareEarths','Mineral_RareEarths_detected']].copy()
det['terms']=det['Mineral_RareEarths_detected'].fillna('').astype(str)
GEN={'rare earth','rare earths','rareearth','rareearths'}; AMB={'gadolinium','lutetium','erbium','yttrium','scandium'}
def flag(s,rule):
    t={x.strip() for x in s.replace(';',',').split(',') if x.strip()}
    if rule=='noamb': return int(len(t-AMB)>0)
    if rule=='gen': return int(len(t&GEN)>0)
for r in ['noamb','gen']:
    det['RE_'+r]=[flag(s,r) for s in det.terms]
agg=det.groupby(['RIC','qkey'])[['RE_noamb','RE_gen']].max().reset_index()
p=p.merge(agg,on=['RIC','qkey'],how='left'); p[['RE_noamb','RE_gen']]=p[['RE_noamb','RE_gen']].fillna(0)
base=E.est_sample(p,'Q_CP','V2'); us=E.subset(base,'US')
full=E.est_sample(p,'Q_CP','V1'); first=full.groupby('RIC').qkey.min()
rows=[]
def run(d,var,lab):
    f=E.fit_q(d,var); sd=d[var].astype(float).std(ddof=0)
    r=dict(spec=lab,b=f.coef()['MR'],se=f.se()['MR'],p=f.pvalue()['MR'],N=f._N,quarters=int(d[var].sum()),firms=d.loc[d[var]>0,'RIC'].nunique(),per_mention=f.coef()['MR']/sd)
    rows.append(r); print(r)
run(us,'Mineral_RareEarths','Main')
run(us,'RE_noamb','Without gadolinium, lutetium, erbium, yttrium, scandium')
run(us,'RE_gen','(7) Generic terms only (rare earth, rare earths)')
inc=['BIIB.OQ','LLY.N','HLT.N','GEHC.OQ']
run(us[~us.RIC.isin(inc)],'Mineral_RareEarths','(8) Excluding Biogen, Eli Lilly, Hilton, and GE HealthCare')
run(us[us.RIC.isin(first.index[first<='20160331'])],'Mineral_RareEarths','(9) Firms with market data from 2016Q1')
run(us[us.qkey<='20250331'],'Mineral_RareEarths','(10) Sample ending in 2025Q1')
pickle.dump(pd.DataFrame(rows),open(f'{RES}/d4x.pkl','wb'))
