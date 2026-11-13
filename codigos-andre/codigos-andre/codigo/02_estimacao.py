"""
Monta o painel firma-trimestre (transcripts + dados da LSEG), cria as variáveis e roda a validação das medidas.

Entradas (ver caminhos.py): a saída do 01, as 13 planilhas LSEG_ChungPruitt_*.xlsx e as duas planilhas de descritivos.

Saídas (pasta SAIDA_EST):
  Resultados_Dissertacao.xlsx, uma aba por resultado:
    Amostra        contagens da amostra (Tabelas 1 e 11)
    T2_Validacao   Equação (5), Tabelas 3 e 4
    T3_Setores     menções por grupo TRBC, Tabela 5
    T4_*           Equação (6) com o Q de Chung e Pruitt ou o simplificado, só trimestres com call (V2) ou todos (V1)
    C_LeaveOneOut  terras raras nos EUA tirando uma firma por vez, Tabela 16
    Tendencias     médias por trimestre das Figuras 2 a 7
  amostra_validacao.pkl e painel_firma_trimestre.pkl, usados pelos scripts seguintes

Regras principais:
  - região pela sede (Country of Headquarters); sedes fora das cinco regiões entram só no Total
  - mesma firma, mesmo dia, mais de um transcript: fica o maior arquivo
  - financeiras ficam fora das regressões do Q
  - Q, alavancagem e ROA winsorizados em 1% e 99% na amostra de estimação
  - efeitos fixos de firma e trimestre, erro padrão por firma; * p<0,10, ** p<0,05, *** p<0,01
"""

import argparse
import glob
import os
import sys
import warnings

import numpy as np
import pandas as pd
import pyfixest as pf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import caminhos as config  # noqa: E402
from caminhos import SIZE  # noqa: E402

warnings.filterwarnings('ignore')

MINERALS = ['Mineral_Lithium', 'Mineral_Cobalt', 'Mineral_Nickel', 'Mineral_Copper', 'Mineral_RareEarths']
PLACEBOS = ['Placebo_Negative', 'Placebo_Positive']
TECHS = ['Tech_LithiumIon', 'Tech_EV', 'Tech_Solar', 'Tech_Wind']
LABEL = {'Mineral_Lithium': 'Lithium', 'Mineral_Cobalt': 'Cobalt', 'Mineral_Nickel': 'Nickel',
         'Mineral_Copper': 'Copper', 'Mineral_RareEarths': 'Rare Earths', 'Placebo_Negative': 'Cotton',
         'Placebo_Positive': 'Energy', 'Composite': 'Composite', 'Tech_LithiumIon': 'Li-ion Batteries',
         'Tech_EV': 'Electric Vehicles', 'Tech_Solar': 'Solar', 'Tech_Wind': 'Wind'}
PANELS = ['Total', 'US', 'UK', 'Nordic', 'Canada', 'Europe']
EUROPE = {'Germany', 'Switzerland', 'France', 'Italy', 'Netherlands', 'Spain', 'Finland', 'Ireland', 'Belgium',
          'Poland', 'Austria', 'Luxembourg', 'Portugal', 'Faroe Islands', 'Cyprus', 'Iceland', 'Greece',
          'Czech Republic', 'Hungary', 'Jersey', 'Guernsey', 'Isle of Man', 'Monaco', 'Liechtenstein', 'Malta'}
# Mesma empresa sob outro RIC que não aparece nos descritivos (ou com outro nome): transcript -> RIC do painel
SAME_COMPANY_ALIASES = {
    'SATG.DE': 'SATG_p.DE',      # Sartorius AG: ação ordinária -> preferencial (RIC do painel)
    'CCL.L': 'CCL.N',            # Carnival plc -> Carnival Corporation (dupla listagem, um grupo só)
    'CCL.L^E26': 'CCL.N',        # Carnival UK Ltd (RIC antigo da mesma estrutura)
    'INLJ.J': 'INVP.L',          # Investec Ltd -> Investec plc (dupla listagem)
    'BEPC.N': 'BEP_u.TO',        # Brookfield Renewable Corp -> Brookfield Renewable Partners (títulos pareados)
}
# Fora do painel financeiro: holding cujo balanço consolidado é o da controlada já presente
DROP_FROM_PANEL = ['HEIO.AS']    # Heineken Holding NV (balanço = Heineken NV, HEIN.AS)
FINANCIALS = ['Banking Services', 'Insurance', 'Investment Banking & Investment Services',
              'Residential & Commercial REITs', 'Collective Investments', 'Investment Holding Companies']


