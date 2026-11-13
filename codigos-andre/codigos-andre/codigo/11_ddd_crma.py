"""
Tripla diferença em torno do CRMA: pareamento, balanceamento, estimativa principal, estudo de evento,
poder, especificações alternativas e wild bootstrap por país (Tabelas 8, 20, 21 e 23 e Figura 8).

As firmas de telecom ficam fora antes da classificação, como no composto da Equação (6).
Com EXCL_TEL=0 elas entram (linha da Tabela 21 com telecom).
"""
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__))); from caminhos import *  # noqa
import os, sys, pickle, warnings
import numpy as np, pandas as pd, pyfixest as pf
from scipy import stats
from scipy.optimize import minimize
warnings.filterwarnings('ignore')
sys.path.insert(0, CODE)
import ddd_core as D, wcr
EXCL = int(os.environ.get('EXCL_TEL', '1'))
TEL = 'Telecommunications Services'
OUT = f'{RES}/ddd_{"nt" if EXCL else "com_telecom"}.pkl'
R = {}

p = pd.read_pickle(R02 + '/painel_firma_trimestre.pkl')
desc = pd.concat([pd.read_excel(f, sheet_name='Extraction') for f in
                  DESC])
exch = desc.drop_duplicates('RIC').set_index('RIC')['Country of Exchange']
d_all = D.build_panel(p)
d = d_all[d_all['TRBC Industry Group Name'] != TEL].copy() if EXCL else d_all

def res(m, k='EUxHighxPost'):
    return dict(b=m.coef()[k], se=m.se()[k], p=m.pvalue()[k], N=m._N)

def row(lbl, m, f=None, **kw):
    r = dict(spec=lbl, **res(m), HxP=m.coef().get('HighxPost', np.nan), HxP_p=m.pvalue().get('HighxPost', np.nan),
             ExP=m.coef().get('EUxPost', np.nan))
    if f is not None:
        r.update(treated=int(f['Treated'].sum()), firms=len(f))
    r.update(kw); return r

def rematch_from(fall):
    fx = fall[fall['Sector'].isin(set(fall.loc[fall['Treated'] == 1, 'Sector']))].copy()
    fx['pscore'], _ = D.propensity(fx); pr, keep = D.match(fx)
    return fx[fx.index.isin(keep)], pr

# ---------------- principal
fa, f, fm, pairs, thr = D.run_matching(d)
R['thr'] = thr; R['n_class'] = len(fa); R['n_treated_all'] = int(fa['Treated'].sum())
m0, s0 = D.ddd(d, fm)
grp = d.drop_duplicates('RIC').set_index('RIC')
tm = fm[fm['Treated'] == 1]
R['treated_sector'] = tm['Sector'].value_counts(); R['treated_hq'] = tm['HQ'].value_counts()
R['irish_us_listed'] = int(((tm['HQ'] == 'Ireland') & (exch.reindex(tm.index) == 'United States of America')).sum())
R['us_controls'] = int(((fm['Treated'] == 0) & (fm['HQ'] == 'United States of America')).sum())
R['meanQ'] = s0['Q'].mean()

# ---------------- Tabela 8
T7 = [row('(1) Matched', m0, fm)]
m, _ = D.ddd(d, fm, qvar='Q_S'); T7.append(row('(2) Simpl. Q', m, fm))
m, _ = D.ddd(d, fm, controls=True); T7.append(row('(3) Controls', m, fm))
m, _ = D.ddd(d, fa); T7.append(row('(4) Unmatched', m, fa))
m, _ = D.ddd(d, fm, start='20220630', end='20260630'); T7.append(row('(5) Window', m, fm))
m, _ = D.ddd(d, fm, post='20220930'); T7.append(row('(6) Announcement', m, fm))
fap, fp_, fmp, _, thrp = D.run_matching(d, cutoff='20190630', cov_year='2018')
m, _ = D.ddd(d, fmp, post='20210630', end='20220630'); T7.append(row('(7) Placebo', m, fmp))
for r in T7:
    pass
