"""
Tabelas dos apêndices escritas direto dos resultados.
  tabA1_variaveis.tex     Tabela 12   definição das variáveis (texto fixo)
  tabA2_amostra.tex       Tabela 11   construção da amostra
  tabC1_replicacao.tex    Tabela 15   o que cada script faz (texto fixo)
  tabD4_testes.tex        Tabela 19   teste agrupado de H2, Q defasado, Romano-Wolf com dez sementes
  tabF1_china_extra.tex   Tabela 24   especificidade das terras raras e tendências por indústria (do 16)
"""
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__))); from caminhos import *  # noqa
from estilo_tabelas import padroniza
import importlib.util, pickle, warnings
import pandas as pd
warnings.filterwarnings('ignore')
spec = importlib.util.spec_from_file_location('e', EST_PY); E = importlib.util.module_from_spec(spec); spec.loader.exec_module(E)

def st(p): return '***' if p < .01 else '**' if p < .05 else '*' if p < .1 else ''
def mm(v, k=4):
    s = f"{v:.{k}f}"
    return (s[1:] if float(s) == 0 else s).replace('-', '$-$')
def n(x): return f"{int(x):,}"
def head(caption, label, cols, size=r'\small', sep='4pt'):
    return [r"\begin{table}[H]", r"  \centering", f"  \\caption{{{caption}}}", f"  \\label{{{label}}}", r"  \begin{threeparttable}",
            f"    {size}", f"    \\setlength{{\\tabcolsep}}{{{sep}}}", f"    \\begin{{tabular}}{{{cols}}}", r"      \toprule"]
def foot(note):
    return [r"      \bottomrule", r"    \end{tabular}", r"    \begin{tablenotes}", r"      \footnotesize", f"      \\item \\textit{{Note:}} {note}",
            r"    \end{tablenotes}", r"  \end{threeparttable}", r"\end{table}"]
def save(name, L, compacta=False): open(f'{TEX}/{name}.tex', 'w', encoding='utf-8').write(padroniza('\n'.join(L) + '\n', compacta))

