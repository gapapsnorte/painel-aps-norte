"""Coleta para o indicador 'consultas por mil habitantes' (RIPSA COB.1.01), nas 7 regiões de saúde do DF.
Saídas em ../dados/brutos/:
  populacao.json       população por RA e ano (série do InfoSaúde, painel Cobertura da APS, tabela base_populacional)
  razao_regioes.json   atendimentos individuais de médico e enfermeiro por região de saúde, ano e mês (desde 2022)
  cadastros.json       cadastros por UBS e equipe e competência (painel Cobertura da APS; o InfoSaúde parou em abr/2025)
  cadastros_regiao.json  cadastros por região de saúde e competência
Uso: python razao.py"""
import json, datetime as dt
from pbi_lib import Painel, col, soma, lit_txt, em
from comum import OUT, URL, TETO, hoje_brt

ANO0 = 2022

cob = Painel(URL["Cobertura da APS"])
pop = cob.consulta({"b": "base_populacional"},
                   [("ano", col("b", "ano")), ("reg", col("b", "regiao_saude_desc")), ("ra", col("b", "ra_ses_desc")), ("pop", col("b", "pop_total_ra"))], [], limite=TETO)
if not pop or len(pop) >= TETO: raise RuntimeError(f"populacao: {len(pop)} linhas (vazio ou no teto)")
(OUT / "populacao.json").write_text(json.dumps(pop, ensure_ascii=False), "utf-8")
print(f"[populacao] {len(pop)} linhas")

cad = cob.consulta({"b": "base_cadastros"},
                   [("comp", col("b", "competencia")), ("cnes", col("b", "cnes")), ("ine", col("b", "ine")), ("n", soma("b", "cadastros"))], [], limite=TETO)
if not cad or len(cad) >= TETO: raise RuntimeError("cadastros bateu no teto de linhas; dividir a consulta")
for l in cad:   # competência vem em milissegundos desde 1970 (UTC)
    d = dt.datetime.fromtimestamp(l["comp"] / 1000, dt.timezone.utc); l["comp"] = f"{d.year}-{d.month:02d}"
(OUT / "cadastros.json").write_text(json.dumps(cad, ensure_ascii=False), "utf-8")
print(f"[cadastros] {len(cad)} linhas, competências até {max(l['comp'] for l in cad)}")

cr = cob.consulta({"b": "base_cadastros", "d": "dIne"},
                  [("comp", col("b", "competencia")), ("reg", col("d", "i_desc_regiao")), ("n", soma("b", "cadastros"))], [], limite=TETO)
if not cr or len(cr) >= TETO: raise RuntimeError(f"cadastros_regiao: {len(cr)} linhas (vazio ou no teto)")
for l in cr:
    d = dt.datetime.fromtimestamp(l["comp"] / 1000, dt.timezone.utc); l["comp"] = f"{d.year}-{d.month:02d}"
(OUT / "cadastros_regiao.json").write_text(json.dumps(cr, ensure_ascii=False), "utf-8")
print(f"[cadastros_regiao] {len(cr)} linhas")

at = Painel(URL["Atendimentos Individuais na APS"]); linhas = []
for ano in range(ANO0, hoje_brt().year + 1):
    r = at.consulta({"f": "fAtd_indiv", "e": "dEstabelecimentos", "fa": "fAtendimentos", "pr": "dProfissionais"},
                    [("reg", col("e", "i_desc_regiao_saude")), ("mes", col("f", "i_mes_compt")), ("cat", col("pr", "i_cat_prof")), ("n", soma("fa", "i_qtd_atendimento_prof"))],
                    [em(col("f", "i_ano_compt"), [lit_txt(str(ano))])], limite=TETO)
    if len(r) >= TETO: raise RuntimeError(f"{ano}: {len(r)} linhas = teto; dividir a consulta")
    for x in r:
        if x["cat"] in ("MÉDICO", "ENFERMEIRO"):
            linhas.append({"ano": ano, "mes": int(x["mes"]), "reg": x["reg"], "cat": x["cat"], "n": x["n"] or 0})
(OUT / "razao_regioes.json").write_text(json.dumps(linhas, ensure_ascii=False), "utf-8")
print(f"[razao_regioes] {len(linhas)} linhas")
