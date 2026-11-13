"""
Confere, linha por linha, os números das tabelas da dissertação contra os resultados dos scripts 02 a 23.
Para cada linha esperada, procura no .tex da dissertação uma linha com as mesmas últimas células (o rótulo pode mudar).

Uso: python 24_conferencia.py [pasta com as tabelas .tex da dissertação]
Saída: relatório na tela e em resultados/conferencia.txt. Para com erro se alguma linha não bater.
"""
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__))); from caminhos import *  # noqa
import re, pickle, sys
import numpy as np, pandas as pd

DIS = sys.argv[1] if len(sys.argv) > 1 else _o.path.join(ROOT, 'tabelas_dissertacao')
LOG = []; FALHAS = []; EXP = {}

def st(p): return '***' if p < .01 else '**' if p < .05 else '*' if p < .1 else ''
def mm(v, k=4): return f"{v:.{k}f}".replace('-', '$-$')
def n(x): return f"{int(x):,}"
def norm(s): return re.sub(r'\s+', '', s)

def cells_of(path):
    out = []
    for line in open(path, encoding='utf-8'):
        if '&' not in line or line.strip().startswith('%'): continue
        line = line.strip()
        line = re.sub(r'\\\\\s*$', '', line)
        out.append([norm(c) for c in re.split(r'(?<!\\)&', line)])  # não separa no \& dos rótulos
    return out

def check(table, expected, label):
    """expected: lista de linhas; cada linha é a lista das últimas células esperadas."""
    EXP.setdefault(table, []).append((label, [list(e) for e in expected]))
    rows = cells_of(f'{DIS}/{table}.tex'); bad = []
    for e in expected:
        e = [norm(c) for c in e]
        if not any(len(r) >= len(e) and r[-len(e):] == e for r in rows): bad.append(' & '.join(e))
    msg = f"{table:22s} {label:42s} {len(expected) - len(bad):3d}/{len(expected):<3d} " + ('OK' if not bad else 'DIFERENÇAS')
    LOG.append(msg); print(msg)
    for b in bad: LOG.append('      não encontrada: ' + b); print('      não encontrada:', b)
    if bad: FALHAS.append((table, label))

def same_numeric(table, generated, label, skip_first=1):
    """Compara as linhas numéricas de uma tabela gerada pelo 20 ou 21 com a da dissertação."""
    isnum = lambda c: re.fullmatch(r'\(?(\$-\$)?[\d,]*\.?\d+\)?\**', c) is not None
    rows = [r[skip_first:] for r in cells_of(generated) if any(isnum(c) for c in r[skip_first:])]
    check(table, rows, label)

PAN = ['Total', 'US', 'UK', 'Nordic', 'Canada', 'Europe']
X1 = pd.read_excel(f'{RES}/resultados_robustez.xlsx', sheet_name=None)
X3 = pd.read_excel(f'{RES}/resultados_valuation.xlsx', sheet_name=None)
O4 = pickle.load(open(f'{RES}/tempo_q.pkl', 'rb'))
D4 = pickle.load(open(f'{RES}/d4x.pkl', 'rb'))
DD = pickle.load(open(f'{RES}/ddd_nt.pkl', 'rb'))
EU = pickle.load(open(f'{RES}/europe.pkl', 'rb'))
CH = pickle.load(open(f'{RES}/china.pkl', 'rb'))
LO = pickle.load(open(f'{RES}/china_loio.pkl', 'rb'))

# ---------------- Tabelas geradas diretamente pelos scripts 20 e 21
same_numeric('tab0_descritivas', f'{TEX}/tab0_descritivas_linhas.tex', 'descritivas, painéis A a C')
for t in ['tab1_amostra', 'tab2a_validacao', 'tab2b_validacao', 'tab3_setores']:
    same_numeric(t, f'{TEX}/{t}.tex', 'números (20_tabelas_base.py)')

# ---------------- Tabela 6 (tab4_valuation) e Tabela 17 (tab4r_robustez)
def six(df, var, vcol='Var', pcol='Painel', b='beta'):
    d = df[df[vcol] == var].set_index(pcol).reindex(PAN)
    return [[mm(r[b]) + st(r.p) if pd.notna(r[b]) else '--' for _, r in d.iterrows()],
            [f"({r.se:.4f})" if pd.notna(r[b]) else '' for _, r in d.iterrows()]]
def obs(df, var, vcol='Var', pcol='Painel'):
    d = df[df[vcol] == var].set_index(pcol).reindex(PAN)
    return [n(x) if pd.notna(x) else '--' for x in d.N]
T6 = X3['T6']
exp = []
for v in ['Mineral_Lithium', 'Mineral_Cobalt', 'Mineral_Nickel', 'Mineral_Copper', 'Mineral_RareEarths', 'Composite', 'Cotton']:
    exp += six(T6, v)
