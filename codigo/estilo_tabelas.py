r"""
Estilo das tabelas: [H], largura total do texto (tabular* com \extracolsep{\fill}), corpo com \tablestyle
(ou \tablestylecompact nas longas) e notas em \footnotesize. Os comandos ficam no preâmbulo do main.tex.
"""
import re


def padroniza(s, compacta=False):
    s = s.replace('\\begin{table}[!htbp]', '\\begin{table}[H]')
    a = s.index('\\begin{threeparttable}') + len('\\begin{threeparttable}')
    b = a + re.search(r'\\begin\{tabular', s[a:]).start()
    manter = ''.join(l.strip() + '\n    ' for l in s[a:b].split('\n') if 'hyphenpenalty' in l)
    estilo = '\\tablestylecompact' if compacta else '\\tablestyle'
    s = s[:a] + '\n    ' + estilo + '\n    ' + manter + s[b:]
    if '\\begin{tabularx}' not in s:
        def rep(m):
            spec = re.sub(r'^@\{\\extracolsep\{\\fill\}\}', '', m.group(1))
            spec = re.sub(r'@\{\}$', '', spec)
            return '\\begin{tabular*}{\\textwidth}{@{\\extracolsep{\\fill}}' + spec + '@{}}'
        s = re.sub(r'\\begin\{tabular\*?\}(?:\{\\textwidth\})?\{((?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*)\}', rep, s, count=1)
        s = s.replace('\\end{tabular}', '\\end{tabular*}')
    s = re.sub(r'\\begin\{tablenotes\}(\[[^\]]*\])?', r'\\begin{tablenotes}[flushleft]', s)
    s = re.sub(r'(\\begin\{tablenotes\}\[flushleft\]\s*\n\s*)\\(small|scriptsize)\b', r'\1\\footnotesize', s)
    return s