R['T7'] = pd.DataFrame(T7)
# Linhas completas da Tabela 8 (três coeficientes)
full = []
for lbl, kw, ff in [('(1)', {}, fm), ('(2)', dict(qvar='Q_S'), fm), ('(3)', dict(controls=True), fm), ('(4)', {}, fa),
                    ('(5)', dict(start='20220630', end='20260630'), fm), ('(6)', dict(post='20220930'), fm),
                    ('(7)', dict(post='20210630', end='20220630'), fmp)]:
    m, s = D.ddd(d, ff, **kw)
    full.append(dict(col=lbl, **{f'{k}_{x}': getattr(m, x)()[k] for k in ['EUxHighxPost', 'EUxPost', 'HighxPost'] for x in ['coef', 'se', 'pvalue']},
                     treated=int(ff['Treated'].sum()), firms=len(ff), N=m._N))
R['T7_full'] = pd.DataFrame(full)
print(R['T7_full'].round(4).T, flush=True)

# ---------------- poder e combinação EU high vs EU low
b, se = m0.coef()['EUxHighxPost'], m0.se()['EUxHighxPost']
R['power'] = dict(ci_lo=b - 1.96 * se, ci_hi=b + 1.96 * se, mde=2.8 * se, meanQ=R['meanQ'])
V = m0._vcov; nm = list(m0.coef().index); i, j = nm.index('EUxHighxPost'), nm.index('HighxPost')
c = m0.coef()['EUxHighxPost'] + m0.coef()['HighxPost']; sc = np.sqrt(V[i, i] + V[j, j] + 2 * V[i, j])
R['eu_high_vs_low'] = dict(b=c, se=sc, p=2 * stats.t.sf(abs(c / sc), fm.shape[0] - 1))
mc, _ = D.ddd(d, fm, vcov={'CRV1': 'HQ'}); R['cluster_country'] = res(mc)
print('power', R['power'], R['eu_high_vs_low'], R['cluster_country'], flush=True)

# ---------------- Tabela 21: especificações alternativas
T13 = [row('Baseline', m0, fm)]
for lbl, post in [('Post from the proposal (2023Q1)', '20230331'), ('Post from the political agreement (2023Q4)', '20231231')]:
    m, _ = D.ddd(d, fm, post=post); T13.append(row(lbl, m, fm))
_, _, f1, _, _ = D.run_matching(d, q=0.0); m, _ = D.ddd(d, f1); T13.append(row('High = any pre-announcement mention', m, f1))
_, _, f2, _, _ = D.run_matching(d, min_calls=4); m, _ = D.ddd(d, f2); T13.append(row('At least four pre-announcement calls', m, f2))
if EXCL:
    _, _, f3, _, _ = D.run_matching(d_all); m, _ = D.ddd(d_all, f3); T13.append(row('Including telecommunications', m, f3))
    d2 = d_all.copy(); tl = d2['TRBC Industry Group Name'] == TEL
    d2.loc[tl, 'Composite'] = d2.loc[tl, 'Composite'] - d2.loc[tl, 'Mineral_Copper']
    _, _, f3b, _, _ = D.run_matching(d2); m, _ = D.ddd(d2, f3b); T13.append(row('Telecommunications kept, their copper mentions not counted', m, f3b))
else:
    dn = d_all[d_all['TRBC Industry Group Name'] != TEL]
    _, _, f3, _, _ = D.run_matching(dn); m, _ = D.ddd(dn, f3); T13.append(row('Excluding telecommunications', m, f3))