# ---------------- A1: variáveis
FIXO_TABA1 = r'''\begin{table}[H]
  \centering
  \caption{Variable Definitions}
  \label{tab:variables}
  \begin{threeparttable}
    \footnotesize
    \setlength{\tabcolsep}{3pt}
    \renewcommand{\arraystretch}{0.92}
    \begin{tabular}{>{\raggedright\arraybackslash}p{0.16\textwidth}>{\raggedright\arraybackslash}p{0.45\textwidth}>{\raggedright\arraybackslash}p{0.31\textwidth}}
      \toprule
      Variable & Definition & Source or field \\
      \midrule
      \multicolumn{3}{l}{\textit{Valuation and controls (LSEG Workspace, US dollars)}} \\
      Tobin's Q & $(\text{MVE} + \text{PS} + \text{DEBT})/\text{TA}$, with $\text{DEBT} = \text{CL} - \text{CA} + \text{LTD}$ (\citealp{chung1994}, as in \citealp{butt2021}); winsorised & MVE: TR.CompanyMarketCap (quarter-end); TA: TR.TotalAssetsReported; CL: TR.TotalCurrentLiabilities; CA: TR.TotalCurrentAssets; LTD: TR.TotalLongTermDebt \\
      Preferred stock (PS) & Total of debt, preferred equity, and minority interest less total debt and minority interest; zero where the total is unavailable & TR.F.DebtInclPrefEq\-MinIntrTot, TR.F.DebtTot, TR.F.MinIntrTot \\
      Simplified Q & $(\text{MVE} + \text{total debt})/\text{TA}$; winsorised & TR.TotalDebtOutstanding \\
      Size & Log of total assets (main) or of market capitalisation & TR.TotalAssetsReported; TR.CompanyMarketCap \\
      Leverage & Total debt over total assets; winsorised & TR.TotalDebtOutstanding, TR.TotalAssetsReported \\
      ROA & Net income over total assets; winsorised & TR.NetIncome, TR.TotalAssetsReported \\
      \multicolumn{3}{l}{\textit{Text-based measures (earnings call transcripts, LSEG Workspace)}} \\
      \textit{Mineral}\newline\textit{Exposure}$^{\mu}_{it}$ & One if firm $i$ mentions mineral $\mu$ in a call of quarter $t$ (Equation~\eqref{eq:mineral-risk}); standardised by panel in Equation~\eqref{eq:main-q} & Dictionaries of Table~\ref{tab:mineral-dict} \\
      Composite & Sum of the five mineral indicators (0 to 5); excludes telecoms & As above \\
      \textit{TechExposure}$^{\tau}$ & One if the call mentions technology $\tau$: electric vehicles, lithium-ion batteries, solar, or wind & Dictionaries of Table~\ref{tab:tech-dict} \\
      Placebos & Cotton (negative control) and Energy (positive control) & Section~\ref{subsec:empirical-model} \\
      \multicolumn{3}{l}{\textit{Classification and design variables}} \\
      Panel & US, UK, Nordic (Denmark, Norway, Sweden), Canada, Europe (rest of Europe) & Country of Headquarters \\
      Sector & TRBC economic sector and industry group; financials excluded & TRBC Industry Group Name \\
      Producer & One for TRBC Metals \& Mining and Uranium & TRBC Industry Group Name \\
      $\text{EU}_i$ & One if headquartered in an EU member state; EEA-EFTA states excluded & Country of Headquarters \\
      $\text{HighExposure}_i$ & One if the mean composite up to 2022Q2 is in the top quartile across firms and positive & Equation~\eqref{eq:ddd} \\
      $\text{Post}_t$ (CRMA) & One from 2024Q2, the first quarter-end after entry into force & Equation~\eqref{eq:ddd} \\
      $\text{Exposed}_i$ (China) & One for the TRBC groups Automobiles \& Auto Parts; Aerospace \& Defense; Machinery, Tools, Heavy Vehicles, Trains \& Ships; and Renewable Energy & Equation~\eqref{eq:china} \\
      $\text{Post}_t$ (China) & One from 2025Q2, the first quarter-end after the controls of 4 April 2025 & Equation~\eqref{eq:china} \\
      \bottomrule
    \end{tabular}
    \begin{tablenotes}
      \footnotesize
      \item \textit{Note:} LSEG Workspace Excel add-in fields, in US dollars; market capitalisation is taken at each quarter-end and the other items are the latest fiscal year (\texttt{FY0}). A missing component of Q leaves Q missing, except the components of PS, which are set to zero. Winsorised variables are cut at the 1st and 99th percentiles.
    \end{tablenotes}
  \end{threeparttable}
\end{table}
'''
open(f'{TEX}/tabA1_variaveis.tex', 'w', encoding='utf-8').write(padroniza(FIXO_TABA1, compacta=True))

# ---------------- A2: construção da amostra
lg = pd.read_excel(f'{R02}/Resultados_Dissertacao.xlsx', sheet_name='Amostra').set_index('Item')['Valor']
p = pd.read_pickle(f'{R02}/painel_firma_trimestre.pkl')
fin = p['TRBC Industry Group Name'].isin(E.FINANCIALS)
v1 = E.est_sample(p, 'Q_CP', 'V1'); v2 = E.est_sample(p, 'Q_CP', 'V2')
rows = [(r"\multicolumn{3}{l}{\textit{Panel A: Earnings call transcripts}}", None, None),
        ('Transcripts collected from LSEG Workspace', lg['Transcripts lidos pelo NLP'], ''),
        ('After removing same-day duplicates (largest file kept)', lg['Transcripts após regra do mesmo dia (maior arquivo)'], ''),
        ('Less: transcripts of firms without financial data', -lg['Transcripts sem RIC no painel financeiro'], ''),
        ('Validation sample (Tables~\\ref{tab:validation} and~\\ref{tab:validation-b})', lg['Transcripts casados com market cap (amostra de validação)'], lg['Firmas na amostra de validação']),
        (r"\multicolumn{3}{l}{\textit{Panel B: Firm-quarter valuation panel, 2016Q1--2026Q2}}", None, None),
        ('Firms in the index constituent lists, 42 quarters each', lg['Painel financeiro: firma-trimestres'], lg['Painel financeiro: firmas']),
        ('After merging duplicate listings of the same company', lg['Painel financeiro após remoção de duplicatas: firma-trimestres'], lg['Painel financeiro após remoção de duplicatas: firmas']),
        ('Less: financial firms', -int(fin.sum()), -p.loc[fin, 'RIC'].nunique()),
        ('Non-financial firms', int((~fin).sum()), p.loc[~fin, 'RIC'].nunique()),
        ("With Tobin's Q and all controls (full panel)", len(v1), v1.RIC.nunique()),
        ('Of which with an earnings call (main sample)', len(v2), v2.RIC.nunique())]
