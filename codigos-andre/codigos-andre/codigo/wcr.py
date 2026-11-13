"""
Wild cluster bootstrap restrito (WCR) e Romano-Wolf.

Modelo: y = b x + Z g + FE de firma + FE de trimestre + e, erro padrão por firma.
Segue Roodman et al. (2019): tira os efeitos fixos e os controles (FWL), impõe b = 0 e calcula antes
as somas por cluster, então cada réplica é só um produto de matriz por vetor.
"""
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__))); from caminhos import *  # noqa
import numpy as np
import scipy.sparse as sp


def _indicator(codes):
    n = len(codes); k = codes.max() + 1
    return sp.csr_matrix((np.ones(n), (np.arange(n), codes)), shape=(n, k))


class Projector:
    """Tira de uma matriz N x k a projeção nos efeitos fixos de firma e trimestre e nos controles."""

    def __init__(self, firm, quarter, Z=None, tol=1e-10, maxit=10000):
        self.F = _indicator(firm); self.T = _indicator(quarter)
        self.fn = np.asarray(self.F.sum(0)).ravel(); self.tn = np.asarray(self.T.sum(0)).ravel()
        self.tol, self.maxit = tol, maxit
        self.Zd = None
        if Z is not None and Z.shape[1] > 0:
            self.Zd = self.demean(Z)
            self.ZZinv = np.linalg.inv(self.Zd.T @ self.Zd)

    def demean(self, V):
        V = np.array(V, dtype=float, copy=True)
        if V.ndim == 1:
            V = V[:, None]
        for _ in range(self.maxit):
            V -= self.F @ ((self.F.T @ V) / self.fn[:, None])
            step = self.T @ ((self.T.T @ V) / self.tn[:, None])
            V -= step
            if np.abs(step).max() < self.tol:
                break
        return V

    def __call__(self, V):
        Vd = self.demean(V)
        if self.Zd is not None:
            Vd -= self.Zd @ (self.ZZinv @ (self.Zd.T @ Vd))
        return Vd


def prepare(y, x, Z, firm, quarter, cluster=None):
    """Calcula antes o que cada réplica precisa. cluster: códigos 0..G-1 (padrão: a firma)."""
    cl = firm if cluster is None else cluster
    M = Projector(firm, quarter, Z)
    yt = M(y).ravel(); xt = M(x).ravel()
    q = xt @ xt
    b = (xt @ yt) / q
    e = yt - xt * b
    G = cl.max() + 1
    H = _indicator(cl)
    # Estatística t observada (CRV1 sem ajuste: o ajuste é constante e não muda o p-valor)
    Sg = H.T @ (xt * e)
    t = b / np.sqrt((Sg ** 2).sum() / q ** 2)
    u = yt                                   # resíduos restritos (b = 0) = y parcializado
    # A[:, g] = M(u * 1_g);  C[h, g] = sum_{i in h} xt_i A[i, g]
    U = sp.csr_matrix((u, (np.arange(len(u)), cl)), shape=(len(u), G)).toarray()
    A = M(U)
    C = np.asarray(H.T @ (xt[:, None] * A))
    a = np.asarray(H.T @ (xt * u)).ravel()     # x'(u w) = a . w
    d = np.asarray(H.T @ (xt * xt)).ravel()
    return dict(b=b, t=t, q=q, C=C, a=a, d=d, G=G)


def boot_t(pre, W):
    """t* para uma matriz de pesos W (G x B)."""
    bstar = (pre['a'] @ W) / pre['q']
    S = pre['C'] @ W - np.outer(pre['d'], bstar)
    return bstar / np.sqrt((S ** 2).sum(0) / pre['q'] ** 2)


def weights(G, B, rng, kind='rademacher'):
    if kind == 'rademacher':
        return rng.choice([-1.0, 1.0], size=(G, B))
    v = np.array([-np.sqrt(1.5), -1, -np.sqrt(.5), np.sqrt(.5), 1, np.sqrt(1.5)])
    return rng.choice(v, size=(G, B))


def pvalue(pre, W):
    ts = boot_t(pre, W)
    return float(np.mean(np.abs(ts) >= abs(pre['t'])))


def romano_wolf(tobs, tboot):
    """Stepdown de Romano e Wolf (2005) com |t|. tobs: (K,), tboot: (K, B)."""
    K = len(tobs); order = np.argsort(-np.abs(tobs))
    absb = np.abs(tboot)
    p = np.empty(K); prev = 0.0
    for j, k in enumerate(order):
        mx = absb[order[j:], :].max(0)
        pj = max(np.mean(mx >= abs(tobs[k])), prev)
        p[k] = pj; prev = pj
    return p
