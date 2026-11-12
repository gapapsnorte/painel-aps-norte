"""Agrega os dados brutos na hierarquia GSAP -> UBS -> equipe -> profissionais e calcula alertas.
Entrada: coleta/referencia.json (lotação do RH) e dados/brutos/*.json (coleta.py).
Saída:   site/painel.js e dados/painel.json: só agregados (Região, GSAP, UBS, equipe), SEM nenhum nome de servidor.
         site/nominal.js: tudo o que identifica servidor (lista de profissionais por equipe e alertas com nomes), CIFRADO com a senha
         dos gestores (AES-GCM; chave derivada da senha por PBKDF2-SHA256). Sem senha configurada, o bloco nominal não é gerado.
         CNS, CPF e matrícula não vão para a versão publicada, nem cifrados (a matrícula só entra quando gerado no computador dela).
Uso: python montar.py"""
import json, hashlib, pathlib, re, datetime as dt
from collections import defaultdict

AQUI = pathlib.Path(__file__).parent
RAIZ = AQUI.parent
BR = RAIZ / "dados" / "brutos"
ref = json.load(open(AQUI / "referencia.json", encoding="utf-8"))
_m = re.search(r"(\d{2})[ .](\d{4})", ref.get("fonte", ""))   # competência da planilha de RH, tirada do nome do arquivo
RH_ROT = (["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"][int(_m.group(1)) - 1] + "/" + _m.group(2)) if _m and 1 <= int(_m.group(1)) <= 12 else "data não identificada"
log = json.load(open(BR / "_log.json", encoding="utf-8"))
MESES = log["meses"]; NM = len(MESES); IX = {m: i for i, m in enumerate(MESES)}
hoje = dt.date.today()
MES_PARCIAL = f"{hoje.year}-{hoje.month:02d}"          # mês em curso: incompleto, fora de alertas
ULT = MESES[-2] if MESES[-1] == MES_PARCIAL else MESES[-1]   # último mês completo
IU = IX[ULT]

IND = {  # id: (nome, unidade, nível: 'prof' = por profissional e equipe; 'eq' = só equipe)
    "atend": ("Atendimentos individuais", "atendimentos", "prof"),
    "atend_med": ("  de médicos", "atendimentos", "prof"),
    "atend_enf": ("  de enfermeiros", "atendimentos", "prof"),
    "visitas": ("Visitas domiciliares (ACS)", "visitas", "prof"),
    "visitas_ok": ("  visitas realizadas", "visitas", "prof"),
    "vacinas": ("Doses de vacina aplicadas", "doses", "prof"),
    "coletivas": ("Atividades coletivas", "atividades", "prof"),
    "participantes": ("  participantes", "pessoas", "prof"),
    "prenatal": ("Atendimentos de pré-natal", "atendimentos", "eq"),
    "has": ("Atendimentos de hipertensão", "atendimentos", "eq"),
    "dm": ("Atendimentos de diabetes", "atendimentos", "eq"),
    "mental": ("Atendimentos de saúde mental", "atendimentos", "eq"),
    "colo": ("Atendimentos por rastreio do colo do útero", "atendimentos", "eq"),
    "mama": ("Atendimentos por rastreio do câncer de mama", "atendimentos", "eq"),
    "ist": ("Atendimentos por IST", "atendimentos", "eq"),
    "odonto1": ("Primeira consulta odontológica", "consultas", "eq"),
    "odonto": ("Consultas odontológicas (total)", "consultas", "eq"),
}
from familias import FAMILIAS, COD2FAM
GRP = {k: "Atendimento e produção" for k in IND}
for _k in ("prenatal", "has", "dm", "mental", "colo", "mama", "ist", "odonto1", "odonto"): GRP[_k] = "Condições avaliadas e odontologia (só por equipe)"
for _k, (_nome, _c) in FAMILIAS.items(): IND[_k] = (_nome, "procedimentos", "prof"); GRP[_k] = "Procedimentos"
from motivos import NOMES as MOT_NOMES, fam_cid
for _k, _n in MOT_NOMES.items(): IND[_k] = (_n, "CID registrados", "eq"); GRP[_k] = "Motivos de consulta (CID, só por equipe)"
TIPOS_ACESSO = {"Consulta no dia": "a_dia", "Consulta agendada": "a_agend", "Consulta agendada programada / Cuidado continuado": "a_prog",
                "Atendimento de urgência": "a_urg", "Escuta inicial / Orientação": "a_escuta"}
for _k, _n in (("a_dia", "Consulta no dia (demanda espontânea)"), ("a_agend", "Consulta agendada"), ("a_prog", "Consulta agendada programada (cuidado continuado)"),
               ("a_urg", "Atendimento de urgência"), ("a_escuta", "Escuta inicial e orientação"), ("atend_out", "Atendimentos de outros profissionais")):
    IND[_k] = (_n, "atendimentos", "eq"); GRP[_k] = "Perfil de acesso (só por equipe)"