def region(hq):
    if hq == 'United States of America': return 'US'
    if hq == 'United Kingdom': return 'UK'
    if hq in ('Sweden', 'Denmark', 'Norway'): return 'Nordic'
    if hq == 'Canada': return 'Canada'
    return 'Europe' if hq in EUROPE else 'Other'


def subset(df, panel):
    return df if panel == 'Total' else df[df['Region_HQ'] == panel]


def stars(p):
    return '***' if p < 0.01 else '**' if p < 0.05 else '*' if p < 0.10 else ''


def winsorise(s, lo=0.01, hi=0.99):
    return s.clip(s.quantile(lo), s.quantile(hi))


def zscore(s):
    sd = s.std(ddof=0)
    return (s - s.mean()) / sd if sd > 0 else s * np.nan



# 1. Dados

def load(args):
    """Lê descritivos, dados financeiros e a saída do 01 e casa cada transcript com a firma-trimestre.

    Passos: (a) sede e região de cada firma; (b) junta os 13 arquivos financeiros (1.350 firmas x 42 trimestres);
    (c) tira transcripts com erro de leitura; (d) fica o maior arquivo do mesmo dia; (e) casa por RIC e trimestre.
    
    """
    log = {}
    # Descritivos por firma
    desc = pd.concat([pd.read_excel(f, sheet_name='Extraction') for f in args.desc], ignore_index=True)
    desc['HQ'] = desc['Country of Headquarters'].replace('NULL', np.nan).fillna(desc['Country of Exchange'])
    desc['Region_HQ'] = desc['HQ'].map(region)
    desc = desc[['RIC', 'Company Name', 'HQ', 'Region_HQ', 'TRBC Industry Group Name']].drop_duplicates('RIC')
    # Mesma empresa com mais de um RIC (classes de ação, dupla listagem, troca de ticker): ver abaixo
    groups = desc.groupby('Company Name')['RIC'].apply(list)
    groups = groups[groups.str.len() > 1]

    # Painel financeiro
    fin = pd.concat([pd.read_excel(f, sheet_name='Extraction', dtype={'Quarter End Date': str})
                     for f in sorted(glob.glob(os.path.join(args.fin, 'LSEG_ChungPruitt_*.xlsx')))],
                    ignore_index=True)
    for c in ['Market Cap (USD)', 'Tobins Q (Chung-Pruitt)', 'Tobins Q (simplificado)', 'Leverage', 'ROA', 'Total Assets (USD)']:
        fin[c] = pd.to_numeric(fin[c], errors='coerce')
    fin = fin.rename(columns={'Quarter End Date': 'qkey', 'Market Cap (USD)': 'MktCap',
                              'Tobins Q (Chung-Pruitt)': 'Q_CP', 'Tobins Q (simplificado)': 'Q_S', 'Total Assets (USD)': 'TA'})
    fin = fin[['RIC', 'qkey', 'MktCap', 'Q_CP', 'Q_S', 'Leverage', 'ROA', 'TA']]
    fin = fin.merge(desc.drop(columns='Company Name'), on='RIC', how='left')
    log['Painel financeiro: firmas'] = fin['RIC'].nunique()
    log['Painel financeiro: firma-trimestres'] = len(fin)

    # Transcripts
    nlp = pd.read_csv(args.nlp, dtype={'Event ID': str}, low_memory=False)
    log['Transcripts lidos pelo NLP'] = len(nlp)
    nlp = nlp[nlp['read_status'] == 'ok'].copy()
    # Um RIC por empresa: o RIC "canônico" é o que tem mais transcripts (empate: sem '^', ordem
    # alfabética). Transcripts dos outros RICs da mesma empresa passam para o canônico; os outros RICs
    # saem do painel financeiro (evita a mesma empresa duas vezes no painel completo, versão V1).
    n_by_ric = nlp['RIC'].value_counts()
    canon, dropped = {}, []
    for rics in groups:
        best = sorted(rics, key=lambda r: (-n_by_ric.get(r, 0), '^' in r, r))[0]
        for r in rics:
            if r != best:
                canon[r] = best
                dropped.append(r)
    # Casos que o agrupamento por nome não pega: outra classe de ação ou
    # estrutura de dupla listagem do mesmo grupo. Os transcripts passam para o RIC do painel.
    canon.update(SAME_COMPANY_ALIASES)
    dropped += [r for r in SAME_COMPANY_ALIASES if r in set(fin['RIC'])] + DROP_FROM_PANEL
    log['Transcripts remapeados para o RIC canônico'] = int(nlp['RIC'].isin(list(canon)).sum())
    nlp['RIC'] = nlp['RIC'].replace(canon)
    fin = fin[~fin['RIC'].isin(dropped)].copy()
    log['RICs duplicados da mesma empresa removidos do painel'] = len(dropped)
    log['Painel financeiro após remoção de duplicatas: firmas'] = fin['RIC'].nunique()
    log['Painel financeiro após remoção de duplicatas: firma-trimestres'] = len(fin)
    nlp['Date event'] = pd.to_datetime(nlp['Date event'])
    nlp['Quarter event'] = pd.to_datetime(nlp['Quarter event'])
    nlp = nlp.dropna(subset=['RIC', 'Date event'])
    nlp['qkey'] = nlp['Quarter event'].dt.strftime('%Y%m%d')
    log['Transcripts com nome válido'] = len(nlp)
    if 'File Size' in nlp.columns:
        nlp = (nlp.sort_values('File Size', ascending=False)
                  .drop_duplicates(['RIC', 'Date event']).sort_index())
    log['Transcripts após regra do mesmo dia (maior arquivo)'] = len(nlp)

    nlp = nlp.drop(columns=[c for c in ['Region_HQ', 'HQ', 'TRBC Industry Group Name', 'MktCap'] if c in nlp.columns])
    # Casamento transcript x painel financeiro (RIC + trimestre); lnMktCap do fim do trimestre
    m = nlp.merge(fin[['RIC', 'qkey', 'MktCap', 'Region_HQ', 'HQ', 'TRBC Industry Group Name']],
                  on=['RIC', 'qkey'], how='left', indicator=True)
    log['Transcripts sem RIC no painel financeiro'] = int((~m['RIC'].isin(fin['RIC'])).sum())
    log['Transcripts com RIC no painel mas sem o trimestre'] = int(
        ((m['_merge'] == 'left_only') & m['RIC'].isin(fin['RIC'])).sum())
    m = m[m['_merge'] == 'both'].drop(columns='_merge')
    m = m[m['MktCap'] > 0].copy()
    m['lnMktCap'] = np.log(m['MktCap'])
    log['Transcripts casados com market cap (amostra de validação)'] = len(m)
    log['Firmas na amostra de validação'] = m['RIC'].nunique()
    return fin, m, log


