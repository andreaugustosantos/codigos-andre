"""Funções da tripla diferença do CRMA: painel, classificação, escore de propensão, pareamento 1:1 com caliper e regressão (usadas pelos scripts 11 a 13)."""
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__))); from caminhos import *  # noqa
import numpy as np, pandas as pd, pyfixest as pf, statsmodels.api as sm, os
exec(open(os.path.join(os.path.dirname(__file__), 'sector_map.py')).read())

FINANCIALS = ['Banking Services', 'Insurance', 'Investment Banking & Investment Services',
              'Residential & Commercial REITs', 'Collective Investments', 'Investment Holding Companies']
EU_MEMBERS = {'Austria', 'Belgium', 'Bulgaria', 'Croatia', 'Cyprus', 'Czech Republic', 'Denmark', 'Estonia',
              'Finland', 'France', 'Germany', 'Greece', 'Hungary', 'Ireland', 'Italy', 'Latvia', 'Lithuania',
              'Luxembourg', 'Malta', 'Netherlands', 'Poland', 'Portugal', 'Romania', 'Slovakia', 'Slovenia',
              'Spain', 'Sweden'}
EEA_EFTA = {'Norway', 'Iceland', 'Liechtenstein'}
POST = '20240630'
CLASS_END = '20220630'      # exposição: calls até 2022T2 (inclusive)
COV_YEAR = '2021'
QUANTILE, CALIPER = 0.75, 0.2
CONTROL_CELLS = ['EU x Low', 'Não-UE x High', 'Não-UE x Low']
CELLS = {(1, 1): 'EU x High (tratadas)', (1, 0): 'EU x Low', (0, 1): 'Não-UE x High', (0, 0): 'Não-UE x Low'}
COVS = [f'{PSM_SIZE}_pre', 'Leverage_pre', 'ROA_pre']  # tamanho do pareamento: caminhos.PSM_SIZE


def winsorise(s, lo=0.01, hi=0.99):
    return s.clip(s.quantile(lo), s.quantile(hi))


def qindex(qkey):
    q = pd.to_datetime(qkey)
    return q.dt.year * 4 + (q.dt.month - 1) // 3


def build_panel(p, wins_after_eea=True):
    d = p[~p['TRBC Industry Group Name'].isin(FINANCIALS)].copy()
    if wins_after_eea:
        d = d[~d['HQ'].isin(EEA_EFTA)]
    d = d.dropna(subset=['Q_CP', 'Q_S', 'Leverage', 'ROA', 'MktCap'])
    d = d[d['MktCap'] > 0].copy()
    for c in ['Q_CP', 'Q_S', 'Leverage', 'ROA']:
        d[c] = winsorise(d[c])
    d = d[~d['HQ'].isin(EEA_EFTA)].copy()
    d['lnMktCap'] = np.log(d['MktCap'])
    d['lnTA'] = np.log(d['TA'].where(d['TA'] > 0))
    d['Size'] = d[SIZE]  # controle de tamanho da coluna com controles (caminhos.SIZE)
    d['EU'] = d['HQ'].isin(EU_MEMBERS).astype(int)
    d['Sector'] = d['TRBC Industry Group Name'].map(SECTOR).fillna('Other')
    d['t'] = qindex(d['qkey'])
    return d


def classify(d, q=QUANTILE, cutoff=CLASS_END, min_calls=1, var='Composite'):
    pre = d[(d['qkey'] <= cutoff) & (d['has_call'] == 1)]
    g = pre.groupby('RIC')[var]
    f = pd.DataFrame({'Exposure_pre': g.mean(), 'n_pre': g.size()})
    f = f[f['n_pre'] >= min_calls]
    thr = f['Exposure_pre'].quantile(q)
    # Se o percentil é zero (placebo), High = qualquer menção
    f['High'] = ((f['Exposure_pre'] >= thr) & (f['Exposure_pre'] > 0)).astype(int)
    return f, thr


