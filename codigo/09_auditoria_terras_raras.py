"""
Usa a classificação manual das 57 firmas-trimestre com terras raras nos EUA (Tabela 18, linhas 18 e 19).

Entrada: dados/auditoria_terras_raras_EUA_codificada.csv (RIC, qkey, Tipo, Motivo), feita a partir da planilha do 03.
Tipo: I = insumo ou risco de oferta; P = produto (a firma produz terras raras); X = menção incidental.
  linha 18: menções incidentais (X) viram zero
  linha 19: só as menções de insumo ou risco (I) contam
A planilha não está no repositório; está disponível com o autor, sob pedido.
Saída: resultados/auditoria.pkl
"""
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__))); from caminhos import *  # noqa
import importlib.util, pickle, warnings
import numpy as np, pandas as pd
warnings.filterwarnings('ignore')
spec = importlib.util.spec_from_file_location('e', EST_PY); E = importlib.util.module_from_spec(spec); spec.loader.exec_module(E)
import wcr
cod = pd.read_csv(f'{DADOS}/auditoria_terras_raras_EUA_codificada.csv', dtype={'qkey': str})
p = pd.read_pickle(f'{R02}/painel_firma_trimestre.pkl')
us = E.subset(E.est_sample(p, 'Q_CP', 'V2'), 'US').merge(cod[['RIC', 'qkey', 'Tipo']], on=['RIC', 'qkey'], how='left')
assert us['Tipo'].notna().sum() == int(us['Mineral_RareEarths'].sum()) == len(cod), 'a codificação não cobre as firmas-trimestre com menção'
us['RE_semX'] = ((us['Mineral_RareEarths'] == 1) & (us['Tipo'] != 'X')).astype(int)
us['RE_I'] = ((us['Mineral_RareEarths'] == 1) & (us['Tipo'] == 'I')).astype(int)

def drop_singletons(dd):
    while True:
        n0 = len(dd)
        for c in ('RIC', 'qkey'): dd = dd[dd.groupby(c)[c].transform('size') > 1]
        if len(dd) == n0: return dd
rows = []
for v, lab in [('Mineral_RareEarths', 'All mentions (row 1)'), ('RE_semX', '(18) Incidental mentions set to zero'),
               ('RE_I', '(19) Input or supply-risk mentions only')]:
    m = E.fit_q(us, v); sd = us[v].astype(float).std(ddof=0)
    dd = us.copy(); dd['MR'] = E.zscore(dd[v].astype(float)); dd = drop_singletons(dd)
    fid = pd.factorize(dd['RIC'])[0]; qid = pd.factorize(dd['qkey'])[0]
    pre = wcr.prepare(dd['Q'].values, dd['MR'].values, dd[['Size', 'Leverage', 'ROA']].values, fid, qid)
    pw = wcr.pvalue(pre, wcr.weights(pre['G'], 9999, np.random.default_rng(20261024)))
    rows.append(dict(spec=lab, b=m.coef()['MR'], se=m.se()['MR'], p=m.pvalue()['MR'], p_wild=pw, N=m._N,
                     quarters=int(us[v].sum()), firms=int(us.loc[us[v] == 1, 'RIC'].nunique()), per_mention=m.coef()['MR'] / sd))
R = pd.DataFrame(rows)
R.attrs['tipos'] = cod['Tipo'].value_counts().to_dict()
print(cod['Tipo'].value_counts().to_dict()); print(R.round(4).to_string())
pickle.dump(R, open(f'{RES}/auditoria.pkl', 'wb'))
