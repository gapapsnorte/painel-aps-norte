"""Coleta mensal da Região Norte (Sala de Situação do InfoSaúde) no nível profissional × equipe.
Saída: ../dados/brutos/<conjunto>.json  (lista de linhas). Uso: python coleta.py [AAAA-MM inicial] [--so-ciap]
O CNS do profissional é trocado pelo código embaralhado (sigilo.hc) antes de gravar: o número real não vai para o disco."""
import json, re, sys, time, datetime as dt
from pbi_lib import Painel, col, conta, soma, lit_txt, lit_int, em
from sigilo import embaralhar_linhas, pepper
from comum import AQUI, OUT, URL, TETO, hoje_brt, mes_where, lit_dt
from familias import COD2FAM

_args = [a for a in sys.argv[1:] if not a.startswith("--")]     # "--so-ciap" pode vir em qualquer posição
INICIO = _args[0] if _args else "2022-01"
pepper()    # sem o segredo, para antes de consultar: nada de coletar para depois não poder gravar
hoje = hoje_brt()
MESES = []
a, m = map(int, INICIO.split("-"))
while (a, m) <= (hoje.year, hoje.month):
    MESES.append((a, m)); a, m = (a + (m == 12), m % 12 + 1)
log = []

def coleta(nome, titulo, entidades, select, filtro_regiao, tempo, por_mes=True):
    t0 = time.time(); p = Painel(URL[titulo]); todas = []
    alvos = MESES if por_mes else sorted({a for a, _ in MESES})
    for alvo in alvos:
        if por_mes:
            a, m = alvo; where = [filtro_regiao] + mes_where(*tempo, a, m)
        else:
            alias, c_ano, _c, inteiro = tempo
            where = [filtro_regiao, em(col(alias, c_ano), [lit_int(alvo) if inteiro else lit_txt(str(alvo))])]
        r = p.consulta(entidades, select, where, limite=TETO)
        if len(r) >= TETO:
            raise RuntimeError(f"{nome} {alvo}: {len(r)} linhas = teto; dividir mais a consulta")
        if por_mes:
            for l in r: l["compt"] = f"{alvo[0]}-{str(alvo[1]).zfill(2)}"
        else:
            for l in r: l["compt"] = f"{alvo}-{str(l['mes']).zfill(2)}"
        todas += r
    if not todas: raise RuntimeError(f"{nome}: a coleta voltou vazia (coluna ou filtro mudou no InfoSaúde?)")
    (OUT / f"{nome}.json").write_text(json.dumps(embaralhar_linhas(todas), ensure_ascii=False), "utf-8")
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
def coleta_proc():
    t0 = time.time(); p = Painel(URL["Painel de Procedimentos"]); todas = []
    PR = {"f": "f_vw_procedimentos_invidualizados_sem_codigo_ab"}
    sel = [("cnes", col("f", "i_estab_cnes")), ("ubs", col("f", "i_sigla_estab_cnes")), ("ine", col("f", "i_ine")), ("cns", col("f", "i_nu_cns")),
           ("nome", col("f", "i_no_profissional")), ("cat", col("f", "i_cat_prof")), ("cod", col("f", "i_cod_procedimento")), ("n", soma("f", "i_qtd"))]
    cods = em(col("f", "i_cod_procedimento"), [lit_txt(c) for c in COD2FAM])
    for a, m in MESES:
        where = [regiao("f"), cods, em(col("f", "data_compt"), [lit_dt(a, m)])]
        r = p.consulta(PR, sel, where, limite=TETO)
        if len(r) >= TETO: raise RuntimeError(f"procedimentos {a}-{m:02d}: {len(r)} linhas = teto; dividir a consulta")
        for l in r: l["compt"] = f"{a}-{str(m).zfill(2)}"
        todas += r
    if not todas: raise RuntimeError("procedimentos: a coleta voltou vazia (coluna ou filtro mudou no InfoSaúde?)")
    (OUT / "procedimentos.json").write_text(json.dumps(embaralhar_linhas(todas), ensure_ascii=False), "utf-8")
    msg = f"[procedimentos] {len(todas)} linhas em {time.time()-t0:.0f}s"; print(msg); log.append(msg)
coleta_proc()

# 8. Motivos de consulta: equipe x CID por mês e, para os registros sem CID, equipe x CIAP. Particionado por UBS para não bater no teto de linhas
def coleta_motivos():
    p = Painel(URL["Atendimentos Individuais na APS"])
    ref = json.load(open(AQUI / "referencia.json", encoding="utf-8"))
    cnes_aps = sorted(c for c, u in ref["ubs"].items() if re.match(r"UBS", u["nome_rh"] or ""))
    def rodada(nome, E, sel, extra, passo):
        t0 = time.time()
        def q(a, m, lista):
            where = [regiao("e")] + mes_where("f", "i_ano_compt", "i_mes_compt", a, m) + [em(col("e", "i_estab_cnes"), [lit_txt(c) for c in lista])] + extra
            r = p.consulta(E, sel, where, limite=TETO)
            if len(r) >= TETO:
                if len(lista) == 1: raise RuntimeError(f"{nome} {a}-{m:02d} cnes {lista[0]}: {len(r)} linhas = teto")
                h = len(lista) // 2; return q(a, m, lista[:h]) + q(a, m, lista[h:])
            return r
        todas = []
        for a, m in MESES:
            for i in range(0, len(cnes_aps), passo):
                for l in q(a, m, cnes_aps[i:i + passo]):
                    l["compt"] = f"{a}-{m:02d}"; todas.append(l)
        if not todas: raise RuntimeError(f"{nome}: a coleta voltou vazia (coluna ou filtro mudou no InfoSaúde?)")
        (OUT / f"{nome}.json").write_text(json.dumps(todas, ensure_ascii=False), "utf-8")
        msg = f"[{nome}] {len(todas)} linhas em {time.time()-t0:.0f}s"; print(msg); log.append(msg)
    base = [("cnes", col("e", "i_estab_cnes")), ("ine", col("e", "i_ine"))]; n = [("n", soma("fa", "i_qtd_atendimento_prof"))]
    if "--so-ciap" not in sys.argv:
        rodada("motivos", {"f": "fAtd_indiv", "e": "dEstabelecimentos", "fa": "fAtendimentos", "c": "dCid"}, base + [("cid", col("c", "cid"))] + n, [], 8)
    # registros sem CID (campo vazio na fato): o motivo vem do CIAP; vazio nos dois = sem motivo registrado
    rodada("motivos_ciap", {"f": "fAtd_indiv", "e": "dEstabelecimentos", "fa": "fAtendimentos"}, base + [("ciap", col("f", "ciap"))] + n, [em(col("f", "cid"), [lit_txt("")])], 20)
coleta_motivos()

(OUT / "_log.json").write_text(json.dumps({"quando": dt.datetime.now().isoformat(timespec="seconds"), "meses": [f"{a}-{m:02d}" for a, m in MESES], "log": log}, ensure_ascii=False, indent=1), "utf-8")
print("[ok]")
