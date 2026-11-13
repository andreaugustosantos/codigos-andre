"""
Verificações adicionais do choque chinês (Tabela 24).

  1. A alta das menções a terras raras é maior que a dos outros minerais?
  2. Tendências lineares por grupo industrial nos Painéis A e B.
Saída: resultados/china_extras.pkl e china_extras.xlsx
"""
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__))); from caminhos import *  # noqa
exec(open(_o.path.join(CODE, '14_china.py'), encoding='utf-8').read().split('# ================= Parte A')[0])
R2 = {}
dA = prep(calls); dB = prep(full)

# ---------------- 1. Especificidade
rows = []
for var in E.MINERALS:
    r = est(dA, var); pre_mean = dA.loc[(dA['T'] == 1) & (dA.Post == 0), var].mean()
    post_mean = dA.loc[(dA['T'] == 1) & (dA.Post == 1), var].mean()
    oth_pre = dA.loc[(dA['T'] == 0) & (dA.Post == 0), var].mean(); oth_post = dA.loc[(dA['T'] == 0) & (dA.Post == 1), var].mean()
    rows.append(dict(var=var, **r, exposed_pre=pre_mean, exposed_post=post_mean, other_pre=oth_pre, other_post=oth_post,
                     ratio_exposed=post_mean / pre_mean if pre_mean > 0 else np.nan,
                     b_rel_pre=r['b'] / pre_mean if pre_mean > 0 else np.nan))
R2['by_mineral'] = pd.DataFrame(rows); print(R2['by_mineral'].round(4).to_string(), flush=True)

# empilhado: uma linha por firma-trimestre-mineral; efeitos fixos de firma x mineral e trimestre x mineral
long = dA.melt(id_vars=['RIC', 'qkey', 'T', 'Post', 'TxPost'], value_vars=E.MINERALS, var_name='mineral', value_name='y')
long['fm'] = long.RIC + '_' + long.mineral; long['qm'] = long.qkey + '_' + long.mineral
rows = []
for other in [m for m in E.MINERALS if m != 'Mineral_RareEarths']:
    x = long[long.mineral.isin(['Mineral_RareEarths', other])].copy(); x['RE'] = (x.mineral == 'Mineral_RareEarths').astype(int)
    x['TxPostxRE'] = x.TxPost * x.RE
    m = pf.feols('y ~ TxPost + TxPostxRE | fm + qm', data=x, vcov={'CRV1': 'RIC'})
    rows.append(dict(other=other, b_other=m.coef()['TxPost'], diff_RE_minus_other=m.coef()['TxPostxRE'],
                     se=m.se()['TxPostxRE'], p=m.pvalue()['TxPostxRE'], N=m._N))
R2['stacked'] = pd.DataFrame(rows); print(R2['stacked'].round(4).to_string(), flush=True)

# participação: entre as firmas-trimestre com alguma menção a mineral, a de terras raras
anym = dA[dA[E.MINERALS].max(axis=1) == 1].copy()
r = est(anym, 'Mineral_RareEarths')
R2['share'] = pd.DataFrame([dict(sample='Firm-quarters with any mineral mention', **r,
                                 exposed_pre=anym.loc[(anym['T'] == 1) & (anym.Post == 0), 'Mineral_RareEarths'].mean(),
                                 exposed_post=anym.loc[(anym['T'] == 1) & (anym.Post == 1), 'Mineral_RareEarths'].mean())])
# terras raras sem cobre no mesmo trimestre (a alta não vem de firmas que passaram a falar de minerais em geral)
dA['RE_only'] = ((dA.Mineral_RareEarths == 1) & (dA[[m for m in E.MINERALS if m != 'Mineral_RareEarths']].max(axis=1) == 0)).astype(int)
R2['RE_without_other'] = pd.DataFrame([dict(**est(dA, 'RE_only'))])
print(R2['share'].round(4).to_string(), R2['RE_without_other'].round(4).to_string(), flush=True)

# ---------------- 2. Tendências lineares por grupo industrial
def with_trends(d, y):
    d = d.copy(); d['tt'] = D.qindex(d['qkey']); d['tt'] = d['tt'] - d['tt'].min()
    g = pd.get_dummies(d[IG], prefix='g', dtype=float)
    cols = []
    for c in g.columns[1:]:
        n = 'tr_' + str(len(cols)); d[n] = g[c].values * d['tt'].values; cols.append(n)
    m = pf.feols(f'{y} ~ TxPost + ' + ' + '.join(cols) + ' | RIC + qkey', data=d, vcov={'CRV1': 'RIC'})
    m2 = pf.feols(f'{y} ~ TxPost + ' + ' + '.join(cols) + ' | RIC + qkey', data=d, vcov={'CRV1': 'IGc'})
    return dict(b=m.coef()['TxPost'], se=m.se()['TxPost'], p=m.pvalue()['TxPost'], se_ind=m2.se()['TxPost'],
                p_ind=m2.pvalue()['TxPost'], N=m._N)
rows = [dict(part='A', **with_trends(dA, 'Mineral_RareEarths')), dict(part='A copper', **with_trends(dA, 'Mineral_Copper')),
        dict(part='B', **with_trends(dB, 'Q'))]
R2['trends'] = pd.DataFrame(rows); print(R2['trends'].round(4).to_string(), flush=True)
pickle.dump(R2, open(f'{RES}/china_extras.pkl', 'wb'))
with pd.ExcelWriter(f'{RES}/china_extras.xlsx') as w:
    for k, v in R2.items(): v.to_excel(w, sheet_name=k[:31], index=False)
print('ok')
