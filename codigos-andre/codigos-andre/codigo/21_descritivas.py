"""
Tabela 2: estatísticas descritivas (Painel A), por painel regional (Painel B) e correlações (Painel C).
Amostra: firmas não financeiras, firmas-trimestre com earnings call.
Saída: resultados/tabelas/tab0_descritivas_linhas.tex e resultados/descritivas.xlsx
"""
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__))); from caminhos import *  # noqa
import importlib.util, warnings
import pandas as pd
warnings.filterwarnings('ignore')
spec = importlib.util.spec_from_file_location('e', EST_PY); E = importlib.util.module_from_spec(spec); spec.loader.exec_module(E)

p = pd.read_pickle(f'{R02}/painel_firma_trimestre.pkl')
b = E.est_sample(p, 'Q_CP', 'V2')

def mm(v, k=3): return f"{v:.{k}f}".replace('-', '$-$')

LAB = [('Q', "Tobin's Q (Chung--Pruitt)"), ('lnMktCap', 'Log market capitalisation'), ('Leverage', 'Leverage'), ('ROA', 'ROA')]
if SIZE == 'lnTA':  # controle de tamanho principal
    LAB.insert(2, ('lnTA', 'Log total assets'))
MIN = [('Mineral_Lithium', 'Lithium'), ('Mineral_Cobalt', 'Cobalt'), ('Mineral_Nickel', 'Nickel'),
       ('Mineral_Copper', 'Copper'), ('Mineral_RareEarths', 'Rare Earths'), ('Composite', 'Composite')]
L = []
def stats_row(v, lab):
    x = b[v].astype(float)
    return f"{lab} & {len(x):,} & {mm(x.mean())} & {mm(x.std())} & {mm(x.quantile(.25))} & {mm(x.median())} & {mm(x.quantile(.75))} \\\\"
for v, lab in LAB: L.append(stats_row(v, lab))
for v, lab in MIN: L.append(stats_row(v, r'\quad ' + lab))
for pn in E.PANELS:
    x = E.subset(b, pn); anyc = (x[E.MINERALS].sum(axis=1) > 0).mean() * 100
    L.append(f"{pn} & {len(x):,} & {x.RIC.nunique():,} & {x.Q.mean():.2f} & {x.Q.std():.2f} & {anyc:.1f} & {x.Mineral_RareEarths.mean() * 100:.2f} \\\\")
# Painel C: o tamanho entra como na Equação (6) (log do ativo total)
V = ['Q', SIZE, 'Leverage', 'ROA', 'Composite', 'Mineral_RareEarths', 'Mineral_Copper']
NM = ["(1) Tobin's Q", '(2) Log total assets' if SIZE == 'lnTA' else '(2) Log market cap.', '(3) Leverage', '(4) ROA', '(5) Composite', '(6) Rare earths', '(7) Copper']
C = b[V].astype(float).corr()
for i, v in enumerate(V):
    cells = [mm(C.iloc[i, j]) if j < i else ('1' if j == i else '') for j in range(6)]
    L.append(f"{NM[i]} & " + " & ".join(cells) + r" \\")
open(f'{TEX}/tab0_descritivas_linhas.tex', 'w', encoding='utf-8').write('\n'.join(L) + '\n')
with pd.ExcelWriter(f'{RES}/descritivas.xlsx') as w:
    b[[v for v, _ in LAB + MIN]].astype(float).describe(percentiles=[.25, .5, .75]).T.to_excel(w, sheet_name='painelA')
    C.to_excel(w, sheet_name='correlacoes')
print('\n'.join(L))