exp += [obs(T6, 'Mineral_Lithium'), [n(x) for x in T6[T6.Var == 'Mineral_Lithium'].set_index('Painel').loc[PAN].firms], obs(T6, 'Composite')]
check('tab4_valuation', exp, 'Tabela 6 (05_valuation.py)')
T11 = X3['T11']
for k in 'ABCD':
    d = T11[T11.Painel_tab == k]
    check('tab4r_robustez', six(d, 'Mineral_RareEarths') + six(d, 'Composite') + [obs(d, 'Mineral_RareEarths')], f'Painel {k} (05_valuation.py)')
M2 = X3['M2_pais']; e = []
for v in ['Mineral_RareEarths', 'Composite']:
    for pn in PAN:
        r = (M2[(M2.Var == v) & (M2.Painel == pn)] if pn in ['Total', 'Nordic', 'Europe'] else T6[(T6.Var == v) & (T6.Painel == pn)]).iloc[0]
        e.append(dict(Var=v, Painel=pn, beta=r.beta, se=r.se, p=r.p, N=r.N))
e = pd.DataFrame(e)
check('tab4r_robustez', six(e, 'Mineral_RareEarths') + six(e, 'Composite') + [obs(e, 'Mineral_RareEarths')], 'Painel E (05_valuation.py)')
Q = O4['quarterly'].rename(columns={'b': 'beta'})
check('tab4r_robustez', six(Q, 'Mineral_RareEarths', 'var', 'panel') + six(Q, 'Composite', 'var', 'panel') + [obs(Q, 'Mineral_RareEarths', 'var', 'panel')], 'Painel F (07_tempo_q.py)')

# ---------------- Tabela de produtoras (tabH2_produtoras)
exp = []
for _, r in X3['M6_produtoras'].iterrows():
    exp.append([mm(r.b_consumidoras) + st(r.p_c), mm(r.b_produtoras) + st(r.p_p), mm(r.dif_produtoras) + st(r.p_dif), f"{r.p_dif_wild:.3f}", str(int(r.prod_com_variacao))])
    exp.append([f"({r.se_c:.4f})", f"({r.se_p:.4f})", f"({r.se_dif:.4f})", '', ''])
check('tabH2_produtoras', exp, 'produtoras (05_valuation.py)')

# ---------------- Tabela 16 (tab7_leave_one_out)
L = X1['M3_LOO_por_mencao']
exp = []
for _, r in L.iterrows():
    exp.append([mm(r.beta) + st(r.p), f"({r.se:.4f})", f"{r.por_mencao:.2f}", n(r.N)])
check('tab7_leave_one_out', exp, 'β, EP, por menção, obs. (06_robustez_q.py)')

# ---------------- Tabela 18 (tabC_rare_extra)
us = lambda df, **k: df[(df.MineralRisk == 'Rare Earths') & (df.Painel == 'US')]
r1 = T6[(T6.Var == 'Mineral_RareEarths') & (T6.Painel == 'US')].iloc[0]
fe = us(X1['M2_FE_setor']).set_index('Spec')
nc = X1['m3_m4_m6']; nc = nc[(nc.Teste == 'm4 Sem controles') & (nc.MineralRisk == 'Rare Earths') & (nc.Painel == 'US')].iloc[0]
ll = us(X1['M4a_leads_lags']).iloc[0]; fd = us(X1['M4a_primeiras_dif']).iloc[0]
def c(b, s, p, N=None): return [mm(b) + st(p), f"({s:.4f})"] + ([n(N)] if N is not None else [''])
exp = [c(r1.beta, r1.se, r1.p, r1.N), c(fe.loc['Setor econ. x trim.'].beta, fe.loc['Setor econ. x trim.'].se, fe.loc['Setor econ. x trim.'].p, fe.loc['Setor econ. x trim.'].N),
       c(fe.loc['Grupo ind. x trim.'].beta, fe.loc['Grupo ind. x trim.'].se, fe.loc['Grupo ind. x trim.'].p, fe.loc['Grupo ind. x trim.'].N),
       c(nc.beta, nc.se, nc.p, nc.N), c(ll.b_lag, ll.se_lag, ll.p_lag, ll.N), c(ll.b_t, ll.se_t, ll.p_t), c(ll.b_lead, ll.se_lead, ll.p_lead),
       c(fd.beta, fd.se, fd.p, fd.N)]
for k in ['(7)', '(8)', '(9)', '(10)']:
    r = D4[D4.spec.str.startswith(k)].iloc[0]; exp.append(c(r.b, r.se, r.p, r.N))
lg = O4['lags']; lg = lg[(lg['var'] == 'Mineral_RareEarths') & (lg.panel == 'US')].set_index('k')
for k in range(-3, 4):
    r = lg.loc[k]; exp.append(c(r.b, r.se, r.p, r.N))
