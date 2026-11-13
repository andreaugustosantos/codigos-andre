"""
Diferença em diferenças em torno dos controles chineses de exportação de terras raras (4 de abril de 2025), Tabela 9 e Figura 9.

Expostas: indústrias que usam ímãs de terras raras segundo a IEA (carros, turbinas eólicas, motores industriais e defesa),
ou seja, os grupos TRBC Automobiles & Auto Parts, Renewable Energy, Machinery, Tools, Heavy Vehicles, Trains & Ships
e Aerospace & Defense. A versão ampla soma eletrônicos, semicondutores, computadores, eletrodomésticos e redes.
A versão por texto usa as firmas que mencionaram terras raras até 2025T1.
Parte A: as menções respondem ao choque? Parte B: o Q de Tobin responde?
"""
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__))); from caminhos import *  # noqa
import importlib.util, sys, warnings, pickle
import numpy as np, pandas as pd, pyfixest as pf
from scipy import stats
warnings.filterwarnings('ignore')
W = ROOT
spec = importlib.util.spec_from_file_location('e', EST_PY); E = importlib.util.module_from_spec(spec); spec.loader.exec_module(E)
sys.path.insert(0, CODE); import ddd_core as D
sys.path.insert(0, CODE); import wcr
SEED = 20261024
NARROW = ['Automobiles & Auto Parts', 'Aerospace & Defense', 'Machinery, Tools, Heavy Vehicles, Trains & Ships', 'Renewable Energy']
WIDE = NARROW + ['Electronic Equipment & Parts', 'Computers, Phones & Household Electronics',
                 'Semiconductors & Semiconductor Equipment', 'Household Goods', 'Communications & Networking']
PRODUCERS = ['Metals & Mining', 'Uranium', 'Chemicals']
POST, START, REF = '20250630', '20230331', '20250331'
p = pd.read_pickle(f'{R02}/painel_firma_trimestre.pkl')
calls = E.est_sample(p, 'Q_CP', 'V2'); full = E.est_sample(p, 'Q_CP', 'V1'); fullS = E.est_sample(p, 'Q_S', 'V1')
IG = 'TRBC Industry Group Name'
re_pre = set(calls.loc[(calls.qkey < '20250401') & (calls.Mineral_RareEarths == 1), 'RIC'])
R = {}

def prep(d, treat='narrow', start=START):
    d = d[d.qkey >= start].copy() if start else d.copy()
    if treat == 'narrow': d['T'] = d[IG].isin(NARROW).astype(int)
    elif treat == 'wide': d['T'] = d[IG].isin(WIDE).astype(int)
    elif treat == 'text': d['T'] = d.RIC.isin(re_pre).astype(int)
    d['Post'] = (d.qkey >= POST).astype(int); d['TxPost'] = d['T'] * d['Post']
    d['IGc'] = d[IG]; d['region'] = d['Region_HQ']
    return d

def est(d, y, fe='RIC + qkey', ctl='', vcov=None):
    m = pf.feols(f'{y} ~ TxPost{ctl} | {fe}', data=d, vcov=vcov or {'CRV1': 'RIC'})
    return dict(b=m.coef()['TxPost'], se=m.se()['TxPost'], p=m.pvalue()['TxPost'], N=m._N,
                treated=int(d.loc[d['T'] == 1, 'RIC'].nunique()), firms=int(d.RIC.nunique()))

def event(d, y, ctl=''):
    d = d.copy(); qs = sorted(d.qkey.unique()); terms = []
    for q in qs:
        if q == REF: continue
        c = f'E_{q}'; d[c] = d['T'] * (d.qkey == q).astype(int); terms.append(c)
    m = pf.feols(f'{y} ~ ' + ' + '.join(terms) + f'{ctl} | RIC + qkey', data=d, vcov={'CRV1': 'RIC'})
    es = pd.DataFrame({'q': [t[2:] for t in terms], 'b': [m.coef()[t] for t in terms], 'se': [m.se()[t] for t in terms],
                       'p': [m.pvalue()[t] for t in terms]})
    nm = list(m.coef().index); V = m._vcov
    def joint(qset):
        idx = [nm.index(f'E_{q}') for q in qset]; bb = m.coef().values[idx]; VV = V[np.ix_(idx, idx)]
        ch = float(bb @ np.linalg.solve(VV, bb)); return dict(chi2=ch, df=len(idx), p=stats.chi2.sf(ch, len(idx)))
    pre = [q for q in es.q if q < REF]; post = [q for q in es.q if q >= POST]
    return es, dict(pre=joint(pre), post=joint(post))

