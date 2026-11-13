"""
Equação (6): Q de Tobin sobre a exposição a cada mineral, nos seis painéis.

Gera os números das Tabelas 6 (principal), 7 (produtoras) e 17 (Painéis A a E), além do wild bootstrap,
do Romano-Wolf e da randomização usados no texto. O composto exclui as firmas de telecomunicações.
Saída: resultados_valuation.xlsx
"""
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__))); from caminhos import *  # noqa
import importlib.util, sys, os, glob, warnings, pickle
import numpy as np, pandas as pd, pyfixest as pf
warnings.filterwarnings('ignore')
W = ROOT
spec = importlib.util.spec_from_file_location('e', EST_PY); E = importlib.util.module_from_spec(spec); spec.loader.exec_module(E)
sys.path.insert(0, CODE); import ddd_core as D
sys.path.insert(0, CODE); import wcr
SEED = 20261024
TEL = 'Telecommunications Services'
PROD = ['Metals & Mining', 'Uranium']

p = pd.read_pickle(f'{R02}/painel_firma_trimestre.pkl')
tr = pd.read_pickle(f'{R02}/amostra_validacao.pkl')
cot = tr.groupby(['RIC', 'qkey'])['Placebo_Negative'].max().rename('Cotton').reset_index()
p = p.merge(cot, on=['RIC', 'qkey'], how='left'); p['Cotton'] = p['Cotton'].fillna(0).astype(int)
# o ativo total já vem no painel do 02_estimacao.py (coluna TA)
p['t'] = D.qindex(p['qkey'])

MIN = E.MINERALS; LAB = E.LABEL; PAN = E.PANELS
R = {}

def cell(f, name='MR'):
    return dict(beta=f.coef()[name], se=f.se()[name], p=f.pvalue()[name], N=f._N)

def fit(d, var, fe='RIC + qkey', ctl=' + Size + Leverage + ROA'):
    d = d.copy(); d['MR'] = E.zscore(d[var].astype(float))
    return pf.feols(f"Q ~ MR{ctl} | {fe}", data=d, vcov={'CRV1': 'RIC'}), d

def sample(b, var):
    return b[b['TRBC Industry Group Name'] != TEL] if var == 'Composite' else b

def nvar(d, var):
    g = d.groupby('RIC')[var].agg(['min', 'max']); return int((g['max'] > g['min']).sum())

base = E.est_sample(p, 'Q_CP', 'V2')

# ---------------- Tabela 6: minerais, composto sem telecom e placebo (algodão)
rows = []
for var in MIN + ['Composite', 'Cotton']:
    for pn in PAN:
        d = sample(E.subset(base, pn), var); f, dd = fit(d, var)
        sd = dd[var].astype(float).std(ddof=0)
        rows.append(dict(Var=var, Painel=pn, **cell(f), firms=dd['RIC'].nunique(), por_mencao=f.coef()['MR'] / sd,
                         firmas_variacao=nvar(dd, var)))
R['T6'] = pd.DataFrame(rows)
print(R['T6'].round(4).to_string(), flush=True)

# ---------------- Tabela 17, Painéis A a D: terras raras e composto
specs = {'A': ('Q_CP', 'V1', 'Size'), 'B': ('Q_S', 'V2', 'Size'), 'C': ('Q_S', 'V1', 'Size'),
         'D': ('Q_CP', 'V2', ALT_SIZE)}  # Painel D: a outra medida de tamanho
rows = []
for k, (q, v, size) in specs.items():
    b = E.est_sample(p, q, v)
    for var in ['Mineral_RareEarths', 'Composite']:
        for pn in PAN:
            d = sample(E.subset(b, pn), var)
            f, _ = fit(d, var, ctl=f' + {size} + Leverage + ROA')
            rows.append(dict(Painel_tab=k, Var=var, Painel=pn, **cell(f)))
R['T11'] = pd.DataFrame(rows)
print(R['T11'].round(4).to_string(), flush=True)

# ---------------- Correlação composto x cobre
bnt = base[base['TRBC Industry Group Name'] != TEL]
R['corr'] = pd.DataFrame([dict(com_telecom=base[['Composite', 'Mineral_Copper']].corr().iloc[0, 1],
                               sem_telecom=bnt[['Composite', 'Mineral_Copper']].corr().iloc[0, 1],
                               firmas_telecom=base.loc[base['TRBC Industry Group Name'] == TEL, 'RIC'].nunique(),
                               obs_telecom=int((base['TRBC Industry Group Name'] == TEL).sum()))])
print(R['corr'], flush=True)

# ---------------- Tabela 17, Painel E: efeitos fixos de país x trimestre (só mudam algo onde há mais de um país)
rows = []
for var in MIN + ['Composite']:
    for pn in ['Total', 'Nordic', 'Europe']:
        d = sample(E.subset(base, pn), var)
        f, _ = fit(d, var, fe='RIC + HQ^qkey')
        rows.append(dict(Var=var, Painel=pn, **cell(f)))
R['M2_pais'] = pd.DataFrame(rows)
print(R['M2_pais'].round(4).to_string(), flush=True)

# ---------------- Tabela 7: produtoras por firma, indicador 0/1, efeitos fixos de região x trimestre
b6 = base[base['Region_HQ'].isin(['US', 'UK', 'Nordic', 'Canada', 'Europe'])].copy()
b6['Prod'] = b6['TRBC Industry Group Name'].isin(PROD).astype(float)
b6['rq'] = b6['Region_HQ'] + '_' + b6['qkey']

