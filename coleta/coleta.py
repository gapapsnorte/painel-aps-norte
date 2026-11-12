"""Coleta mensal da Região Norte (Sala de Situação do InfoSaúde) no nível profissional × equipe.
Saída: ../dados/brutos/<conjunto>.json  (lista de linhas). Uso: python coleta.py [AAAA-MM inicial]"""
import json, re, sys, time, pathlib, datetime as dt
from pbi_lib import Painel, col, conta, soma, lit_txt, lit_int, em

AQUI = pathlib.Path(__file__).parent
OUT = AQUI.parent / "dados" / "brutos"; OUT.mkdir(parents=True, exist_ok=True)
URL = {i["titulo"]: i["url"] for i in json.load(open(AQUI / "paineis_aps.json", encoding="utf-8"))}
INICIO = sys.argv[1] if len(sys.argv) > 1 else "2024-01"
hoje = dt.date.today()
MESES = []
a, m = map(int, INICIO.split("-"))
while (a, m) <= (hoje.year, hoje.month):
    MESES.append((a, m)); a, m = (a + (m == 12), m % 12 + 1)
TETO = 30000
log = []

def mes_where(alias, c_ano, c_mes, a, m, inteiro=False):
    if inteiro: return [em(col(alias, c_ano), [lit_int(a)]), em(col(alias, c_mes), [lit_int(m)])]
    return [em(col(alias, c_ano), [lit_txt(str(a))]), em(col(alias, c_mes), [lit_txt(str(m).zfill(2))])]

def coleta(nome, titulo, entidades, select, filtro_regiao, tempo, por_mes=True):
    t0 = time.time(); p = Painel(URL[titulo]); todas = []
    alvos = MESES if por_mes else sorted({a for a, _ in MESES})
    for alvo in alvos:
        if por_mes:
            a, m = alvo; where = [filtro_regiao] + mes_where(*tempo, a, m)
        else:
            alias, c_ano, _c, inteiro = tempo
            where = [filtro_regiao, em(col(alias, c_ano), [lit_int(alvo) if inteiro else lit_txt(str(alvo))])]
        for tentativa in range(3):
            try:
                r = p.consulta(entidades, select, where, limite=TETO); break
            except Exception as ex:
                if tentativa == 2: raise
                time.sleep(5)
        if len(r) >= TETO:
            raise RuntimeError(f"{nome} {alvo}: {len(r)} linhas = teto; dividir mais a consulta")
        if por_mes:
            for l in r: l["compt"] = f"{alvo[0]}-{str(alvo[1]).zfill(2)}"
        else:
            for l in r: l["compt"] = f"{alvo}-{str(l['mes']).zfill(2)}"
        todas += r
    (OUT / f"{nome}.json").write_text(json.dumps(todas, ensure_ascii=False), "utf-8")
    msg = f"[{nome}] {len(todas)} linhas em {time.time()-t0:.0f}s"; print(msg); log.append(msg)
    return todas

def regiao(alias, c="i_desc_regiao_saude"): return em(col(alias, c), [lit_txt("Região Norte")])

# 1. Atendimentos individuais: profissional × equipe × tipo de atendimento (regra validada: soma de fAtendimentos.i_qtd_atendimento_prof)
coleta("atendimentos", "Atendimentos Individuais na APS",
       {"f": "fAtd_indiv", "e": "dEstabelecimentos", "fa": "fAtendimentos", "pr": "dProfissionais"},
       [("cnes", col("e", "i_estab_cnes")), ("ubs", col("e", "i_sigla_estab_cnes")), ("ine", col("e", "i_ine")), ("tipo_eq", col("e", "i_tipo_equipe")),
        ("cns", col("f", "i_nu_cns_prof")), ("nome", col("pr", "i_no_profissional")), ("cat", col("pr", "i_cat_prof")),
        ("tipo", col("f", "i_tipo_atendimento")), ("n", soma("fa", "i_qtd_atendimento_prof"))],
       regiao("e"), ("f", "i_ano_compt", "i_mes_compt"))

