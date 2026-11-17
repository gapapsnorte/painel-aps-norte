"""Norte × DF × regiões na Visão geral: números da tela = painel.js; botão lateral liga as outras regiões; celular sem rolagem lateral."""
import json, pathlib, re
from playwright.sync_api import sync_playwright
RAIZ = pathlib.Path(__file__).resolve().parent.parent
P = json.loads((RAIZ / "dados" / "painel.json").read_text("utf-8"))
RG, M = P["regioes"], P["meses"]; IU = M.index(P["ultimo_mes_completo"])
def pop(regs, mes):
    a = int(mes[:4]); t = 0
    for r in regs:
        anos = sorted(int(x) for x in RG["pop"][r]); ano = max([x for x in anos if x <= a] or [anos[0]]); t += RG["pop"][r][str(ano)]
    return t
def doze(regs, k):
    return sum(sum(RG["serie"][r].get(k, [0]*len(M))[i] for r in regs) * 1000 / pop(regs, M[i]) for i in range(IU - 11, IU + 1))
esp_n, esp_d = doze(["Região Norte"], "atend"), doze(RG["regs"], "atend")
erros = []; falhas = []
with sync_playwright() as p:
    nav = p.chromium.launch(channel="chrome", headless=True)
    pg = nav.new_page(viewport={"width": 1280, "height": 900})
    pg.on("pageerror", lambda e: erros.append(str(e))); pg.on("console", lambda m: erros.append(m.text) if m.type == "error" else None)
    pg.goto((RAIZ / "site" / "index.html").as_uri()); pg.wait_for_selector("#cmp-regioes .kpi-reg")
    ns = [float(t.replace(".", "").replace(",", ".")) for t in pg.locator("#cmp-regioes .kpi-reg .n").all_inner_texts()]
    print("tela Norte/DF:", ns, "| esperado:", round(esp_n, 1), round(esp_d, 1))
    if abs(ns[0] - esp_n) > 0.1 or abs(ns[1] - esp_d) > 0.1: falhas.append("números divergem do JSON")
    n0 = pg.locator("#cmp-regioes polyline").count()
    pg.locator("#cmp-regioes .cmp-lado input").nth(0).check(); pg.wait_for_timeout(200)
    n1 = pg.locator("#cmp-regioes polyline").count(); print("linhas:", n0, "→", n1, "| tabela:", pg.locator("#cmp-regioes table tbody tr").count())
    if n1 <= n0: falhas.append("botão lateral não acrescentou região")
    pg.click("#cmp-todas"); pg.wait_for_timeout(200); print("ligar todas → linhas da tabela:", pg.locator("#cmp-regioes table tbody tr").count())
    pg.locator("#cmp-regioes").screenshot(path=str(RAIZ / "testes" / "shot_regioes.png"))
    pg.select_option("#sel-per", "99"); pg.wait_for_timeout(300); print("período Tudo:", pg.locator("#sel-per option:checked").inner_text())
    pg.locator("#cmp-regioes").screenshot(path=str(RAIZ / "testes" / "shot_regioes_tudo.png"))
    pg.locator("#vista-h .painel-graf").nth(1).screenshot(path=str(RAIZ / "testes" / "shot_barras_tudo.png"))
    c = p.chromium.launch(channel="chrome", headless=True).new_page(viewport={"width": 390, "height": 800})
    c.goto((RAIZ / "site" / "index.html").as_uri()); c.wait_for_selector("#cmp-regioes .kpi-reg")
    lar = c.evaluate("document.documentElement.scrollWidth"); print("celular scrollWidth:", lar)
    if lar > 392: falhas.append("rolagem lateral no celular")
    c.locator("#cmp-regioes").screenshot(path=str(RAIZ / "testes" / "shot_regioes_celular.png"))
print("erros:", erros); print("FALHAS:" if falhas or erros else "OK", falhas)
