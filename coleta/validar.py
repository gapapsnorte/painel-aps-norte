"""Trava de segurança: falha (exit 1) se o painel gerado parecer vazio ou quebrado, para o workflow NÃO publicar."""
import json, os, pathlib, re, sys, unicodedata

# Limiares: cada um protege contra um tipo de carga quebrada ou incompleta do InfoSaúde.
ATEND_MES_MIN = 20000            # atendimentos da Região num mês completo; abaixo disso a carga veio pela metade
QUEDA_MENSAL_MAX = 0.5           # queda sobre o mês anterior (fração do anterior) que indica carga incompleta
GSAPS_MIN, EQUIPES_MIN = 14, 150 # estrutura mínima da hierarquia (GSAPs e equipes)
MES_MIN_DA_MEDIANA = 0.5         # mês da série abaixo dessa fração da mediana: mês vazio ou pela metade
MED_POR_MIL_MIN, MED_POR_MIL_MAX = 300, 1500    # consultas de médico por mil hab. plausíveis na Região Norte
REGIOES_MIN = 7                  # regiões de saúde do DF no bloco Norte x DF
ATEND_POR_PESSOA_MIN, ATEND_POR_PESSOA_MAX = 1.5, 8   # atendimentos por pessoa atendida em 12 meses
PESSOAS_MIN = 50000              # pessoas distintas atendidas na Região Norte em 12 meses
UBS_COM_PORTE_MIN = 30           # UBS com porte calculado (população cadastrada conhecida)
NOME_MIN_LETRAS = 10             # nomes mais curtos (só letras) dão falso positivo na busca em texto aberto
ENVELOPE_MIN = 1000              # tamanho mínimo do texto cifrado de site/nominal.js
ITERACOES_MIN = 600000           # PBKDF2: menos que isso facilita adivinhar a senha dos gestores

p = json.load(open(pathlib.Path(__file__).parent.parent / "dados" / "painel.json", encoding="utf-8"))
M = p["meses"]; iu = M.index(p["ultimo_mes_completo"]); falhas = []
at = p["regiao"].get("atend", [0] * len(M))
if at[iu] < ATEND_MES_MIN: falhas.append(f"atendimentos do último mês completo muito baixos: {at[iu]}")
if iu and at[iu - 1] < ATEND_MES_MIN: falhas.append(f"atendimentos do mês anterior muito baixos: {at[iu-1]}")
if iu and at[iu] < QUEDA_MENSAL_MAX * at[iu - 1]: falhas.append(f"queda de mais de 50% sobre o mês anterior ({at[iu-1]} -> {at[iu]}); provável carga incompleta")
n_eq = sum(len(u["equipes"]) for g in p["gsaps"] for u in g["ubs"])
if len(p["gsaps"]) < GSAPS_MIN or n_eq < EQUIPES_MIN: falhas.append(f"estrutura incompleta: {len(p['gsaps'])} GSAPs, {n_eq} equipes")
for k in ("visitas", "vacinas", "coletivas"):
    if not any(p["regiao"].get(k, [0])[iu - 1:iu + 1]): falhas.append(f"{k} zerado nos 2 últimos meses completos")
# séries que nunca deveriam vir zeradas na Região (uma coluna renomeada no InfoSaúde zera o conjunto inteiro sem erro)
for k in ("atend_med", "atend_enf", "prenatal", "has", "odonto", "p_cito", "p_ts_sif", "m_has", "m_sem", "a_dia"):
    if not p["regiao"].get(k, [0] * len(M))[iu]: falhas.append(f"série '{k}' zerada na Região no último mês completo")
