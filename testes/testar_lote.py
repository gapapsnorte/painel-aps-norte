"""Lote de 12/11/2026: perfil dos atendimentos (resumo de 12 meses), inconsistências (só com senha), grupos por boa prática,
habitual único, aviso na equipe, link que preserva a tela, planilha de providências e relatório acompanhando.
Uso: python testar_lote.py"""
import json, pathlib
from playwright.sync_api import sync_playwright
from _entrar import entrar
RAIZ = pathlib.Path(__file__).resolve().parent.parent
url = (RAIZ / "site" / "index.html").as_uri()
P = json.load(open(RAIZ / "dados" / "painel.json", encoding="utf-8")); N = json.load(open(RAIZ / "dados" / "nominal.json", encoding="utf-8"))
iu = P["meses"].index(P["ultimo_mes_completo"]); erros, falhas = [], []
def conf(nome, ok, det=""):
    print(("OK   " if ok else "FALHA"), nome, ("| " + str(det)) if det != "" else "")
    if not ok: falhas.append(nome)
def br(n): return f"{int(n + 0.5):,}".replace(",", ".")   # arredonda como o Math.round da página
with sync_playwright() as p:
    nav = p.chromium.launch(channel="chrome", headless=True); ctx = nav.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True); pg = ctx.new_page()
    pg.on("console", lambda m: erros.append(f"console.{m.type}: {m.text}") if m.type in ("error", "warning") else None); pg.on("pageerror", lambda e: erros.append(f"pageerror: {e}"))
    pg.goto(url); pg.wait_for_selector("#arvore details.g")
    # ---- abas e público sem senha
    conf("abas visíveis sem senha: Visão geral, Mapa de calor, Perfil dos atendimentos", pg.locator("nav.abas button:visible").all_inner_texts() == ["Visão geral", "Mapa de calor", "Perfil dos atendimentos"], pg.locator("nav.abas button:visible").all_inner_texts())
    pub = (RAIZ / "site" / "painel.js").read_text("utf-8")
    conf("inconsistências não estão no arquivo público", '"incons"' not in pub and "lot_sem_prod" not in pub)
    # ---- grupos por boa prática
    conf("10 grupos de indicador", pg.locator("#grp-ind button").count() == 10, " | ".join(pg.locator("#grp-ind button").all_inner_texts()))
    vistos = set()
    for g in ["prod", "inf", "gest", "dm", "has", "idoso", "mulher", "bucal", "outras", "mot"]:
        pg.click(f"#grp-ind button[data-g='{g}']"); pg.wait_for_timeout(150); vistos |= set(pg.locator("#sel-ind option").evaluate_all("l => l.map(o => o.value)"))
    conf("todo indicador aparece em pelo menos um grupo", vistos == set(P["indicadores"]), sorted(set(P["indicadores"]) - vistos))
    pg.click("#grp-ind button[data-g='mulher']"); ops = pg.locator("#sel-ind option").evaluate_all("l => l.map(o => o.value)")
    conf("DIU e implante separados no grupo Saúde da mulher", "p_diu" in ops and "p_implante" in ops and "p_larc" not in P["indicadores"], ops)
    pg.click("#grp-ind button[data-g='has']"); ops = pg.locator("#sel-ind option").evaluate_all("l => l.map(o => o.value)")
    conf("pressão arterial junto com peso e altura em Hipertensão", "p_pa" in ops and "p_antropo" in ops, ops)
    pg.select_option("#sel-ind", "p_antropo"); pg.wait_for_timeout(200)
    conf("número do cartão do gráfico = JSON (peso e altura)", "Peso, altura" in pg.inner_text("#tit-graf") and P["regiao"]["p_antropo"][iu] > 0, P["regiao"]["p_antropo"][iu])
    pg.click(".kpi[data-k='atend']"); pg.wait_for_timeout(200)
    conf("cartões do topo dizem contra qual mês é a variação", "versus" in pg.inner_text(".kpi[data-k='atend']"), pg.inner_text(".kpi[data-k='atend']").replace("\n", " "))
    conf("sem '−0%' nem '+0%' na tela", "−0%" not in pg.inner_text("body") and "+0%" not in pg.inner_text("body"))
    # ---- habitual único (mapa = etiqueta)
    pg.click("#aba-m"); pg.wait_for_selector("#mapa-corpo td.c"); t24 = pg.locator("#mapa-corpo tr:not(.grupo) td.c:last-child").all_inner_texts()
    pg.select_option("#sel-per", "12"); pg.wait_for_timeout(300); t12 = pg.locator("#mapa-corpo tr:not(.grupo) td.c:last-child").all_inner_texts()
    conf("mapa: o habitual não muda com o período escolhido", t24 == t12 and len(t24) > 50, f"{len(t24)} equipes")
    e0 = next(e for g in P["gsaps"] for u in g["ubs"] for e in u["equipes"] if e["ine"] and e["tipo"] == "eSF" and not e.get("migrou") and e["serie"].get("atend"))
    v = sorted(e0["serie"]["atend"][iu - 12:iu]); med = (v[5] + v[6]) / 2
    conf("habitual = mediana dos 12 meses anteriores (1ª eSF)", br(med) in t24, f"{e0['nome']}: {br(med)}")
    pg.select_option("#sel-per", "24")
    # ---- Perfil dos atendimentos
    pg.click("#aba-p"); pg.wait_for_selector("#p-tab")
    conf("sub-botões do Perfil aparecem", pg.locator("#sub-perfil button:visible").count() == 4)
    r = P["regiao"]; s12 = lambda k: sum(r[k][iu - 11:iu + 1]); tot = sum(s12(k) for k in ("a_dia", "a_agend", "a_prog", "a_urg", "a_escuta"))
    linha = pg.inner_text("#p-tab tbody tr.dest")
    conf("Região: total de 12 meses e % no dia = JSON", br(tot) in linha and f"{round(s12('a_dia') / tot * 100)}%" in linha, linha.replace("\n", " ")[:110])
    cad = sum(u.get("cad") or 0 for g in P["gsaps"] for u in g["ubs"])
    conf("Região: consultas de médico por mil cadastrados = JSON", br(s12("atend_med") / cad * 1000) in linha, br(s12("atend_med") / cad * 1000))
    conf("uma linha por GSAP", pg.locator("#p-tab tbody tr:not(.det)").count() == 17)
    pg.locator("#p-tab button.p-det").nth(1).click(); pg.wait_for_timeout(200)
    conf("detalhe abre os três blocos com gráficos", pg.locator("#p-tab tr.det .tres > div").count() == 3 and pg.locator("#p-tab tr.det svg").count() >= 5)
    pg.screenshot(path=str(RAIZ / "testes" / "shot_perfil.png"))
    pg.locator("#p-tab button.lk").first.click(); pg.wait_for_timeout(200)
    conf("clicar na GSAP desce para as UBS", "GSAP 1" in pg.inner_text("#p-crumb") and pg.inner_text("#p-tab thead th.l") == "UBS")
    pg.locator("#p-crumb button").first.click()
    for b, vista in (("aba-x", "x"), ("aba-u", "u"), ("aba-r", "r"), ("sub-p", "p")):
        pg.click("#" + b); pg.wait_for_timeout(250)
        conf(f"parte {b} abre dentro do Perfil", pg.locator("#vista-" + vista).is_visible() and pg.get_attribute("#aba-p", "aria-selected") == "true" and pg.locator("#sel-ind").is_disabled())
    pg.click("#aba-r"); pg.wait_for_selector("#r-ref table")
    conf("consultas por mil: frase do denominador corrigida e selo de comparação exploratória", "não a tendência" not in pg.inner_text("#vista-r") and "também a variação no tempo" in pg.inner_text("#r-ref-nota") and "comparação exploratória" in pg.inner_text("#r-aviso"))
    # ---- link que preserva a tela
    pg.click("#aba-h"); pg.select_option("#sel-ind", "visitas"); pg.locator("#arvore > details.g > summary").first.click(); pg.wait_for_timeout(200); pg.locator("#g0u0 > summary").click(); pg.wait_for_timeout(200); pg.locator("#g0u0 details.e > summary").first.click(); pg.wait_for_timeout(300)
    link = pg.evaluate("location.href"); u0 = P["gsaps"][0]["ubs"][0]
    conf("o endereço guarda indicador, UBS e equipe", "i=visitas" in link and "u=" + u0["cnes"] in link and "e=" in link, link.split("#")[1])
    pg2 = ctx.new_page(); pg2.on("pageerror", lambda e: erros.append(f"pageerror (link): {e}")); pg2.goto(link); pg2.wait_for_selector("#arvore details.g"); pg2.wait_for_timeout(500)
    conf("abrir o link repõe indicador e equipe aberta", pg2.input_value("#sel-ind") == "visitas" and pg2.locator("#g0u0 details.e[open]").count() == 1 and "Visitas" in pg2.inner_text("#tit-graf"))
    pg2.goto(url + "#v=m&i=p_cito&p=12"); pg2.reload(); pg2.wait_for_selector("#mapa-corpo td.c")
    conf("link direto para o mapa de calor de citopatológico em 12 meses", pg2.locator("#vista-m").is_visible() and pg2.input_value("#sel-ind") == "p_cito" and pg2.input_value("#sel-per") == "12")
    pg2.goto(url + "#v=i"); pg2.reload(); pg2.wait_for_selector("#arvore details.g"); pg2.wait_for_timeout(300)
    conf("link para Inconsistências sem senha cai na Visão geral, sem nomes", pg2.locator("#vista-h").is_visible() and not pg2.locator("#aba-i").is_visible() and pg2.inner_text("#i-corpo") == "")
    pg2.close()
    pg.locator("#g0 > summary").click(); pg.select_option("#sel-ind", "atend")
    # ---- planilha de providências (pública: só alertas, sem nomes)
    with pg.expect_download() as d: pg.click("#f-barra .btn-prov")
    txt = pathlib.Path(d.value.path()).read_bytes().decode("utf-8-sig"); lin = txt.split("\r\n")
    conf("planilha de providências pública: cabeçalho, uma linha por alerta, sem inconsistências", lin[0].startswith('"Emitido em"') and "Responsável" in lin[0] and len(lin) > 40 and '"Inconsistência"' not in txt and lin[1].endswith('"novo"'), f"{len(lin) - 1} linhas")
    # ---- aviso contextual numa equipe abaixo do habitual em UBS com produção sem equipe
    alvo = None
    for gi, g in enumerate(P["gsaps"]):
        for ui, u in enumerate(g["ubs"]):
            sem = next((e for e in u["equipes"] if not e["ine"]), None); ns = sem["serie"].get("atend", [0] * (iu + 1))[iu] if sem else 0
            for ei, e in enumerate(u["equipes"]):
                s = e["serie"].get("atend")
                if e["ine"] and s and ns > 0 and not e.get("migrou"):
                    v = sorted(s[iu - 12:iu]); h = (v[5] + v[6]) / 2
                    if h >= 50 and s[iu] < 0.7 * h: alvo = alvo or (gi, ui, ei, ns, e["nome"])
    if alvo:
        gi, ui, ei, ns, nm = alvo; pg.evaluate(f"irPara(P.gsaps[{gi}].nome + ' › ' + P.gsaps[{gi}].ubs[{ui}].nome + ' › ' + P.gsaps[{gi}].ubs[{ui}].equipes[{ei}].nome)"); pg.wait_for_timeout(400)
        av = pg.inner_text(f"#g{gi}u{ui}e{ei} .aviso-ctx")
        conf("equipe abaixo do habitual: aviso com a produção sem equipe da UBS", br(ns) in av and "sem equipe vinculada" in av and "não redistribui" in av, f"{nm}: {av[:90]}")
        pg.screenshot(path=str(RAIZ / "testes" / "shot_aviso_equipe.png"))
    else: conf("existe equipe abaixo do habitual em UBS com produção sem equipe (para testar o aviso)", False)
    # ---- área dos gestores: Inconsistências
    entrar(pg); pg.wait_for_timeout(400)
    conf("com senha aparece a aba Inconsistências", pg.locator("#aba-i").is_visible())
    pg.click("#aba-i"); pg.wait_for_selector("#i-corpo table"); inc = N["incons"]
    conf("cartões por tipo = JSON", all(br(sum(1 for x in inc if x["tipo"] == k)) == pg.inner_text(f"#i-cartoes button[data-t='{k}'] .n") for k in ("sem_ine", "lot_outra", "lot_sem_prod", "prod_fora_rh", "ine_fora_rh", "eq_sem_prod", "mudou_ubs", "lugar_errado")), {k: sum(1 for x in inc if x["tipo"] == k) for k in sorted({x["tipo"] for x in inc})})
    pg.click("#i-cartoes button[data-t='sem_ine']"); pg.wait_for_timeout(200); n_sem = sum(1 for x in inc if x["tipo"] == "sem_ine")
    conf("filtro 'sem INE' lista profissionais com nome", pg.locator("#i-corpo tbody tr").count() == min(n_sem, 500) and next(x["nome"] for x in inc if x["tipo"] == "sem_ine") in pg.inner_text("#i-corpo"), f"{n_sem} linhas")
    pg.select_option("#i-gsap", P["gsaps"][0]["nome"]); pg.wait_for_timeout(150); n_g = sum(1 for x in inc if x["tipo"] == "sem_ine" and x["gsap"] == P["gsaps"][0]["nome"])
    conf("filtro por GSAP", pg.locator("#i-corpo tbody tr").count() == n_g, n_g)
    pg.screenshot(path=str(RAIZ / "testes" / "shot_incons.png"))
    with pg.expect_download() as d: pg.click("#i-csv")
    conf("CSV da lista filtrada", len(pathlib.Path(d.value.path()).read_bytes().decode("utf-8-sig").split("\r\n")) == n_g + 1)
    with pg.expect_download() as d: pg.click("#vista-i .btn-prov")
    txt = pathlib.Path(d.value.path()).read_bytes().decode("utf-8-sig")
    conf("planilha de providências com senha inclui as inconsistências", '"Inconsistência"' in txt and txt.count('"Inconsistência"') >= len(inc) - 20)
    pg.select_option("#i-gsap", ""); pg.locator("#i-corpo button.lk").first.click(); pg.wait_for_timeout(400)
    conf("clicar na unidade abre a Visão geral nela", pg.locator("#vista-h").is_visible() and pg.locator("#arvore details.u[open]").count() >= 1)
    conf("rótulo 'já saiu' trocado", "já saiu" not in pg.inner_text("body") and "vínculo atual confirmado" in pg.inner_text("label:has(#chk-inativos)"))
    # ---- relatório acompanha
    conf("relatório: 13 partes para escolher", pg.evaluate("REL_SEC.length") == 13)
    h = pg.evaluate("relatorioHTML('g:0', REL_SEC.map(x => x[0]))")
    for t in ("Produção por boa prática", "Inserção de DIU", "Perfil dos atendimentos, ", "Perfil dos atendimentos em ", "Inconsistências de código e de vínculo", "Quadro de providências", "comparação exploratória", "versus"):
        conf(f"relatório traz: {t}", t in h)
    conf("relatório não usa mais 'Acesso em' nem 'já saiu'", "Acesso em" not in h and "já saiu" not in h)
    # ---- celular
    m = ctx.new_page(); m.set_viewport_size({"width": 390, "height": 800}); m.goto(url); m.wait_for_selector("#arvore details.g")
    for b in ("aba-p", "aba-x", "aba-u", "aba-r", "aba-m", "aba-h"):
        m.click("#" + b); m.wait_for_timeout(250)
        conf(f"celular {b}: sem rolagem lateral da página", not m.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth"))
    m.click("#aba-p"); m.wait_for_timeout(200); m.screenshot(path=str(RAIZ / "testes" / "shot_perfil_celular.png"))
    nav.close()
print("ERROS:", erros if erros else "nenhum"); print("FALHAS:", falhas if falhas else "nenhuma")
