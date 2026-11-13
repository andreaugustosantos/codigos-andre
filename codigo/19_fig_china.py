"""
Figura 9: estudo de evento dos controles chineses, a partir de china.pkl (saída do 14).
Painel A: menção a terras raras. Painel B: Q de Tobin.
"""
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__))); from caminhos import *  # noqa
import pickle, sys
import numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt

PKL = sys.argv[1] if len(sys.argv) > 1 else f'{RES}/china.pkl'
OUT = sys.argv[2] if len(sys.argv) > 2 else FIG + '/Graph_EventStudy_China.png'
R = pickle.load(open(PKL, 'rb'))
plt.rcParams.update({'font.family': 'serif', 'font.size': 11})
fig, axs = plt.subplots(1, 2, figsize=(11, 5.2))
def ql(q): y = int(q[:4]); m = int(q[4:6]); return f"{y}Q{(m-1)//3+1}"
for ax, es, ttl, yl in [(axs[0], R['A_es'], 'A. Rare-earth mention', 'Coefficient (probability of a mention)'),
                        (axs[1], R['B_es'], "B. Tobin's Q", "Coefficient (Tobin's Q)")]:
    es = pd.concat([es, pd.DataFrame([dict(q='20250331', b=0.0, se=0.0, p=np.nan)])]).sort_values('q').reset_index(drop=True)
    x = np.arange(len(es)); labs = [ql(q) for q in es.q]
    ax.errorbar(x, es.b, yerr=1.96 * es.se, fmt='o', color='black', ms=3.5, ecolor='grey', elinewidth=1, capsize=2.5)
    ax.axhline(0, color='black', lw=0.8)
    pos = {l: i for i, l in enumerate(labs)}
    top = (es.b + 1.96 * es.se).max(); bot = (es.b - 1.96 * es.se).min()
    ax.set_ylim(bot - 0.05 * (top - bot), top + 0.40 * (top - bot))  # espaço para os rótulos acima dos intervalos
    for after, txt in [('2025Q1', 'Export controls'), ('2025Q3', 'Second wave')]:
        xv = pos[after] + 0.5; ax.axvline(xv, color='#c0392b', ls='--', lw=0.9)
        ax.text(xv - 0.12, 0.99, txt, color='#c0392b', rotation=90, va='top', ha='right', fontsize=9.5, transform=ax.get_xaxis_transform())
    ax.set_xticks(x); ax.set_xticklabels(labs, rotation=60, fontsize=9); ax.set_ylabel(yl)
    ax.set_title(ttl, loc='left', fontweight='bold', fontsize=11)
    for s in ['top', 'right']: ax.spines[s].set_visible(False)
fig.tight_layout(); fig.savefig(OUT, dpi=300)
print('ok', OUT)
