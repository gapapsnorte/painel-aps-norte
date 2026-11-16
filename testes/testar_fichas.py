"""Ficha do servidor (12 meses × mediana do cargo, PDF/Word individual) e fichas em lote no Gerar relatório.
Uso: python testar_fichas.py"""
import json, pathlib, statistics
from playwright.sync_api import sync_playwright
from _entrar import entrar
RAIZ = pathlib.Path(__file__).resolve().parent.parent
url = (RAIZ / "site" / "index.html").as_uri()
P = json.load(open(RAIZ / "dados" / "painel.json", encoding="utf-8")); N = json.load(open(RAIZ / "dados" / "nominal.json", encoding="utf-8"))
iu = P["meses"].index(P["ultimo_mes_completo"]); erros, falhas = [], []
def conf(nome, ok, det=""):
    print(("OK   " if ok else "FALHA"), nome, ("| " + str(det)) if det != "" else "")
    if not ok: falhas.append(nome)
def br(n): return f"{int(n + 0.5):,}".replace(",", ".")
# pessoa de conferência: ACS com mais visitas nos 12 meses
pess = {}
for eq in N["prof"].values():
    for p in eq:
        x = pess.setdefault(p["id"], {"nome": p["nome"], "cargo": p.get("cargo") or p.get("cat"), "s": {}, "ativo": False})
        x["ativo"] |= bool(p.get("ativo")); x["cg"] = x.get("cg") or p.get("cargo"); x["ct"] = x.get("ct") or p.get("cat"); x["cargo"] = x["cg"] or x["ct"]
        for k, v in p["serie"].items():
            a = x["s"].setdefault(k, [0] * len(v))
            for i, y in enumerate(v): a[i] += y or 0
s12 = lambda v: sum(v[iu - 11: iu + 1])
alvo = max((x for x in pess.values() if "visitas" in x["s"] and x["ativo"]), key=lambda x: s12(x["s"]["visitas"]))
esperado = s12(alvo["s"]["visitas"])
with sync_playwright() as p:
    nav = p.chromium.launch(channel="chrome", headless=True); ctx = nav.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True); pg = ctx.new_page()
    pg.on("console", lambda m: erros.append(m.text) if m.type == "error" else None); pg.on("pageerror", lambda e: erros.append(f"pageerror: {e}"))
    pg.goto(url); pg.wait_for_selector("#arvore details.g"); entrar(pg)
    pid = pg.evaluate("n => [...pessoas.values()].find(x => x.nome === n).id", alvo["nome"])
    pg.evaluate("id => abrirFicha(id)", pid); pg.wait_for_selector("#ficha[open]")
    txt = pg.inner_text("#ficha-corpo")
    conf("ficha abre com o quadro de 12 meses", "Últimos 12 meses" in txt and "Mediana do cargo" in txt)
    lin = pg.locator("#ficha-corpo tr", has_text="Visitas domiciliares").first.inner_text()
    conf("visitas em 12 meses = JSON", br(esperado) in lin, f"{lin.strip()} | esperado {br(esperado)}")
    pares = sorted(s12(x["s"]["visitas"]) for x in pess.values() if x["cargo"] == alvo["cargo"] and x["ativo"] and "visitas" in x["s"] and s12(x["s"]["visitas"]) > 0)
    med = pares[round(.5 * (len(pares) - 1))]
    conf("mediana do cargo = conta no JSON", br(med) in lin, f"mediana {br(med)} de {len(pares)} {alvo['cargo']}")
    conf("botões PDF e Word na ficha", pg.locator("#ficha-pdf").count() == 1 and pg.locator("#ficha-word").count() == 1)
    with pg.expect_download() as d: pg.click("#ficha-word")
    arq = d.value.path().read_bytes()
    conf("Word individual baixado com o nome", d.value.suggested_filename.startswith("ficha_") and len(arq) > 5000, d.value.suggested_filename)
    pg.click("#ficha-x")
    # lote: uma UBS
    pg.click("#btn-rel"); pg.wait_for_selector("#dlg-rel[open]")
    pg.click("#rel-nenhuma"); pg.check("input[name='rel-sec'][value='fichas']")
    pg.select_option("#rel-escopo", "r"); pg.click("#rel-ok")
    conf("lote recusa a Região inteira", "GSAP ou por UBS" in pg.inner_text("#rel-aviso"))
    pg.select_option("#rel-escopo", "u:0:0")
    html = pg.evaluate("() => relatorioHTML('u:0:0', ['fichas'])")
    n = html.count('class="quebra"'); n_esp = pg.evaluate("() => { const no = noRel('u:0:0'); return [...pessoas.values()].filter(x => x.v.some(y => y.p.ativo && y.caminho.startsWith(no.cam + ' › '))).length; }")
    conf("lote: uma página por servidor ativo da UBS", n == n_esp and n > 0, f"{n} páginas, {n_esp} servidores")
    pg.check("input[name='rel-fmt'][value='word']")
    with pg.expect_download(timeout=120000) as d: pg.click("#rel-ok")
    conf("lote em Word baixado", d.value.path().stat().st_size > 20000, f"{d.value.suggested_filename} {d.value.path().stat().st_size // 1024} KB")
    conf("sem erro de console", not erros, erros[:3])
    pg.evaluate("id => abrirFicha(id)", pid); pg.wait_for_timeout(300); pg.locator("#ficha").screenshot(path=str(RAIZ / "testes" / "shot_ficha_12m.png"))
    nav.close()
print("\n" + ("TUDO OK" if not falhas else f"{len(falhas)} FALHA(S): {falhas}"))