# 2. Validação (Tabelas 3 e 4)

def table2(tr):
    """Equação (5): uma regressão por mineral ou placebo e por painel, com as quatro tecnologias juntas.

    Modelo de probabilidade linear, erro padrão por firma. Painéis com menos de 5 firmas ficam de fora.
    
    """
    rows = []
    for panel in PANELS:
        d = subset(tr, panel)
        if d['RIC'].nunique() < 5:
            continue
        for dep in MINERALS + PLACEBOS:
            if d[dep].std() == 0:
                continue
            f = pf.feols(f"{dep} ~ {' + '.join(TECHS)} + lnMktCap | RIC + qkey", data=d, vcov={'CRV1': 'RIC'})
            for t in TECHS:
                rows.append({'Painel': panel, 'Tecnologia': LABEL[t], 'Dependente': LABEL[dep],
                             'beta': f.coef()[t], 'se': f.se()[t], 'p': f.pvalue()[t],
                             'cell': f"{f.coef()[t]:.4f}{stars(f.pvalue()[t])}", 'N': f._N,
                             'Firmas': d['RIC'].nunique(), 'R2': f._r2})
    return pd.DataFrame(rows)


# 3. Setores (Tabela 5)

def table3(tr):
    """Porcentagem de transcripts que mencionam cada mineral, por grupo TRBC com 5 ou mais firmas."""
    g = tr.groupby('TRBC Industry Group Name')
    t = g[MINERALS].mean() * 100
    t.columns = [LABEL[c] for c in MINERALS]
    t['Average'] = t.mean(axis=1)
    counts = pd.DataFrame({'Firmas': g['RIC'].nunique()})
    for r in ['US', 'UK', 'Nordic', 'Canada', 'Europe']:
        counts[f'Firmas {r}'] = tr[tr['Region_HQ'] == r].groupby('TRBC Industry Group Name')['RIC'].nunique()
    t = counts.fillna(0).astype(int).join(t)
    return t[t['Firmas'] >= 5].sort_values('Average', ascending=False).head(20).round(2)


