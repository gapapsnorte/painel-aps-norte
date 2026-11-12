"""Aba Pessoas atendidas: números da tela = dados/painel.json; descida Região → GSAP → UBS → equipe.
Uso: python -X utf8 testes/testar_usuarios.py"""
import json, pathlib, sys
from playwright.sync_api import sync_playwright

RAIZ = pathlib.Path(__file__).parent.parent
P = json.load(open(RAIZ / "dados" / "painel.json", encoding="utf-8")); US = P["usuarios"]
SHOTS = pathlib.Path(__file__).parent / "_dicas"; SHOTS.mkdir(exist_ok=True)
falhas, erros = [], []
br = lambda n: f"{round(n):,}".replace(",", ".")
pc = lambda a, b: f"{a / b * 100:.1f}".replace(".", ",") + "%"


def confere(nome, tela, esperado):
    ok = esperado in tela
    print(("OK   " if ok else "FALHA"), nome, "| esperado:", esperado, "| tela:", tela[:90].replace("\n", " "))
    if not ok: falhas.append(nome)


with sync_playwright() as p:
    nav = p.chromium.launch(channel="chrome", headless=True); pg = nav.new_page(viewport={"width": 1280, "height": 900})
    pg.on("console", lambda m: erros.append(m.text) if m.type == "error" else None); pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto((RAIZ / "site" / "index.html").as_uri()); pg.wait_for_selector("details.caixa")
    pg.click("#aba-p"); pg.click("#aba-u"); pg.wait_for_selector("#u-corpo table")
    r = US["regiao"]; cart = pg.inner_text("#u-cartoes")
    confere("Região: pessoas atendidas", cart, br(r["pess"]))
    confere("Região: pessoas com 12+", cart, br(r["fp"][4] + r["fp"][5]))
    confere("Região: % da agenda das 12+", cart, pc(r["fa"][4] + r["fa"][5], r["atend"]))
    confere("Região: % dos 10% que mais usam", cart, pc(r["top10"], r["atend"]))
    n_lin = pg.locator("#u-corpo tbody tr").count(); print("  linhas na tabela da Região:", n_lin, "(esperado", len(P["gsaps"]) + 1, ")")
    if n_lin != len(P["gsaps"]) + 1: falhas.append("linhas de GSAP")
    pg.screenshot(path=str(SHOTS / "usuarios_regiao.png"), full_page=True)
    # desce para a 1ª GSAP e a 1ª UBS
    g = P["gsaps"][0]; pg.locator("#u-corpo button.lk", has_text=g["nome"]).first.click(); pg.wait_for_timeout(200)
    confere("GSAP: pessoas", pg.inner_text("#u-cartoes"), br(US["gsap"][g["nome"]]["pess"]))
    u = g["ubs"][0]; pg.locator("#u-corpo button.lk", has_text=u["nome"]).first.click(); pg.wait_for_timeout(200)
    confere("UBS: pessoas", pg.inner_text("#u-cartoes"), br(US["ubs"][u["cnes"]]["pess"]))
    eqs = [e for e in u["equipes"] if e.get("ine") and e["ine"] in US["equipe"]]
    n_eq = pg.locator("#u-corpo tbody tr").count() - 1; print("  equipes na UBS:", n_eq, "(esperado", len(eqs), ")")
    if n_eq != len(eqs): falhas.append("equipes na UBS")
    if eqs: confere("equipe: pessoas na linha", pg.locator("#u-corpo tbody tr", has_text=eqs[0]["nome"]).first.inner_text(), br(US["equipe"][eqs[0]["ine"]]["pess"]))
    # dica nas faixas, ordenação, volta
    pg.locator("#u-pilha-p svg rect").nth(4).hover(force=True); pg.wait_for_timeout(120)
    confere("dica na faixa", pg.evaluate("document.getElementById('dica').innerText"), "pessoas")
    pg.select_option("#u-ord", "hf"); pg.wait_for_timeout(100)
    pg.locator("#u-crumb button", has_text="Região Norte").click(); pg.wait_for_timeout(200)
    confere("voltou à Região", pg.inner_text("#u-tit"), "Região Norte")
    confere("seletor de indicador desabilitado", str(pg.locator("#sel-ind").is_disabled()), "True")
    confere("rodapé com lotação de outubro", pg.inner_text("#rodape"), "out/2026")
    pg.set_viewport_size({"width": 390, "height": 800}); pg.wait_for_timeout(200)
    rol = pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth"); print("celular: rolagem lateral da página (px):", rol)
    if rol > 1: falhas.append("rolagem lateral no celular")
    pg.screenshot(path=str(SHOTS / "usuarios_celular.png"))
    nav.close()
print("erros de console:", erros or "nenhum")
if falhas or erros: print("FALHAS:", falhas); sys.exit(1)
print("RESULTADO: tudo certo")
