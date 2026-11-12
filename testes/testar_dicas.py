import sys as _s, pathlib as _p; _s.path.insert(0, str(_p.Path(__file__).parent)); from _entrar import entrar
"""Confere a dica com números ao passar o mouse em cada tipo de gráfico. Uso: python -X utf8 testes/testar_dicas.py"""
import pathlib, sys
from playwright.sync_api import sync_playwright

SITE = (pathlib.Path(__file__).parent.parent / "site" / "index.html").as_uri()
SHOTS = pathlib.Path(__file__).parent / "_dicas"; SHOTS.mkdir(exist_ok=True)
falhas, erros = [], []


def dica(pg):
    return pg.evaluate("() => { const d = document.getElementById('dica'); return d && d.style.display === 'block' ? d.innerText : '' }")


def passar(pg, loc, nome, pos=None):
    loc.scroll_into_view_if_needed(); loc.hover(position=pos, force=True); pg.wait_for_timeout(120)
    t = dica(pg)
    ok = bool(t) and any(c.isdigit() for c in t)
    print(("ok   " if ok else "FALHA"), nome, "→", t.replace("\n", " | ")[:110])
    if not ok: falhas.append(nome)
    pg.screenshot(path=str(SHOTS / f"{nome}.png"))
    return t


def passar_ponto(pg, seletor, nome):
    """Passa o mouse num ponto que está de fato sobre a forma (fatia de pizza, barra com dica)."""
    achar = "sel => [...document.querySelectorAll(sel)].find(e => e.getClientRects().length && (e.querySelector(':scope > title') || e.dataset.dica))"
    pg.evaluate("sel => { const el = (" + achar + ")(sel); if (el) el.scrollIntoView({block: 'center'}); }", seletor); pg.wait_for_timeout(300)
    xy = pg.evaluate("""sel => { const el = (ACHAR)(sel); if (!el) return null; const r = el.getBoundingClientRect();
        for (let i = 1; i < 12; i++) for (let j = 1; j < 12; j++) { const x = r.x + r.width * i / 12, y = r.y + r.height * j / 12; if (document.elementFromPoint(x, y) === el) return [x, y]; }
        return null; }""".replace("ACHAR", achar), seletor)
    if not xy: print("aviso: nada encontrado para", nome); falhas.append(nome); return ""
    pg.mouse.move(xy[0], xy[1]); pg.wait_for_timeout(120); t = dica(pg)
    ok = bool(t) and any(c.isdigit() for c in t)
    print(("ok   " if ok else "FALHA"), nome, "→", t.replace("\n", " | ")[:110])
    if not ok: falhas.append(nome)
    pg.screenshot(path=str(SHOTS / f"{nome}.png")); return t


with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True); pg = b.new_page(viewport={"width": 1280, "height": 900})
    pg.on("console", lambda m: erros.append(m.text) if m.type == "error" else None); pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto(SITE); pg.wait_for_selector("details.caixa"); entrar(pg)
    # minigráfico do resumo da 1ª GSAP
    passar(pg, pg.locator("svg.sp:visible").first, "minigrafico")
    # abre GSAP → UBS → equipe
    for nivel in range(3):
        d = pg.locator("details.caixa:not([open]):visible").first; d.locator("summary").first.click(); pg.wait_for_timeout(250)
    t = passar(pg, pg.locator("details.caixa[open] svg[aria-label='Série mensal']:not(.sp) rect.col:visible").last, "serie_coluna")
    if "\n" not in t: falhas.append("serie_coluna sem segunda linha")
    pizzas = pg.locator(".pizza svg path:visible")
    for bt in pg.locator("details.caixa[open] button:visible").all()[:14]:
        if pizzas.count(): break
        try: bt.click(timeout=500); pg.wait_for_timeout(120)
        except Exception: pass
    if pizzas.count(): passar(pg, pizzas.first, "pizza")
    else: print("aviso: nenhuma pizza aberta na árvore")
    # abas
    pg.click("#aba-h"); pg.click("#f-barra .abrir-cmp"); pg.wait_for_selector("#vista-c circle.pt"); passar(pg, pg.locator("#vista-c circle.pt:visible").first, "comparar_ponto")
    pg.click("#aba-p"); pg.click("#aba-x"); pg.wait_for_timeout(400)
    passar_ponto(pg, "#vista-x svg rect", "acesso_barra")
    passar_ponto(pg, "#vista-x .pizza svg path", "acesso_pizza")
    for aba in pg.locator("button[id^='aba-']:visible").all():
        if "calor" in aba.inner_text().lower(): aba.click(); break
    pg.wait_for_timeout(500)
    if pg.locator("#mapa-corpo td.c:visible").count(): passar(pg, pg.locator("#mapa-corpo td.c:visible").nth(3), "mapa_celula")
    else: print("aviso: mapa de calor não aberto")
    # celular: sem rolagem lateral e dica dentro da tela
    pg.set_viewport_size({"width": 390, "height": 800}); pg.wait_for_timeout(200)
    if pg.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth + 1"): falhas.append("rolagem lateral no celular")
    b.close()

print("erros de console:", erros or "nenhum")
if falhas or erros: print("FALHAS:", falhas); sys.exit(1)
print("dicas ok")