# 4. Q de Tobin (Equação 6)

def firm_quarter(fin, tr):
    """Painel firma-trimestre: cada mineral vale 1 se apareceu em alguma call do trimestre;
    Composite = soma dos cinco (0 a 5). Trimestre sem call recebe 0 (só importa na versão V1).
    
    """
    agg = tr.groupby(['RIC', 'qkey']).agg(n_calls=('File Name', 'size'),
                                          **{c: (c, 'max') for c in MINERALS + ['Mineral_Lithium_Unmasked']})
    agg = agg.reset_index()
    p = fin.merge(agg, on=['RIC', 'qkey'], how='left')
    p['has_call'] = p['n_calls'].notna().astype(int)
    for c in MINERALS + ['Mineral_Lithium_Unmasked', 'n_calls']:
        p[c] = p[c].fillna(0).astype(int)
    p['Composite'] = p[MINERALS].sum(axis=1)
    p['Composite_Unmasked'] = p[['Mineral_Lithium_Unmasked'] + MINERALS[1:]].sum(axis=1)
    return p


def est_sample(p, qvar, version):
    """Amostra das regressões do Q: V2 = só trimestres com call; V1 = todos.
    Tira financeiras, exige Q e controles e winsoriza Q, alavancagem e ROA em 1% e 99%.
    
    """
    d = p[p['has_call'] == 1] if version == 'V2' else p
    d = d[~d['TRBC Industry Group Name'].isin(FINANCIALS)]
    d = d.dropna(subset=[qvar, 'Leverage', 'ROA', 'MktCap'])
    d = d[d['MktCap'] > 0].copy()
    for c in [qvar, 'Leverage', 'ROA']:
        d[c] = winsorise(d[c])
    d['lnMktCap'] = np.log(d['MktCap'])
    d['lnTA'] = np.log(d['TA'].where(d['TA'] > 0))
    # Controle de tamanho das regressões do Q (caminhos.SIZE); o ativo total existe em todas as firmas-trimestre
    d['Size'] = d[SIZE]
    assert d['Size'].notna().all(), 'tamanho ausente na amostra de estimação'
    return d.rename(columns={qvar: 'Q'})


def fit_q(d, var):
    """Equação (6): Q sobre a exposição padronizada (z-score dentro do painel), tamanho, alavancagem e ROA,
    com efeitos fixos de firma e trimestre. O beta é o efeito de 1 desvio-padrão.
    
    """
    if d['RIC'].nunique() < 5:
        return None
    d = d.copy()
    d['MR'] = zscore(d[var].astype(float))
    if d['MR'].isna().all():
        return None
    return pf.feols("Q ~ MR + Size + Leverage + ROA | RIC + qkey", data=d, vcov={'CRV1': 'RIC'})


def table4(p, qvar, version):
    """Os cinco minerais e o composto nos seis painéis, para uma medida de Q e uma versão da amostra."""
    base = est_sample(p, qvar, version)
    rows = []
    for var in MINERALS + ['Composite']:
        for panel in PANELS:
            d = subset(base, panel)
            f = fit_q(d, var)
            if f is None:
                rows.append({'MineralRisk': LABEL[var], 'Painel': panel, 'cell': '--'})
                continue
            rows.append({'MineralRisk': LABEL[var], 'Painel': panel, 'beta': f.coef()['MR'],
                         'se': f.se()['MR'], 'p': f.pvalue()['MR'],
                         'cell': f"{f.coef()['MR']:.4f}{stars(f.pvalue()['MR'])}", 'N': f._N,
                         'Firmas': d['RIC'].nunique(), 'Firmas que mencionam': d.loc[d[var] > 0, 'RIC'].nunique()})
    return pd.DataFrame(rows)