L = head('Sample Construction', 'tab:sample-construction', 'lrr', size=r'\footnotesize')
L += [r"      & Observations & Firms \\", r"      \midrule"]
for a, b, c in rows:
    if b is None: L.append(f"      {a} \\\\"); continue
    fmt = lambda x: '' if x == '' else (f"$-${abs(int(x)):,}" if int(x) < 0 else f"{int(x):,}")
    L.append(f"      {a} & {fmt(b)} & {fmt(c)} \\\\")
L += foot(r"Observations are transcripts in Panel A and firm-quarters in Panel B. Duplicate listings of the same company are merged into the listing with the most transcripts. The fixed-effects estimator drops singleton observations, so the regressions of Table~\ref{tab:valuation} use 31,795 of the 31,805 firm-quarters of the main sample.")
save('tabA2_amostra', L)

# ---------------- C1: replicação
FIXO_TABC1 = r'''\begin{table}[H]
  \centering
  \caption{Replication Code: Scripts and the Results They Produce}
  \label{tab:replication}
  \begin{threeparttable}
    \footnotesize
    \begin{tabular}{>{\raggedright\arraybackslash}p{0.31\textwidth}>{\raggedright\arraybackslash}p{0.37\textwidth}>{\raggedright\arraybackslash}p{0.26\textwidth}}
      \toprule
      Script & What it does & Results \\
      \midrule
      \texttt{01\_nlp} & Cleans the transcripts and applies the dictionaries & Measures of Section~\ref{subsubsec:mineral-exposure} \\
      \texttt{02\_estimacao} & Builds the firm-quarter panel; estimates Equation~\eqref{eq:twfe} & Tables~\ref{tab:validation}, \ref{tab:validation-b}, and~\ref{tab:sector-exposure} \\
      \texttt{03\_extrair\_terras\_raras\_eua} & Extracts the US rare-earth mentions for the manual classification & Section~\ref{subsubsec:re-us} \\
      \texttt{04\_conferir\_q} & Recomputes Tobin's Q in every row of the LSEG workbooks & Table~\ref{tab:variables} \\
      \addlinespace[2pt]
      \texttt{05\_valuation} & Equation~\eqref{eq:main-q}; alternative versions; producers; wild bootstrap; Romano--Wolf & Tables~\ref{tab:valuation}, \ref{tab:producers}, and~\ref{tab:valuation-rob} (Panels A to E) \\
      \texttt{06\_robustez\_q} & Leave-one-out, fixed effects, timing, randomisation inference, pooled test & Tables~\ref{tab:robustness}, \ref{tab:rare-extra} (rows 2 to 6), and~\ref{tab:addl-tests} (Panel A) \\
      \texttt{07\_tempo\_q} & Tobin's Q around a mention; quarterly reporters & Tables~\ref{tab:rare-extra} (rows 11 to 17) and~\ref{tab:valuation-rob} (Panel F) \\
      \texttt{08\_medicao\_terras\_raras} & Alternative rare-earth measures and samples & Table~\ref{tab:rare-extra} (rows 7 to 10) \\
      \texttt{09\_auditoria\_terras\_raras} & Equation~\eqref{eq:main-q} with the manual classification & Table~\ref{tab:rare-extra} (rows 18 and 19) \\
      \texttt{10\_q\_extras} & Lagged Tobin's Q; Romano--Wolf with ten seeds & Table~\ref{tab:addl-tests} (Panels B and C) \\
      \texttt{11\_ddd\_crma} & Matching, Equation~\eqref{eq:ddd}, event study, alternatives & Tables~\ref{tab:ddd}, \ref{tab:psm-balance}, \ref{tab:ddd-robust}, and~\ref{tab:ddd-es} \\
      \texttt{12\_ddd\_europa} & Triple difference within Europe & Table~\ref{tab:ddd-robust} (Europe only) \\
      \texttt{13\_ddd\_extras} & Anticipation, collapsed and balanced versions, raw means & Tables~\ref{tab:ddd-robust} and~\ref{tab:ddd-means} \\
      \texttt{14\_china} & Equation~\eqref{eq:china}, event studies, inference by industry & Table~\ref{tab:china} \\
      \texttt{15\_china\_loio} & Drops each exposed industry group in turn & Table~\ref{tab:china} \\
      \texttt{16\_china\_extras} & Other minerals and industry trends & Table~\ref{tab:china-extra} \\
      \addlinespace[2pt]
      \texttt{17\_fig\_tendencias} & Trends in mineral mentions by panel & Figures~\ref{fig:trend-total} to~\ref{fig:trend-europe} \\
      \texttt{18\_fig\_crma} & Event study around the CRMA & Figure~\ref{fig:event-study} \\
      \texttt{19\_fig\_china} & Event studies around China's export controls & Figure~\ref{fig:china-es} \\
      \addlinespace[2pt]
      \texttt{20\_tabelas\_base} & Sample, validation, sector, dictionary, leave-one-out & Tables~\ref{tab:data_gathering}, \ref{tab:validation}, \ref{tab:validation-b}, \ref{tab:sector-exposure}, \ref{tab:tech-dict}, and~\ref{tab:robustness} \\
      \texttt{21\_descritivas} & Descriptive statistics & Table~\ref{tab:descriptives} \\
      \texttt{22\_tabelas\_ddd\_apendice} & Appendix tables of the triple difference & Tables~\ref{tab:ddd-means}, \ref{tab:ddd-es}, and~\ref{tab:ddd-robust} (one block) \\
      \texttt{23\_tabelas\_apendice} & Other appendix tables & Tables~\ref{tab:sample-construction}, \ref{tab:variables}, \ref{tab:replication}, \ref{tab:addl-tests}, and~\ref{tab:china-extra} \\
      \addlinespace[2pt]
      \texttt{24\_conferencia} & Checks every number of the other tables & All tables \\
      \bottomrule
    \end{tabular}
    \begin{tablenotes}
      \footnotesize
      \item \textit{Note:} Code available at \url{https://github.com/andreaugustosantos/codigos-andre}. \texttt{00\_rodar\_tudo.py} runs \texttt{02} and \texttt{04} to \texttt{24} in this order; each uses only the results of lower-numbered scripts. Scripts \texttt{01} and \texttt{03} read the transcripts and run separately. Shared functions are in \texttt{caminhos.py} (folders), \texttt{ddd\_core.py} and \texttt{sector\_map.py} (triple difference), \texttt{wcr.py} (wild bootstrap and Romano--Wolf), and \texttt{estilo\_tabelas.py} (table layout).
    \end{tablenotes}
  \end{threeparttable}
\end{table}
'''
open(f'{TEX}/tabC1_replicacao.tex', 'w', encoding='utf-8').write(padroniza(FIXO_TABC1, compacta=True))

