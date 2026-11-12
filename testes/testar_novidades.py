import sys as _s, pathlib as _p; _s.path.insert(0, str(_p.Path(__file__).parent)); from _entrar import entrar
import json, pathlib
from playwright.sync_api import sync_playwright
RAIZ = pathlib.Path(__file__).resolve().parent.parent
url = (RAIZ / "site" / "index.html").as_uri()
P = json.load(open(RAIZ / "dados" / "painel.json", encoding="utf-8"))
N = json.load(open(RAIZ / "dados" / "nominal.json", encoding="utf-8"))   # bloco nominal em claro: só existe no computador (dados/ fica fora do git)
EQ = {f"{u['cnes']}|{e['ine'] or 'SEM'}": e["nome"] for g in P["gsaps"] for u in g["ubs"] for e in u["equipes"]}
alvo = next((x, EQ[k]) for k, l in N["prof"].items() for x in l if x.get("mat") and x["lotado"] and x["serie"].get("atend"))
prof, nome_eq = alvo
erros = []
with sync_playwright() as p:
    nav = p.chromium.launch(channel="chrome", headless=True); pg = nav.new_page(viewport={"width": 1280, "height": 900})
    pg.on("console", lambda m: erros.append(f"console.{m.type}: {m.text}") if m.type in ("error", "warning") else None)
    pg.on("pageerror", lambda e: erros.append(f"pageerror: {e}"))
    pg.goto(url); pg.wait_for_selector("#arvore details.g"); entrar(pg)
    # 1. busca por matrícula (com pontos também)
    mat = prof["mat"]; mat_fmt = mat[:-3] + "." + mat[-3:]
    for q in (mat, mat_fmt):
        pg.fill("#busca", q); pg.wait_for_selector("#achados button[data-i]")
        achou = pg.locator("#achados button[data-i]").first.inner_text()
        print(f"busca '{q}':", "OK" if prof["nome"].split()[0].lower() in achou.lower() else "FALHOU", "|", achou.replace("\n", " ")[:90])
    pg.locator("#achados button[data-i]").first.click(); pg.wait_for_selector("dialog#ficha[open]")
    print("ficha abriu para:", pg.locator("#ficha-t").inner_text(), "| sub:", pg.locator("#ficha-sub").inner_text())
    print("ficha: gráficos", pg.locator("#ficha .graf svg").count(), "| linhas de equipe", pg.locator("#ficha tbody tr").count())
    pg.screenshot(path=str(RAIZ / "testes" / "shot_ficha.png"))
    pg.click("#ficha button.link"); pg.wait_for_timeout(400)
    print("ficha -> equipe aberta:", pg.locator("details.e[open]").count() >= 1, "| ficha fechou:", not pg.locator("dialog#ficha[open]").count())
    print("gráfico de linhas na equipe:", pg.locator("details.e[open] svg polyline").count() >= 3)
    pg.screenshot(path=str(RAIZ / "testes" / "shot_equipe.png"))
    # 2. busca por nome parcial sem acento
    pg.fill("#busca", prof["nome"].split()[0][:5].lower()); pg.wait_for_selector("#achados button[data-i]"); print("busca por nome parcial:", pg.locator("#achados button[data-i]").count(), "resultados")
    pg.keyboard.press("Escape")
    # 3. mapa de calor
    pg.click("#aba-m"); pg.wait_for_selector("#mapa-corpo td.c")
    print("mapa: linhas", pg.locator("#mapa-corpo tr:not(.grupo) td.rot").count(), "| células", pg.locator("#mapa-corpo td.c").count())
    pg.select_option("#mapa-ord", "queda"); pg.wait_for_timeout(200); primeira = pg.locator("#mapa-corpo td.rot").first.inner_text(); print("pior equipe (último mês vs habitual):", primeira)
    pg.screenshot(path=str(RAIZ / "testes" / "shot_mapa.png"))
    pg.click("#grp-ind button[data-g='bucal']"); pg.select_option("#sel-ind", "odonto1"); pg.wait_for_timeout(300); print("odonto -> mapa tipo:", pg.locator("#mapa-tipo").input_value(), "| linhas", pg.locator("#mapa-corpo tr:not(.grupo) td.rot").count())
    pg.click("#grp-ind button[data-g='prod']"); pg.select_option("#sel-ind", "atend")
    pg.locator("#mapa-corpo td.rot").first.click(); pg.wait_for_timeout(300); print("clique na equipe do mapa abre hierarquia:", pg.locator("#vista-h").is_visible())
    # 4. celular
    m = nav.new_page(viewport={"width": 390, "height": 800}); m.goto(url); m.wait_for_selector("#arvore details.g")
    m.click("#aba-m"); m.wait_for_selector("#mapa-corpo td.c")
    print("celular: rolagem horizontal da PÁGINA:", m.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth"))
    m.screenshot(path=str(RAIZ / "testes" / "shot_mapa_celular.png"))
    nav.close()
print("ERROS:", erros if erros else "nenhum")