def leave_one_out(p):
    """Terras raras nos EUA, tirando uma por vez cada firma que menciona terras raras.
    A primeira linha é a amostra completa.
    
    """
    us = subset(est_sample(p, 'Q_CP', 'V2'), 'US')
    firms = us.loc[us['Mineral_RareEarths'] == 1, 'RIC'].value_counts()
    out = []
    f = fit_q(us, 'Mineral_RareEarths')
    out.append({'Retirada': 'Nenhuma (amostra US completa)', 'beta': f.coef()['MR'], 'se': f.se()['MR'],
                'p': f.pvalue()['MR'], 'N': f._N})
    for ric, k in firms.items():
        f = fit_q(us[us['RIC'] != ric], 'Mineral_RareEarths')
        out.append({'Retirada': ric, 'Trimestres com menção': k, 'beta': f.coef()['MR'], 'se': f.se()['MR'],
                    'p': f.pvalue()['MR'], 'N': f._N})
    out = pd.DataFrame(out)
    out['cell'] = [f"{b:.4f}{stars(q)}" for b, q in zip(out['beta'], out['p'])]
    return out


# 5. Tendências (Figuras 2 a 7)

def trends(tr):
    """Figuras 2 a 7: porcentagem de transcripts com algum mineral, por trimestre e painel,
    separando quem fala de tecnologia limpa de quem não fala.
    
    """
    t = tr.copy()
    t['any_mineral'] = t[MINERALS].max(axis=1)
    t['exposed'] = t[TECHS].max(axis=1)
    rows = []
    for panel in PANELS:
        d = subset(t, panel)
        g = d.groupby(['qkey', 'exposed'])['any_mineral'].agg(['mean', 'std', 'size']).reset_index()
        g.insert(0, 'Painel', panel)
        rows.append(g)
    return pd.concat(rows, ignore_index=True)


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--nlp', default=config.NLP_CSV)
    ap.add_argument('--fin', default=config.PASTA_FINANCEIROS)
    ap.add_argument('--desc', nargs='+', default=config.DESCRITIVOS)
    ap.add_argument('--out', default=config.SAIDA_EST)
    args = ap.parse_args()
    for f in [args.nlp] + list(args.desc):
        if not os.path.isfile(f):
            sys.exit(f"Arquivo não encontrado: {f}\nAjuste caminhos.py (ou rode antes o 01_nlp.py).")
    os.makedirs(args.out, exist_ok=True)

    fin, tr, log = load(args)
    print('\n'.join(f'{k}: {v:,}' for k, v in log.items()))
    p = firm_quarter(fin, tr)

    res = {'T2_Validacao': table2(tr), 'T3_Setores': table3(tr)}
    for q, qn in [('Q_CP', 'CP'), ('Q_S', 'Simpl')]:
        for v in ['V2', 'V1']:
            res[f'T4_{qn}_{v}'] = table4(p, q, v)
    res['C_LeaveOneOut'] = leave_one_out(p)
    res['Tendencias'] = trends(tr)

    s = est_sample(p, 'Q_CP', 'V2')
    log['Tobin V2 C&P: firma-trimestres'] = len(s)
    log['Tobin V2 C&P: firmas'] = s['RIC'].nunique()
    log['Financeiras excluídas (firmas)'] = fin.loc[fin['TRBC Industry Group Name'].isin(FINANCIALS), 'RIC'].nunique()
    for r in PANELS:
        log[f'Firmas validação {r}'] = subset(tr, r)['RIC'].nunique()
        log[f'Transcripts validação {r}'] = len(subset(tr, r))
    res['Amostra'] = pd.DataFrame(list(log.items()), columns=['Item', 'Valor'])

    with pd.ExcelWriter(os.path.join(args.out, 'Resultados_Dissertacao.xlsx')) as w:
        for k in ['Amostra'] + [k for k in res if k != 'Amostra']:
            res[k].to_excel(w, sheet_name=k, index=(k == 'T3_Setores'))
    p.to_pickle(os.path.join(args.out, 'painel_firma_trimestre.pkl'))
    tr.to_pickle(os.path.join(args.out, 'amostra_validacao.pkl'))
    print('Pronto:', args.out)


if __name__ == '__main__':
    main()
