"""
Lê os transcripts e marca, em cada um, se ele menciona cada mineral, cada tecnologia limpa e os placebos.

RIC, data e trimestre saem do nome do arquivo da LSEG (AAAA-Mmm-DD-<RIC>-<EventID>-Transcript.txt).
O trimestre é o fim do trimestre civil da call (ex.: 2021-04-01 vira 2021-06-30).

Os dicionários são os do estudo companheiro (Mendes-da-Silva et al., 2026), aqui chamado de R1, com dois ajustes:
  1. Lítio: antes de procurar "lithium" como mineral, as frases de bateria ("lithium ion battery" etc.)
     são mascaradas. Sem isso, toda menção a bateria de lítio-íon contaria também como menção ao mineral.
  2. Hífen: a limpeza do texto apaga hífens, então "lithium-ion" vira "lithiumion" e "Li-ion" vira "liion".
     Essas formas entram no dicionário de baterias.

Saídas (pasta SAIDA_NLP):
  Processed_Data_Dissertacao.csv   uma linha por transcript, com as marcações 0/1 (entra no 02)
  Term_Frequencies.csv             quantas vezes cada termo aparece
  diagnostico.txt                  contagens e arquivos que não abriram
  txt_name_collisions.csv          arquivos repetidos em duas pastas, se houver

Para rodar, ajuste PASTA_TRANSCRIPTS em caminhos.py. Com os 41.701 arquivos, leva umas 2h30.
"""

import os
import re
import sys
from collections import Counter

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import caminhos as config  # noqa: E402


# 1. Dicionários (os do estudo companheiro, R1)

MINERALS = {
    'Mineral_Lithium': ['lithium', 'lithiums', 'spodumene'],
    'Mineral_Cobalt': ['cobalt', 'cobalts', 'cobaltite', 'cobaltate'],
    'Mineral_Nickel': ['nickel', 'nickels', 'laterite'],
    'Mineral_Copper': ['copper', 'coppers', 'chalcopyrite'],
    'Mineral_RareEarths': ['rare earth', 'rare earths', 'rareearth', 'rareearths',
                           'cerium', 'lanthanum', 'praseodymium', 'neodymium', 'promethium',
                           'europium', 'gadolinium', 'samarium', 'dysprosium', 'yttrium',
                           'terbium', 'holmium', 'erbium', 'thulium', 'ytterbium', 'lutetium', 'scandium'],
}

TECH_R1 = {
    'Tech_LithiumIon': ['ion battery', 'lithium ion battery', 'lithium ion batteries',
                        'lithium batteries', 'ion batteries', 'lithium polymer',
                        'lithium ion', 'lithium battery'],
    'Tech_EV': ['hybrid vehicle', 'electric vehicle', 'electric motorcycle',
                'vehicle charging', 'hybrid electric', 'plugin hybrids',
                'electric buses', 'electrical vehicles', 'electric car', 'electric vehicles'],
    'Tech_Solar': ['solar power', 'solar energy', 'solar business', 'solar cell', 'solar projects',
                   'solar market', 'solar capital', 'solar industry', 'solar cells', 'solar panels',
                   'solar project', 'solar panel', 'solar pv', 'solar module', 'solar modules',
                   'solar side', 'solar technology', 'solar farm', 'solar products', 'solar assets',
                   'solar systems', 'solar industries', 'solar generation', 'solar pwr', 'solar markets',
                   'solar wafer', 'solar plant', 'solar grade', 'solar capacity', 'solar facility',
                   'solar farms', 'solar companies', 'solar plants', 'solar installations',
                   'solar equipment', 'solar product', 'solar technologies', 'solar thermal',
                   'solar customers', 'solar segment', 'solar applications', 'solar installation',
                   'solar materials', 'solar facilities', 'solar sales'],
    'Tech_Wind': ['wind power', 'wind energy', 'wind resource', 'onshore wind',
                  'offshore wind', 'wind turbine', 'wind resources', 'wind turbines'],
}

PLACEBOS = {
    'Placebo_Negative': ['cotton'],   # controle negativo: não deve se associar a tecnologia limpa
    'Placebo_Positive': ['energy'],   # controle positivo: deve se associar a todas
}

# Ajuste 2: formas com hífen, como ficam depois da limpeza
HYPHEN_TERMS = ['lithiumion', 'liion', 'lithiumpolymer']
TECH = {k: list(v) for k, v in TECH_R1.items()}
TECH['Tech_LithiumIon'] += HYPHEN_TERMS

# Ajuste 1: frases de bateria mascaradas antes de procurar o lítio (lista do R1).
# As formas hifenizadas não precisam de máscara: "lithiumion" não casa com \blithium\b.
LITHIUM_TECH_PHRASES = [
    'lithium ion battery', 'lithium ion batteries', 'lithium-ion battery', 'lithium-ion batteries',
    'lithium batteries', 'lithium battery', 'lithium polymer', 'lithium ion', 'lithium-ion',
    'ion battery', 'ion batteries',
]

CATEGORIES = {**MINERALS, **TECH, **PLACEBOS}


def alternation(terms):
    """Uma regex por categoria, termo mais longo primeiro, com fronteira de palavra."""
    terms = sorted(terms, key=len, reverse=True)
    return re.compile(r'\b(?:' + '|'.join(re.escape(t) for t in terms) + r')\b')