check('tabC_rare_extra', exp, 'linhas 1 a 17 (05, 06, 07, 08)')
per = [f"(per mention: {lg.loc[k].per_mention:.2f})" for k in range(-3, 4)]
t = norm(open(f'{DIS}/tabC_rare_extra.tex', encoding='utf-8').read()); bad = [x for x in per if norm(x) not in t]
LOG.append(f"{'tabC_rare_extra':22s} {'por menção, linhas 11 a 17':42s} {7 - len(bad):3d}/7   " + ('OK' if not bad else 'DIFERENÇAS')); print(LOG[-1])
if bad: FALHAS.append(('tabC_rare_extra', 'por menção'))

# ---------------- Tabela 8 (tab8_ddd), Tabela 20 (tab9_psm_balance), Tabela 21 (tab10_ddd_robustez)
F = DD['T7_full']
def drow(pref):
    return [[mm(r[pref + '_coef']) + st(r[pref + '_pvalue']) for _, r in F.iterrows()], [f"({r[pref + '_se']:.4f})" for _, r in F.iterrows()]]
exp = drow('EUxHighxPost') + drow('EUxPost') + drow('HighxPost') + [[str(int(x)) for x in F.treated], [n(x) for x in F.firms], [n(x) for x in F.N]]
check('tab8_ddd', exp, 'colunas 1 a 7 (11_ddd_crma.py)')
B = DD['T12']; exp = [[f"{v:.3f}".replace('-', '$-$') for v in r.values[1:]] for _, r in B.iterrows()]
check('tab9_psm_balance', exp, 'balanceamento (11_ddd_crma.py)')
T13 = DD['T13']; exp = []
for _, r in T13.iterrows():
    exp.append([f"{mm(r.b)}{st(r.p)} ({r.se:.4f})", str(int(r.treated)) if pd.notna(r.treated) else '--', n(r.firms), n(r.N)])
for k in ['main', 'eb']:
    r = EU[k]; exp.append([f"{mm(r['b'])}{st(r['p'])} ({r['se']:.4f})", str(r['treated']), n(r['firms']), n(r['N'])])
check('tab10_ddd_robustez', exp, '16 linhas + Europa (11 e 12)')

# ---------------- Tabela 9 (tabE_china)
A = CH['A']; Bq = CH['B']
def cr(r): return [f"{mm(r.b)}{st(r.p)} ({r.se:.4f})", str(int(r.treated)), n(r.firms), n(r.N)]
a = A[A['var'] == 'Mineral_RareEarths']
exp = [cr(r) for _, r in a.iterrows()] + [cr(r) for _, r in Bq.iterrows()]
la = LO[LO.part == 'A']; exp.append([f"{mm(la.b.min(), 3)}to{mm(la.b.max(), 3)}", '', '', ''])
r = LO[(LO.part == 'B') & (LO.excluded == 'Aerospace & Defense')].iloc[0]; exp.append(cr(r))
check('tabE_china', exp, 'Painéis A e B (14 e 15)')
o = A[(A.spec == 'Main (narrow)') & (A['var'] != 'Mineral_RareEarths')].set_index('var')
txt = [f"lithium {mm(o.loc['Mineral_Lithium'].b)}{st(o.loc['Mineral_Lithium'].p)}", f"cobalt {mm(o.loc['Mineral_Cobalt'].b)}{st(o.loc['Mineral_Cobalt'].p)}",
       f"nickel {mm(o.loc['Mineral_Nickel'].b)}{st(o.loc['Mineral_Nickel'].p)}", f"copper {mm(o.loc['Mineral_Copper'].b)}{st(o.loc['Mineral_Copper'].p)}",
       f"$p = {CH['A_wild']['p_wild_ind']:.3f}$", f"$p = {CH['A_ri']['p_ri']:.3f}$", f"$p = {CH['B_wild']['p_wild_ind']:.3f}$", f"$p = {CH['B_ri']['p_ri']:.3f}$"]
t = norm(open(f'{DIS}/tabE_china.tex', encoding='utf-8').read()); bad = [x for x in txt if norm(x) not in t]
LOG.append(f"{'tabE_china':22s} {'outros minerais e p de bootstrap/RI':42s} {len(txt) - len(bad):3d}/{len(txt):<3d} " + ('OK' if not bad else 'DIFERENÇAS: ' + ' | '.join(bad))); print(LOG[-1])
if bad: FALHAS.append(('tabE_china', 'notas'))

LOG.append('\nRESULTADO: ' + ('todas as linhas conferem' if not FALHAS else f'{len(FALHAS)} blocos com diferenças: {FALHAS}'))
print(LOG[-1])
open(f'{RES}/conferencia.txt', 'w', encoding='utf-8').write('\n'.join(LOG) + '\n')
pickle.dump(EXP, open(f'{RES}/conferencia_linhas.pkl', 'wb'))  # linhas esperadas, para consulta
sys.exit(1 if FALHAS else 0)