_med = sorted(at[:iu + 1])[(iu + 1) // 2]
for i in range(iu + 1):   # mês do meio vazio ou pela metade distorce o habitual e a comparação com o ano anterior
    if at[i] < MES_MIN_DA_MEDIANA * _med: falhas.append(f"atendimentos de {M[i]} muito abaixo da mediana da série ({at[i]} x {_med})")
rz = p.get("razao")
if not rz: falhas.append("bloco 'razao' (consultas por mil hab.) ausente: coleta/razao.py não rodou ou veio vazio")
else:
    n = rz["entes"][0]["m12"]; v = n["med"] / n["pop"] * 1000 if n["pop"] else 0
    if not MED_POR_MIL_MIN <= v <= MED_POR_MIL_MAX: falhas.append(f"consultas de médico por mil hab. na Região Norte fora do plausível: {v:.0f}")
    if not rz.get("cad_regiao"): falhas.append("cadastros por UBS vazios")
rg = p.get("regioes")
if not rg or "Região Norte" not in rg.get("serie", {}) or len(rg.get("regs", [])) < REGIOES_MIN: falhas.append("bloco 'regioes' (Norte × DF) ausente ou incompleto: coleta/regioes.py não rodou")
us = p.get("usuarios")
if not us: falhas.append("bloco 'usuarios' (pessoas atendidas) ausente: coleta/usuarios.py não rodou")
else:
    r = us["regiao"]; q = r["atend"] / r["pess"] if r["pess"] else 0
    if not ATEND_POR_PESSOA_MIN <= q <= ATEND_POR_PESSOA_MAX: falhas.append(f"atendimentos por pessoa na Região Norte fora do plausível: {q:.1f}")
    if r["pess"] < PESSOAS_MIN: falhas.append(f"pessoas atendidas na Região Norte muito baixas: {r['pess']}")
# nada nominal na parte aberta do site (segunda conferência, independente da trava do montar.py)
_raiz = pathlib.Path(__file__).parent.parent
def _n(x): return re.sub(r"[^A-Z]", "", unicodedata.normalize("NFD", str(x or "")).upper())
_ref = json.load(open(pathlib.Path(__file__).parent / "referencia.json", encoding="utf-8"))
_nomes = {_n(x["nome"]) for l in _ref["lotacao"].values() for x in l if x.get("nome") and " " in x["nome"]}
# quem registrou produção e não está na lotação (cerca de 4 em 10 nomes) também não pode aparecer
for _f in ("atendimentos", "visitas", "vacinas", "coletivas", "procedimentos"):
    for _x in json.load(open(_raiz / "dados" / "brutos" / f"{_f}.json", encoding="utf-8")):
        if _x.get("nome") and " " in str(_x["nome"]): _nomes.add(_n(_x["nome"]))
        if re.fullmatch(r"\d{15}", str(_x.get("cns") or "")): falhas.append(f"CNS em claro em dados/brutos/{_f}.json (a coleta deve gravar embaralhado)"); break
_nomes = {x for x in _nomes if len(x) >= NOME_MIN_LETRAS}
for _arq in ("painel.js", "index.html"):
    _t = (_raiz / "site" / _arq).read_text("utf-8"); _tn = _n(_t)
    _v = sum(1 for x in _nomes if x in _tn)
    if _v: falhas.append(f"{_v} nome(s) de servidor em texto aberto em site/{_arq}")
    if re.search(r'"(prof|mat|cns|cargo|chs|tp)":', _t): falhas.append(f"campo nominal em site/{_arq}")
    if re.search(r'"(vinculo|vinc|ft|ivt|faixa_ivt)":', _t): falhas.append(f"campo de força de trabalho ou IVT em site/{_arq}")
# IVT (lote 3): só no bloco cifrado. Nem a palavra nem o INE com índice podem aparecer na parte aberta com dado de IVT.
_pj = (_raiz / "site" / "painel.js").read_text("utf-8")
if re.search(r"(?<![a-z])ivt(?![a-z])", _pj, re.I): falhas.append("IVT na parte aberta (site/painel.js): o índice só pode ir no bloco cifrado")
_ivt_arq = pathlib.Path(__file__).parent / "ivt_apsdf_2024.json"
if _ivt_arq.exists():
    _html_t = (_raiz / "site" / "index.html").read_text("utf-8")
    _ivt_lista = json.load(open(_ivt_arq, encoding="utf-8"))
    if any(x["ine"] in _html_t for x in _ivt_lista): falhas.append("INE com IVT escrito em site/index.html")
    if any(f'"ivt":{x["ivt"]}' in _pj.replace(" ", "") for x in _ivt_lista): falhas.append("valor de IVT em site/painel.js")
tu = p.get("tipo_ubs")
if not tu or not tu.get("cortes") or None in tu["cortes"]: falhas.append("bloco 'tipo_ubs' (cortes de porte) ausente: montar.py não calculou o porte das UBS")
else:
    _pu = [u.get("porte") for g in p["gsaps"] for u in g["ubs"]]
    if sum(1 for x in _pu if x) < UBS_COM_PORTE_MIN: falhas.append(f"porte calculado para poucas UBS ({sum(1 for x in _pu if x)})")
if os.environ.get("GITHUB_ACTIONS") and not p.get("restrito"): falhas.append("painel sem a área dos gestores numa geração feita no GitHub (APS_SENHA ausente?)")
_extra = sorted(x.name for x in (_raiz / "site").iterdir() if x.name not in ("index.html", "painel.js", "nominal.js"))
if _extra: falhas.append(f"arquivo inesperado em site/ (iria ao ar sem conferência): {_extra}")
if p.get("restrito") and not (_raiz / "site" / "nominal.js").exists(): falhas.append("painel marcado como restrito, mas site/nominal.js não foi gerado")
_nom = _raiz / "site" / "nominal.js"
if _nom.exists():   # tem de ser exatamente o envelope cifrado: nada de lista em claro com um "ct" no meio
    _txt = _nom.read_text("utf-8")
    try:
        _env = json.loads(_txt.removeprefix("window.NOMINAL=").removesuffix(";"))
    except ValueError:
        _env = None
    if not isinstance(_env, dict) or set(_env) != {"v", "it", "sal", "iv", "ct", "gerado"} or len(_env["ct"]) < ENVELOPE_MIN or not re.fullmatch(r"[A-Za-z0-9+/=]+", _env["ct"]):
        falhas.append("site/nominal.js não é o envelope cifrado esperado")
    elif _env["it"] < ITERACOES_MIN: falhas.append("site/nominal.js cifrado com menos iterações que o mínimo (600 mil)")
if falhas:
    print("VALIDAÇÃO FALHOU:\n - " + "\n - ".join(falhas)); sys.exit(1)
_area = "cifrada" if p.get("restrito") else "NÃO gerada (sem senha)"
print(f"validação ok: {p['ultimo_mes_completo']} atendimentos {at[iu]}, {len(p['gsaps'])} GSAPs, {n_eq} equipes, {len(p['alertas'])} alertas; "
      f"área dos gestores: {_area}; {len(_nomes)} nomes conferidos, nenhum em texto aberto")