COND_MAP = {"prenatal": "Pré-natal", "has": "Hipertensão arterial", "dm": "Diabetes", "mental": "Saúde mental",
            "colo": "Rast. câncer do colo do útero", "mama": "Rast. câncer de mama", "ist": "D.Transmissíveis - DST"}

def L(n): return json.load(open(BR / f"{n}.json", encoding="utf-8"))
# ---- indicador 'consultas por mil hab.' (RIPSA COB.1.01): denominadores ----
_cad = L("cadastros") if (BR / "cadastros.json").exists() else []
CAD_COMP = max((c["comp"] for c in _cad), default=None)          # última competência de cadastros no InfoSaúde (parada em abr/2025)
CAD_CNES, CAD_INE = defaultdict(int), defaultdict(int)
for _c in _cad:
    if _c["comp"] != CAD_COMP: continue
    CAD_CNES[str(_c["cnes"]).zfill(7)] += _c["n"] or 0
    if _c["ine"] and str(_c["ine"]).isdigit(): CAD_INE[str(_c["ine"]).zfill(10)] += _c["n"] or 0
CENSO_2022 = {"Região Norte": 345286, "Distrito Federal": 2817381}   # DF: IBGE SIDRA 4709; Norte: soma das 4 RAs pelo IPEDF (malha preliminar, mar/2024). Sem valor para as outras regiões.
BRASIL_RIPSA = {"2022": 883, "2023": 1021, "2024": 1128}           # RIPSA 3ª ed. (jun/2026), ficha COB.1.01, consultas médicas na APS por mil hab.
def zeros(): return [0] * NM
def titulo(s):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    peq = {"de", "da", "do", "dos", "das", "e"}
    t = " ".join(w.lower() if w.lower() in peq and i else w.capitalize() for i, w in enumerate(s.split(" ")))
    SIGLAS = {"Ubs": "UBS", "Ii": "II", "Der": "DER", "Esf": "eSF", "Acs": "ACS", "Thd": "THD", "Sob": "SOB", "Cepis": "CEPIS"}
    t = " ".join(SIGLAS.get(w, w) for w in t.split(" "))   # palavra inteira, sem regex: nao troca o inicio de Sobradinho
    return t
import os
def _pepper():
    p = os.environ.get("APS_PEPPER")
    if not p:
        f = pathlib.Path(__file__).parent / "pepper.local"
        if f.exists(): p = f.read_text(encoding="utf-8").strip()
    if not p: raise SystemExit("Falta o segredo APS_PEPPER (variável de ambiente, ou arquivo coleta/pepper.local).")
    return p
PEPPER = _pepper()
def hc(c): return hashlib.sha256((PEPPER + "|" + str(c)).encode()).hexdigest()[:12] if c else ""   # igual nos dois scripts
_SEQ = {}
def pid(chave): return _SEQ.setdefault(chave, f"p{len(_SEQ) + 1}")   # id sequencial: nada derivado do CNS sai do gerador
def norm_nome(s): return re.sub(r"[^A-Z]", "", str(s or "").upper().replace("Ç", "C").replace("Ã", "A").replace("Á", "A").replace("É", "E").replace("Ê", "E").replace("Í", "I").replace("Ó", "O").replace("Ô", "O").replace("Ú", "U"))
def ine10(x):
    x = str(x or "")
    return x.zfill(10) if x.isdigit() else ""

# ---------- estrutura a partir do RH ----------
ubs_ref = ref["ubs"]; eq_ref = ref["equipes"]; lot_ref = ref["lotacao"]
_priv = AQUI / "referencia_privada.json"
PRIV = json.load(open(_priv, encoding="utf-8")) if _priv.exists() else {}   # só existe no computador dela; no GitHub o painel sai sem matrícula
APS = {c: u for c, u in ubs_ref.items() if re.match(r"UBS", u["nome_rh"] or "")}   # só UBS na hierarquia
estr = {}   # cnes -> {"gsap","nome","ra","eq": {ine: {...}}}
def no_ubs(cnes, nome=None):
    if cnes not in estr:
        u = ubs_ref.get(cnes, {})
        estr[cnes] = {"cnes": cnes, "nome": titulo(u.get("nome_rh") or nome or cnes), "sigla": nome, "ra": u.get("ra"), "gsap": u.get("gsap") or f"Fora do RH de {RH_ROT}", "eq": {}}
    return estr[cnes]
def no_eq(cnes, ine, tipo=None, nome=None, nome_prod=None):
    u = no_ubs(cnes, nome_prod)
    chave = ine or "SEM"
    if chave not in u["eq"]:
        e = eq_ref.get(ine, {}) if ine else {}
        if ine:
            nm = e.get("nome") or f"INE {ine} (fora do RH de {RH_ROT})"
        else:
            nm = "Sem equipe vinculada"
        u["eq"][chave] = {"ine": ine, "nome": nm, "tipo": e.get("tipo") or tipo or ("—" if not ine else "?"), "zona": e.get("zona"),
                          "prof": {}, "serie": {k: zeros() for k, v in IND.items()}, "no_rh": bool(e)}
    return u["eq"][chave]