def firm_table(d, cls, cov_year=COV_YEAR):
    pre = d[d['qkey'].str[:4] == cov_year]
    cov = pre.groupby('RIC').agg(lnMktCap_pre=('lnMktCap', 'mean'), lnTA_pre=('lnTA', 'mean'), Leverage_pre=('Leverage', 'mean'),
                                 ROA_pre=('ROA', 'mean'))
    info = d.groupby('RIC').agg(EU=('EU', 'first'), Sector=('Sector', 'first'), HQ=('HQ', 'first'))
    f = info.join(cls, how='inner').join(cov, how='inner')
    f['Treated'] = f['EU'] * f['High']
    f['Cell'] = [CELLS[(e, h)] for e, h in zip(f['EU'], f['High'])]
    return f


def propensity(f):
    dummies = pd.get_dummies(f['Sector'], prefix='S', drop_first=True, dtype=float)
    X = sm.add_constant(pd.concat([f[COVS], dummies], axis=1))
    res = sm.Logit(f['Treated'], X).fit(disp=0, maxiter=500)
    return res.predict(X), res


def greedy(f, treated, cal):
    tr = f.loc[treated].sort_values('pscore', ascending=False)
    pairs = []
    for cell in CONTROL_CELLS:
        pool = f[f['Cell'] == cell]
        lo, hi = max(tr['lps'].min(), pool['lps'].min()), min(tr['lps'].max(), pool['lps'].max())
        avail = pool[(pool['lps'] >= lo) & (pool['lps'] <= hi)][['lps', 'Sector']].copy()
        for ric, row in tr.iterrows():
            if not (lo <= row['lps'] <= hi):
                continue
            cand = avail[avail['Sector'] == row['Sector']]
            if cand.empty:
                continue
            dist = (cand['lps'] - row['lps']).abs()
            j = dist.idxmin()
            if dist[j] > cal:
                continue
            pairs.append({'Tratada': ric, 'Celula': cell, 'Controle': j})
            avail = avail.drop(j)
    return pd.DataFrame(pairs, columns=['Tratada', 'Celula', 'Controle'])


def match(f, caliper=CALIPER):
    f = f.copy()
    f['lps'] = np.log(f['pscore'] / (1 - f['pscore']))
    cal = caliper * f['lps'].std() if caliper is not None else np.inf
    treated = list(f.index[f['Treated'] == 1])
    while True:
        pairs = greedy(f, treated, cal)
        n = pairs.groupby('Tratada')['Celula'].nunique()
        complete = [r for r in treated if n.get(r, 0) == len(CONTROL_CELLS)]
        if len(complete) == len(treated):
            break
        treated = complete
    return pairs, set(treated) | set(pairs['Controle'])


def run_matching(d, q=QUANTILE, caliper=CALIPER, cutoff=CLASS_END, cov_year=COV_YEAR, min_calls=1):
    cls, thr = classify(d, q, cutoff, min_calls)
    f_all = firm_table(d, cls, cov_year)
    f = f_all[f_all['Sector'].isin(set(f_all.loc[f_all['Treated'] == 1, 'Sector']))].copy()
    f['pscore'], logit = propensity(f)
    pairs, keep = match(f, caliper)
    return f_all, f, f[f.index.isin(keep)], pairs, thr


def ddd(d, f, post=POST, qvar='Q_CP', start=None, end=None, controls=False, extra_fe='', vcov=None):
    s = d[d['RIC'].isin(f.index)].copy()
    if start is not None:
        s = s[s['qkey'] >= start]
    if end is not None:
        s = s[s['qkey'] <= end]
    s = s.join(f[['High']], on='RIC')
    s['Post'] = (s['qkey'] >= post).astype(int)
    s['EUxHighxPost'] = s['EU'] * s['High'] * s['Post']
    s['EUxPost'] = s['EU'] * s['Post']
    s['HighxPost'] = s['High'] * s['Post']
    s = s.rename(columns={qvar: 'Q'})
    ctl = ' + Size + Leverage + ROA' if controls else ''
    m = pf.feols(f"Q ~ EUxHighxPost + EUxPost + HighxPost{ctl} | RIC + qkey{extra_fe}", data=s,
                 vcov=vcov or {'CRV1': 'RIC'})
    return m, s
