"""Diferença em diferenças da China tirando um grupo industrial exposto por vez (Tabela 9). Usa as funções do 14."""
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__))); from caminhos import *  # noqa
exec(open(_o.path.join(CODE, '14_china.py'), encoding='utf-8').read().split('# ================= Parte A')[0])
out=[]
for g in NARROW:
    for part,data,y in [('A',calls,'Mineral_RareEarths'),('B',full,'Q')]:
        d=prep(data); d=d[d[IG]!=g]; r=est(d,y); out.append(dict(part=part,excluded=g,**r))
o=pd.DataFrame(out); print(o.round(4).to_string())
pickle.dump(o,open(f'{RES}/china_loio.pkl','wb'))