same = d[d['HQ'] == d['RIC'].map(exch)]
_, _, f4, _, _ = D.run_matching(same); m, _ = D.ddd(same, f4); T13.append(row('Headquarters country = listing country', m, f4))
_, _, f5, _, _ = D.run_matching(d, caliper=None); m, _ = D.ddd(d, f5); T13.append(row('No caliper', m, f5))
# contínua, sem pareamento
s = d[d['RIC'].isin(fa.index)].join(fa[['Exposure_pre']], on='RIC')
s['X'] = (s['Exposure_pre'] - fa['Exposure_pre'].mean()) / fa['Exposure_pre'].std()
s['Post'] = (s['qkey'] >= D.POST).astype(int)
s['EUxHighxPost'] = s['EU'] * s['X'] * s['Post']; s['EUxPost'] = s['EU'] * s['Post']; s['HighxPost'] = s['X'] * s['Post']
m = pf.feols('Q_CP ~ EUxHighxPost + EUxPost + HighxPost | RIC + qkey', data=s, vcov={'CRV1': 'RIC'})
T13.append(row('Continuous exposure, unmatched', m, None, treated=np.nan, firms=len(fa)))
# sem os EUA (IRA)
m, _ = D.ddd(d, fm, extra_fe=' + HQ^Post'); T13.append(row('Country of headquarters x post fixed effects', m, fm))
fmu = fm[fm['HQ'] != 'United States of America']
m, _ = D.ddd(d[d['HQ'] != 'United States of America'], fmu); T13.append(row('US firms removed from the matched controls', m, fmu))
cls, _ = D.classify(d); fall = D.firm_table(d, cls); fall = fall[fall['HQ'] != 'United States of America']
fmx, _ = rematch_from(fall); m, _ = D.ddd(d, fmx); T13.append(row('Matching repeated without US firms', m, fmx))
# sem as produtoras (mesmo limiar)
fall = D.firm_table(d, cls); g = grp['TRBC Industry Group Name'].reindex(fall.index)
fmm, _ = rematch_from(fall[(g != 'Metals & Mining').values]); m, _ = D.ddd(d, fmm); T13.append(row('Excluding Metals & Mining firms', m, fmm))
fmb, _ = rematch_from(fall[(fall['Sector'] != 'Basic Materials').values]); m, _ = D.ddd(d, fmb); T13.append(row('Excluding the Basic Materials sector', m, fmb))
# entropy balancing
fe = f.copy()
X = pd.concat([fe[D.COVS], pd.get_dummies(fe['Sector'], dtype=float)], axis=1)
X = X.loc[:, X.loc[fe['Treated'] == 1].std() > 0]
tmean = X[fe['Treated'] == 1].mean(); w = pd.Series(0.0, index=fe.index); w[fe['Treated'] == 1] = 1.0
for cell in D.CONTROL_CELLS:
    idx = fe.index[fe['Cell'] == cell]; Z = (X.loc[idx] - tmean).values
    obj = lambda lam: np.log(np.exp(Z @ lam).sum()); grad = lambda lam: (np.exp(Z @ lam) / np.exp(Z @ lam).sum()) @ Z
    r = minimize(obj, np.zeros(Z.shape[1]), jac=grad, method='BFGS', options={'maxiter': 5000, 'gtol': 1e-10})
    ww = np.exp(Z @ r.x); w[idx] = ww / ww.sum() * (fe['Treated'] == 1).sum()
se_ = d[d['RIC'].isin(fe.index)].join(fe[['High']], on='RIC'); se_['w'] = se_['RIC'].map(w); se_ = se_[se_['w'] > 0]
se_['Post'] = (se_['qkey'] >= D.POST).astype(int); se_['EUxHighxPost'] = se_['EU'] * se_['High'] * se_['Post']
se_['EUxPost'] = se_['EU'] * se_['Post']; se_['HighxPost'] = se_['High'] * se_['Post']
me = pf.feols('Q_CP ~ EUxHighxPost + EUxPost + HighxPost | RIC + qkey', data=se_, weights='w', vcov={'CRV1': 'RIC'})
T13.append(row('Entropy balancing, all eligible firms', me, None, treated=int((fe['Treated'] == 1).sum()), firms=se_['RIC'].nunique()))
R['T13'] = pd.DataFrame(T13)
print(R['T13'].round(4).to_string(), flush=True)
# High x Post sem os EUA (pareamento refeito)
R['HxP_noUS'] = [r for r in T13 if r['spec'] == 'Matching repeated without US firms'][0]

# ---------------- Tabela 20: balanceamento
def smd(a, b, sd):
    return (a.mean() - b.mean()) / sd
