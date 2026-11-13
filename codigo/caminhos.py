"""
Pastas usadas por todos os scripts. Só precisa mexer aqui para reler os transcripts (PASTA_TRANSCRIPTS).

Estrutura esperada (a pasta-mãe é a que tem 'codigo'):
    codigo/        os scripts
    dados/         Processed_Data_Dissertacao.csv, LSEG_Descriptives_UNBALANCED_v2.xlsx,
                   LSEG_Descriptives_EXPANSION.xlsx e a pasta financeiros/ (13 LSEG_ChungPruitt_*.xlsx)
    resultados/    criada pelos scripts.
"""
import os
CODE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('DISS_ROOT', os.path.dirname(CODE))
DADOS = os.path.join(ROOT, 'dados')
FIN = os.path.join(DADOS, 'financeiros')
DESC = [os.path.join(DADOS, 'LSEG_Descriptives_UNBALANCED_v2.xlsx'), os.path.join(DADOS, 'LSEG_Descriptives_EXPANSION.xlsx')]
RES = os.path.join(ROOT, 'resultados')
R02 = os.path.join(RES, '02_estimacao')
FIG = os.path.join(RES, 'figuras')
TEX = os.path.join(RES, 'tabelas')
EST_PY = os.path.join(CODE, '02_estimacao.py')
# Controle de tamanho nas regressões do Q. Principal: log do ativo total.
# Com DISS_SIZE=lnMktCap, usa o log do valor de mercado (Tabela 17, Painel D).
SIZE = os.environ.get('DISS_SIZE', 'lnTA')
ALT_SIZE = 'lnMktCap' if SIZE == 'lnTA' else 'lnTA'
# Tamanho usado no escore de propensão do pareamento do DDD (média de 2021)
PSM_SIZE = os.environ.get('DISS_PSM_SIZE', 'lnMktCap')

# Pasta com os transcripts .txt (só o 01 e o 03 leem). Defina DISS_TRANSCRIPTS ou troque o caminho aqui.
PASTA_TRANSCRIPTS = os.environ.get('DISS_TRANSCRIPTS', os.path.join(ROOT, 'transcripts'))

# Nomes usados pelos scripts 01, 02, 03, 17 e 20
PASTA_FINANCEIROS = FIN
DESCRITIVOS = DESC
PASTA_SAIDA = RES
SAIDA_NLP = os.path.join(RES, '01_nlp')
# Se o 01_nlp.py tiver sido rodado, usa a saída dele; senão, o CSV entregue em dados/
NLP_CSV = os.path.join(SAIDA_NLP, 'Processed_Data_Dissertacao.csv')
if not os.path.isfile(NLP_CSV):
    NLP_CSV = os.path.join(DADOS, 'Processed_Data_Dissertacao.csv')
SAIDA_EST = R02
SAIDA_FIG = FIG
SAIDA_TEX = TEX

for _d in (RES, R02, FIG, TEX):
    os.makedirs(_d, exist_ok=True)
