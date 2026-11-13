"""
Recalcula, linha a linha, as colunas calculadas das 13 planilhas LSEG_ChungPruitt_*.xlsx e compara com o que está
gravado nelas. Não altera nada.

Fórmulas (Tabela 12 da dissertação):
  PS   = K - L - M      (L e M vazios = 0; K vazio => PS = 0)
  DEBT = (H - I) + J    (precisa de H, I e J)
  Q    = (F + PS + DEBT) / G       Q simplificado = (F + N) / G
  alavancagem = N / G              ROA = O / G
"""
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__))); from caminhos import *  # noqa
import glob, os
import numpy as np, pandas as pd

TOL = 1e-6  # tolerância relativa
num = lambda s: pd.to_numeric(s, errors='coerce')
linhas, problemas = [], []
for f in sorted(glob.glob(os.path.join(FIN, 'LSEG_ChungPruitt_*.xlsx'))):
    d = pd.read_excel(f, sheet_name='Extraction')
    F, G, H, I, J, K, L, M, N, O = [num(d[c]) for c in d.columns[5:15]]
    PS = (K - L.fillna(0) - M.fillna(0)).where(K.notna(), 0)
    DEBT = H - I + J
    ok = F.notna() & G.notna() & (G != 0) & DEBT.notna()
    calc = {'Preferred Stock (deduzido)': PS, 'DEBT Chung-Pruitt': DEBT.where(ok | DEBT.notna()),
            'Tobins Q (Chung-Pruitt)': ((F + PS + DEBT) / G).where(ok),
            'Tobins Q (simplificado)': (F + N) / G, 'Leverage': N / G, 'ROA': O / G}
    nome = os.path.basename(f).replace('LSEG_ChungPruitt_', '').replace('.xlsx', '')
    r = dict(arquivo=nome, linhas=len(d), com_Q=int(num(d['Tobins Q (Chung-Pruitt)']).notna().sum()))
    for col, v in calc.items():
        x = num(d[col])
        if col == 'Preferred Stock (deduzido)': x = x.fillna(0)  # linhas 'PS SUPOSTO ZERO' vêm em branco
        so_um_lado = int((v.notna() != x.notna()).sum())
        dif = ((v - x).abs() / np.maximum(1, x.abs())).where(v.notna() & x.notna())
        ruins = int((dif > TOL).sum())
        r[{'Preferred Stock (deduzido)': 'PS', 'DEBT Chung-Pruitt': 'DEBT', 'Tobins Q (Chung-Pruitt)': 'Q C&P', 'Tobins Q (simplificado)': 'Q simpl.'}.get(col, col)] = 'ok' if (so_um_lado == 0 and ruins == 0) else f'{ruins} dif, {so_um_lado} ausência'
        if ruins or so_um_lado:
            problemas.append((nome, col, ruins, so_um_lado))
    r['PS > 0 (firmas)'] = int(d.loc[PS > 1, 'RIC'].nunique())
    linhas.append(r)

T = pd.DataFrame(linhas)
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 20)
print(T.to_string(index=False))
print(f"\nTotal: {T.linhas.sum():,} linhas, {T.com_Q.sum():,} com Q.")
print('RESULTADO: todas as colunas calculadas conferem' if not problemas else f'RESULTADO: {len(problemas)} diferenças: {problemas}')
