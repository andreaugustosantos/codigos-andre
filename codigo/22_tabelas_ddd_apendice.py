"""
Tabelas do Apêndice E que saem do 11 e do 13.
  tab11_ddd_medias.tex     Tabela 22   Q médio e mediano por célula e período
  tab12_ddd_evento.tex     Tabela 23   coeficientes do estudo de evento e testes conjuntos
  tab10_bloco_extra.tex    Tabela 21   últimas linhas (antecipação, colapsado, balanceado)
"""
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__))); from caminhos import *  # noqa
from estilo_tabelas import padroniza
import pickle
import numpy as np, pandas as pd
R = pickle.load(open(f'{RES}/ddd_extras.pkl', 'rb'))

def st(p): return '***' if p < .01 else '**' if p < .05 else '*' if p < .1 else ''
def mm(v, k=2):
    s = f"{v:.{k}f}"
    return (s[1:] if float(s) == 0 else s).replace('-', '$-$')  # sem "-0.00"

# ---------------- Tabela de médias por célula e período
C = R['C5']; T = R['C5_tests']
PER = ['Pre (to 2022Q2)', 'Anticipation (2022Q3-2024Q1)', 'Post (2024Q2-2026Q2)']
CELL = [('EU x High (tratadas)', 'EU, high exposure (treated)'), ('EU x Low', 'EU, low exposure'),
        ('Não-UE x High', 'Non-EU, high exposure'), ('Não-UE x Low', 'Non-EU, low exposure')]
L = [r"\begin{table}[H]", r"  \centering", r"  \caption{Tobin's Q by Group and Period in the Matched Sample}", r"  \label{tab:ddd-means}",
     r"  \begin{threeparttable}", r"    \small", r"    \setlength{\tabcolsep}{4pt}", r"    \begin{tabular}{lcccc}", r"      \toprule",
     r"      & \makecell{Pre-announcement\\ (to 2022Q2)} & \makecell{Anticipation\\ (2022Q3--2024Q1)} & \makecell{Post\\ (2024Q2--2026Q2)} & Firms \\",
     r"      \midrule", r"      \multicolumn{5}{l}{\textit{Panel A: Mean (median) Tobin's Q}} \\"]
for k, lab in CELL:
    x = C[C.Cell == k].set_index('Period')
    L.append(f"      {lab} & " + " & ".join(f"{x.loc[p, 'mean']:.2f} ({x.loc[p, 'median']:.2f})" for p in PER) + f" & {int(x['firms'].max())} \\\\")
L += [r"      \midrule", r"      \multicolumn{5}{l}{\textit{Panel B: Treated minus each comparison group, difference in means}} \\"]
for k, lab in CELL[1:]:
    x = T[T.vs == k].set_index('Period')
    L.append(f"      {lab} & " + " & ".join(f"{mm(x.loc[p, 'diff_mean'])}{st(x.loc[p, 'p'])} ({x.loc[p, 'se']:.2f})" for p in PER) + r" & \\")
m = C.pivot(index='Cell', columns='Period', values='mean')
dd = lambda p: (m.loc['EU x High (tratadas)', p] - m.loc['EU x Low', p] - m.loc['Não-UE x High', p] + m.loc['Não-UE x Low', p])
raw = dd(PER[2]) - dd(PER[0])
L += [r"      \bottomrule", r"    \end{tabular}", r"    \begin{tablenotes}", r"      \small",
      r"      \item \textit{Note:} Matched sample of Table~\ref{tab:ddd}, column (1); firm-quarter means and medians of Chung and Pruitt's Q. "
      r"Panel B: differences in means between the treated firms and each comparison group, from a regression of Q on a treatment indicator within each period, "
      f"with firm-clustered standard errors in parentheses. The triple difference of the raw means between the post and the pre-announcement periods is {mm(raw)}. "
      r"Mann--Whitney tests on the firm medians give the same signs. * $p < 0.10$, ** $p < 0.05$, *** $p < 0.01$.",
      r"    \end{tablenotes}", r"  \end{threeparttable}", r"\end{table}"]
open(f'{TEX}/tab11_ddd_medias.tex', 'w', encoding='utf-8').write(padroniza('\n'.join(L) + '\n'))

