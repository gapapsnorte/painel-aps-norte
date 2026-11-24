"""Totais mensais por região de saúde do DF (InfoSaúde, Power BI público), desde jan/2022, para cada indicador do painel.
Mesmas regras de contagem de coleta.py/montar.py, agrupando por região de saúde (sem filtrar a Norte).
Saída: ../dados/brutos/regioes.json = [{"reg","compt","ind","n"}]. Uso (de dentro de coleta/): python -X utf8 regioes.py"""
import json, time
from collections import defaultdict
from pbi_lib import Painel, col, conta, soma, lit_txt, em
from familias import COD2FAM, FAMILIAS
from comum import OUT, URL, TETO, hoje_brt, mes_where as mes_where_comum, lit_dt

ANO0 = 2022
hoje = hoje_brt()
ANOS = list(range(ANO0, hoje.year + 1))
MESES = [(a, m) for a in ANOS for m in range(1, 13) if (a, m) <= (hoje.year, hoje.month)]
T0 = time.time()
TIPOS_ACESSO = {"Consulta no dia": "a_dia", "Consulta agendada": "a_agend", "Consulta agendada programada / Cuidado continuado": "a_prog",
                "Atendimento de urgência": "a_urg", "Escuta inicial / Orientação": "a_escuta"}
CONDS = {"prenatal": "Pré-natal", "has": "Hipertensão arterial", "dm": "Diabetes", "mental": "Saúde mental",
         "colo": "Rast. câncer do colo do útero", "mama": "Rast. câncer de mama", "ist": "D.Transmissíveis - DST"}


REGS7 = {"Região Central", "Região Centro-Sul", "Região Leste", "Região Norte", "Região Oeste", "Região Sudoeste", "Região Sul"}
DESCARTADAS = defaultdict(int)   # rótulos que não são região de saúde (Samu, Privado, SVS...) e quanto somavam


def reg_norm(r):
    s = " ".join(str(r or "").split())
    if s in REGS7: return s
    DESCARTADAS[s or "(vazio)"] += 1
    return None


def ano_where(alias, ano): return em(col(alias, "i_ano_compt"), [lit_txt(str(ano))])
def mes_where(alias, a, m): return mes_where_comum(alias, "i_ano_compt", "i_mes_compt", a, m)


ACUM = defaultdict(float)   # (reg, compt, ind) -> n
PRIMEIRA = {}               # fonte -> 1ª competência com dado
def add(fonte, reg, compt, ind, n):
    reg = reg_norm(reg)
    if reg is None or not n: return
    ACUM[(reg, compt, ind)] += n
    if compt < PRIMEIRA.get(fonte, "9999"): PRIMEIRA[fonte] = compt
def checa(nome, r, chave):
    if len(r) >= TETO: raise RuntimeError(f"{nome} {chave}: {len(r)} linhas = teto; dividir mais a consulta")
def vazia(nome, total):
    if total == 0: raise RuntimeError(f"{nome}: a coleta voltou vazia (coluna ou filtro mudou no InfoSaúde?)")


# 1. Atendimentos individuais: região x categoria x tipo, por mês
p = Painel(URL["Atendimentos Individuais na APS"]); tot = 0
ENT = {"f": "fAtd_indiv", "e": "dEstabelecimentos", "fa": "fAtendimentos", "pr": "dProfissionais"}
for a, m in MESES:
    r = p.consulta(ENT, [("reg", col("e", "i_desc_regiao_saude")), ("cat", col("pr", "i_cat_prof")), ("tipo", col("f", "i_tipo_atendimento")),
                        ("n", soma("fa", "i_qtd_atendimento_prof"))], mes_where("f", a, m), limite=TETO)
    checa("atendimentos", r, (a, m)); tot += len(r); c = f"{a}-{m:02d}"
    for l in r:
        n = l["n"] or 0
        for ind in ["atend"] + (["atend_med"] if l["cat"] == "MÉDICO" else []) + (["atend_enf"] if l["cat"] == "ENFERMEIRO" else []): add("atendimentos", l["reg"], c, ind, n)
        if TIPOS_ACESSO.get(l["tipo"]): add("atendimentos", l["reg"], c, TIPOS_ACESSO[l["tipo"]], n)
        if l["cat"] not in ("MÉDICO", "ENFERMEIRO"): add("atendimentos", l["reg"], c, "atend_out", n)
vazia("atendimentos", tot); print(f"[atendimentos] {tot} linhas, {time.time()-T0:.0f}s", flush=True)

# 2. Visitas: região x desfecho
p = Painel(URL["Visita Domiciliar dos ACS"]); tot = 0
for a, m in MESES:
    r = p.consulta({"f": "tab_visita_domiciliar"}, [("reg", col("f", "i_desc_regiao_saude")), ("desfecho", col("f", "i_desc_desfecho_visita")), ("n", conta("f", "i_id_fato"))],
               mes_where("f", a, m), limite=TETO)
    checa("visitas", r, (a, m)); tot += len(r); c = f"{a}-{m:02d}"
    for l in r:
        add("visitas", l["reg"], c, "visitas", l["n"] or 0)
        if l["desfecho"] == "Visita realizada": add("visitas", l["reg"], c, "visitas_ok", l["n"] or 0)
vazia("visitas", tot); print(f"[visitas] {tot} linhas, {time.time()-T0:.0f}s", flush=True)