# ---------------- D4: testes adicionais da Eq. (6)
H = pd.read_excel(f'{RES}/resultados_robustez.xlsx', sheet_name='M6a_teste_H2')
Q = pickle.load(open(f'{RES}/q_extras.pkl', 'rb'))
L = head('Valuation Results: Pooled Regional Test, Timing, and Multiple Testing', 'tab:addl-tests', 'lcccc', size=r'\footnotesize')
L += [r"      \multicolumn{5}{l}{\textit{Panel A: Pooled regression (US level and differences from the US)}} \\",
      r"      & US & Canada $-$ US & Europe $-$ US & UK $-$ US \\", r"      \midrule"]
for mv, lab in [('Rare Earths', 'Rare earths'), ('Copper', 'Copper')]:
    h = H[H.MineralRisk == mv].set_index('Termo')
    keys = ['EUA (nível, por menção)', 'Canada menos EUA', 'Europe menos EUA', 'UK menos EUA']
    L.append(f"      {lab} & " + " & ".join(f"{mm(h.loc[k, 'beta'], 3)}{st(h.loc[k, 'p'])}" for k in keys) + r" \\")
    L.append("      & " + " & ".join(f"({h.loc[k, 'se']:.3f})" for k in keys) + r" \\")
L += [r"      \midrule", r"      \multicolumn{5}{l}{\textit{Panel B: Mention in quarter $t$ on standardised Tobin's Q in $t-k$, US panel}} \\",
      r"      & $k = 1$ & $k = 2$ & $k = 4$ & Mean mention \\", r"      \midrule"]
