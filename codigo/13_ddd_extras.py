"""
Verificações adicionais da tripla diferença do CRMA. Mesmo desenho do 11.

  - exclui os trimestres entre o anúncio e a vigência (2022T3 a 2024T1)
  - Q médio e mediano por célula e período, com testes de diferença (Tabela 22)
  - versão colapsada: média pré e pós por firma (Bertrand, Duflo e Mullainathan, 2004)
  - painel balanceado (firmas com Q em todos os trimestres de 2020T3 a 2026T2)
  - tamanho e ROA de 2021 interagidos com Post
  - tabela do estudo de evento com testes conjuntos (Tabela 23)
Saídas: resultados/ddd_extras.pkl e ddd_extras.xlsx
"""
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__))); from caminhos import *  # noqa
import pickle, warnings
import numpy as np, pandas as pd, pyfixest as pf
from scipy import stats
import statsmodels.formula.api as smf
warnings.filterwarnings('ignore')
import ddd_core as D

TEL = 'Telecommunications Services'
ANT0, ANT1 = '20220930', '20240331'          # anúncio (set/2022) até o trimestre antes da vigência
p = pd.read_pickle(f'{R02}/painel_firma_trimestre.pkl')
d = D.build_panel(p); d = d[d['TRBC Industry Group Name'] != TEL].copy()
fa, f, fm, pairs, thr = D.run_matching(d)
m0, s0 = D.ddd(d, fm)
R = {}

def res(m, k='EUxHighxPost'):
    return dict(b=m.coef()[k], se=m.se()[k], p=m.pvalue()[k], N=m._N,
                HxP=m.coef().get('HighxPost', np.nan), HxP_p=m.pvalue().get('HighxPost', np.nan))

rows = [dict(spec='Baseline (Table 8, column 1)', **res(m0), firms=s0.RIC.nunique())]
# ---------------- sem os trimestres entre o anúncio e a vigência
dn = d[~d['qkey'].between(ANT0, ANT1)]
m, s = D.ddd(dn, fm); rows.append(dict(spec='Donut: 2022Q3 to 2024Q1 excluded', **res(m), firms=s.RIC.nunique()))
# variante: só o período pré-anúncio como base, mantendo a antecipação como período próprio
s = s0.copy(); s['Ant'] = s['qkey'].between(ANT0, ANT1).astype(int)
s['EUxHighxAnt'] = s.EU * s.High * s.Ant; s['EUxAnt'] = s.EU * s.Ant; s['HighxAnt'] = s.High * s.Ant
m = pf.feols('Q ~ EUxHighxPost + EUxPost + HighxPost + EUxHighxAnt + EUxAnt + HighxAnt | RIC + qkey', data=s, vcov={'CRV1': 'RIC'})
rows.append(dict(spec='Anticipation period modelled separately (post)', **res(m), firms=s.RIC.nunique()))
rows.append(dict(spec='Anticipation period modelled separately (anticipation)', **res(m, 'EUxHighxAnt'), firms=s.RIC.nunique()))
# ---------------- tamanho e ROA de 2021 interagidos com Post
s = s0.join(fm[['lnMktCap_pre', 'lnTA_pre', 'ROA_pre', 'Leverage_pre']], on='RIC')
for c in ['lnMktCap_pre', 'lnTA_pre', 'ROA_pre', 'Leverage_pre']:
    s[c + 'xPost'] = (s[c] - s[c].mean()) * s.Post
m = pf.feols('Q ~ EUxHighxPost + EUxPost + HighxPost + lnMktCap_prexPost + ROA_prexPost | RIC + qkey', data=s, vcov={'CRV1': 'RIC'})
rows.append(dict(spec='Size2021 x Post and ROA2021 x Post', **res(m), firms=s.RIC.nunique()))
m = pf.feols('Q ~ EUxHighxPost + EUxPost + HighxPost + lnMktCap_prexPost + lnTA_prexPost + ROA_prexPost + Leverage_prexPost | RIC + qkey', data=s, vcov={'CRV1': 'RIC'})
rows.append(dict(spec='All 2021 covariates x Post', **res(m), firms=s.RIC.nunique()))
# ---------------- painel balanceado na janela do estudo de evento
win = s0[s0.qkey.between('20200930', '20260630')]
nq = win['qkey'].nunique(); full_firms = win.groupby('RIC').qkey.nunique(); bal = full_firms.index[full_firms == nq]
fb = fm[fm.index.isin(bal)]
m, s = D.ddd(d[d.qkey.between('20200930', '20260630')], fb)
rows.append(dict(spec=f'Balanced panel 2020Q3 to 2026Q2 (matched firms kept)', **res(m), firms=s.RIC.nunique(),
                 treated=int(fb.Treated.sum())))