def drop_singletons(dd, fe=('RIC', 'rq')):
    while True:
        n0 = len(dd)
        for c in fe:
            dd = dd[dd.groupby(c)[c].transform('size') > 1]
        if len(dd) == n0:
            return dd

rows = []
B = 9999
for var in MIN + ['Composite']:
    d = sample(b6, var).copy()
    d['X'] = d[var].astype(float); d['XP'] = d['X'] * d['Prod']
    f = pf.feols("Q ~ X + XP + Size + Leverage + ROA | RIC + rq", data=d, vcov={'CRV1': 'RIC'})
    V = f._vcov; names = list(f.coef().index); i, j = names.index('X'), names.index('XP')
    bp = f.coef()['X'] + f.coef()['XP']; sep = np.sqrt(V[i, i] + V[j, j] + 2 * V[i, j])
    from scipy import stats
    dfree = d['RIC'].nunique() - 1
    dd = drop_singletons(d)
    fid = pd.factorize(dd['RIC'])[0]; qid = pd.factorize(dd['rq'])[0]
    pre = wcr.prepare(dd['Q'].values, dd['XP'].values, dd[['X', 'Size', 'Leverage', 'ROA']].values, fid, qid)
    Wt = wcr.weights(pre['G'], B, np.random.default_rng(SEED))
    pw = wcr.pvalue(pre, Wt)
    prodvar = nvar(d[d['Prod'] == 1], var); consvar = nvar(d[d['Prod'] == 0], var)
    rows.append(dict(Var=var, b_consumidoras=f.coef()['X'], se_c=f.se()['X'], p_c=f.pvalue()['X'],
                     dif_produtoras=f.coef()['XP'], se_dif=f.se()['XP'], p_dif=f.pvalue()['XP'], p_dif_wild=pw,
                     b_produtoras=bp, se_p=sep, p_p=2 * stats.t.sf(abs(bp / sep), dfree),
                     firmas_prod=int(d.loc[d['Prod'] == 1, 'RIC'].nunique()), prod_com_variacao=prodvar,
                     cons_com_variacao=consvar, N=f._N))
    print('produtoras', var, flush=True)
R['M6_produtoras'] = pd.DataFrame(rows)
print(R['M6_produtoras'].round(4).to_string(), flush=True)
fr = b6.drop_duplicates('RIC')
R['M6_info'] = fr.groupby('Region_HQ')['Prod'].agg(['sum', 'size', 'mean']).reset_index()
pickle.dump(R, open(f'{RES}/valuation_parcial.pkl', 'wb'))

# ---------------- inferência: wild bootstrap, Romano-Wolf e randomização
def ds2(dd):
    return drop_singletons(dd, ('RIC', 'qkey'))
allfirms = pd.Index(sorted(base['RIC'].unique()))
Wg = wcr.weights(len(allfirms), B, np.random.default_rng(SEED))
keys, tobs, tb = [], [], []
for var in MIN + ['Composite']:
    for pn in PAN:
        dd = sample(E.subset(base, pn), var).copy(); dd['MR'] = E.zscore(dd[var].astype(float)); dd = ds2(dd)
        fidx = pd.Index(sorted(dd['RIC'].unique())); fid = fidx.get_indexer(dd['RIC']); qid = pd.factorize(dd['qkey'])[0]
        pre = wcr.prepare(dd['Q'].values, dd['MR'].values, dd[['Size', 'Leverage', 'ROA']].values, fid, qid)
        ts = wcr.boot_t(pre, Wg[allfirms.get_indexer(fidx)])
        keys.append((var, pn)); tobs.append(pre['t']); tb.append(ts)
        print('wcr', var, pn, round(pre['b'], 4), flush=True)
tobs = np.array(tobs); tb = np.vstack(tb)
p_rw = wcr.romano_wolf(tobs, tb); p_wild = np.mean(np.abs(tb) >= np.abs(tobs)[:, None], axis=1)
R['M5_rw'] = pd.DataFrame({'Var': [k[0] for k in keys], 'Painel': [k[1] for k in keys], 't': tobs,
                           'p_wild': p_wild, 'p_romano_wolf': p_rw})
rng = np.random.default_rng(SEED); rows = []
for var, pn in [('Composite', 'US'), ('Composite', 'Total')]:
    d = sample(E.subset(base, pn), var); f, dd = fit(d, var); b0 = f.coef()['MR']; perm = []
    for _ in range(999):
        x = dd.copy(); x[var] = x.groupby('RIC')[var].transform(lambda s: rng.permutation(s.values))
        fp, _ = fit(x, var); perm.append(fp.coef()['MR'])
    perm = np.array(perm); k = keys.index((var, pn))
    rows.append(dict(Var=var, Painel=pn, beta=b0, p_CRV1=f.pvalue()['MR'], p_wild=p_wild[k],
                     p_RI=(1 + (np.abs(perm) >= abs(b0)).sum()) / (1 + len(perm)), p_RW=p_rw[k]))
R['M5_composto'] = pd.DataFrame(rows)
print(R['M5_rw'].round(4).to_string()); print(R['M5_composto'])
with pd.ExcelWriter(f'{RES}/resultados_valuation.xlsx') as w:
    for k, v in R.items():
        v.to_excel(w, sheet_name=k[:31], index=False)
print('ok')