fbal = f.copy(); fbal['lps'] = np.log(fbal['pscore'] / (1 - fbal['pscore']))
sect = pd.get_dummies(fbal['Sector'], dtype=float)
vars_ = pd.concat([fbal[D.COVS], fbal[['pscore']], sect], axis=1)
rows = []
tr_b = vars_[fbal['Treated'] == 1]; tr_a = vars_.loc[fm.index[fm['Treated'] == 1]]
for v in vars_.columns:
    r = dict(var=v, treated_mean=tr_a[v].mean())
    for cell in D.CONTROL_CELLS:
        cb = vars_[fbal['Cell'] == cell][v]; ca = vars_.loc[fm.index[fm['Cell'] == cell]][v]
        sd = np.sqrt((tr_b[v].var() + cb.var()) / 2)
        r[f'{cell}_before'] = (tr_b[v].mean() - cb.mean()) / sd if sd > 0 else 0
        r[f'{cell}_after'] = (tr_a[v].mean() - ca.mean()) / sd if sd > 0 else 0
    rows.append(r)
R['T12'] = pd.DataFrame(rows)
print(R['T12'].round(3).to_string(), flush=True)

# ---------------- estudo de evento
s = s0.copy()
qs = sorted(s['qkey'].unique()); k0 = '20200930'; ref = '20220630'
def lab(q): return 'early' if q < k0 else q
s['bin'] = s['qkey'].map(lab)
bins = ['early'] + [q for q in qs if q >= k0 and q != ref]
terms = []
for bn in bins:
    ind = (s['bin'] == bn).astype(int)
    s[f'T_{bn}'] = s['EU'] * s['High'] * ind; s[f'E_{bn}'] = s['EU'] * ind; s[f'H_{bn}'] = s['High'] * ind
    terms += [f'T_{bn}', f'E_{bn}', f'H_{bn}']
me_ = pf.feols('Q ~ ' + ' + '.join(terms) + ' | RIC + qkey', data=s, vcov={'CRV1': 'RIC'})
es = pd.DataFrame({'q': bins, 'b': [me_.coef()[f'T_{b}'] for b in bins], 'se': [me_.se()[f'T_{b}'] for b in bins],
                   'p': [me_.pvalue()[f'T_{b}'] for b in bins]})
R['ES'] = es
nm = list(me_.coef().index); Vv = me_._vcov
def joint(qset):
    idx = [nm.index(f'T_{q}') for q in qset]; bb = me_.coef().values[idx]; VV = Vv[np.ix_(idx, idx)]
    ch = float(bb @ np.linalg.solve(VV, bb)); return dict(chi2=ch, df=len(idx), p=stats.chi2.sf(ch, len(idx)))
pre = [q for q in bins if q != 'early' and q < ref]
ant = [q for q in bins if q != 'early' and '20220930' <= q < D.POST]
post = [q for q in bins if q != 'early' and q >= D.POST]
R['ES_joint'] = dict(pre=joint(pre), ant=joint(ant), post=joint(post))
print(es.round(3).to_string(), R['ES_joint'], flush=True)

# ---------------- wild bootstrap por país
def drop_singletons(dd):
    while True:
        n0 = len(dd)
        for c in ('RIC', 'qkey'):
            dd = dd[dd.groupby(c)[c].transform('size') > 1]
        if len(dd) == n0:
            return dd
s1 = drop_singletons(s0.copy())
fid = pd.factorize(s1['RIC'])[0]; qid = pd.factorize(s1['qkey'])[0]; cid = pd.factorize(s1['HQ'])[0]
Zd = s1[['EUxPost', 'HighxPost']].values.astype(float)
pre_ = wcr.prepare(s1['Q'].values, s1['EUxHighxPost'].values.astype(float), Zd, fid, qid, cluster=cid)
Wc = wcr.weights(pre_['G'], 9999, np.random.default_rng(20261024), kind='webb')
R['wild_country'] = dict(p=wcr.pvalue(pre_, Wc), G=pre_['G'])
print('wild', R['wild_country'])
pickle.dump(R, open(OUT, 'wb')); print('ok', OUT)
