"""Tripla diferença só com firmas europeias (UE contra Europa fora da UE), pareada e com entropy balancing (Tabela 21, bloco "European firms only")."""
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__))); from caminhos import *  # noqa
import ddd_core as D, pandas as pd, numpy as np, warnings, pickle, sys
warnings.filterwarnings('ignore'); sys.path.insert(0,CODE); import wcr
p=pd.read_pickle(R02 + '/painel_firma_trimestre.pkl'); d=D.build_panel(p); d=d[d['TRBC Industry Group Name']!='Telecommunications Services']
NONEU_EUR={'United Kingdom','Switzerland','Faroe Islands'}
cls,thr=D.classify(d); fall=D.firm_table(d,cls)
fe=fall[(fall.EU==1)|(fall.HQ.isin(NONEU_EUR))]
print('thr',thr,'cells', fe.Cell.value_counts().to_dict())
fx=fe[fe.Sector.isin(set(fe.loc[fe.Treated==1,'Sector']))].copy()
fx['pscore'],_=D.propensity(fx); pr,keep=D.match(fx); fm=fx[fx.index.isin(keep)]
print('matched', fm.Cell.value_counts().to_dict(), 'HQ controls', fm[fm.EU==0].HQ.value_counts().to_dict())
de=d[d.RIC.isin(fe.index)]
R={}
m,s=D.ddd(de,fm)
for k in ['EUxHighxPost','EUxPost','HighxPost']: print(k, round(m.coef()[k],4), round(m.se()[k],4), round(m.pvalue()[k],3))
R['main']=dict(b=m.coef()['EUxHighxPost'],se=m.se()['EUxHighxPost'],p=m.pvalue()['EUxHighxPost'],HxP=m.coef()['HighxPost'],HxP_p=m.pvalue()['HighxPost'],N=m._N,treated=int(fm.Treated.sum()),firms=len(fm))
# Europa sem pareamento
m2,_=D.ddd(de,fe); print('unmatched', round(m2.coef()['EUxHighxPost'],4), round(m2.se()['EUxHighxPost'],4), round(m2.pvalue()['EUxHighxPost'],3), m2._N, int(fe.Treated.sum()), len(fe))
R['unmatched']=dict(b=m2.coef()['EUxHighxPost'],se=m2.se()['EUxHighxPost'],p=m2.pvalue()['EUxHighxPost'],N=m2._N,treated=int(fe.Treated.sum()),firms=len(fe))
# wild bootstrap por firma na amostra pareada
def ds(dd):
    while True:
        n0=len(dd)
        for c in ('RIC','qkey'): dd=dd[dd.groupby(c)[c].transform('size')>1]
        if len(dd)==n0: return dd
s1=ds(s.copy()); fid=pd.factorize(s1.RIC)[0]; qid=pd.factorize(s1.qkey)[0]
pre=wcr.prepare(s1.Q.values,s1.EUxHighxPost.values.astype(float),s1[['EUxPost','HighxPost']].values.astype(float),fid,qid)
R['main']['p_wild']=wcr.pvalue(pre,wcr.weights(pre['G'],9999,np.random.default_rng(20261024)))
print('wild',R['main']['p_wild'])
R['balance_size']=fm.groupby('Cell')['lnMktCap_pre'].mean().to_dict()
pickle.dump(R,open(f'{RES}/europe.pkl','wb'))
from scipy.optimize import minimize
import pyfixest as pf
f=fe[fe.Sector.isin(set(fe.loc[fe.Treated==1,'Sector']))].copy()
X=pd.concat([f[D.COVS], pd.get_dummies(f['Sector'],dtype=float)],axis=1); X=X.loc[:,X.loc[f.Treated==1].std()>0]
tm=X[f.Treated==1].mean(); w=pd.Series(0.0,index=f.index); w[f.Treated==1]=1.0
for cell in D.CONTROL_CELLS:
    idx=f.index[f.Cell==cell]; Z=(X.loc[idx]-tm).values
    obj=lambda l: np.log(np.exp(Z@l).sum()); gr=lambda l:(np.exp(Z@l)/np.exp(Z@l).sum())@Z
    r=minimize(obj,np.zeros(Z.shape[1]),jac=gr,method='BFGS',options={'maxiter':5000,'gtol':1e-10})
    ww=np.exp(Z@r.x); w[idx]=ww/ww.sum()*(f.Treated==1).sum()
    print(cell,len(idx),'maxdiff',round(np.abs(X.loc[idx].T@(ww/ww.sum())-tm).max(),5))
se=de[de.RIC.isin(f.index)].join(f[['High']],on='RIC'); se['w']=se.RIC.map(w); se=se[se.w>0]
se['Post']=(se.qkey>=D.POST).astype(int); se['EUxHighxPost']=se.EU*se.High*se.Post; se['EUxPost']=se.EU*se.Post; se['HighxPost']=se.High*se.Post
me=pf.feols('Q_CP ~ EUxHighxPost + EUxPost + HighxPost | RIC + qkey',data=se,weights='w',vcov={'CRV1':'RIC'})
print('EB', round(me.coef()['EUxHighxPost'],4), round(me.se()['EUxHighxPost'],4), round(me.pvalue()['EUxHighxPost'],3), me._N, int((f.Treated==1).sum()), se.RIC.nunique(), 'HxP',round(me.coef()['HighxPost'],3),round(me.pvalue()['HighxPost'],3))
R['eb']=dict(b=me.coef()['EUxHighxPost'],se=me.se()['EUxHighxPost'],p=me.pvalue()['EUxHighxPost'],N=me._N,treated=int((f.Treated==1).sum()),firms=se.RIC.nunique())
pickle.dump(R,open(f'{RES}/europe.pkl','wb'))