# 3. Vacinas
p = Painel(URL["Vacinas Aplicadas na APS"]); tot = 0
for a, m in MESES:
    r = p.consulta({"f": "tab_vacinacao_vacina"}, [("reg", col("f", "i_desc_regiao_saude")), ("n", conta("f", "i_id_fato_vacinacao_vacina"))], mes_where("f", a, m), limite=TETO)
    checa("vacinas", r, (a, m)); tot += len(r)
    for l in r: add("vacinas", l["reg"], f"{a}-{m:02d}", "vacinas", l["n"] or 0)
vazia("vacinas", tot); print(f"[vacinas] {tot} linhas, {time.time()-T0:.0f}s", flush=True)

# 4. Atividades coletivas
p = Painel(URL["Atividade Coletiva na APS"]); tot = 0
for a, m in MESES:
    r = p.consulta({"f": "fDados"}, [("reg", col("f", "i_desc_regiao_saude")), ("n", conta("f", "i_id_fato")), ("part", soma("f", "i_qtd_participantes"))], mes_where("f", a, m), limite=TETO)
    checa("coletivas", r, (a, m)); tot += len(r); c = f"{a}-{m:02d}"
    for l in r: add("coletivas", l["reg"], c, "coletivas", l["n"] or 0); add("coletivas", l["reg"], c, "participantes", l["part"] or 0)
vazia("coletivas", tot); print(f"[coletivas] {tot} linhas, {time.time()-T0:.0f}s", flush=True)

# 5. Condições avaliadas (por ano; o mês vem na linha)
p = Painel(URL["Atendimentos Individuais na APS – Condição Avaliada"]); tot = 0
for ano in ANOS:
    r = p.consulta({"f": "cond_aval"}, [("reg", col("f", "i_desc_regiao_saude")), ("mes", col("f", "i_mes_compt"))] + [(k, soma("f", c)) for k, c in CONDS.items()], [ano_where("f", ano)], limite=TETO)
    checa("condicoes", r, ano); tot += len(r)
    for l in r:
        c = f"{ano}-{str(l['mes']).zfill(2)}"
        for k in CONDS: add("condicoes", l["reg"], c, k, l[k] or 0)
vazia("condicoes", tot); print(f"[condicoes] {tot} linhas, {time.time()-T0:.0f}s", flush=True)

# 6. Odontologia
p = Painel(URL["Atendimentos Odontológicos na APS"]); tot = 0
for ano in ANOS:
    r = p.consulta({"f": "odont_tipo_consulta"}, [("reg", col("f", "i_desc_regiao_saude")), ("mes", col("f", "i_mes_compt")),
               ("primeira", soma("f", "Primeira consulta odontológica")), ("n", soma("f", "i_qtd_total"))], [ano_where("f", ano)], limite=TETO)
    checa("odonto", r, ano); tot += len(r)
    for l in r:
        c = f"{ano}-{str(l['mes']).zfill(2)}"; add("odonto", l["reg"], c, "odonto1", l["primeira"] or 0); add("odonto", l["reg"], c, "odonto", l["n"] or 0)
vazia("odonto", tot); print(f"[odonto] {tot} linhas, {time.time()-T0:.0f}s", flush=True)

# 7. Procedimentos: região x código por mês
p = Painel(URL["Painel de Procedimentos"]); tot = 0
PR = {"f": "f_vw_procedimentos_invidualizados_sem_codigo_ab"}
cods = em(col("f", "i_cod_procedimento"), [lit_txt(c) for c in COD2FAM])
for a, m in MESES:
    r = p.consulta(PR, [("reg", col("f", "i_desc_regiao_saude")), ("cod", col("f", "i_cod_procedimento")), ("n", soma("f", "i_qtd"))],
               [cods, em(col("f", "data_compt"), [lit_dt(a, m)])], limite=TETO)
    checa("procedimentos", r, (a, m)); tot += len(r)
    for l in r:
        fam = COD2FAM.get(str(l["cod"]))
        if fam: add("procedimentos", l["reg"], f"{a}-{m:02d}", fam, l["n"] or 0)
vazia("procedimentos", tot); print(f"[procedimentos] {tot} linhas, {time.time()-T0:.0f}s", flush=True)

linhas = [{"reg": k[0], "compt": k[1], "ind": k[2], "n": int(v) if float(v).is_integer() else v} for k, v in sorted(ACUM.items(), key=lambda t: (t[0][2], t[0][1], t[0][0]))]
(OUT / "regioes.json").write_text(json.dumps(linhas, ensure_ascii=False), "utf-8")
regs = sorted({l["reg"] for l in linhas}); inds = {l["ind"] for l in linhas}
TODOS = {"atend", "atend_med", "atend_enf", "visitas", "visitas_ok", "vacinas", "coletivas", "participantes", "prenatal", "has", "dm", "mental", "colo", "mama", "ist",
         "odonto1", "odonto", "a_dia", "a_agend", "a_prog", "a_urg", "a_escuta", "atend_out"} | set(FAMILIAS)
print("regiões:", regs); print("rótulos descartados (não são região de saúde):", dict(DESCARTADAS))
print("1ª competência por fonte:", PRIMEIRA)
print("indicadores sem linhas:", sorted(TODOS - inds))
print(f"[regioes] {len(linhas)} linhas, {len(regs)} regiões, {len(inds)} indicadores | tempo total {time.time()-T0:.0f}s")
