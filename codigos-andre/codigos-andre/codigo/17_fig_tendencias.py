"""
Figuras 2 a 7: tendência das menções a minerais críticos.

Porcentagem de transcripts que mencionam algum dos cinco minerais, por trimestre, para firmas que falam de tecnologia
limpa (linha cheia) e as demais (tracejada). Média móvel de 4 trimestres, com intervalo de 95%.
Linhas verticais: guerra na Ucrânia (24/02/2022), CRMA (23/05/2024) e controles chineses (04/04/2025).
O lítio entra com a máscara das frases de bateria.
Saída: Graph_Panel_A_Total.png a Graph_Panel_F_Europe.png (pasta SAIDA_FIG)
"""

import os
import sys

import matplotlib
import numpy as np
import pandas as pd
from scipy import stats

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import caminhos as config  # noqa: E402

MINERALS = ['Mineral_Lithium', 'Mineral_Cobalt', 'Mineral_Nickel', 'Mineral_Copper', 'Mineral_RareEarths']
TECHS = ['Tech_LithiumIon', 'Tech_EV', 'Tech_Solar', 'Tech_Wind']
EVENTS = [('Ukraine War', '2022-02-24'), ('EU CRM Act', '2024-05-23'), ('China Restrictions', '2025-04-04')]
PANELS = {'Total': 'Total Market', 'US': 'US Panel', 'UK': 'UK Panel', 'Nordic': 'Nordic Panel',
          'Canada': 'Canada Panel', 'Europe': 'Europe Panel'}
FILES = {'Total': 'Graph_Panel_A_Total', 'US': 'Graph_Panel_B_US', 'UK': 'Graph_Panel_C_UK',
         'Nordic': 'Graph_Panel_D_Nordic', 'Canada': 'Graph_Panel_E_Canada', 'Europe': 'Graph_Panel_F_Europe'}


def main(est_dir=config.SAIDA_EST, out_dir=config.SAIDA_FIG):
    src = os.path.join(est_dir, 'amostra_validacao.pkl')
    if not os.path.isfile(src):
        sys.exit(f"Não encontrei {src}. Rode antes o 02_estimacao.py.")
    os.makedirs(out_dir, exist_ok=True)
    tr = pd.read_pickle(src)
    tr['pct'] = tr[MINERALS].max(axis=1) * 100
    tr['exposed'] = tr[TECHS].max(axis=1)
    tr['q'] = pd.to_datetime(tr['qkey'])
    plt.rcParams.update({'font.family': 'serif', 'font.size': 11})

    for panel in PANELS:
        d = tr if panel == 'Total' else tr[tr['Region_HQ'] == panel]
        fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
        ymax = 0
        for g, col, ls, lab in [(0, '#7f7f7f', '--', 'Does not mention a clean energy technology'), (1, 'black', '-', 'Mentions a clean energy technology')]:
            a = d[d['exposed'] == g].groupby('q')['pct'].agg(['mean', 'std', 'size']).sort_index()
            se = a['std'] / np.sqrt(a['size'])
            tq = stats.t.ppf(0.975, np.maximum(a['size'] - 1, 1))
            m = a['mean'].rolling(4).mean()
            lo = (a['mean'] - tq * se).rolling(4).mean()
            hi = (a['mean'] + tq * se).rolling(4).mean()
            ok = m.notna()
            ax.fill_between(m.index[ok], lo[ok], hi[ok], color=col, alpha=0.2, lw=0)
            ax.plot(m.index[ok], m[ok], color=col, ls=ls, lw=1.6, marker='o', ms=3.5, label=lab)
            ymax = max(ymax, np.nanmax(hi[ok]))
        for name, dt in EVENTS:
            x = pd.Timestamp(dt)
            ax.axvline(x, color='darkred', ls='--', lw=1, alpha=0.8)
            ax.text(x, ymax * 1.02, name, rotation=90, color='darkred', ha='right', va='top', fontsize=9.5)
        ax.set_xlabel('Quarter (four-quarter moving average; first point 2016Q4)')
        ax.set_ylabel('% of Transcripts Mentioning Critical Minerals')
        ax.spines[['top', 'right']].set_visible(False)
        ax.set_ylim(bottom=0)
        ax.legend(loc='upper center', frameon=False, ncol=2, bbox_to_anchor=(0.5, -0.11))
        fig.tight_layout()
        fig.savefig(os.path.join(out_dir, FILES[panel] + '.png'), bbox_inches='tight')
        plt.close(fig)
    print('Pronto:', out_dir)


if __name__ == '__main__':
    main(*sys.argv[1:3])