lq = Q['lagQ']
for v, lab in [('Mineral_RareEarths', 'Rare earths'), ('Mineral_Copper', 'Copper'), ('Composite', 'Composite')]:
    x = lq[(lq['var'] == v) & (lq.panel == 'US')].set_index('lag')
    L.append(f"      {lab} & " + " & ".join(f"{mm(x.loc[k, 'b_Qz'])}{st(x.loc[k, 'p'])}" for k in [1, 2, 4]) + f" & {x.loc[1, 'mean_mention']:.4f} \\\\")
    L.append("      & " + " & ".join(f"({x.loc[k, 'se']:.4f})" for k in [1, 2, 4]) + r" & \\")
L += [r"      \midrule", r"      \multicolumn{5}{l}{\textit{Panel C: Romano--Wolf $p$-values across ten seeds (wild bootstrap $p < 0.05$)}} \\",
      r"      & $t$ & Wild $p$ & Romano--Wolf $p$ & \makecell{Romano--Wolf $p$,\\ ten seeds} \\", r"      \midrule"]
s = Q['rw_summary']; s = s[s.p_wild_max < 0.05].sort_values('t', ascending=False)
lab = {'Mineral_RareEarths': 'Rare earths', 'Mineral_Copper': 'Copper', 'Composite': 'Composite', 'Mineral_Lithium': 'Lithium', 'Mineral_Cobalt': 'Cobalt', 'Mineral_Nickel': 'Nickel'}
for _, r in s.iterrows():
    m0 = Q['rw_seeds']; m0 = m0[(m0.seed == 20261024) & (m0['var'] == r['var']) & (m0.panel == r.panel)].iloc[0]
    L.append(f"      {lab[r['var']]}, {r.panel} & {r.t:.2f} & {m0.p_wild:.3f} & {m0.p_rw:.3f} & {r.p_rw_min:.3f} to {r.p_rw_max:.3f} \\\\")
L += foot(r"Panel A: pooled regression of Tobin's Q on the unstandardised mention indicator interacted with the regional panels, with the controls of Equation~\eqref{eq:main-q}, firm and region-by-quarter fixed effects; the first column is the US coefficient and the others the differences from it. "
          r"Panel B: linear probability model of the mention indicator on Tobin's Q $k$ quarters earlier, standardised, with the controls of that quarter and firm and quarter fixed effects. "
          r"Panel C: wild cluster bootstrap (9,999 replications, Rademacher weights) and the Romano--Wolf stepdown correction across the thirty-six coefficients of Table~\ref{tab:valuation}, with the seed used throughout (20261024); the last column gives the range of the Romano--Wolf $p$-value across this and nine further seeds. Firm-clustered standard errors in parentheses. * $p < 0.10$, ** $p < 0.05$, *** $p < 0.01$.")