# 2. Visitas domiciliares: profissional × equipe × desfecho
coleta("visitas", "Visita Domiciliar dos ACS", {"f": "tab_visita_domiciliar"},
       [("cnes", col("f", "i_estab_cnes")), ("ubs", col("f", "i_sigla_estab_cnes")), ("ine", col("f", "i_ine")), ("cns", col("f", "i_nu_cns")),
        ("nome", col("f", "i_no_profissional")), ("cat", col("f", "i_categoria_profissional")), ("desfecho", col("f", "i_desc_desfecho_visita")), ("n", conta("f", "i_id_fato"))],
       regiao("f"), ("f", "i_ano_compt", "i_mes_compt"))

# 3. Vacinas: profissional × equipe (doses)
coleta("vacinas", "Vacinas Aplicadas na APS", {"f": "tab_vacinacao_vacina"},
       [("cnes", col("f", "i_estab_cnes")), ("ubs", col("f", "i_sigla_estab_cnes")), ("ine", col("f", "i_ine")), ("cns", col("f", "i_nu_cns_prof")),
        ("nome", col("f", "i_no_profissional")), ("cat", col("f", "i_cat_prof")), ("n", conta("f", "i_id_fato_vacinacao_vacina"))],
       regiao("f"), ("f", "i_ano_compt", "i_mes_compt"))

# 4. Atividade coletiva: profissional × equipe × tipo
coleta("coletivas", "Atividade Coletiva na APS", {"f": "fDados"},
       [("cnes", col("f", "i_estab_cnes")), ("ubs", col("f", "i_sigla_estab_cnes")), ("ine", col("f", "i_ine")), ("cns", col("f", "i_nu_cns")),
        ("nome", col("f", "i_no_profissional")), ("cat", col("f", "i_categoria_profissional")), ("tipo", col("f", "i_tipo_atividade")),
        ("n", conta("f", "i_id_fato")), ("participantes", soma("f", "i_qtd_participantes"))],
       regiao("f"), ("f", "i_ano_compt", "i_mes_compt"))

# 5. Condição avaliada: só equipe (a tabela não tem profissional)
CONDS = ["Pré-natal", "Puerpério (até 42 dias)", "Hipertensão arterial", "Diabetes", "Saúde mental", "Rast. câncer do colo do útero", "Rast. câncer de mama",
         "D.Transmissíveis - DST", "D.Transmissíveis - Tuberculose", "D.Transmissíveis - Hanseníase", "Usuário de álcool", "Usuário de outras drogas", "Obesidade", "Tabagismo"]
coleta("condicoes", "Atendimentos Individuais na APS – Condição Avaliada", {"f": "cond_aval"},
       [("cnes", col("f", "i_estab_cnes")), ("ubs", col("f", "i_sigla_estab_cnes")), ("ine", col("f", "i_ine")), ("mes", col("f", "i_mes_compt"))]
       + [(c, soma("f", c)) for c in CONDS], regiao("f"), ("f", "i_ano_compt", "i_mes_compt", False), por_mes=False)

# 6. Odontologia: equipe de saúde bucal
coleta("odonto", "Atendimentos Odontológicos na APS", {"f": "odont_tipo_consulta"},
       [("cnes", col("f", "i_estab_cnes")), ("ubs", col("f", "i_sigla_estab_cnes")), ("ine", col("f", "i_ine")), ("mes", col("f", "i_mes_compt")),
        ("primeira", soma("f", "Primeira consulta odontológica")), ("retorno", soma("f", "Consulta de retorno")), ("manutencao", soma("f", "Consulta de manutenção")), ("n", soma("f", "i_qtd_total"))],
       regiao("f"), ("f", "i_ano_compt", "i_mes_compt", False), por_mes=False)

