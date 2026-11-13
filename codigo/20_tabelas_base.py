"""
Escreve em LaTeX as Tabelas 1, 3, 4, 5, 14 e 16 e os números citados no texto, direto das planilhas do 02.

  tab1_amostra.tex        Tabela 1    amostra por índice
  tab2a_validacao.tex     Tabela 3    Equação (5): Total, US, UK
  tab2b_validacao.tex     Tabela 4    Equação (5): Nordic, Canada, Europe
  tab3_setores.tex        Tabela 5    dez grupos TRBC com mais menções
  tab6_tech_dict.tex      Tabela 14   dicionário de tecnologias
  tab7_leave_one_out.tex  Tabela 16   leave-one-out, 21 firmas
  numeros_texto.txt       números citados nas Seções 3 e 4
As Tabelas 6 e 17 saem do 05 e do 07 e são conferidas pelo 24.
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import caminhos as config  # noqa: E402

PANELS = ['Total', 'US', 'UK', 'Nordic', 'Canada', 'Europe']
TECH_ROWS = [('Li-ion Batteries', 'Tech\\_LithiumIon'), ('Electric Vehicles', 'Tech\\_EV'),
             ('Solar', 'Tech\\_Solar'), ('Wind', 'Tech\\_Wind')]
DEPS = ['Lithium', 'Cobalt', 'Nickel', 'Copper', 'Rare Earths', 'Cotton', 'Energy']
MINS = ['Lithium', 'Cobalt', 'Nickel', 'Copper', 'Rare Earths']
MIN_COLS = ['Mineral_Lithium', 'Mineral_Cobalt', 'Mineral_Nickel', 'Mineral_Copper', 'Mineral_RareEarths']
STARS_NOTE = '* $p<0.10$, ** $p<0.05$, *** $p<0.01$.'


def fmt(x, d=4):
    """Número com o sinal de menos em modo matemático."""
    s = f"{x:.{d}f}"
    return s.replace('-', '$-$') if s.startswith('-') else s


def cell(b, p):
    st = '***' if p < 0.01 else '**' if p < 0.05 else '*' if p < 0.10 else ''
    return fmt(b) + st


def n(x):
    return f"{int(x):,}"


def write(path, lines):
    # '§' marca apóstrofo dentro de strings r'...' (ex.: Tobin§s -> Tobin's)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(('\n'.join(lines) + '\n').replace('§', "'"))


# ---------------------------------------------------------------------------
def tab1(tr, desc, fin_counts, out):
    tr = tr.assign(Market=tr['RIC'].map(desc['Market']))
    g = tr.groupby('Market').agg(firms=('RIC', 'nunique'), ects=('File Name', 'size'))
    rows = [('Nordic', 'Denmark (OMXC25)', 'Denmark'), ('Nordic', 'Norway (OBX)', 'Norway'),
            ('Nordic', 'Sweden (OMXS30)', 'Sweden'), ('UK', 'United Kingdom (FTSE 100)', 'UK'),
            ('US', 'United States (S\\&P 500)', 'US'), ('Canada', 'Canada (S\\&P/TSX Composite)', 'Canada'),
            ('Europe', 'Broader Europe (STOXX Europe 600)$^{\\dagger}$', 'Europe')]
    L = [r'\begin{table}[H]', r'\centering', r'\caption{Sample: Firm Distribution by Index.}',
         r'\label{tab:data_gathering}', r'\small', r'\begin{tabular}{llrrr}', r'\toprule',
         r'Region & Index & \makecell{Firms\\(index)} & \makecell{Firms\\(sample)} & \makecell{ECTs\\(matched)} \\',
         r'\midrule']
    for reg, lab, key in rows:
        L.append(f"{reg} & {lab} & {n(fin_counts[key])} & {n(g.loc[key, 'firms'])} & {n(g.loc[key, 'ects'])} \\\\")
    L += [r'\midrule',
          f"Total & & {n(sum(fin_counts.values()))} & {n(tr['RIC'].nunique())} & {n(len(tr))} \\\\",
          r'\bottomrule', r'\end{tabular}', '', r'\vspace{2mm}', r'\begin{minipage}{0.95\textwidth}', r'\footnotesize',
          r"Note: ECT stands for Earnings Call Transcript. ``Firms (index)'' are the index constituents for which "
          r"financial data were collected; ``Firms (sample)'' and ``ECTs (matched)'' are the firms and transcripts "
          r"matched to a firm-quarter of the financial panel (Section~\ref{subsec:etl}). Rows group firms by the "
          r"index from which they were drawn; the regional panels of the analysis are defined by country of "
          r"headquarters (Section~\ref{subsec:empirical-model-q}). $^{\dagger}$Constituents of the STOXX Europe~600 "
          r"that are not already in the FTSE~100 or the Nordic indices. Period: 2016Q1--2026Q2. Source: LSEG Workspace.",
          r'\end{minipage}', r'\end{table}']
    write(os.path.join(out, 'tab1_amostra.tex'), L)


# ---------------------------------------------------------------------------
def tab2(t2, out):
    def block(panels, label, caption, letters):
        L = [r'\begin{table}[H]', r'\centering', f'\\caption{{{caption}}}', f'\\label{{{label}}}', '',
             r'\begin{threeparttable}', r'\scriptsize', '',
             r'\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}lccccccc@{}}', r'\toprule',
             r'& \multicolumn{5}{c}{Mineral exposure} & \multicolumn{2}{c}{Placebo} \\',
             r'\cmidrule(lr){2-6}\cmidrule(lr){7-8}',
             r'Technology & Lithium & Cobalt & Nickel & Copper & Rare Earths & Cotton & Energy \\', r'\midrule']
        for letter, pn in zip(letters, panels):
            d = t2[t2['Painel'] == pn]
            nobs, nf = int(d['N'].iloc[0]), int(d['Firmas'].iloc[0])
            L += ['', f'\\multicolumn{{8}}{{l}}{{\\textit{{Panel {letter}: {pn} (n = {n(nobs)}; firms = {n(nf)})}}}} \\\\', r'\hline']
            for tl, tex in TECH_ROWS:
                r = d[d['Tecnologia'] == tl].set_index('Dependente')
                L.append(f"{tex:<16} & " + ' & '.join(cell(r.loc[x, 'beta'], r.loc[x, 'p']) for x in DEPS) + r' \\')
                L.append(f"{'':<16} & " + ' & '.join('(' + f"{r.loc[x, 'se']:.4f}" + ')' for x in DEPS) + r' \\')
            if letter != letters[-1]:
                L += [r'\addlinespace', r'\hline']
        L += ['', r'\bottomrule', r'\end{tabular*}', '', r'\begin{tablenotes}', r'\footnotesize',
              r'\item \textit{Note:} Each column reports one estimation of Equation~\eqref{eq:twfe} per panel, with '
              r'the four technology indicators entering jointly and the mineral (or placebo) exposure indicator as '
              r'the dependent variable. Lithium is measured after masking battery-technology phrases '
              r'(Section~\ref{subsubsec:mineral-exposure}). Cotton is a negative and Energy a positive placebo. '
              r'Regional panels are defined by the firm§s country of headquarters; $n$ is the number of transcripts in '
              r'each estimation, after the estimator drops singleton fixed-effect groups. All specifications include firm '
              r'and quarter-year fixed effects and a log market capitalisation control; firm-clustered standard '
              r'errors in parentheses. ' + STARS_NOTE,
              r'\end{tablenotes}', '', r'\end{threeparttable}', r'\end{table}']
        return L
    write(os.path.join(out, 'tab2a_validacao.tex'),
          block(['Total', 'US', 'UK'], 'tab:validation',
                'Validating Mineral Exposure Across Technologies: Total, US, and UK.', 'ABC'))
    write(os.path.join(out, 'tab2b_validacao.tex'),
          block(['Nordic', 'Canada', 'Europe'], 'tab:validation-b',
                'Validating Mineral Exposure Across Technologies: Nordic, Canada, and Europe.', 'DEF'))


# ---------------------------------------------------------------------------
def tab3(t3, out):
    t3 = t3.reset_index() if 'TRBC Industry Group Name' not in t3.columns else t3
    t3 = t3.head(10)  # a dissertação mostra os dez grupos de maior exposição média (o 02 guarda vinte)
    L = [r'\begin{table}[H]', r'  \centering', r'  \caption{Mineral Exposure by Top 10 TRBC Industry Groups.}',
         r'  \label{tab:sector-exposure}', r'  \begin{threeparttable}', r'    \scriptsize', r'    \setstretch{1.15}',
         r'    \setlength{\tabcolsep}{4pt}', r'    \begin{tabular}{l r r r r r r r}', r'      \toprule',
         r'      \textbf{TRBC Industry Group} & \multicolumn{1}{c}{Firms} & \multicolumn{1}{c}{Lithium} & '
         r'\multicolumn{1}{c}{Cobalt} & \multicolumn{1}{c}{Nickel} & \multicolumn{1}{c}{Copper} & '
         r'\multicolumn{1}{c}{Rare Earths} & \multicolumn{1}{c}{Average} \\', r'      \midrule']
    for _, r in t3.iterrows():
        name = str(r['TRBC Industry Group Name']).replace('&', r'\&')
        L.append(f"      {name:<50} & {int(r['Firmas'])} & " + ' & '.join(f"{r[c]:.2f}" for c in MINS + ['Average']) + r' \\')
    L += [r'      \bottomrule', r'    \end{tabular}', r'    \begin{tablenotes}', r'      \small',
          r'      \item \textit{Note:} Each cell reports the percentage of a group§s matched transcripts that mention '
          r'the respective mineral (lithium after masking battery-technology phrases). Industry groups follow the '
          r'Thomson Reuters Business Classification (TRBC). The ten groups with the highest average exposure are '
          r'shown, ranked by the final column. Industry groups represented by fewer than five firms are excluded to '
          r'avoid estimates driven by individual firms.',
          r'    \end{tablenotes}', r'  \end{threeparttable}', r'\end{table}']
    write(os.path.join(out, 'tab3_setores.tex'), L)


# ---------------------------------------------------------------------------
def tab6(out):
    # Mesmo texto da Tabela 14 da dissertação: as formas com hífen aparecem como ficam depois da limpeza
    L = r'''\begin{table}[H]
  \centering
  \caption{Technology Term Dictionary}
  \label{tab:tech-dict}
  \begin{threeparttable}
    \tablestyle
    \begin{tabularx}{\textwidth}{@{}l X@{}}
      \toprule
      Technology & Terms \\
      \midrule
      Lithium-ion Batteries & ion battery, lithium ion battery, lithium ion
                              batteries, lithium batteries, ion batteries, lithium
                              polymer, lithium ion, lithium battery, lithiumion$^{a}$,
                              liion$^{a}$, lithiumpolymer$^{a}$ \\
      Electric Vehicles     & hybrid vehicle, electric vehicle, electric motorcycle,
                              vehicle charging, hybrid electric, plugin hybrids,
                              electric buses, electrical vehicles, electric car,
                              electric vehicles \\
      Solar                 & solar power, solar energy, solar business, solar cell,
                              solar projects, solar market, solar capital, solar
                              industry, solar cells, solar panels, solar project,
                              solar panel, solar pv, solar module, solar modules,
                              solar side, solar technology, solar farm, solar
                              products, solar assets, solar systems, solar
                              industries, solar generation, solar pwr, solar markets,
                              solar wafer, solar plant, solar grade, solar capacity,
                              solar facility, solar farms, solar companies, solar
                              plants, solar installations, solar equipment, solar
                              product, solar technologies, solar thermal, solar
                              customers, solar segment, solar applications, solar
                              installation, solar materials, solar facilities, solar
                              sales \\
      Wind                  & wind power, wind energy, wind resource, onshore wind,
                              offshore wind, wind turbine, wind resources, wind
                              turbines \\
      \bottomrule
    \end{tabularx}
    \begin{tablenotes}[flushleft]
      \footnotesize
      \item \textit{Note:} Terms are matched as whole words or phrases after the preprocessing of Section~\ref{subsec:preprocessing}. $^{a}$Forms that the hyphenated terms ``lithium-ion'', ``Li-ion'', and ``lithium-polymer'' take after preprocessing, which deletes hyphens.
    \end{tablenotes}
  \end{threeparttable}
\end{table}'''
    write(os.path.join(out, 'tab6_tech_dict.tex'), [L])


# ---------------------------------------------------------------------------
def tab7(c, desc, out):
    L = [r'\begin{table}[H]', r'  \centering', r'  \caption{Leave-One-Firm-Out: Rare-Earth Risk and Valuation (US)}',
         r'  \label{tab:robustness}', r'  \begin{threeparttable}', r'    \footnotesize',
         r'    \begin{tabular}{l c c c r}', r'      \toprule',
         r'      Excluded firm & \makecell{Quarters with\\mention} & $\hat{\beta}$ (Rare Earths) & Std.\ error & Obs. \\',
         r'      \midrule']
    for _, r in c.iterrows():
        if str(r['Retirada']).startswith('Nenhuma'):
            name, q = 'None (full US sample)', '--'
        else:
            name = str(desc['Company Name'].get(r['Retirada'], r['Retirada'])).replace('&', r'\&')
            q = str(int(r['Trimestres com menção']))
        L.append(f"      {name:<40} & {q} & {cell(r['beta'], r['p'])} & ({r['se']:.4f}) & {n(r['N'])} \\\\")
        if str(r['Retirada']).startswith('Nenhuma'):
            L.append(r'      \midrule')
    L += [r'      \bottomrule', r'    \end{tabular}', r'    \begin{tablenotes}', r'      \small',
          r'      \item \textit{Note:} Each row re-estimates the US rare-earth specification of Table~\ref{tab:valuation}, '
          r'excluding the named firm; firms are ordered by the number of firm-quarters in which they mention rare earths. '
          r'Firm-clustered standard errors in parentheses. All specifications retain the controls and firm and '
          r'quarter-year fixed effects of the main model. ' + STARS_NOTE,
          r'    \end{tablenotes}', r'  \end{threeparttable}', r'\end{table}']
    write(os.path.join(out, 'tab7_leave_one_out.tex'), L)


# ---------------------------------------------------------------------------
def numbers(x, tr, p, out):
    a = dict(zip(x['Amostra']['Item'], x['Amostra']['Valor']))
    lines = ['NÚMEROS CITADOS NO TEXTO', '', '[Seção 3.1, amostra]']
    lines += [f'  {k}: {int(v):,}' for k, v in a.items()]
    lines += ['', '[Seção 3.3.1, % de firmas em Metals & Mining por painel (sede), amostra de validação]']
    for r in PANELS[1:]:
        f = tr[tr['Region_HQ'] == r].drop_duplicates('RIC')
        lines.append(f"  {r}: {(f['TRBC Industry Group Name'] == 'Metals & Mining').mean() * 100:.1f}% de {len(f)} firmas")
    lines += ['', '[Seção 4.4, frequência das menções (% dos transcripts)]',
              f"  algum mineral: {tr[MIN_COLS].max(axis=1).mean() * 100:.1f}%"]
    lines += [f"  {m}: {tr[c].mean() * 100:.2f}%" for m, c in zip(MINS, MIN_COLS)]
    t4 = x['T4_CP_V2']
    lines += ['', '[Seções 4.4 e 4.5, firmas que mencionam cada mineral por painel (Tobin V2 C&P)]']
    for m in MINS + ['Composite']:
        r = t4[t4['MineralRisk'] == m].set_index('Painel')
        lines.append(f"  {m}: " + ', '.join(f"{pn} {int(r.loc[pn, 'Firmas que mencionam'])}" for pn in PANELS))
    loo = x['C_LeaveOneOut']
    lines += ['', '[Apêndice C]',
              f"  firma-trimestres US com menção a terras raras (amostra da Tabela 4): "
              f"{int(loo['Trimestres com menção'].sum())}",
              f"  firmas US que mencionam terras raras (amostra da Tabela 4): {len(loo) - 1}",
              f"  faixa do beta no leave-one-out: {loo['beta'].min():.4f} a {loo['beta'].max():.4f}; "
              f"maior p-valor: {loo['p'].max():.4f}"]
    write(os.path.join(out, 'numeros_texto.txt'), lines)


def main(est=config.SAIDA_EST, out=config.SAIDA_TEX, fin_dir=config.PASTA_FINANCEIROS, desc_files=None):
    import glob
    os.makedirs(out, exist_ok=True)
    x = pd.read_excel(os.path.join(est, 'Resultados_Dissertacao.xlsx'), sheet_name=None)
    tr = pd.read_pickle(os.path.join(est, 'amostra_validacao.pkl'))
    p = pd.read_pickle(os.path.join(est, 'painel_firma_trimestre.pkl'))
    desc = pd.concat([pd.read_excel(f, sheet_name='Extraction') for f in (desc_files or config.DESCRITIVOS)])
    desc = desc.drop_duplicates('RIC').set_index('RIC')
    # firmas por índice de coleta = RICs em cada arquivo financeiro, agrupados por mercado
    fin_counts = {}
    for f in glob.glob(os.path.join(fin_dir, 'LSEG_ChungPruitt_*.xlsx')):
        key = os.path.basename(f).replace('LSEG_ChungPruitt_', '').split('_')[0].replace('.xlsx', '')
        fin_counts[key] = fin_counts.get(key, 0) + pd.read_excel(f, sheet_name='Extraction', usecols=['RIC'])['RIC'].nunique()
    tab1(tr, desc, fin_counts, out)
    tab2(x['T2_Validacao'], out)
    tab3(x['T3_Setores'], out)
    tab6(out)
    tab7(x['C_LeaveOneOut'], desc, out)
    numbers(x, tr, p, out)
    print('Pronto:', out)


if __name__ == '__main__':
    a = sys.argv[1:]
    main(*a[:3], desc_files=a[3:] or None) if a else main()
