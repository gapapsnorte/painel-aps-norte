"""Trava de segurança: falha (exit 1) se o painel gerado parecer vazio ou quebrado, para o workflow NÃO publicar."""
import json, pathlib, sys
p = json.load(open(pathlib.Path(__file__).parent.parent / "dados" / "painel.json", encoding="utf-8"))
M = p["meses"]; iu = M.index(p["ultimo_mes_completo"]); falhas = []
at = p["regiao"].get("atend", [0] * len(M))
if at[iu] < 20000: falhas.append(f"atendimentos do último mês completo muito baixos: {at[iu]}")
if iu and at[iu - 1] < 20000: falhas.append(f"atendimentos do mês anterior muito baixos: {at[iu-1]}")
if iu and at[iu] < 0.5 * at[iu - 1]: falhas.append(f"queda de mais de 50% sobre o mês anterior ({at[iu-1]} -> {at[iu]}); provável carga incompleta")
n_eq = sum(len(u["equipes"]) for g in p["gsaps"] for u in g["ubs"])
if len(p["gsaps"]) < 14 or n_eq < 150: falhas.append(f"estrutura incompleta: {len(p['gsaps'])} GSAPs, {n_eq} equipes")
for k in ("visitas", "vacinas", "coletivas"):
    if not any(p["regiao"].get(k, [0])[iu - 1:iu + 1]): falhas.append(f"{k} zerado nos 2 últimos meses completos")
rz = p.get("razao")
if not rz: falhas.append("bloco 'razao' (consultas por mil hab.) ausente: coleta/razao.py não rodou ou veio vazio")
else:
    n = rz["entes"][0]["m12"]; v = n["med"] / n["pop"] * 1000 if n["pop"] else 0
    if not 300 <= v <= 1500: falhas.append(f"consultas de médico por mil hab. na Região Norte fora do plausível: {v:.0f}")
    if not rz.get("cad_regiao"): falhas.append("cadastros por UBS vazios")
us = p.get("usuarios")
if not us: falhas.append("bloco 'usuarios' (pessoas atendidas) ausente: coleta/usuarios.py não rodou")
else:
    r = us["regiao"]; q = r["atend"] / r["pess"] if r["pess"] else 0
    if not 1.5 <= q <= 8: falhas.append(f"atendimentos por pessoa na Região Norte fora do plausível: {q:.1f}")
    if r["pess"] < 50000: falhas.append(f"pessoas atendidas na Região Norte muito baixas: {r['pess']}")
# nada nominal na parte aberta do site (segunda conferência, independente da trava do montar.py)
import re, unicodedata
_raiz = pathlib.Path(__file__).parent.parent
def _n(x): return re.sub(r"[^A-Z]", "", unicodedata.normalize("NFD", str(x or "")).upper())
_ref = json.load(open(pathlib.Path(__file__).parent / "referencia.json", encoding="utf-8"))
_nomes = {_n(x["nome"]) for l in _ref["lotacao"].values() for x in l if x.get("nome") and " " in x["nome"]}
_nomes = {x for x in _nomes if len(x) >= 10}
for _arq in ("painel.js", "index.html"):
    _t = (_raiz / "site" / _arq).read_text("utf-8"); _tn = _n(_t)
    _v = sum(1 for x in _nomes if x in _tn)
    if _v: falhas.append(f"{_v} nome(s) de servidor em texto aberto em site/{_arq}")
    if re.search(r'"(prof|mat|cns|cargo|chs)":', _t): falhas.append(f"campo nominal em site/{_arq}")
if p.get("restrito") and not (_raiz / "site" / "nominal.js").exists(): falhas.append("painel marcado como restrito, mas site/nominal.js não foi gerado")
if (_raiz / "site" / "nominal.js").exists() and '"ct"' not in (_raiz / "site" / "nominal.js").read_text("utf-8")[:400]: falhas.append("site/nominal.js não parece cifrado")
if falhas:
    print("VALIDAÇÃO FALHOU:\n - " + "\n - ".join(falhas)); sys.exit(1)
print(f"validação ok: {p['ultimo_mes_completo']} atendimentos {at[iu]}, {len(p['gsaps'])} GSAPs, {n_eq} equipes, {len(p['alertas'])} alertas; área dos gestores: {'cifrada' if p.get('restrito') else 'NÃO gerada (sem senha)'}; {len(_nomes)} nomes conferidos, nenhum em texto aberto")
