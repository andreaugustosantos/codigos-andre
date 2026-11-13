"""
Monta a planilha da classificação manual das menções a terras raras nos EUA (Tabela 18, linhas 18 e 19).

Pega as 57 firmas-trimestre da amostra dos EUA com menção a terras raras, abre os transcripts e extrai cada
menção com o parágrafo, a seção (apresentação ou perguntas) e quem fala.
Gera resultados/auditoria_terras_raras_EUA.xlsx com três abas: mencoes, firma_trim e codigos (o livro de códigos).

Uso: python 03_extrair_terras_raras_eua.py [pasta dos transcripts]. Precisa dos .txt e do 02 rodado antes.
"""
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__))); from caminhos import *  # noqa
import importlib.util, os, re, sys, warnings
import pandas as pd
warnings.filterwarnings('ignore')
import caminhos as config
spec = importlib.util.spec_from_file_location('e', EST_PY); E = importlib.util.module_from_spec(spec); spec.loader.exec_module(E)

PASTA = sys.argv[1] if len(sys.argv) > 1 else config.PASTA_TRANSCRIPTS
TERMS = ['rare earths', 'rare earth', 'cerium', 'lanthanum', 'praseodymium', 'neodymium', 'promethium', 'europium',
         'gadolinium', 'samarium', 'dysprosium', 'yttrium', 'terbium', 'holmium', 'erbium', 'thulium', 'ytterbium',
         'lutetium', 'scandium']
# No texto original, "rare earth" aparece também como "rare-earth" e "rareearth"; o 01_nlp.py remove o hífen.
RX = re.compile(r'\b(rare[\s\-]?earths?|' + '|'.join(t for t in TERMS if ' ' not in t) + r')\b', re.I)
HEAD = re.compile(r'^(?P<who>[^\n\[]{2,}?)\s{2,}\[(?P<n>\d+)\]\s*$', re.M)

# ---------------- 1. As 57 firmas-trimestre e os transcripts correspondentes
p = pd.read_pickle(f'{R02}/painel_firma_trimestre.pkl')
tr = pd.read_pickle(f'{R02}/amostra_validacao.pkl')
us = E.subset(E.est_sample(p, 'Q_CP', 'V2'), 'US')
fq = us.loc[us['Mineral_RareEarths'] == 1, ['RIC', 'qkey']].drop_duplicates()
print('Firmas-trimestre com menção (EUA, amostra de estimação):', len(fq), '| firmas:', fq.RIC.nunique())
tr['qkey'] = pd.to_datetime(tr['Quarter event']).dt.strftime('%Y%m%d')
files = tr[tr['Mineral_RareEarths'] == 1].merge(fq, on=['RIC', 'qkey'])
names = p.drop_duplicates('RIC').set_index('RIC')['Company Name'] if 'Company Name' in p else pd.Series(dtype=str)
if names.empty:
    desc = pd.concat([pd.read_excel(f, sheet_name='Extraction') for f in DESC]).drop_duplicates('RIC').set_index('RIC')
    names = desc['Company Name']
print('Transcripts a ler:', len(files))

# ---------------- 2. Índice dos .txt
index = {}
for root, _, fs in os.walk(PASTA):
    for f in fs:
        if f.lower().endswith('.txt') and f not in index:
            index[f] = os.path.join(root, f)
missing = [f for f in files['File Name'] if f not in index]
if missing:
    print(f'AVISO: {len(missing)} transcripts não encontrados em {PASTA}:', missing[:5])

# ---------------- 3. Extração
def paragraph(text, i, j):
    a = text.rfind('\n', 0, i) + 1; b = text.find('\n', j); b = len(text) if b < 0 else b
    par = text[a:b].strip()
    if len(par) > 1200:  # parágrafo muito longo: recorta em volta da menção
        k = i - a; par = ('...' if k > 600 else '') + par[max(0, k - 600):k + 600] + '...'
    return par

rows = []
for _, r in files.iterrows():
    path = index.get(r['File Name'])
    if path is None: continue
    text = open(path, encoding='utf-8', errors='replace').read().replace('\r', '')
    qa = text.find('Questions and Answers')
    heads = [(m.start(), m.group('who').strip()) for m in HEAD.finditer(text)]
    for k, m in enumerate(RX.finditer(text), 1):
        who = [h for h in heads if h[0] < m.start()]
        who = who[-1][1] if who else ''
        rows.append({'id': f"{r['RIC']}_{r['qkey']}_{k}", 'Empresa': names.get(r['RIC'], ''), 'RIC': r['RIC'],
                     'Trimestre': r['qkey'], 'Data da call': pd.to_datetime(r['Date event']).date(), 'Arquivo': r['File Name'],
                     'Seção': 'Perguntas e respostas' if 0 <= qa < m.start() else 'Apresentação',
                     'Quem fala': who, 'Analista?': 'sim' if re.search(r'analyst', who, re.I) else 'não',
                     'Termo': m.group(0), 'Trecho': paragraph(text, m.start(), m.end()),
                     'C1 Refere-se à firma': '', 'C2 Natureza': '', 'C3 Tom': '', 'C4 Incidental': '', 'Notas': ''})
men = pd.DataFrame(rows)
print('Ocorrências extraídas:', len(men))

fqt = fq.copy(); fqt['Empresa'] = fqt.RIC.map(names)
if len(men):
    agg = men.groupby(['RIC', 'Trimestre']).agg(ocorrencias=('id', 'size'), termos=('Termo', lambda s: ', '.join(sorted(set(t.lower() for t in s)))),
                                                arquivos=('Arquivo', 'nunique')).reset_index().rename(columns={'Trimestre': 'qkey'})
    fqt = fqt.merge(agg, on=['RIC', 'qkey'], how='left')
fqt['D1 Exposição da firma a terras raras como insumo (sim/não)'] = ''
fqt['D2 Menção só incidental (sim/não)'] = ''
fqt['Notas'] = ''
codes = pd.DataFrame([
    ('C1 Refere-se à firma', 'sim: o trecho trata da própria firma (insumos, produtos, fornecedores, operações); não: fala de terceiros, do setor ou da economia em geral'),
    ('C2 Natureza', '1 insumo ou custo; 2 risco de oferta, preços ou geopolítica (China, controles de exportação); 3 estratégia de mitigação (contratos, estoques, fornecedores alternativos, reciclagem); 4 produto ou receita (a firma vende ou produz o mineral); 5 política pública (CRMA, IRA, tarifas, defesa); 6 outro sentido do termo (medicamento, contraste de ressonância, química fina)'),
    ('C3 Tom', 'negativo (preocupação, custo, risco), neutro, positivo (oportunidade, vantagem, segurança de suprimento)'),
    ('C4 Incidental', 'sim: a menção não diz nada sobre exposição da firma (ex.: lista de commodities, nome de fundo, citação de terceiro)'),
    ('D1', 'Decisão por firma-trimestre: a menção indica exposição da firma a terras raras como insumo ou risco de oferta?'),
    ('D2', 'Decisão por firma-trimestre: todas as menções do trimestre são incidentais?'),
], columns=['Código', 'Definição'])
out = f'{RES}/auditoria_terras_raras_EUA.xlsx'
with pd.ExcelWriter(out) as w:
    men.to_excel(w, sheet_name='mencoes', index=False)
    fqt.to_excel(w, sheet_name='firma_trim', index=False)
    codes.to_excel(w, sheet_name='codigos', index=False)
print('Pronto:', out)