def ri_industry(d, y, n=999):
    """Randomização por grupo industrial: sorteia conjuntos de grupos do mesmo tamanho do grupo exposto."""
    rng = np.random.default_rng(SEED); groups = sorted(d[IG].unique()); k = d.loc[d['T'] == 1, IG].nunique()
    b0 = est(d, y)['b']; draws = []
    for _ in range(n):
        g = set(rng.choice(groups, size=k, replace=False))
        x = d.copy(); x['T'] = x[IG].isin(g).astype(int); x['TxPost'] = x['T'] * x['Post']
        draws.append(pf.feols(f'{y} ~ TxPost | RIC + qkey', data=x, vcov='iid').coef()['TxPost'])
    draws = np.array(draws)
    return dict(b=b0, p_ri=(1 + (np.abs(draws) >= abs(b0)).sum()) / (1 + n), k=k, n_groups=len(groups))

def wild_industry(d, y):
    dd = d.copy()
    while True:
        n0 = len(dd)
        for c in ('RIC', 'qkey'): dd = dd[dd.groupby(c)[c].transform('size') > 1]
        if len(dd) == n0: break
    fid = pd.factorize(dd.RIC)[0]; qid = pd.factorize(dd.qkey)[0]; cid = pd.factorize(dd[IG])[0]
    pre = wcr.prepare(dd[y].values.astype(float), dd.TxPost.values.astype(float), None, fid, qid, cluster=cid)
    return dict(p_wild_ind=wcr.pvalue(pre, wcr.weights(pre['G'], 9999, np.random.default_rng(SEED), kind='webb')), G=pre['G'])

#  Parte A: menções (trimestres com call)
rows = []
for var in E.MINERALS:
    d = prep(calls); r = est(d, var); rows.append(dict(part='A', spec='Main (narrow)', var=var, **r))
dA = prep(calls)
rA = est(dA, 'Mineral_RareEarths', vcov={'CRV1': 'IGc'}); rows.append(dict(part='A', spec='Cluster industry group', var='Mineral_RareEarths', **rA))
rows.append(dict(part='A', spec='Wide', var='Mineral_RareEarths', **est(prep(calls, 'wide'), 'Mineral_RareEarths')))
rows.append(dict(part='A', spec='Region x quarter FE', var='Mineral_RareEarths', **est(dA, 'Mineral_RareEarths', fe='RIC + region^qkey')))
rows.append(dict(part='A', spec='US only', var='Mineral_RareEarths', **est(dA[dA.region == 'US'], 'Mineral_RareEarths')))
rows.append(dict(part='A', spec='Full period 2016-2026', var='Mineral_RareEarths', **est(prep(calls, start=None), 'Mineral_RareEarths')))
R['A'] = pd.DataFrame(rows); print(R['A'].round(4).to_string(), flush=True)
R['A_es'], R['A_joint'] = event(dA, 'Mineral_RareEarths'); print(R['A_es'].round(4).to_string(), R['A_joint'], flush=True)
R['A_ri'] = ri_industry(dA, 'Mineral_RareEarths', n=499); print('A RI', R['A_ri'], flush=True)
R['A_wild'] = wild_industry(dA, 'Mineral_RareEarths'); print('A wild', R['A_wild'], flush=True)
R['A_means'] = dA.groupby(['T', 'Post']).Mineral_RareEarths.mean()

#  Parte B: Q de Tobin (painel completo)
rows = []
dB = prep(full)
def add(spec, d, **kw): rows.append(dict(part='B', spec=spec, **est(d, 'Q', **kw)))
add('Main (narrow)', dB)
add('Cluster industry group', dB, vcov={'CRV1': 'IGc'})
add('Region x quarter FE', dB, fe='RIC + region^qkey')
add('With controls', dB, ctl=' + Size + Leverage + ROA')
add('Wide', prep(full, 'wide'))
add('Text: rare-earth mention to 2025Q1', prep(full, 'text'))
add('US only', dB[dB.region == 'US'])
add('Producers excluded from controls', dB[~dB[IG].isin(PRODUCERS)])
add('Simplified Q', prep(fullS))
add('Full period 2016-2026', prep(full, start=None))
add('Quarters with a call only', prep(calls))
R['B'] = pd.DataFrame(rows); print(R['B'].round(4).to_string(), flush=True)
R['B_es'], R['B_joint'] = event(dB, 'Q'); print(R['B_es'].round(4).to_string(), R['B_joint'], flush=True)
R['B_ri'] = ri_industry(dB, 'Q', n=499); print('B RI', R['B_ri'], flush=True)
R['B_wild'] = wild_industry(dB, 'Q'); print('B wild', R['B_wild'], flush=True)
R['B_meanQ'] = dB.loc[(dB['T'] == 1) & (dB.Post == 0), 'Q'].mean()
R['counts'] = dict(narrow=int(dB.loc[dB['T'] == 1, 'RIC'].nunique()), firms=int(dB.RIC.nunique()),
                   by_group=dB[dB['T'] == 1].drop_duplicates('RIC')[IG].value_counts().to_dict(),
                   by_region=dB[dB['T'] == 1].drop_duplicates('RIC').region.value_counts().to_dict(),
                   text_treated=len(re_pre))
print(R['counts'])
pickle.dump(R, open(f'{RES}/china.pkl', 'wb'))
