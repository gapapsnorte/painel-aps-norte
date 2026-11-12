"""Testa a aba 'Consultas por mil hab.': sem erro de console, números da tela = números recalculados a partir do JSON."""
import json, pathlib
from playwright.sync_api import sync_playwright
RAIZ = pathlib.Path(__file__).resolve().parent.parent
url = (RAIZ / "site" / "index.html").as_uri()
P = json.load(open(RAIZ / "dados" / "painel.json", encoding="utf-8")); iu = P["meses"].index(P["ultimo_mes_completo"]); RZ = P["razao"]
erros = []; ok = True
def confere(rotulo, tela, esperado):
    global ok
    bom = tela == esperado; ok &= bom; print(("OK  " if bom else "ERRO"), rotulo, "| tela:", tela, "| esperado:", esperado)
fmt = lambda v: f"{round(v):,}".replace(",", ".")
with sync_playwright() as p:
    nav = p.chromium.launch(channel="chrome", headless=True)
    for larg, nome in ((1280, "desktop"), (390, "celular")):
        pg = nav.new_page(viewport={"width": larg, "height": 900})
        pg.on("console", lambda m: erros.append(f"console.{m.type}: {m.text}") if m.type in ("error", "warning") else None); pg.on("pageerror", lambda e: erros.append(f"pageerror: {e}"))
        pg.goto(url); pg.wait_for_selector("#arvore details.g"); pg.click("#aba-p"); pg.click("#aba-r"); pg.wait_for_selector("#r-ref table")
        if nome == "celular":
            sobra = pg.evaluate("document.documentElement.scrollWidth - window.innerWidth"); print("celular: rolagem lateral da página (px):", sobra); ok &= sobra <= 1
            pg.screenshot(path=str(RAIZ / "testes" / "shot_razao_celular.png")); pg.close(); continue
        norte = RZ["entes"][0]; df = RZ["entes"][1]
        linhas = {r.locator("td").first.inner_text(): r.locator("td").all_inner_texts() for r in pg.locator("#r-ref tbody tr").all() if r.locator("td").count() > 2}
        a25 = norte["anos"]["2025"]; confere("Norte médico 2025 por mil", linhas["Região Norte"][RZ["anos"].index("2025") + 1], fmt(a25["med"] / a25["pop"] * 1000))
        d24 = df["anos"]["2024"]; confere("DF médico 2024 por mil", linhas["Distrito Federal"][RZ["anos"].index("2024") + 1], fmt(d24["med"] / d24["pop"] * 1000))
        confere("Brasil 2024 (RIPSA)", linhas["Brasil (RIPSA)"][RZ["anos"].index("2024") + 1], fmt(RZ["brasil"]["2024"]))
        m12 = norte["m12"]; confere("Norte médico 12 meses", linhas["Região Norte"][len(RZ["anos"]) + 1], fmt(m12["med"] / m12["pop"] * 1000))
        for base, chave in (("censo", "pop_censo"), ("cad", "pop_cad")):
            pg.select_option("#r-base", base); pg.wait_for_timeout(150)
            lb = {r.locator("td").first.inner_text(): r.locator("td").all_inner_texts() for r in pg.locator("#r-ref tbody tr").all() if r.locator("td").count() > 2}
            confere(f"Norte médico 2025 por mil, base {base}", lb["Região Norte"][RZ["anos"].index("2025") + 1], fmt(a25["med"] / norte[chave] * 1000))
            confere(f"DF médico 2024 por mil, base {base}", lb["Distrito Federal"][RZ["anos"].index("2024") + 1], fmt(d24["med"] / df[chave] * 1000))
        pg.select_option("#r-base", "censo"); pg.wait_for_timeout(150)
        confere("Região Central sem Censo", {r.locator("td").first.inner_text(): r.locator("td").all_inner_texts() for r in pg.locator("#r-ref tbody tr").all() if r.locator("td").count() > 2}["Região Central"][1], "–")
        pg.select_option("#r-base", "infosaude"); pg.wait_for_timeout(150)
        pg.select_option("#r-ind", "enf"); pg.wait_for_timeout(150)
        l2 = {r.locator("td").first.inner_text(): r.locator("td").all_inner_texts() for r in pg.locator("#r-ref tbody tr").all() if r.locator("td").count() > 2}
        confere("Norte enfermeiro 2025 por mil", l2["Região Norte"][RZ["anos"].index("2025") + 1], fmt(a25["enf"] / a25["pop"] * 1000)); print("     Brasil some no indicador de enfermeiro:", "Brasil (RIPSA)" not in l2)
        pg.select_option("#r-ind", "med"); pg.wait_for_timeout(150)
        # nível UBS: razão da primeira UBS na tela = soma 12 meses de atend_med ÷ cadastrados
        g0 = P["gsaps"][0]; u0 = g0["ubs"][0]
        pg.locator("#r-corpo button.lk").first.click(); pg.wait_for_timeout(150); pg.locator("#r-corpo button.lk").first.click(); pg.wait_for_timeout(150)
        cab = pg.locator("#r-crumb").inner_text(); print("  trilha:", cab)
        linha_dest = pg.locator("#r-corpo tr.dest td").all_inner_texts()
        s = P["gsaps"][0]["ubs"][0]
        esp = sum(s["serie"]["atend_med"][iu - 11:iu + 1]) / s["cad"] * 1000
        confere(f"UBS {s['nome']} por mil cadastrados", linha_dest[3].split()[0], fmt(esp))
        # equipe: só eSF com cadastro, e ao clicar abre a hierarquia
        n_eq = pg.locator("#r-corpo tbody tr:not(.dest)").count(); esp_eq = sum(1 for e in s["equipes"] if e.get("cad") and e["serie"].get("atend_med")); confere("equipes listadas na UBS", n_eq, esp_eq)
        pg.screenshot(path=str(RAIZ / "testes" / "shot_razao_ubs.png"))
        pg.locator("#r-corpo button.lk").first.click(); pg.wait_for_timeout(300); print("  clique na equipe abre a hierarquia:", pg.locator("#vista-h").is_visible()); ok &= pg.locator("#vista-h").is_visible()
        pg.click("#aba-p"); pg.click("#aba-r"); pg.wait_for_selector("#r-ref table"); pg.screenshot(path=str(RAIZ / "testes" / "shot_razao.png"), full_page=True)
        print("  seletor de indicador do topo desabilitado na aba:", pg.locator("#sel-ind").is_disabled())
        pg.close()
    nav.close()
print("erros de console:", erros or "nenhum"); ok &= not erros
print("RESULTADO:", "tudo certo" if ok else "FALHOU")