RX = {k: alternation(v) for k, v in CATEGORIES.items()}
RX_TECH_R1 = alternation(TECH_R1['Tech_LithiumIon'])
RX_MASK = alternation(LITHIUM_TECH_PHRASES)
NAME_RX = re.compile(r'^(\d{4}-[A-Za-z]{3}-\d{2})-(.+)-(\d+)-Transcript\.txt$')


def clean(text):
    """Minúsculas e só letras, números, _ e espaço (por isso o hífen some)."""
    return re.sub(r'[^a-z0-9\s_]', '', text.lower())


def scan(rx, text, counter):
    """Termos encontrados (sem repetir) e atualiza as frequências."""
    hits = [m.group(0) for m in rx.finditer(text)]
    counter.update(hits)
    return list(dict.fromkeys(hits))


def main(transcripts_dir=config.PASTA_TRANSCRIPTS, out_dir=config.SAIDA_NLP):
    if not os.path.isdir(transcripts_dir):
        sys.exit(f"Pasta de transcripts não encontrada: {transcripts_dir}\nAjuste PASTA_TRANSCRIPTS em caminhos.py.")
    os.makedirs(out_dir, exist_ok=True)

    # 2. Índice: nome do arquivo -> caminho (o mesmo arquivo em duas pastas é lido uma vez só)
    index, collisions = {}, []
    for root, _, files in os.walk(transcripts_dir):
        for f in files:
            if f.lower().endswith('.txt'):
                if f in index:
                    collisions.append((f, index[f], os.path.join(root, f)))
                else:
                    index[f] = os.path.join(root, f)
    print(f"Arquivos .txt encontrados: {len(index):,}")
    if collisions:
        pd.DataFrame(collisions, columns=['File Name', 'usado', 'ignorado']).to_csv(
            os.path.join(out_dir, 'txt_name_collisions.csv'), index=False)
        print(f"AVISO: {len(collisions):,} arquivos repetidos em pastas diferentes (ver txt_name_collisions.csv)")

    # 3. Leitura e marcação
    counts, counts_r1 = Counter(), Counter()
    rows = []
    for i, (fname, path) in enumerate(sorted(index.items())):
        m = NAME_RX.match(fname)
        row = {'File Name': fname,
               'Subfolder': os.path.relpath(os.path.dirname(path), transcripts_dir),
               'File Size': os.path.getsize(path),
               'RIC': m.group(2) if m else None,
               'Date event': pd.to_datetime(m.group(1), format='%Y-%b-%d') if m else None,
               'Event ID': m.group(3) if m else None}
        try:
            with open(path, 'r', encoding='utf-8') as fh:
                content = clean(fh.read())
            row['read_status'] = 'ok'
        except Exception as e:  # registra e segue
            row['read_status'] = f'read error: {e!r}'
            rows.append(row)
            continue

        masked = RX_MASK.sub('[TECH_MASKED]', content)
        for key, rx in RX.items():
            found = scan(rx, masked if key == 'Mineral_Lithium' else content, counts)
            row[key] = int(bool(found))
            row[f'{key}_detected'] = '; '.join(found)
        row['Mineral_Lithium_Unmasked'] = int(bool(RX['Mineral_Lithium'].search(content)))
        found = scan(RX_TECH_R1, content, counts_r1)
        row['Tech_LithiumIon_R1'] = int(bool(found))
        rows.append(row)
        if (i + 1) % 1000 == 0:
            print(f"  {i + 1:,} de {len(index):,}")

    df = pd.DataFrame(rows)
    df['Quarter event'] = pd.to_datetime(df['Date event']) + pd.offsets.QuarterEnd(0)

    # 4. Diagnóstico
    ok = df['read_status'] == 'ok'
    flags = list(CATEGORIES) + ['Mineral_Lithium_Unmasked', 'Tech_LithiumIon_R1']
    lines = [f"Arquivos processados:       {len(df):,}",
             f"Lidos com sucesso:          {ok.sum():,}",
             f"Erros de leitura:           {(~ok).sum():,}",
             f"Nome fora do padrão LSEG:   {df['RIC'].isna().sum():,}",
             "", "Transcripts marcados:"]
    lines += [f"  {c:<28} {int(df[c].sum()):>7,}" for c in flags]
    gain = int(((df['Tech_LithiumIon'] == 1) & (df['Tech_LithiumIon_R1'] == 0)).sum())
    lines += ["", f"Transcripts que só entram no Tech_LithiumIon por causa do hífen: {gain:,}"]
    print("\n" + "\n".join(lines))
    with open(os.path.join(out_dir, 'diagnostico.txt'), 'w', encoding='utf-8') as fh:
        fh.write("\n".join(lines) + "\n")

    # 5. Saída
    freq = pd.DataFrame([(k, t, counts[t], 'corrigida') for k, v in CATEGORIES.items() for t in v]
                        + [('Tech_LithiumIon', t, counts_r1[t], 'R1') for t in TECH_R1['Tech_LithiumIon']],
                        columns=['Category', 'Term', 'Frequency', 'Versao'])
    df.to_csv(os.path.join(out_dir, 'Processed_Data_Dissertacao.csv'), index=False, encoding='utf-8')
    freq.to_csv(os.path.join(out_dir, 'Term_Frequencies.csv'), index=False, encoding='utf-8')
    print(f"\nPronto. Resultados em {out_dir}")


if __name__ == '__main__':
    main(*sys.argv[1:3])
