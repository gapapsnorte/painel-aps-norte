"""Mês em consolidação (aviso nos 10 primeiros dias do mês) e motivos de consulta por CID ou CIAP.
Uso: python testar_consol.py"""
import json, pathlib, sys
from playwright.sync_api import sync_playwright
RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "coleta"))
import motivos
url = (RAIZ / "site" / "index.html").as_uri()
P = json.load(open(RAIZ / "dados" / "painel.json", encoding="utf-8"))
erros, falhas = [], []
def conf(nome, ok, det=""):
    print(("OK   " if ok else "FALHA"), nome, ("| " + str(det)) if det != "" else "")
    if not ok: falhas.append(nome)
# troca a data de geração antes de a página ler o painel: simula o dia do mês
FINGE = """(dia) => { let p; Object.defineProperty(window, 'PAINEL', { configurable: true, get: () => p,
  set: v => { if (v.mes_parcial) v.gerado = v.mes_parcial + '-' + dia + 'T08:00'; p = v; } }); }"""
def abre(nav, dia):
    pg = nav.new_page(viewport={"width": 1280, "height": 900})
    pg.on("pageerror", lambda e: erros.append(f"pageerror: {e}")); pg.on("console", lambda m: erros.append(m.text) if m.type == "error" else None)
    if dia: pg.add_init_script(f"({FINGE})('{dia}')")
    pg.goto(url); pg.wait_for_selector("#arvore details.g"); return pg
with sync_playwright() as p:
    nav = p.chromium.launch(channel="chrome", headless=True)
    # dia 5: último mês completo ainda em consolidação
    pg = abre(nav, "05")
    conf("dia 5: aviso de consolidação visível", pg.locator("#consol").is_visible() and "ainda em consolidação" in pg.inner_text("#consol"), pg.inner_text("#consol")[:70])
    conf("dia 5: linha do topo diz (em consolidação)", "(em consolidação)" in pg.inner_text("#sub"))
    pg.select_option("#f-alerta", "alta"); pg.wait_for_timeout(700)
    chips = pg.locator("#arvore details.e .sinais .chip"); n = chips.count()
    conf("dia 5: etiquetas marcadas e com o aviso na dica", n > 0 and all("(em consolidação)" in chips.nth(i).inner_text() and "ainda em consolidação" in (chips.nth(i).get_attribute("title") or chips.nth(i).get_attribute("data-dica") or "") for i in range(n)), f"{n} etiquetas")
    conf("dia 5: sem rolagem lateral", pg.evaluate("document.documentElement.scrollWidth <= innerWidth"))
    pg.close()
    # dia 11: mês tratado como fechado
    pg = abre(nav, "11")
    conf("dia 11: sem aviso", not pg.locator("#consol").is_visible() and "(em consolidação)" not in pg.inner_text("#sub"))
    pg.select_option("#f-alerta", "alta"); pg.wait_for_timeout(700)
    conf("dia 11: etiquetas sem a marca", "(em consolidação)" not in pg.inner_text("#arvore"))
    pg.close()
    # ---- motivos: CID ou CIAP
    iu = P["meses"].index(P["ultimo_mes_completo"]); R = P["regiao"]
    mot = {k: R[k][iu] for k in R if k.startswith("m_")}; tot = sum(mot.values()); sem = mot.get("m_sem", 0)
    conf("motivos: 'sem CID nem CIAP' abaixo de 12% dos registros na Região", tot > 0 and 0 < sem / tot < 0.12, f"{sem} de {tot} = {sem / tot:.1%}")
    conf("motivos: rótulo novo da linha sem código", P["indicadores"]["m_sem"]["nome"] == "Sem CID nem CIAP registrado" if isinstance(P["indicadores"]["m_sem"], dict) else "Sem CID nem CIAP" in str(P["indicadores"]["m_sem"]))
    br = json.load(open(RAIZ / "dados" / "brutos" / "motivos.json", encoding="utf-8")); bc = json.load(open(RAIZ / "dados" / "brutos" / "motivos_ciap.json", encoding="utf-8"))
    um = P["ultimo_mes_completo"]
    vazio_cid = sum(l["n"] or 0 for l in br if l["compt"] == um and motivos.fam_cid(l["cid"]) == "m_sem"); so_ciap = sum(l["n"] or 0 for l in bc if l["compt"] == um)
    # um atendimento sem CID com dois CIAP conta uma vez na consulta por CID (vazio) e duas na consulta por CIAP: o total por CIAP é igual ou um pouco maior
    conf("coleta: total por CIAP coerente com os registros sem CID", vazio_cid <= so_ciap <= 1.4 * vazio_cid, f"{vazio_cid} sem CID x {so_ciap} códigos CIAP")
    conf("códigos CIAP: tabela sem duplicidade e capítulos cobertos", all(motivos.fam_ciap(c) in motivos.NOMES for c in list(motivos.CIAP_COD) + [x + "01" for x in "ABDFHKLNPRSTUWXYZ"]))
    pg = abre(nav, None)
    conf("página: texto explica CID e CIAP", "CIAP-2" in pg.inner_text("body") or "CIAP-2" in pg.content())
    nav.close()
print("erros de console:", erros or "nenhum"); print("FALHAS:", falhas or "nenhuma")
sys.exit(1 if erros or falhas else 0)
