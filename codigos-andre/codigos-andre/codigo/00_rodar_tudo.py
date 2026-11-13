"""
Roda tudo na ordem certa: o painel, as regressões, as figuras, as tabelas e as conferências.

  02        painel firma-trimestre, validação e setores
  04        confere o Q de Tobin nas planilhas da LSEG
  05 a 16   regressões: valor da firma (05 a 10), CRMA (11 a 13), China (14 a 16)
  17 a 19   figuras
  20 a 23   tabelas
  24        confere as tabelas da dissertação contra os resultados

O 01 e o 03 ficam de fora porque leem os transcripts (.txt). Demora cerca de 1h30.
"""
import os, subprocess, sys, time
AQUI = os.path.dirname(os.path.abspath(__file__))
ORDEM = ['02_estimacao.py', '04_conferir_q.py',
         # regressões
         '05_valuation.py', '06_robustez_q.py', '07_tempo_q.py', '08_medicao_terras_raras.py', '09_auditoria_terras_raras.py',
         '10_q_extras.py', '11_ddd_crma.py', '12_ddd_europa.py', '13_ddd_extras.py', '14_china.py', '15_china_loio.py',
         '16_china_extras.py',
         # figuras
         '17_fig_tendencias.py', '18_fig_crma.py', '19_fig_china.py',
         # tabelas
         '20_tabelas_base.py', '21_descritivas.py', '22_tabelas_ddd_apendice.py', '23_tabelas_apendice.py',
         # conferência final
         '24_conferencia.py']
# saída em UTF-8 (no Windows, sem isso o log não imprime o β)
ENV = dict(os.environ, PYTHONIOENCODING='utf-8')
so = sys.argv[1:]  # para rodar só alguns: python 00_rodar_tudo.py 11_ddd_crma.py 18_fig_crma.py
for s in (so or ORDEM):
    t0 = time.time(); print(f'>>> {s}', flush=True)
    r = subprocess.run([sys.executable, os.path.join(AQUI, s)], cwd=AQUI, env=ENV)
    print(f'<<< {s}: {"ok" if r.returncode == 0 else "ERRO " + str(r.returncode)} ({(time.time() - t0) / 60:.1f} min)', flush=True)
    if r.returncode != 0:
        sys.exit(r.returncode)
