import sys as _s, pathlib as _p; _s.path.insert(0, str(_p.Path(__file__).parent)); from _entrar import entrar
import sys, pathlib
from playwright.sync_api import sync_playwright
RAIZ = pathlib.Path(__file__).resolve().parent.parent
url = (RAIZ / "site" / "index.html").as_uri()
erros = []
with sync_playwright() as p:
    nav = p.chromium.launch(channel="chrome", headless=True)
    pg = nav.new_page(viewport={"width": 1280, "height": 900})
    pg.on("console", lambda m: erros.append(f"console.{m.type}: {m.text}") if m.type in ("error", "warning") else None)
    pg.on("pageerror", lambda e: erros.append(f"pageerror: {e}"))
    pg.goto(url); pg.wait_for_selector("#arvore details.g"); entrar(pg)   # área dos gestores: os testes antigos conferem a lista de profissionais
    print("GSAPs na tela:", pg.locator("#arvore > details.g").count(), "| KPIs:", pg.locator(".kpi").count(), "| opções do filtro de alertas:", pg.locator("#f-alerta option").count())
    pg.locator("#arvore > details.g").nth(0).locator("summary").click()
    pg.wait_for_selector("#g0 details.u"); print("UBS na GSAP 1 Planaltina:", pg.locator("#g0 details.u").count())
    pg.locator("#g0u0 > summary").click(); pg.wait_for_selector("#g0u0 details.e"); print("equipes na 1ª UBS:", pg.locator("#g0u0 details.e").count())
    pg.locator("#g0u0e0 > summary").click(); pg.wait_for_selector("#g0u0e0 table")
    print("linhas de profissionais (visíveis):", pg.locator("#g0u0e0 table").last.locator("tbody tr:visible").count(), "| total no DOM:", pg.locator("#g0u0e0 table").last.locator("tbody tr").count())
    pg.screenshot(path=str(RAIZ / "testes" / "shot_arvore.png"), full_page=False)
    # troca de indicador mantém abertos
    pg.select_option("#sel-ind", "visitas"); pg.wait_for_timeout(300)
    print("após trocar p/ visitas, equipe ainda aberta:", pg.locator("#g0u0e0").get_attribute("open") is not None)
    # busca
    pg.fill("#busca", "amarela"); pg.wait_for_selector("#achados button[data-i]"); print("achados 'amarela':", pg.locator("#achados button[data-i]").count())
    pg.locator("#achados button[data-i]").first.click(); pg.wait_for_timeout(400)
    print("busca abriu equipe:", pg.locator("details.e[open]").count() >= 1)
    # alertas
    pg.select_option("#f-alerta", "*"); pg.wait_for_timeout(900); print("equipes com alerta listadas pelo filtro:", pg.locator("#arvore details.e").count(), "| etiquetas:", pg.locator("#arvore .sinais .chip").count())
    print("filtro fica na Visão geral:", pg.locator("#vista-h").is_visible()); pg.select_option("#f-alerta", "")
    pg.screenshot(path=str(RAIZ / "testes" / "shot_alerta.png"))
    # mobile
    m = nav.new_page(viewport={"width": 390, "height": 800}); m.goto(url); m.wait_for_selector("#arvore details.g")
    ov = m.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth"); print("rolagem horizontal da página no celular:", ov)
    m.screenshot(path=str(RAIZ / "testes" / "shot_celular.png"))
    nav.close()
print("ERROS:", erros if erros else "nenhum")