# ---------------- Tabela do estudo de evento
ES = R['ES_table']; J = R['ES_joint']
es = ES[ES.q != 'early'].copy(); es['lab'] = [f"{q[:4]}Q{(int(q[4:6]) - 1) // 3 + 1}" for q in es.q]
cells = [f"{l} & {mm(b, 3)}{st(p)} ({s:.3f})" for l, b, s, p in zip(es.lab, es.b, es.se, es.p)]
cells.insert(7, r"2022Q2 & \multicolumn{1}{c}{reference}")
early = ES[ES.q == 'early'].iloc[0]
cells.insert(0, f"To 2020Q2 (pooled) & {mm(early.b, 3)}{st(early.p)} ({early.se:.3f})")
half = (len(cells) + 1) // 2
L = [r"\begin{table}[H]", r"  \centering", r"  \caption{Event Study around the CRMA: Coefficients and Joint Tests}", r"  \label{tab:ddd-es}",
     r"  \begin{threeparttable}", r"    \small", r"    \setlength{\tabcolsep}{5pt}", r"    \begin{tabular}{lclc}", r"      \toprule",
     r"      Quarter & EU $\times$ High $\times$ quarter & Quarter & EU $\times$ High $\times$ quarter \\", r"      \midrule"]
for i in range(half):
    right = cells[i + half] if i + half < len(cells) else '&'
    L.append(f"      {cells[i]} & {right} \\\\")
lab = {'pre': 'Pre-announcement, 2020Q3--2022Q1', 'ant': 'Anticipation, 2022Q3--2024Q1', 'post': 'Post, 2024Q2--2026Q2'}
L += [r"      \midrule", r"      \multicolumn{4}{l}{\textit{Joint tests that the coefficients are zero}} \\"]
for k in ['pre', 'ant', 'post']:
    L.append(f"      \\multicolumn{{2}}{{l}}{{{lab[k]}}} & \\multicolumn{{2}}{{l}}{{$\\chi^2({J[k]['df']}) = {J[k]['chi2']:.2f}$, $p = {J[k]['p']:.2f}$}} \\\\")
L += [r"      \bottomrule", r"    \end{tabular}", r"    \begin{tablenotes}", r"      \small",
      r"      \item \textit{Note:} Coefficients plotted in Figure~\ref{fig:event-study}: interactions of $\text{EU}_i \times \text{HighExposure}_i$ with quarter indicators, "
      r"with the corresponding interactions of $\text{EU}_i$ and of $\text{HighExposure}_i$, firm and quarter fixed effects, on the matched sample. "
      r"Firm-clustered standard errors in parentheses. * $p < 0.10$, ** $p < 0.05$, *** $p < 0.01$.",
      r"    \end{tablenotes}", r"  \end{threeparttable}", r"\end{table}"]
open(f'{TEX}/tab12_ddd_evento.tex', 'w', encoding='utf-8').write(padroniza('\n'.join(L) + '\n'))

# ---------------- últimas linhas da Tabela 21
rob = R['rob'].set_index('spec'); col = R['collapsed'].set_index('spec')
def row(lab, b, se, p, tr, firms, N):
    return f"      {lab} & {mm(b, 4)}{st(p)} ({se:.4f}) & {tr} & {firms:,} & {N:,} \\\\"
r = rob.loc['Donut: 2022Q3 to 2024Q1 excluded']; a = rob.loc['Anticipation period modelled separately (post)']
c = col.loc['Pre = up to 2024Q1']; b = rob.loc['Balanced panel 2020Q3 to 2026Q2 (matching repeated)']; s = rob.loc['Size2021 x Post and ROA2021 x Post']
L = [r"      \midrule", r"      \multicolumn{5}{l}{\textit{Anticipation, serial correlation, and composition}} \\",
     row('Anticipation quarters (2022Q3--2024Q1) excluded', r.b, r.se, r.p, 68, int(r.firms), int(r.N)),
     row('Anticipation quarters as a separate period', a.b, a.se, a.p, 68, int(a.firms), int(a.N)),
     row('Collapsed: firm means before and after 2024Q2', c.b, c.se, c.p, 68, int(c.firms), int(c.firms)),
     row('Balanced panel, 2020Q3--2026Q2', b.b, b.se, b.p, int(b.treated), int(b.firms), int(b.N)),
     row('Size$_{2021}$ $\\times$ Post and ROA$_{2021}$ $\\times$ Post', s.b, s.se, s.p, 68, int(s.firms), int(s.N))]
open(f'{TEX}/tab10_bloco_extra.tex', 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print('\n'.join(L))