# 7. Procedimentos (famílias de interesse): profissional x equipe x código, por mês
from familias import COD2FAM
def lit_dt(a, m): return {"Literal": {"Value": f"datetime'{a}-{m:02d}-01T00:00:00'"}}
def coleta_proc():
    t0 = time.time(); p = Painel(URL["Painel de Procedimentos"]); todas = []
    PR = {"f": "f_vw_procedimentos_invidualizados_sem_codigo_ab"}
    sel = [("cnes", col("f", "i_estab_cnes")), ("ubs", col("f", "i_sigla_estab_cnes")), ("ine", col("f", "i_ine")), ("cns", col("f", "i_nu_cns")),
           ("nome", col("f", "i_no_profissional")), ("cat", col("f", "i_cat_prof")), ("cod", col("f", "i_cod_procedimento")), ("n", soma("f", "i_qtd"))]
    cods = em(col("f", "i_cod_procedimento"), [lit_txt(c) for c in COD2FAM])
    for a, m in MESES:
        where = [regiao("f"), cods, em(col("f", "data_compt"), [lit_dt(a, m)])]
        for tentativa in range(3):
            try:
                r = p.consulta(PR, sel, where, limite=TETO); break
            except Exception:
                if tentativa == 2: raise
                time.sleep(5)
        if len(r) >= TETO: raise RuntimeError(f"procedimentos {a}-{m:02d}: {len(r)} linhas = teto; dividir a consulta")
        for l in r: l["compt"] = f"{a}-{str(m).zfill(2)}"
        todas += r
    (OUT / "procedimentos.json").write_text(json.dumps(todas, ensure_ascii=False), "utf-8")
    msg = f"[procedimentos] {len(todas)} linhas em {time.time()-t0:.0f}s"; print(msg); log.append(msg)
coleta_proc()

# 8. Motivos de consulta (CID): equipe x CID por mês, particionado por UBS para não bater no teto de linhas
def coleta_motivos():
    t0 = time.time(); p = Painel(URL["Atendimentos Individuais na APS"])
    ref = json.load(open(AQUI / "referencia.json", encoding="utf-8"))
    cnes_aps = sorted(c for c, u in ref["ubs"].items() if re.match(r"UBS", u["nome_rh"] or ""))
    E = {"f": "fAtd_indiv", "e": "dEstabelecimentos", "fa": "fAtendimentos", "c": "dCid"}
    sel = [("cnes", col("e", "i_estab_cnes")), ("ine", col("e", "i_ine")), ("cid", col("c", "cid")), ("n", soma("fa", "i_qtd_atendimento_prof"))]
    def q(a, m, lista):
        where = [regiao("e")] + mes_where("f", "i_ano_compt", "i_mes_compt", a, m) + [em(col("e", "i_estab_cnes"), [lit_txt(c) for c in lista])]
        for tentativa in range(3):
            try:
                r = p.consulta(E, sel, where, limite=TETO); break
            except Exception:
                if tentativa == 2: raise
                time.sleep(5)
        if len(r) >= TETO:
            if len(lista) == 1: raise RuntimeError(f"motivos {a}-{m:02d} cnes {lista[0]}: {len(r)} linhas = teto")
            h = len(lista) // 2; return q(a, m, lista[:h]) + q(a, m, lista[h:])
        return r
    todas = []
    for a, m in MESES:
        for i in range(0, len(cnes_aps), 8):
            for l in q(a, m, cnes_aps[i:i + 8]):
                l["compt"] = f"{a}-{m:02d}"; todas.append(l)
    (OUT / "motivos.json").write_text(json.dumps(todas, ensure_ascii=False), "utf-8")
    msg = f"[motivos] {len(todas)} linhas em {time.time()-t0:.0f}s"; print(msg); log.append(msg)
coleta_motivos()

(OUT / "_log.json").write_text(json.dumps({"quando": dt.datetime.now().isoformat(timespec="seconds"), "meses": [f"{a}-{m:02d}" for a, m in MESES], "log": log}, ensure_ascii=False, indent=1), "utf-8")
print("[ok]")