for cnes in APS: no_ubs(cnes)
for ine, e in eq_ref.items():
    if e["cnes"] in APS: no_eq(e["cnes"], ine)

def no_prof(eq, cns, nome, cat=None):
    chave = cns or norm_nome(nome)
    if chave not in eq["prof"]:
        eq["prof"][chave] = {"id": pid(chave), "nome": titulo(nome), "cat": cat, "cargo": None, "chs": None, "lotado": False, "serie": {}}
    p = eq["prof"][chave]
    if cat and not p["cat"]: p["cat"] = cat
    if PRIV.get(chave): p["mat"] = PRIV[chave]
    return p

# lotados (RH) -> aparecem mesmo sem produção
por_cns_lot = {}
for ine, lista in lot_ref.items():
    if ine.startswith("UBS:"): continue
    e = eq_ref.get(ine)
    if not e or e["cnes"] not in APS: continue
    eqn = no_eq(e["cnes"], ine)
    for x in lista:
        p = no_prof(eqn, x["cns"], x["nome"], x["cat"])
        p.update(lotado=True, cargo=x["cargo"], chs=x["chs"], cat=x["cat"] or p["cat"])
        por_cns_lot[x["cns"]] = ine

def soma_serie(p, ind, i, v):
    s = p["serie"].setdefault(ind, zeros()); s[i] += v

fora_aps = defaultdict(lambda: zeros())  # produção da Região Norte em unidades fora da APS (hospitais etc.)

def processa(nome_arq, fn):
    for l in L(nome_arq):
        i = IX.get(l["compt"])
        if i is None: continue
        if l.get("cns"): l["cns"] = hc(l["cns"])
        cnes = str(l["cnes"]).zfill(7)
        if cnes not in APS:
            fn(None, None, l, i, cnes); continue
        ine = ine10(l["ine"])
        eq = no_eq(cnes, ine if ine and ine in eq_ref else (ine or ""), tipo=l.get("tipo_eq"), nome_prod=l.get("ubs"))
        fn(eq, None, l, i, cnes)

def f_atend(eq, _, l, i, cnes):
    n = l["n"] or 0
    if eq is None: fora_aps[nome_unid(cnes, l)][i] += n; return
    p = no_prof(eq, l["cns"], l["nome"], titulo(l["cat"]))
    for ind in ["atend"] + (["atend_med"] if l["cat"] == "MÉDICO" else []) + (["atend_enf"] if l["cat"] == "ENFERMEIRO" else []):
        soma_serie(p, ind, i, n); eq["serie"][ind][i] += n
    if TIPOS_ACESSO.get(l["tipo"]): eq["serie"][TIPOS_ACESSO[l["tipo"]]][i] += n          # perfil de acesso: só no nível da equipe
    if l["cat"] not in ("MÉDICO", "ENFERMEIRO"): eq["serie"]["atend_out"][i] += n
def nome_unid(cnes, l): return l.get("ubs") or cnes
def f_vis(eq, _, l, i, cnes):
    if eq is None: return
    n = l["n"] or 0; p = no_prof(eq, l["cns"], l["nome"], titulo(re.sub(r"^ACS - ", "", l["cat"] or "")))
    soma_serie(p, "visitas", i, n); eq["serie"]["visitas"][i] += n
    if l["desfecho"] == "Visita realizada": soma_serie(p, "visitas_ok", i, n); eq["serie"]["visitas_ok"][i] += n
def f_vac(eq, _, l, i, cnes):
    if eq is None: return
    n = l["n"] or 0; p = no_prof(eq, l["cns"], l["nome"], titulo(l["cat"]))
    soma_serie(p, "vacinas", i, n); eq["serie"]["vacinas"][i] += n
def f_col(eq, _, l, i, cnes):
    if eq is None: return
    n = l["n"] or 0; q = l["participantes"] or 0; p = no_prof(eq, l["cns"], l["nome"], titulo(l["cat"]))
    soma_serie(p, "coletivas", i, n); soma_serie(p, "participantes", i, q); eq["serie"]["coletivas"][i] += n; eq["serie"]["participantes"][i] += q
def f_cond(eq, _, l, i, cnes):
    if eq is None: return
    for ind, c in COND_MAP.items(): eq["serie"][ind][i] += l.get(c) or 0
def f_odo(eq, _, l, i, cnes):
    if eq is None: return
    eq["serie"]["odonto1"][i] += l.get("primeira") or 0; eq["serie"]["odonto"][i] += l.get("n") or 0

def f_mot(eq, _, l, i, cnes):
    if eq is None: return
    eq["serie"][fam_cid(l["cid"])][i] += l["n"] or 0