db = d[d.RIC.isin(d[d.qkey.between('20200930', '20260630')].groupby('RIC').qkey.nunique().pipe(lambda x: x.index[x == nq]))]
fa_b, f_b, fm_b, _, _ = D.run_matching(db)
m, s = D.ddd(db[db.qkey.between('20200930', '20260630')], fm_b)
rows.append(dict(spec='Balanced panel 2020Q3 to 2026Q2 (matching repeated)', **res(m), firms=s.RIC.nunique(), treated=int(fm_b.Treated.sum())))
# ---------------- High x Post sem Metals & Mining (mesmo pareamento, sem as firmas do grupo)
mm_ = d.drop_duplicates('RIC').set_index('RIC')['TRBC Industry Group Name'].eq('Metals & Mining')
m, s = D.ddd(d, fm[~fm.index.isin(mm_[mm_].index)])
rows.append(dict(spec='Metals & Mining firms dropped from the matched sample', **res(m), firms=s.RIC.nunique()))
R['rob'] = pd.DataFrame(rows)
for c in ['treated']:
    if c not in R['rob']: R['rob'][c] = np.nan
print(R['rob'].round(4).to_string(), flush=True)

# ---------------- versão colapsada (média pré e pós por firma)
rows = []
for lbl, pre_end in [('Pre = up to 2024Q1', ANT1), ('Pre = up to 2022Q2 (anticipation excluded)', '20220630')]:
    s = s0.copy()
    s = s[(s.qkey <= pre_end) | (s.qkey >= D.POST)]
    g = s.groupby(['RIC', 'Post']).Q.mean().unstack()
    g = g.dropna().rename(columns={0: 'pre', 1: 'post'}); g['dQ'] = g.post - g.pre
    g = g.join(fm[['EU', 'High']])
    o = smf.ols('dQ ~ EU * High', data=g).fit(cov_type='HC1')
    rows.append(dict(spec=lbl, b=o.params['EU:High'], se=o.bse['EU:High'], p=o.pvalues['EU:High'],
                     HxP=o.params['High'], HxP_p=o.pvalues['High'], firms=len(g)))
R['collapsed'] = pd.DataFrame(rows); print(R['collapsed'].round(4).to_string(), flush=True)

# ---------------- Q por célula e período (Tabela 22)
s = s0.copy(); s['Cell'] = s.RIC.map(fm['Cell'])
s['Period'] = np.where(s.Post == 1, 'Post (2024Q2-2026Q2)', np.where(s.qkey <= '20220630', 'Pre (to 2022Q2)', 'Anticipation (2022Q3-2024Q1)'))
tab = s.groupby(['Cell', 'Period']).Q.agg(['mean', 'median', 'size']).reset_index()
tab['firms'] = s.groupby(['Cell', 'Period']).RIC.nunique().values
# testes: diferença de média entre as tratadas e cada célula de controle, em cada período, EP por firma
tests = []
for per in s.Period.unique():
    x = s[s.Period == per].copy()
    for c in D.CONTROL_CELLS:
        y = x[x.Cell.isin(['EU x High (tratadas)', c])].copy(); y['T'] = (y.Cell == 'EU x High (tratadas)').astype(int)
        o = pf.feols('Q ~ T', data=y, vcov={'CRV1': 'RIC'})
        mw = stats.mannwhitneyu(y.groupby('RIC').Q.median()[y.groupby('RIC').T.first() == 1],
                                y.groupby('RIC').Q.median()[y.groupby('RIC').T.first() == 0])
        tests.append(dict(Period=per, vs=c, diff_mean=o.coef()['T'], se=o.se()['T'], p=o.pvalue()['T'], p_median_firm=mw.pvalue))
# DiD das médias (pré até 2022T2 contra pós): cálculo direto, igual ao colapsado sem efeitos fixos
mean = tab.pivot(index='Cell', columns='Period', values='mean')
R['C5'] = tab; R['C5_tests'] = pd.DataFrame(tests); R['C5_means'] = mean
print(tab.round(3).to_string()); print(R['C5_tests'].round(3).to_string(), flush=True)

# ---------------- estudo de evento (Tabela 23, coeficientes do 11)
DD = pickle.load(open(f'{RES}/ddd_nt.pkl', 'rb'))
R['ES_table'] = DD['ES']; R['ES_joint'] = DD['ES_joint']
pickle.dump(R, open(f'{RES}/ddd_extras.pkl', 'wb'))
with pd.ExcelWriter(f'{RES}/ddd_extras.xlsx') as w:
    for k, v in R.items():
        if isinstance(v, pd.DataFrame): v.to_excel(w, sheet_name=k[:31])
print('ok')
