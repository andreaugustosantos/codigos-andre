"""
Testes adicionais da Equação (6) (Tabela 19, Painéis B e C).

  1. O Q defasado prevê a menção? Menção em t sobre o Q de t-1, t-2 e t-4.
  2. O Romano-Wolf muda com a semente? Os 36 coeficientes da Tabela 6, com dez sementes.
  3. Quantas menções a cobre vêm das firmas de telecom (por isso o composto as exclui).
Saída: resultados/q_extras.pkl e q_extras.xlsx
"""
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__))); from caminhos import *  # noqa
import importlib.util, pickle, warnings
import numpy as np, pandas as pd, pyfixest as pf
warnings.filterwarnings('ignore')
spec = importlib.util.spec_from_file_location('e', EST_PY); E = importlib.util.module_from_spec(spec); spec.loader.exec_module(E)
import ddd_core as D, wcr
TEL = 'Telecommunications Services'
p = pd.read_pickle(f'{R02}/painel_firma_trimestre.pkl'); p['t'] = D.qindex(p['qkey'])
base = E.est_sample(p, 'Q_CP', 'V2'); full = E.est_sample(p, 'Q_CP', 'V1')
R = {}

# ---------------- 1. Q defasado prevê a menção
rows = []
fq = full[['RIC', 't', 'Q', 'Size', 'Leverage', 'ROA']]
for var in ['Mineral_RareEarths', 'Composite', 'Mineral_Copper']:
    for pn in ['US', 'Total']:
        b = E.subset(base, pn); b = b[b['TRBC Industry Group Name'] != TEL] if var == 'Composite' else b
        for k in [1, 2, 4]:
            x = fq.copy(); x['t'] = x['t'] + k
            dd = b[['RIC', 't', 'qkey', var]].merge(x, on=['RIC', 't'])
            dd['Qz'] = E.zscore(dd['Q'])
            m = pf.feols(f'{var} ~ Qz + Size + Leverage + ROA | RIC + qkey', data=dd, vcov={'CRV1': 'RIC'})
            rows.append(dict(var=var, panel=pn, lag=k, b_Qz=m.coef()['Qz'], se=m.se()['Qz'], p=m.pvalue()['Qz'],
                             mean_mention=dd[var].mean(), sdQ=dd['Q'].std(ddof=0), N=m._N, firms=dd.RIC.nunique()))
R['lagQ'] = pd.DataFrame(rows); print(R['lagQ'].round(4).to_string(), flush=True)

# ---------------- 2. Romano-Wolf com dez sementes
def drop_singletons(dd):
    while True:
        n0 = len(dd)
        for c in ('RIC', 'qkey'): dd = dd[dd.groupby(c)[c].transform('size') > 1]
        if len(dd) == n0: return dd
allfirms = pd.Index(sorted(base['RIC'].unique()))
cells = []
for var in E.MINERALS + ['Composite']:
    for pn in E.PANELS:
        dd = E.subset(base, pn); dd = dd[dd['TRBC Industry Group Name'] != TEL] if var == 'Composite' else dd
        dd = dd.copy(); dd['MR'] = E.zscore(dd[var].astype(float)); dd = drop_singletons(dd)
        fidx = pd.Index(sorted(dd['RIC'].unique()))
        pre = wcr.prepare(dd['Q'].values, dd['MR'].values, dd[['Size', 'Leverage', 'ROA']].values,
                          fidx.get_indexer(dd['RIC']), pd.factorize(dd['qkey'])[0])
        cells.append(((var, pn), pre, allfirms.get_indexer(fidx)))
keys = [c[0] for c in cells]; tobs = np.array([c[1]['t'] for c in cells])
rows = []
for seed in [20261024] + list(range(1, 10)):
    Wg = wcr.weights(len(allfirms), 9999, np.random.default_rng(seed))
    tb = np.vstack([wcr.boot_t(pre, Wg[ix]) for _, pre, ix in cells])
    prw = wcr.romano_wolf(tobs, tb); pw = np.mean(np.abs(tb) >= np.abs(tobs)[:, None], axis=1)
    for k, (var, pn) in enumerate(keys):
        rows.append(dict(seed=seed, var=var, panel=pn, t=tobs[k], p_wild=pw[k], p_rw=prw[k]))
    print('seed', seed, 'RE US RW', round(prw[keys.index(('Mineral_RareEarths', 'US'))], 4), flush=True)
rw = pd.DataFrame(rows); R['rw_seeds'] = rw
R['rw_summary'] = rw.groupby(['var', 'panel']).agg(t=('t', 'first'), p_rw_min=('p_rw', 'min'), p_rw_max=('p_rw', 'max'),
                                                  p_rw_mean=('p_rw', 'mean'), p_wild_min=('p_wild', 'min'), p_wild_max=('p_wild', 'max')).reset_index()
print(R['rw_summary'][R['rw_summary'].p_rw_mean < 0.5].round(4).to_string(), flush=True)

# ---------------- 3. Cobre nas firmas de telecom
tr = pd.read_pickle(f'{R02}/amostra_validacao.pkl')
tel = tr['TRBC Industry Group Name'] == TEL
R['telecom_copper'] = pd.DataFrame([dict(
    transcripts_telecom=int(tel.sum()), firms_telecom=int(tr.loc[tel, 'RIC'].nunique()),
    copper_transcripts_telecom=int(tr.loc[tel, 'Mineral_Copper'].sum()),
    copper_share_telecom_transcripts=float(tr.loc[tel, 'Mineral_Copper'].mean()),
    copper_transcripts_all=int(tr['Mineral_Copper'].sum()),
    telecom_share_of_copper=float(tr.loc[tel, 'Mineral_Copper'].sum() / tr['Mineral_Copper'].sum()),
    firmq_copper_telecom_est=int(base.loc[base['TRBC Industry Group Name'] == TEL, 'Mineral_Copper'].sum()),
    firmq_copper_all_est=int(base['Mineral_Copper'].sum()))])
print(R['telecom_copper'].T, flush=True)
pickle.dump(R, open(f'{RES}/q_extras.pkl', 'wb'))
with pd.ExcelWriter(f'{RES}/q_extras.xlsx') as w:
    for k, v in R.items(): v.to_excel(w, sheet_name=k[:31], index=False)
print('ok')