def f_proc(eq, _, l, i, cnes):
    fam = COD2FAM.get(str(l["cod"]))
    if eq is None or not fam: return
    n = l["n"] or 0; p = no_prof(eq, l["cns"], l["nome"], titulo(l["cat"]))
    soma_serie(p, fam, i, n); eq["serie"][fam][i] += n

for arq, fn in (("motivos", f_mot), ("procedimentos", f_proc), ("atendimentos", f_atend), ("visitas", f_vis), ("vacinas", f_vac), ("coletivas", f_col), ("condicoes", f_cond), ("odonto", f_odo)):
    processa(arq, fn)

# ---------- séries agregadas, estatísticas e alertas ----------
def soma_listas(listas):
    out = zeros()
    for s in listas:
        for i, v in enumerate(s): out[i] += v
    return out
def agrega(series_dicts):
    return {k: soma_listas([d[k] for d in series_dicts if k in d]) for k in IND if any(k in d for d in series_dicts)}
def media(s, a, b): return sum(s[a:b]) / max(b - a, 1)
def med12(s):   # "habitual" = mediana dos 12 meses anteriores ao último mês completo (o mês avaliado não entra); mesma regra da página
    v = sorted(s[max(IU - 12, 0):IU]); n = len(v)
    return (v[(n - 1) // 2] + v[n // 2]) / 2 if n else 0
def var_ano(s):
    base = s[IU - 12] if IU >= 12 else None
    return None if not base else round(s[IU] / base - 1, 3)

alertas = []
alertas_nominais = []   # mesma chave (caminho, tipo), texto com nomes: vai só para o bloco cifrado
def alerta(nivel, tipo, path, texto, valor=None, nominal=None):
    alertas.append({"nivel": nivel, "tipo": tipo, "caminho": path, "texto": texto, "valor": round(valor, 4) if isinstance(valor, float) else valor})
    if nominal: alertas_nominais.append({"caminho": path, "tipo": tipo, "texto": nominal})

ALERTA_QUEDA = 0.30; BASE_MIN_EQ = 150; BASE_MIN_UBS = 600
# eSF que mudou de UBS: a mesma INE para de registrar numa UBS e segue ativa em outra (não é equipe parada)
migrou = {}
_por_ine = defaultdict(list)
for _cnes, _u in estr.items():
    for _e in _u["eq"].values():
        if _e["ine"] and _e["tipo"] == "eSF" and _e["serie"].get("atend"):
            _s = _e["serie"]["atend"]; _por_ine[_e["ine"]].append((_cnes, _u["nome"], max((i for i, x in enumerate(_s) if x), default=-1)))
for _ine, _v in _por_ine.items():
    if len(_v) < 2: continue
    _vivo = max(_v, key=lambda t: t[2])
    for _cnes, _nome, _ult in _v:
        if _cnes != _vivo[0] and _ult < _vivo[2] and _vivo[2] >= IU:
            migrou[(_cnes, _ine)] = {"para": _vivo[1], "ultimo": MESES[_ult] if _ult >= 0 else None}

gsaps = defaultdict(lambda: {"ubs": []})
for cnes, u in estr.items():
    equipes = []
    for chave, e in u["eq"].items():
        profs = []
        for p in e["prof"].values():
            p["serie"] = {k: v for k, v in p["serie"].items() if any(v)}
            recente = sum(sum(v[max(IU - 2, 0):IU + 1]) for v in p["serie"].values())
            p["ativo"] = bool(p["lotado"] or recente)
            p["ultimo"] = next((MESES[j] for j in range(NM - 1, -1, -1) if any(v[j] for v in p["serie"].values())), None)
            profs.append(p)
        profs.sort(key=lambda p: (not p["ativo"], not p["lotado"], -(sum(p["serie"].get("atend", [0])) + sum(p["serie"].get("visitas", [0]))), p["nome"]))
        e["prof"] = profs
        e["serie"] = {k: v for k, v in e["serie"].items() if any(v)}
        e["kpi"] = {}
        caminho = f"{u['gsap']} › {u['nome']} › {e['nome']}"
        s = e["serie"].get("atend", zeros())
        mig = migrou.get((cnes, e["ine"])) if e["ine"] else None
        if mig:
            e["migrou"] = mig
            alerta("media", "equipe mudou de UBS", caminho, f"Esta equipe (INE {e['ine']}) passou a registrar na {mig['para']}; o último registro aqui foi em {mig['ultimo']}. Não é equipe parada: confira se a lotação no RH está atualizada.", 0)
        elif e["tipo"] == "eSF":
            hist = med12(s)
            if s[IU] == 0 and hist >= 100:
                alerta("alta", "equipe zerada", caminho, f"Nenhum atendimento individual em {ULT} (habitual, mediana dos 12 meses anteriores: {hist:.0f}).", 0)
            elif var_ano(s) is not None and var_ano(s) <= -ALERTA_QUEDA and s[IU - 12] >= BASE_MIN_EQ:
                alerta("media", "queda de atendimentos", caminho, f"Atendimentos {var_ano(s):+.0%} contra {MESES[IU-12]} ({s[IU-12]} → {s[IU]}).", var_ano(s))
            med = e["serie"].get("atend_med", zeros())
            if med[IU] == 0 and med12(med) >= 30:
                alerta("alta", "sem atendimento médico", caminho, f"Nenhum atendimento de médico em {ULT} (habitual, mediana dos 12 meses anteriores: {med12(med):.0f}/mês).", 0)
            lot_acs = [p for p in profs if p["lotado"] and (p["cat"] or "").startswith("Agente")]
            sem_vis = [p["nome"] for p in lot_acs if not p["serie"].get("visitas", zeros())[IU]]
            if sem_vis:
                _pub = f"{len(sem_vis)} de {len(lot_acs)} ACS lotados sem visita registrada em {ULT}"
                alerta("media", "ACS sem visita", caminho, _pub, len(sem_vis), nominal=_pub + ": " + ", ".join(sem_vis[:4]) + ("…" if len(sem_vis) > 4 else ""))
            n3 = sum(s[max(IU - 2, 0):IU + 1])
            for fam, rot in (("p_cito", "coleta de citopatológico"), ("p_ts_sif", "teste rápido de sífilis")):
                if n3 >= 300 and not sum(e["serie"].get(fam, zeros())[max(IU - 2, 0):IU + 1]):
                    alerta("media", "sem registro de procedimento", caminho, f"Nenhum registro de {rot} em {MESES[max(IU-2,0)]} a {ULT} (a equipe teve {n3} atendimentos no período).", 0)
        e["kpi"] = {"atend_ult": s[IU], "var_ano": var_ano(s)}
        if e["ine"] and CAD_INE.get(e["ine"]): e["cad"] = CAD_INE[e["ine"]]
        equipes.append(e)
    ordem = {"eSF": 0, "eSB": 1, "eMulti": 2, "eCR": 3}
    equipes.sort(key=lambda e: (e["ine"] == "", ordem.get(e["tipo"], 9), e["nome"]))
    ser = agrega([e["serie"] for e in equipes])
    if (var_ano(ser.get("atend", zeros())) or 0) <= -ALERTA_QUEDA and ser.get("atend", zeros())[IU - 12 if IU >= 12 else 0] >= BASE_MIN_UBS:
        a = ser["atend"]; alerta("media", "queda de atendimentos", f"{u['gsap']} › {u['nome']}", f"UBS: atendimentos {var_ano(a):+.0%} contra {MESES[IU-12]} ({a[IU-12]} → {a[IU]}).", var_ano(a))
    sem = sum(e["serie"].get("atend", zeros())[IU] for e in equipes if not e["ine"])
    tot = (ser.get("atend") or zeros())[IU]
    if tot >= 200 and sem / tot >= 0.30:
        alerta("media", "produção sem equipe", f"{u['gsap']} › {u['nome']}", f"{sem/tot:.0%} dos atendimentos de {ULT} ({sem} de {tot}) sem equipe vinculada.", sem / tot)
    gsaps[u["gsap"]]["ubs"].append({"cnes": cnes, "nome": u["nome"], "sigla": u["sigla"], "ra": u["ra"], "equipes": equipes, "serie": ser, "cad": CAD_CNES.get(cnes) or None,
                                    "n_esf": sum(1 for e in equipes if e["tipo"] == "eSF")})

saida_g = []
for g, d in sorted(gsaps.items(), key=lambda t: (t[0].startswith("Fora"), t[0])):
    d["ubs"].sort(key=lambda x: x["nome"])
    saida_g.append({"nome": g, "ubs": d["ubs"], "serie": agrega([x["serie"] for x in d["ubs"]]), "n_esf": sum(x["n_esf"] for x in d["ubs"])})
regiao = agrega([g["serie"] for g in saida_g])
alertas.sort(key=lambda a: (a["nivel"] != "alta", a["tipo"], a["caminho"]))

# ---------- consultas por mil habitantes nas regiões de saúde (InfoSaúde ÷ população do InfoSaúde por RA) ----------
def bloco_razao():
    if not (BR / "razao_regioes.json").exists() or not (BR / "populacao.json").exists(): return None
    rz, pp = L("razao_regioes"), L("populacao")
    POPR = defaultdict(int)
    for x in pp:
        if x["reg"]: POPR[(int(x["ano"]), x["reg"])] += x["pop"] or 0
    REGS = sorted({r for (_, r) in POPR if r.startswith("Região ")}, key=lambda r: (r != "Região Norte", r))
    N = defaultdict(int)
    for x in rz:
        if x["reg"] in REGS: N[(x["reg"], x["ano"], x["mes"], x["cat"])] += x["n"]
    uy, um = map(int, ULT.split("-"))
    def janela(ano_fim, mes_fim):      # 12 meses terminando em (ano_fim, mes_fim)
        return [((ano_fim * 12 + mes_fim - 1 - k) // 12, (ano_fim * 12 + mes_fim - 1 - k) % 12 + 1) for k in range(11, -1, -1)]
    def soma(regs, meses, cat): return sum(N[(r, a, m, cat)] for r in regs for a, m in meses)
    def popu(regs, ano): return sum(POPR.get((ano, r), 0) for r in regs)
    entes = [("Região Norte", ["Região Norte"]), ("Distrito Federal", REGS)] + [(r, [r]) for r in REGS if r != "Região Norte"]
    anos_ok = [a for a in range(2022, uy + (1 if um == 12 else 0)) if popu(REGS, a)]
    out = []
    for nome, regs in entes:
        anos = {}
        for a in anos_ok:
            meses = [(a, m) for m in range(1, 13)]
            anos[str(a)] = {"med": soma(regs, meses, "MÉDICO"), "enf": soma(regs, meses, "ENFERMEIRO"), "pop": popu(regs, a)}
        j1, j0 = janela(uy, um), janela(uy - 1, um)
        out.append({"nome": nome, "anos": anos,
                    "m12": {"med": soma(regs, j1, "MÉDICO"), "enf": soma(regs, j1, "ENFERMEIRO"), "pop": popu(regs, uy)},
                    "m12ant": {"med": soma(regs, j0, "MÉDICO"), "enf": soma(regs, j0, "ENFERMEIRO"), "pop": popu(regs, uy - 1)}})
    # bases alternativas de população (filtro da aba): Censo 2022 (só Norte e DF) e população cadastrada na última competência
    cr = L("cadastros_regiao") if (BR / "cadastros_regiao.json").exists() else []
    cad_reg = defaultdict(int)
    for x in cr:
        if x["comp"] == CAD_COMP and x["reg"] in REGS: cad_reg[x["reg"]] += x["n"] or 0
    for e in out:
        regs = REGS if e["nome"] == "Distrito Federal" else [e["nome"]]
        e["pop_censo"] = CENSO_2022.get(e["nome"])
        e["pop_cad"] = sum(cad_reg[r] for r in regs) or None
    return {"entes": out, "brasil": BRASIL_RIPSA, "anos": [str(a) for a in anos_ok], "cad_comp": CAD_COMP,
            "janela": f"{MESES[IU-11] if IU >= 11 else ''}", "ult": ULT,
            "cad_regiao": sum(CAD_CNES[c] for c in APS), "cad_df": sum(CAD_CNES.values())}
RAZAO = bloco_razao()
USUARIOS = L("usuarios") if (BR / "usuarios.json").exists() else None   # pessoas distintas e hiperfrequentadores (coleta/usuarios.py); só contagens por faixa

# ---------- separa o que identifica servidor (bloco nominal) do que é público ----------
import base64, gzip
SAL_SENHA = "6d1a1def6f094a28d4e7c3edea6257aa"     # sal fixo do PBKDF2 (não é segredo; fixo para o "lembrar neste navegador" valer entre atualizações)
ITERACOES = 600_000
SENHA_MIN = 12
EM_CI = bool(os.environ.get("GITHUB_ACTIONS"))
def _senha():
    s = os.environ.get("APS_SENHA")
    if not s:
        f = AQUI / "senha.local"
        if f.exists(): s = f.read_text(encoding="utf-8")
    s = (s or "").strip()
    if s and len(s) < SENHA_MIN: raise SystemExit(f"A senha dos gestores precisa ter pelo menos {SENHA_MIN} caracteres: o arquivo cifrado é público e senha curta pode ser descoberta por tentativa.")
    return s
SENHA = _senha()

# ---------- inconsistências de registro e de lotação (só na área dos gestores: vai inteiro para o bloco cifrado) ----------
incons = []
_MA = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
def rot_mes(m): return f"{_MA[int(m[5:7]) - 1]}/{m[2:4]}" if m else "–"
M3 = rot_mes(MESES[max(IU - 2, 0)]); ULT_R = rot_mes(ULT)
def s3(v): return sum(v[max(IU - 2, 0):IU + 1])
def p3(p): return sum(s3(v) for v in p["serie"].values())
def a3(p): return s3(p["serie"].get("atend", zeros()))
def inc(tipo, g, u, e, det, n=0, nome="", cat=""):
    incons.append({"tipo": tipo, "gsap": g["nome"], "ubs": u["nome"], "equipe": e["nome"] if e else "", "nome": nome, "cat": cat or "", "det": det, "n": n})
_pess = defaultdict(list)
for g in saida_g:
    for u in g["ubs"]:
        for e in u["equipes"]:
            for p in e["prof"]: _pess[p["id"]].append((g, u, e, p))
for g in saida_g:
    for u in g["ubs"]:
        sem_ubs = sum(e["serie"].get("atend", zeros())[IU] for e in u["equipes"] if not e["ine"])
        for e in u["equipes"]:
            tot3 = sum(s3(v) for v in e["serie"].values())
            if not e["ine"]:      # produção registrada sem INE: quem registrou
                for p in e["prof"]:
                    if not p3(p): continue
                    lot = [(x[2], x[1]) for x in _pess[p["id"]] if x[3]["lotado"]]
                    onde = f"lotado na {lot[0][0]['nome']} ({lot[0][1]['nome']})" if lot else f"não consta na lotação de {RH_ROT}"
                    inc("sem_ine", g, u, e, f"{a3(p)} atendimentos e {p3(p) - a3(p)} outros registros sem equipe de {M3} a {ULT_R}; {onde}.", p3(p), p["nome"], p["cat"])
                continue
            s = e["serie"].get("atend", zeros())
            if e.get("migrou"):
                inc("mudou_ubs", g, u, e, f"INE {e['ine']} passou a registrar na {e['migrou']['para']}; último registro aqui em {rot_mes(e['migrou']['ultimo'])}. Conferir a lotação no RH.")
            elif not e["no_rh"] and tot3:
                inc("ine_fora_rh", g, u, e, f"INE {e['ine']} ({e['tipo']}) tem {tot3} registros de {M3} a {ULT_R}, mas não consta na planilha de RH de {RH_ROT}.", tot3)
            elif e["no_rh"] and not tot3:
                inc("eq_sem_prod", g, u, e, f"Equipe da planilha de RH de {RH_ROT} (INE {e['ine']}, {e['tipo']}) sem nenhum registro de {M3} a {ULT_R}.")
            if e["tipo"] == "eSF" and not e.get("migrou") and med12(s) >= 100 and s[IU] < 0.5 * med12(s) and sem_ubs >= 50:
                inc("lugar_errado", g, u, e, f"{s[IU]} atendimentos em {ULT_R} (habitual {med12(s):.0f}) e a UBS tem {sem_ubs} atendimentos sem equipe vinculada no mesmo mês: parte pode ser desta equipe.", sem_ubs)
            for p in e["prof"]:
                vinc = _pess[p["id"]]
                if p["lotado"]:
                    aqui = p3(p); fora = [(x, p3(x[3])) for x in vinc if x[3] is not p and p3(x[3])]
                    tfora = sum(n for _, n in fora)
                    if not aqui and not tfora:
                        inc("lot_sem_prod", g, u, e, f"Consta na lotação de {RH_ROT} e não tem nenhum registro de {M3} a {ULT_R} (pode ser férias, afastamento ou função sem registro).", 0, p["nome"], p["cat"])
                    elif tfora > aqui and tfora >= 20:
                        (xg, xu, xe, _), n = max(fora, key=lambda t: t[1])
                        inc("lot_outra", g, u, e, f"Lotado nesta equipe, com {aqui} registros aqui e {tfora} em outro lugar de {M3} a {ULT_R}; o maior volume está em {xe['nome']} ({xu['nome']}).", tfora, p["nome"], p["cat"])
                elif p3(p) >= 10 and not any(x[3]["lotado"] for x in vinc):
                    inc("prod_fora_rh", g, u, e, f"{p3(p)} registros nesta equipe de {M3} a {ULT_R} e não consta na lotação de {RH_ROT}.", p3(p), p["nome"], p["cat"])
for a in alertas:
    if a["tipo"] == "sem registro de procedimento":
        gn, un, en = a["caminho"].split(" › ")
        incons.append({"tipo": "lugar_errado", "gsap": gn, "ubs": un, "equipe": en, "nome": "", "cat": "", "det": a["texto"] + " Pode estar sendo registrado em outra equipe, sem equipe ou fora do campo de procedimento.", "n": 0})
incons.sort(key=lambda x: (x["tipo"], x["gsap"], x["ubs"], x["equipe"], -x["n"], x["nome"]))

nominal_prof, nomes_todos = {}, set()
for g in saida_g:
    for u in g["ubs"]:
        for e in u["equipes"]:
            profs = e.pop("prof")
            e["n_prof"] = sum(1 for p in profs if p["ativo"])       # contagem, pública
            if profs: nominal_prof[f"{u['cnes']}|{e['ine'] or 'SEM'}"] = profs
            nomes_todos.update(p["nome"] for p in profs)
GERADO = dt.datetime.now().isoformat(timespec="minutes")
nominal = {"gerado": GERADO, "com_matricula": bool(PRIV), "prof": nominal_prof, "alertas": alertas_nominais, "incons": incons}
if EM_CI and (PRIV or any("mat" in p for l in nominal_prof.values() for p in l)):
    raise SystemExit("Matrícula encontrada numa geração feita no GitHub: abortado. A matrícula só pode existir na geração local.")

painel = {
    "gerado": GERADO, "meses": MESES, "ultimo_mes_completo": ULT,
    "mes_parcial": MES_PARCIAL if MESES[-1] == MES_PARCIAL else None,
    "fonte": f"InfoSaúde-DF · Sala de Situação · Atenção Primária (SES-DF); lotação: RH APS Norte {RH_ROT}", "rh_rot": RH_ROT,
    "indicadores": {k: {"nome": v[0].strip(), "sub": v[0].startswith(" "), "unidade": v[1], "nivel": v[2], "grp": GRP[k]} for k, v in IND.items()},
    "regiao": regiao, "razao": RAZAO, "usuarios": USUARIOS, "gsaps": saida_g, "alertas": alertas, "restrito": bool(SENHA),
    "fora_da_aps": {k: v for k, v in sorted(fora_aps.items(), key=lambda t: -sum(t[1]))[:12]},
}
publico = json.dumps(painel, ensure_ascii=False, separators=(",", ":"))

# trava: nada nominal no que é público (nome de servidor, sequência longa de dígitos, campos do bloco nominal)
_pub_norm = norm_nome(publico); _html = (RAIZ / "site" / "index.html").read_text("utf-8") if (RAIZ / "site" / "index.html").exists() else ""
_html_norm = norm_nome(_html)
_vaz = sorted(n for n in nomes_todos if len(norm_nome(n)) >= 10 and " " in n and (norm_nome(n) in _pub_norm or norm_nome(n) in _html_norm))
if _vaz: raise SystemExit(f"TRAVA: {len(_vaz)} nome(s) de servidor apareceriam na parte pública (ex.: equipe ou unidade com o mesmo texto de um nome). Nada foi gravado.")
if re.search(r"(?<![0-9.])[0-9]{11,}", publico): raise SystemExit("TRAVA: sequência de 11 ou mais dígitos na parte pública (pode ser CNS ou CPF). Nada foi gravado.")
if '"prof":' in publico or '"mat":' in publico or '"cns":' in publico or '"nome_rh":' in publico: raise SystemExit("TRAVA: campo nominal na parte pública. Nada foi gravado.")

(RAIZ / "dados").mkdir(exist_ok=True)
(RAIZ / "dados" / "painel.json").write_text(publico, "utf-8")
(RAIZ / "site").mkdir(exist_ok=True)   # mesmo conteúdo como script, para a página abrir direto do arquivo (file://) sem servidor
(RAIZ / "site" / "painel.js").write_text("window.PAINEL=" + publico + ";", "utf-8")
_nom_js = RAIZ / "site" / "nominal.js"; _nom_claro = RAIZ / "dados" / "nominal.json"
if SENHA:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    import unicodedata
    chave = hashlib.pbkdf2_hmac("sha256", unicodedata.normalize("NFC", SENHA).encode("utf-8"), bytes.fromhex(SAL_SENHA), ITERACOES, 32)
    iv = os.urandom(12)
    claro = gzip.compress(json.dumps(nominal, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), 9)
    ct = AESGCM(chave).encrypt(iv, claro, b"aps-norte-v1")
    b64 = lambda b: base64.b64encode(b).decode()
    _nom_js.write_text("window.NOMINAL=" + json.dumps({"v": 1, "it": ITERACOES, "sal": b64(bytes.fromhex(SAL_SENHA)), "iv": b64(iv), "ct": b64(ct), "gerado": GERADO}) + ";", "utf-8")
else:
    if _nom_js.exists(): _nom_js.unlink()
    print("AVISO: senha dos gestores não configurada (APS_SENHA ou coleta/senha.local). O painel saiu SÓ com a parte pública, sem lista de profissionais.")
if EM_CI:
    if _nom_claro.exists(): _nom_claro.unlink()
else:   # cópia em claro só no computador dela (pasta dados/, fora do git): usada pelos testes
    _nom_claro.write_text(json.dumps(nominal, ensure_ascii=False, separators=(",", ":")), "utf-8")

# resumo para conferência
n_eq = sum(len(u["equipes"]) for g in saida_g for u in g["ubs"]); n_pr = sum(len(l) for l in nominal_prof.values())
print(f"{len(saida_g)} GSAPs | {sum(len(g['ubs']) for g in saida_g)} UBS | {n_eq} equipes | {n_pr} profissionais | {len(alertas)} alertas | último mês completo {ULT}")
print("atendimentos região (últimos 4):", regiao["atend"][-4:], "| só APS (excl. hospitais):", f"hospitais/outros fora da APS em {ULT}: {sum(v[IU] for v in fora_aps.values())}")
print("inconsistências por tipo:", {t: sum(1 for x in incons if x["tipo"] == t) for t in sorted({x["tipo"] for x in incons})})
print("alertas por tipo:", {t: sum(1 for a in alertas if a["tipo"] == t) for t in sorted({a['tipo'] for a in alertas})})
for a in alertas[:12]: print(" -", a["nivel"], "|", a["caminho"], "|", a["texto"])   # texto público, sem nomes
print("bloco nominal:", f"cifrado em site/nominal.js ({round(_nom_js.stat().st_size / 1e6, 2)} MB)" if SENHA else "NÃO gerado (sem senha)")
print("tamanho:", round((RAIZ / "dados" / "painel.json").stat().st_size / 1e6, 2), "MB")
