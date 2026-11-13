"""
Testes de robustez da Equação (6), principalmente para terras raras nos EUA.

  - efeito por menção e leave-one-out (Tabela 16)
  - efeitos fixos de setor e de grupo industrial x trimestre, sem controles, defasagens e avanços,
    primeiras diferenças (Tabela 18, linhas 2 a 6)
  - teste agrupado de H2 (Tabela 19, Painel A)
  - randomização das células citadas no texto
Saída: resultados_robustez.xlsx
"""
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__))); from caminhos import *  # noqa
import importlib.util, sys, os, warnings
import numpy as np, pandas as pd, pyfixest as pf
warnings.filterwarnings('ignore')
W = ROOT
spec = importlib.util.spec_from_file_location('e', EST_PY); E = importlib.util.module_from_spec(spec); spec.loader.exec_module(E)
sys.path.insert(0, CODE); import ddd_core as D
OUT = RES
SEED = 20261024

p = pd.read_pickle(f'{R02}/painel_firma_trimestre.pkl')
tr = pd.read_pickle(f'{R02}/amostra_validacao.pkl')
cot = tr.groupby(['RIC', 'qkey'])['Placebo_Negative'].max().rename('Cotton').reset_index()
p = p.merge(cot, on=['RIC', 'qkey'], how='left'); p['Cotton'] = p['Cotton'].fillna(0).astype(int)
p['Sector'] = p['TRBC Industry Group Name'].map(D.SECTOR).fillna('Other')
p['t'] = D.qindex(p['qkey'])
base = E.est_sample(p, 'Q_CP', 'V2')
VARS = E.MINERALS + ['Composite']
LAB = E.LABEL
R = {}

def cell(f, name='MR'):
    return dict(beta=f.coef()[name], se=f.se()[name], p=f.pvalue()[name], N=f._N)

def fit(d, var, fe='RIC + qkey', ctl=' + Size + Leverage + ROA', vcov=None):
    d = d.copy(); d['MR'] = E.zscore(d[var].astype(float))
    return pf.feols(f"Q ~ MR{ctl} | {fe}", data=d, vcov=vcov or {'CRV1': 'RIC'}), d

def fit_num(d, var):
    """Mesma Equação (6), com ids numéricos e colunas float (o wildboottest exige)."""
    d = d[['RIC', 'qkey', 'Q', 'Size', 'Leverage', 'ROA', var]].copy()
    d['MR'] = E.zscore(d[var].astype(float))
    d['fid'] = pd.factorize(d['RIC'])[0]; d['qid'] = pd.factorize(d['qkey'])[0]
    for c in ['Q', 'Size', 'Leverage', 'ROA', 'MR']:
        d[c] = d[c].astype('float64')
    return pf.feols("Q ~ MR + Size + Leverage + ROA | fid + qid", data=d, vcov={'CRV1': 'fid'}), d


def nvar(d, var):
    """Firmas em que o indicador varia ao longo do tempo (são elas que identificam o beta)."""
    g = d.groupby('RIC')[var].agg(['min', 'max'])
    return int((g['max'] > g['min']).sum())

# ---------------- efeito por menção e firmas que identificam o beta
rows = []
for var in VARS:
    for pn in E.PANELS:
        d = E.subset(base, pn); f, dd = fit(d, var)
        sd = dd[var].astype(float).std(ddof=0); c = cell(f)
        rows.append(dict(MineralRisk=LAB[var], Painel=pn, **c, sd_raw=sd, por_mencao=c['beta'] / sd,
                         firmas_mencionam=int(dd.loc[dd[var] > 0, 'RIC'].nunique()), firmas_com_variacao=nvar(f._data if False else dd, var),
                         mean_Q=dd['Q'].mean()))
R['M3_por_mencao'] = pd.DataFrame(rows)
us = E.subset(base, 'US'); loo = []
for ric in [None] + list(us.loc[us['Mineral_RareEarths'] == 1, 'RIC'].value_counts().index):
    d = us if ric is None else us[us['RIC'] != ric]
    f, dd = fit(d, 'Mineral_RareEarths'); sd = dd['Mineral_RareEarths'].std(ddof=0); c = cell(f)
    loo.append(dict(Retirada=ric or 'Nenhuma', **c, sd_raw=sd, por_mencao=c['beta'] / sd,
                    firmas_com_variacao=nvar(dd, 'Mineral_RareEarths')))
R['M3_LOO_por_mencao'] = pd.DataFrame(loo)

