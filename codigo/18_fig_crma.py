"""
Figura 8: estudo de evento do CRMA, a partir de ddd_nt.pkl (saída do 11, sem telecom).
IC de 95%: b +/- t(0,975; G-1) x EP, com G = número de firmas do pareamento.
"""
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__))); from caminhos import *  # noqa
import pickle, sys
import numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from scipy import stats

PKL = sys.argv[1] if len(sys.argv) > 1 else f'{RES}/ddd_nt.pkl'
OUT = sys.argv[2] if len(sys.argv) > 2 else FIG + '/Graph_EventStudy_CRMA.png'
R = pickle.load(open(PKL, 'rb'))
G = int(R['T7'].iloc[0]['firms']) if 'firms' in R['T7'].columns else 272
crit = stats.t.ppf(0.975, G - 1)

es = R['ES'][R['ES'].q != 'early'].copy()
es = pd.concat([es, pd.DataFrame([dict(q='20220630', b=0.0, se=0.0, p=np.nan)])]).sort_values('q').reset_index(drop=True)
es['lab'] = [f"{q[:4]}Q{(int(q[4:6]) - 1) // 3 + 1}" for q in es.q]
es['lo'] = es.b - crit * es.se; es['hi'] = es.b + crit * es.se

plt.rcParams.update({'font.family': 'serif', 'font.size': 11})
fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
x = np.arange(len(es))
ax.axhline(0, color='black', lw=0.8)
ax.errorbar(x, es['b'], yerr=[es['b'] - es['lo'], es['hi'] - es['b']], fmt='o', color='black',
            ecolor='#7f7f7f', elinewidth=1.4, capsize=3, ms=4.5)
ymax = ax.get_ylim()[1]
pos = {q: i for i, q in enumerate(es['lab'])}
for q, lab in [('2022Q3', 'Announcement'), ('2023Q1', 'Proposal'), ('2023Q4', 'Political Agreement'),
               ('2024Q2', 'EU CRM Act in Force')]:
    xv = pos[q] - 0.5
    ax.axvline(xv, color='darkred', ls='--', lw=1, alpha=0.8)
    ax.text(xv, ymax, lab, rotation=90, color='darkred', ha='right', va='top', fontsize=9.5)
ax.set_xticks(x)
ax.set_xticklabels(es['lab'], rotation=60, fontsize=9)
ax.set_xlabel('Quarter (reference 2022Q2, the last quarter before the announcement)')
ax.set_ylabel("Coefficient on EU × High × Quarter (Tobin's Q)")
ax.spines[['top', 'right']].set_visible(False)
fig.tight_layout()
fig.savefig(OUT, bbox_inches='tight')
print('ok', OUT, 'G', G, 'crit', round(crit, 3))