save('tabD4_testes', L)

# ---------------- F1: China, especificidade e tendências
C = pickle.load(open(f'{RES}/china_extras.pkl', 'rb'))
bm = C['by_mineral'].set_index('var'); sk = C['stacked'].set_index('other'); tr = C['trends'].set_index('part')
L = head("China's Rare-Earth Export Controls: Specificity and Industry Trends", 'tab:china-extra', 'lccccc', size=r'\footnotesize')
L += [r"      \multicolumn{6}{l}{\textit{Panel A: Mentions by mineral, quarters with an earnings call}} \\",
      r"      & \makecell{Exposed $\times$ Post} & \makecell{Exposed,\\ pre (\%)} & \makecell{Exposed,\\ post (\%)} & \makecell{Post/pre,\\ exposed} & \makecell{Rare earths\\ minus mineral} \\", r"      \midrule"]
ml = [('Mineral_RareEarths', 'Rare earths'), ('Mineral_Copper', 'Copper'), ('Mineral_Lithium', 'Lithium'), ('Mineral_Cobalt', 'Cobalt'), ('Mineral_Nickel', 'Nickel')]
for v, lab_ in ml:
    r = bm.loc[v]; d = sk.loc[v] if v in sk.index else None
    dd = '' if d is None else f"{mm(d.diff_RE_minus_other)}{st(d.p)}"
    ds = '' if d is None else f"({d.se:.4f})"
    L.append(f"      {lab_} & {mm(r.b)}{st(r.p)} & {100 * r.exposed_pre:.1f} & {100 * r.exposed_post:.1f} & {r.ratio_exposed:.1f} & {dd} \\\\")
    L.append(f"      & ({r.se:.4f}) & & & & {ds} \\\\")
o = C['RE_without_other'].iloc[0]; sh = C['share'].iloc[0]
L += [r"      \midrule", r"      \multicolumn{6}{l}{\textit{Panel B: Rare-earth mentions, alternative outcomes}} \\",
      f"      No other mineral & {mm(o.b)}{st(o.p)} & & & & \\\\", f"      & ({o.se:.4f}) & & & & \\\\",
      f"      Share of mineral quarters & {mm(sh.b)}{st(sh.p)} & {100 * sh.exposed_pre:.1f} & {100 * sh.exposed_post:.1f} & & \\\\", f"      & ({sh.se:.4f}) & & & & \\\\",
      r"      \midrule", r"      \multicolumn{6}{l}{\textit{Panel C: With linear trends by industry group}} \\",
      r"      & Exposed $\times$ Post & SE, firm & $p$, firm & SE, industry & $p$, industry \\", r"      \midrule"]
for k, lab_ in [('A', 'Rare-earth mention'), ('A copper', 'Copper mention'), ('B', "Tobin's Q")]:
    r = tr.loc[k]; L.append(f"      {lab_} & {mm(r.b)} & ({r.se:.4f}) & {r.p:.3f} & ({r.se_ind:.4f}) & {r.p_ind:.3f} \\\\")
L += foot(r"Equation~\eqref{eq:china}, 2023Q1 to 2026Q2. Panel A: difference in differences for each mineral indicator, firm-clustered standard errors in parentheses; pre and post are the mention rates of the exposed firms before and after 2025Q2; the last column comes from a stacked regression of the rare-earth and each other indicator, with firm-by-mineral and quarter-by-mineral fixed effects, and is the difference between the two coefficients. "
          r"Panel B: the first row counts a rare-earth mention only in quarters without a mention of another mineral; the second restricts the sample to firm-quarters with a mention of any mineral, and its pre and post columns are rare-earth shares among those quarters. Panel C adds a linear trend for each TRBC industry group. * $p < 0.10$, ** $p < 0.05$, *** $p < 0.01$.")
save('tabF1_china_extra', L)
print('ok')