# ---------------- efeitos fixos de setor x trimestre
rows = []
for var in VARS:
    for pn in E.PANELS:
        d = E.subset(base, pn)
        for lab, fe in [('Base', 'RIC + qkey'), ('Setor econ. x trim.', 'RIC + Sector^qkey'),
                        ('Grupo ind. x trim.', 'RIC + TRBC Industry Group Name^qkey')]:
            d2 = d.rename(columns={'TRBC Industry Group Name': 'IG'}); fe2 = fe.replace('TRBC Industry Group Name', 'IG')
            if pn == 'Total' and lab != 'Base':
                fe2 = fe2 + ' + HQ^qkey'
            try:
                f, _ = fit(d2, var, fe=fe2); rows.append(dict(MineralRisk=LAB[var], Painel=pn, Spec=lab, **cell(f)))
            except Exception as ex:
                rows.append(dict(MineralRisk=LAB[var], Painel=pn, Spec=lab, erro=str(ex)[:80]))
R['M2_FE_setor'] = pd.DataFrame(rows)

# ---------------- defasagens e avanços (vizinho sem call = ausente) e primeiras diferenças
pc = p[p['has_call'] == 1][['RIC', 't'] + VARS]
def add_nb(d, var):
    d = d.copy()
    for k, nm in [(1, 'lead'), (-1, 'lag')]:
        nb = pc[['RIC', 't', var]].copy(); nb['t'] = nb['t'] - k
        d = d.merge(nb.rename(columns={var: f'{var}_{nm}'}), on=['RIC', 't'], how='left')
    return d
rows = []
for var in VARS:
    for pn in E.PANELS:
        d = add_nb(E.subset(base, pn), var).dropna(subset=[f'{var}_lead', f'{var}_lag'])
        for c_ in [var, f'{var}_lead', f'{var}_lag']:
            d[c_ + '_z'] = E.zscore(d[c_].astype(float))
        if d[[var + '_z', var + '_lead_z', var + '_lag_z']].isna().any().any():
            continue
        f = pf.feols(f"Q ~ {var}_lag_z + {var}_z + {var}_lead_z + Size + Leverage + ROA | RIC + qkey",
                     data=d, vcov={'CRV1': 'RIC'})
        r = dict(MineralRisk=LAB[var], Painel=pn, N=f._N)
        for nm, c_ in [('lag', f'{var}_lag_z'), ('t', f'{var}_z'), ('lead', f'{var}_lead_z')]:
            r[f'b_{nm}'] = f.coef()[c_]; r[f'se_{nm}'] = f.se()[c_]; r[f'p_{nm}'] = f.pvalue()[c_]
        r['firmas_com_variacao_t'] = nvar(d, var)
        rows.append(r)
R['M4a_leads_lags'] = pd.DataFrame(rows)
# Primeiras diferenças: Q (winsorizado no painel completo não financeiro) de t-1 para t, ambos trimestres com call
full = E.est_sample(p, 'Q_CP', 'V1')[['RIC', 't', 'Q', 'Size', 'Leverage', 'ROA']]
rows = []
for var in VARS:
    for pn in E.PANELS:
        d = E.subset(base, pn)[['RIC', 't', 'qkey', var]].merge(full, on=['RIC', 't'])
        prev = d[['RIC', 't', var, 'Q', 'Size', 'Leverage', 'ROA']].copy(); prev['t'] += 1
        d = d.merge(prev, on=['RIC', 't'], suffixes=('', '_prev'))
        for c_ in [var, 'Q', 'Size', 'Leverage', 'ROA']:
            d['d_' + c_] = d[c_] - d[c_ + '_prev']
        if d['d_' + var].std() == 0:
            continue
        d['dMR'] = d['d_' + var] / d[var].astype(float).std(ddof=0)
        f = pf.feols("d_Q ~ dMR + d_Size + d_Leverage + d_ROA | qkey", data=d, vcov={'CRV1': 'RIC'})
        rows.append(dict(MineralRisk=LAB[var], Painel=pn, **cell(f, 'dMR')))
R['M4a_primeiras_dif'] = pd.DataFrame(rows)

# ---------------- sem controles, composto sem telecom e placebo (algodão)
rows = []
for var in VARS + ['Cotton']:
    for pn in E.PANELS:
        d = E.subset(base, pn)
        if var == 'Cotton':
            f, _ = fit(d, 'Cotton'); rows.append(dict(Teste='m6 Placebo algodão', MineralRisk='Cotton', Painel=pn, **cell(f))); continue
        f, _ = fit(d, var, ctl=''); rows.append(dict(Teste='m4 Sem controles', MineralRisk=LAB[var], Painel=pn, **cell(f)))
for pn in E.PANELS:
    d = E.subset(base, pn); d = d[d['TRBC Industry Group Name'] != 'Telecommunications Services']
    f, _ = fit(d, 'Composite'); rows.append(dict(Teste='m3 Composto sem telecom', MineralRisk='Composite', Painel=pn, **cell(f)))
R['m3_m4_m6'] = pd.DataFrame(rows)

# ---------------- teste agrupado de H2 (indicador 0/1 x região, efeitos fixos de região x trimestre)
rows = []
b6 = base[base['Region_HQ'].isin(['US', 'UK', 'Nordic', 'Canada', 'Europe'])].copy()
for var in ['Mineral_RareEarths', 'Mineral_Copper', 'Composite']:
    d = b6.copy()
    for r_ in ['UK', 'Nordic', 'Canada', 'Europe']:
        d[f'X_{r_}'] = d[var] * (d['Region_HQ'] == r_)
    d['X_US'] = d[var].astype(float)
    f = pf.feols("Q ~ X_US + X_UK + X_Nordic + X_Canada + X_Europe + Size + Leverage + ROA | RIC + Region_HQ^qkey",
                 data=d, vcov={'CRV1': 'RIC'})
    for c_ in ['X_US', 'X_UK', 'X_Nordic', 'X_Canada', 'X_Europe']:
        rows.append(dict(MineralRisk=LAB[var], Termo=('EUA (nível, por menção)' if c_ == 'X_US' else f'{c_[2:]} menos EUA'),
                         **cell(f, c_)))
R['M6a_teste_H2'] = pd.DataFrame(rows)

# (O DDD com e sem as firmas dos EUA, ligado ao IRA, está no 11_ddd_crma.py.)

# ---------------- peso de Metals & Mining em cada painel
fr = base.drop_duplicates('RIC')
n1 = fr.groupby('Region_HQ').apply(lambda g: pd.Series({'Firmas': len(g), 'Metals & Mining': int((g['TRBC Industry Group Name'] == 'Metals & Mining').sum())}))
n1['%'] = 100 * n1['Metals & Mining'] / n1['Firmas']
R['N1_metals_mining'] = n1.reset_index()

import pickle; pickle.dump(R, open(f'{OUT}/R_parte1.pkl','wb')); print('parte 1 ok', flush=True)
if os.environ.get('SO_PARTE1'): sys.exit(0)
# ---------------- inferência das células citadas no texto
# Wild bootstrap e Romano-Wolf das 36 células da Tabela 6: calculados uma vez só, no 05_valuation.py
# (composto sem telecomunicações, como na Tabela 6). Aqui entram só a randomização e os p-valores lidos do 05.
RW6 = pd.read_excel(f'{RES}/resultados_valuation.xlsx', sheet_name='M5_rw').set_index(['Var', 'Painel'])
CITED = [('Mineral_RareEarths', 'US'), ('Mineral_RareEarths', 'Canada'), ('Mineral_RareEarths', 'Nordic'),
         ('Mineral_Copper', 'US'), ('Mineral_Copper', 'UK')]  # o composto tem a randomização no 05
rng = np.random.default_rng(SEED)
rows = []
for var, pn in CITED:
    d = E.subset(base, pn); f, dd = fit(d, var); b0 = f.coef()['MR']; perm = []
    for _ in range(999):
        x = dd.copy(); x[var] = x.groupby('RIC')[var].transform(lambda s: rng.permutation(s.values))
        fp, _ = fit(x, var); perm.append(fp.coef()['MR']); del fp
    perm = np.array(perm)
    rows.append(dict(MineralRisk=LAB[var], Painel=pn, beta=b0, p_CRV1=f.pvalue()['MR'], p_wild=RW6.loc[(var, pn), 'p_wild'],
                     p_randomizacao=(1 + (np.abs(perm) >= abs(b0)).sum()) / (1 + len(perm)),
                     p_romano_wolf=RW6.loc[(var, pn), 'p_romano_wolf'], firmas_com_variacao=nvar(dd, var)))
    print('RI', var, pn, flush=True)
R['M5_inferencia'] = pd.DataFrame(rows)
# (O wild bootstrap do DDD por país de sede está no 11_ddd_crma.py.)

with pd.ExcelWriter(f'{OUT}/resultados_robustez.xlsx') as w:
    for k, v in R.items():
        v.to_excel(w, sheet_name=k[:31], index=False)
print('ok')
