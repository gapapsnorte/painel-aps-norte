"""Navegação única por unidade (GSAP > UBS > equipe): barra do topo com caminho, menus e busca, árvore lateral (gaveta no celular),
e o efeito da unidade escolhida em cada aba. Uso: python -X utf8 testes/testar_navegacao.py (a senha vem de coleta/senha.local)."""
import pathlib, sys
from playwright.sync_api import sync_playwright
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _entrar import entrar

RAIZ = pathlib.Path(__file__).resolve().parent.parent
URL = (RAIZ / "site" / "index.html").as_uri()
SHOT = RAIZ / "testes"
falhas, erros = [], []


def conf(nome, ok, det=""):
    print(("OK   " if ok else "FALHA"), nome, ("| " + str(det)) if det != "" else "")
    if not ok: falhas.append(nome)


def nova(nav, larg=1280, alt=900, **kw):
    pg = nav.new_page(viewport={"width": larg, "height": alt}, **kw)
    pg.on("console", lambda m: erros.append(f"console.{m.type}: {m.text}") if m.type in ("error", "warning") else None)
    pg.on("pageerror", lambda e: erros.append(f"pageerror: {e}"))
    pg.goto(URL); pg.wait_for_selector("#arvore details.g"); pg.wait_for_selector("#arv-lat .lat-s", state="attached")
    return pg


def txt_barra(pg): return " ".join(pg.inner_text("#nav-cam").split())


def lateral(pg, g, u=None, e=None):
    """Escolhe pela árvore lateral, abrindo os níveis pelo caminho (clicar numa GSAP já abre as UBS)."""
    pg.click(f'#arv-lat .lat-s[data-s="{g}"]')
    if u is not None: pg.click(f'#arv-lat .lat-s[data-s="{g}:{u}"]')
    if e is not None: pg.click(f'#arv-lat .lat-s[data-s="{g}:{u}:{e}"]')


def sem_rolagem(pg): return pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 1


with sync_playwright() as p:
    nav = p.chromium.launch(channel="chrome", headless=True)
    pg = nova(nav)
    # ---- uma equipe com alerta, do tipo eSF e com séries (serve para todas as abas)
    alvo = pg.evaluate("""() => {
      for (const [cam] of sinais()) { const p = cam.split(" › "); if (p.length !== 3) continue; const ix = IDX.get(cam); if (!ix) continue;
        const e = P.gsaps[ix.g].ubs[ix.u].equipes[ix.e];
        if (e.ine && e.tipo === "eSF" && !e.migrou && e.serie.atend && e.serie.atend[IU] > 0 && e.cad && e.serie.atend_med) return { cam, ...ix, g_n: p[0], u_n: p[1], e_n: p[2], ine: e.ine, cnes: P.gsaps[ix.g].ubs[ix.u].cnes }; }
      return null; }""")
    conf("há equipe de teste (eSF com alerta e séries)", alvo is not None, alvo and alvo["cam"])
    g, u, e = alvo["g"], alvo["u"], alvo["e"]
    outra_g = 0 if g != 0 else 1

    # ---- 1. estado inicial e escolha pela árvore lateral, sem zerar indicador, período nem filtro
    conf("barra do topo e árvore lateral existem", pg.locator("#navuni").is_visible() and pg.locator("#arv-lat").is_visible() and txt_barra(pg).startswith("Região Norte"), txt_barra(pg))
    pg.select_option("#sel-ind", "visitas"); pg.select_option("#sel-per", "12"); pg.select_option("#f-alerta", "*"); pg.wait_for_timeout(300)
    lateral(pg, g, u, e); pg.wait_for_timeout(500)
    b = txt_barra(pg)
    conf("caminho na barra mostra região, GSAP, UBS e equipe", all(x in b for x in ("Região Norte", alvo["g_n"], alvo["u_n"], alvo["e_n"])), b)
    conf("árvore lateral destaca a equipe (aria-current)", pg.locator(f'#arv-lat .lat-s[data-s="{g}:{u}:{e}"]').get_attribute("aria-current") == "true" and pg.locator("#arv-lat [aria-current]").count() == 1)
    conf("trocar a unidade não zera indicador, período nem filtro", pg.input_value("#sel-ind") == "visitas" and pg.input_value("#sel-per") == "12" and pg.input_value("#f-alerta") == "*")
    cx = f"#g{g}u{u}e{e}"
    conf("Visão geral abre as caixas até a equipe e destaca", pg.locator(cx).get_attribute("open") is not None and "sel-dest" in (pg.locator(cx).get_attribute("class") or ""))
    h = pg.evaluate("location.hash")
    conf("o endereço guarda a unidade (g, u, e) e o indicador", all(k in h for k in ("g=", "u=" + alvo["cnes"], "e=" + alvo["ine"], "i=visitas", "p=12", "f=*")), h)
    pg.screenshot(path=str(SHOT / "shot_nav_desktop.png"))

    # ---- 2. mostrar só esta unidade
    conf("botão 'mostrar só esta unidade' aparece com unidade escolhida", pg.locator("#btn-so-sel").is_visible())
    pg.click("#btn-so-sel"); pg.wait_for_timeout(200)
    visiveis = pg.evaluate("[...document.querySelectorAll('#arvore > details.g')].filter(d => !d.classList.contains('fora')).length")
    irmas_u = pg.evaluate(f"[...document.querySelectorAll('#g{g} details.u')].filter(d => d.id !== 'g{g}u{u}' && !d.classList.contains('fora')).length")
    conf("esconde as GSAPs e UBS irmãs", visiveis == 1 and irmas_u == 0, f"GSAPs visíveis {visiveis}, UBS irmãs visíveis {irmas_u}")
    conf("o link guarda 'so=1'", "so=1" in pg.evaluate("location.hash"))
    pg.click("#btn-so-sel"); pg.wait_for_timeout(200)
    conf("desligar volta a mostrar as irmãs", pg.evaluate("[...document.querySelectorAll('#arvore > details.g')].filter(d => d.classList.contains('fora')).length") == 0)

    # ---- 3. cada aba mostra a unidade
    pg.select_option("#f-alerta", ""); pg.wait_for_timeout(300)
    pg.click("#aba-m"); pg.wait_for_selector("#mapa-corpo td.rot")
    conf("Mapa de calor: só a equipe escolhida", pg.locator("#mapa-corpo td.rot").count() == 1 and alvo["e_n"] in pg.inner_text("#mapa-corpo td.rot") and pg.locator("#mapa-sel").is_visible(), pg.locator("#mapa-corpo td.rot").count())
    pg.screenshot(path=str(SHOT / "shot_nav_mapa.png"))
    pg.click("#aba-p"); pg.wait_for_selector("#p-tab")
    conf("Resumo por unidade: já desce até a UBS e destaca a equipe", alvo["u_n"] in pg.inner_text("#p-crumb") and pg.locator("#p-tab tr.sel-linha").count() == 1, pg.inner_text("#p-crumb"))
    pg.click("#aba-x"); pg.wait_for_selector("#x-corpo .x-barra")
    conf("Tipo de atendimento: desce até a UBS e destaca a equipe", alvo["u_n"] in pg.inner_text("#x-crumb") and pg.locator("#x-corpo .sel-linha").count() == 1, pg.inner_text("#x-crumb"))
    pg.click("#aba-u"); pg.wait_for_selector("#u-corpo table")
    conf("Pessoas atendidas: desce até a UBS", alvo["u_n"] in pg.inner_text("#u-crumb"), pg.inner_text("#u-crumb"))
    pg.click("#aba-r"); pg.wait_for_selector("#r-corpo table")
    conf("Consultas por mil hab.: desce até a UBS e destaca a equipe", alvo["u_n"] in pg.inner_text("#r-crumb") and pg.locator("#r-corpo tr.sel-linha").count() == 1, pg.inner_text("#r-crumb"))
    pg.screenshot(path=str(SHOT / "shot_nav_perfil.png"))
    # descer por clique dentro da aba atualiza a unidade global
    pg.click("#r-crumb button[data-e='g']"); pg.wait_for_timeout(200)
    b = txt_barra(pg)
    conf("subir um nível dentro da aba atualiza a barra (fica só a GSAP)", alvo["g_n"] in b and alvo["u_n"] not in b, b)
    pg.click("#r-corpo button.lk >> nth=1"); pg.wait_for_timeout(200)
    conf("descer por clique dentro da aba atualiza a barra (UBS)", "UBS" in txt_barra(pg) and "eSF" not in txt_barra(pg), txt_barra(pg))
    lateral(pg, g, u, e)
    pg.click("#aba-h"); pg.wait_for_timeout(400)
    conf("voltar à Visão geral mantém a equipe aberta e destacada", pg.locator(cx).get_attribute("open") is not None and "sel-dest" in (pg.locator(cx).get_attribute("class") or ""))

    # ---- 4. abrir o link restaura
    link = pg.evaluate("location.href")
    pg2 = nova(nav); pg2.goto(link); pg2.reload(); pg2.wait_for_selector("#arvore details.g"); pg2.wait_for_timeout(600)
    conf("abrir o link restaura barra, árvore lateral e equipe aberta", alvo["e_n"] in txt_barra(pg2) and pg2.locator(cx).get_attribute("open") is not None and pg2.locator(f'#arv-lat .lat-s[data-s="{g}:{u}:{e}"]').get_attribute("aria-current") == "true", txt_barra(pg2))
    pg2.goto(link + "&v=m"); pg2.reload(); pg2.wait_for_selector("#mapa-corpo td.rot")
    conf("link de outra aba restaura a unidade nela (mapa de calor)", pg2.locator("#mapa-corpo td.rot").count() == 1 and pg2.locator("#vista-m").is_visible())
    pg2.goto(link.split("#")[0] + "#v=x&" + link.split("#")[1]); pg2.reload(); pg2.wait_for_selector("#x-corpo .x-barra")
    conf("link do Tipo de atendimento abre já descido até a UBS", alvo["u_n"] in pg2.inner_text("#x-crumb"))
    pg2.close()

    # ---- 5. menus de irmãos na barra
    pg.click('#nav-cam [data-m="u"]'); pg.wait_for_selector("#nav-menu:not([hidden])")
    itens = pg.locator("#nav-menu button").count(); n_ubs = pg.evaluate(f"P.gsaps[{g}].ubs.length")
    conf("menu da UBS lista as UBS da GSAP", itens == n_ubs and pg.get_attribute('#nav-cam [data-m="u"]', "aria-expanded") == "true", f"{itens} de {n_ubs}")
    pg.screenshot(path=str(SHOT / "shot_nav_menu.png"))
    pg.keyboard.press("Escape"); pg.wait_for_timeout(150)
    conf("Esc fecha o menu e devolve o foco", pg.locator("#nav-menu").is_hidden() and pg.evaluate("document.activeElement.dataset.m") == "u")
    if n_ubs > 1:
        pg.click('#nav-cam [data-m="u"]'); pg.wait_for_selector("#nav-menu:not([hidden])")
        outra = pg.evaluate(f"[...document.querySelectorAll('#nav-menu button')].findIndex(b => !b.hasAttribute('aria-current'))")
        nome_outra = pg.evaluate(f"document.querySelectorAll('#nav-menu button')[{outra}].childNodes[0].textContent").strip()
        pg.locator("#nav-menu button").nth(outra).click(); pg.wait_for_timeout(300)
        b = txt_barra(pg)
        conf("escolher outra UBS no menu troca a UBS e tira a equipe", nome_outra in b and alvo["e_n"] not in b and alvo["g_n"] in b, b)
        conf("indicador e período continuam", pg.input_value("#sel-ind") == "visitas" and pg.input_value("#sel-per") == "12")
    pg.click('#nav-cam [data-n="r"]'); pg.wait_for_timeout(200)
    conf("clicar em Região Norte limpa a unidade", txt_barra(pg).startswith("Região Norte") and "›" in txt_barra(pg) and alvo["g_n"] not in txt_barra(pg) and "so=1" not in pg.evaluate("location.hash"), txt_barra(pg))

    # ---- 6. busca: equipe, INE, UBS, CNES
    pg.fill("#busca", alvo["e_n"].split(" - ")[-1][:6]); pg.wait_for_timeout(500); pg.wait_for_selector("#achados button[data-i]")
    conf("busca por nome de equipe acha a equipe", "Equipe" in pg.inner_text("#achados"))
    pg.fill("#busca", alvo["ine"].lstrip("0")[:7]); pg.wait_for_timeout(500); pg.wait_for_selector("#achados button[data-i]")
    conf("busca por INE acha a equipe e mostra o INE", alvo["e_n"] in pg.inner_text("#achados") and "INE " + alvo["ine"] in pg.inner_text("#achados"))
    pg.locator("#achados button[data-i]", has_text=alvo["e_n"]).first.click(); pg.wait_for_timeout(400)
    conf("escolher o resultado seleciona a equipe (barra, árvore e Visão geral)", alvo["e_n"] in txt_barra(pg) and pg.locator(cx).get_attribute("open") is not None, txt_barra(pg))
    pg.fill("#busca", alvo["cnes"]); pg.wait_for_timeout(500); pg.wait_for_selector("#achados button[data-i]")
    conf("busca por CNES acha a UBS", alvo["u_n"] in pg.inner_text("#achados") and "CNES" in pg.inner_text("#achados"))
    pg.locator("#achados button[data-i]").first.click(); pg.wait_for_timeout(300)
    conf("resultado de UBS seleciona a UBS", alvo["u_n"] in txt_barra(pg) and alvo["e_n"] not in txt_barra(pg), txt_barra(pg))
    pg.fill("#busca", "")
    ntag = pg.evaluate("[...document.querySelectorAll('.nv-it')].length"); conf("barra mostra GSAP e UBS", ntag == 2, ntag)

    # ---- 7. servidor: a busca por nome só existe depois da senha
    entrar(pg)
    serv = pg.evaluate("""() => { for (const [gi, g] of P.gsaps.entries()) for (const [ui, u] of g.ubs.entries()) for (const [ei, e] of u.equipes.entries()) if (e.prof.length && e.prof[0].nome && e.prof[0].nome.includes(" ")) return { nome: e.prof[0].nome, g: gi, u: ui, e: ei, cam: g.nome + " › " + u.nome + " › " + e.nome, en: e.nome }; return null; }""")
    conf("há servidor com equipe na área dos gestores", serv is not None)
    pg3 = nova(nav)   # página nova, sem senha
    consulta = " ".join(serv["nome"].split()[:2])
    pg3.fill("#busca", consulta); pg3.wait_for_timeout(500)
    conf("sem senha: busca por nome de servidor não acha nada", "Profissional" not in pg3.inner_text("#achados") and serv["nome"] not in pg3.content())
    entrar(pg3)
    pg3.fill("#busca", consulta); pg3.wait_for_timeout(500); pg3.wait_for_selector("#achados button[data-i]")
    conf("com senha: busca por nome de servidor acha o profissional", "Profissional" in pg3.inner_text("#achados"))
    pg3.locator("#achados button[data-i]", has_text="Profissional").first.click(); pg3.wait_for_selector("dialog#ficha[open]")
    pg3.click("#ficha-x"); pg3.wait_for_timeout(300)
    conf("servidor leva à equipe dele (barra do topo)", "›" in txt_barra(pg3) and len(pg3.locator("#nav-cam .nv-it").all()) == 3, txt_barra(pg3))
    # ---- 8. inconsistências e relatório (com senha)
    inc = pg3.evaluate("(NOM.incons || []).length ? { gsap: NOM.incons[0].gsap, ubs: NOM.incons[0].ubs } : null")
    if inc:
        ix = pg3.evaluate(f"IDX.get({inc['gsap']!r} + ' › ' + {inc['ubs']!r})")
        lateral(pg3, ix["g"], ix["u"])
        pg3.click("#aba-i"); pg3.wait_for_selector("#i-corpo table")
        cams = pg3.evaluate("[...document.querySelectorAll('#i-corpo button.lk')].map(b => b.dataset.c)")
        conf("Inconsistências: só as da unidade escolhida", len(cams) > 0 and all(c.startswith(inc["gsap"] + " › " + inc["ubs"]) for c in cams) and "Filtrado pela unidade" in pg3.inner_text("#i-sel"), f"{len(cams)} linhas")
        pg3.click("#btn-rel"); pg3.wait_for_selector("#dlg-rel[open]")
        conf("relatório vem com a unidade escolhida", pg3.input_value("#rel-escopo") == f"u:{ix['g']}:{ix['u']}", pg3.input_value("#rel-escopo"))
        pg3.click("#rel-cancelar")
        pg3.click('#nav-cam [data-n="r"]'); pg3.wait_for_timeout(200)
        conf("sem unidade, Inconsistências mostram tudo", "Filtrado" not in pg3.inner_text("#i-sel"))
    else:
        conf("há inconsistências para testar", False)
    pg3.close()

    # ---- 9. celular 390 px
    m = nova(nav, 390, 800)
    conf("celular: sem rolagem horizontal", sem_rolagem(m))
    conf("celular: árvore escondida e botão na barra", not m.locator("#arv-lat").is_visible() and m.locator("#nav-arv").is_visible() and m.get_attribute("#nav-arv", "aria-expanded") == "false")
    m.click("#nav-arv"); m.wait_for_timeout(400)
    conf("celular: gaveta abre", m.locator("#arv-lat").is_visible() and m.get_attribute("#nav-arv", "aria-expanded") == "true" and sem_rolagem(m))
    m.screenshot(path=str(SHOT / "shot_nav_gaveta.png"))
    m.keyboard.press("Escape"); m.wait_for_timeout(400)
    conf("celular: Esc fecha a gaveta", not m.locator("#arv-lat").is_visible() and m.get_attribute("#nav-arv", "aria-expanded") == "false")
    m.click("#nav-arv"); m.wait_for_timeout(300); m.click(".lat-t >> nth=0"); m.click(f'#arv-lat .lat-s[data-s="{outra_g}"]'); m.wait_for_timeout(500)
    conf("celular: escolher na gaveta seleciona e fecha", not m.locator("#arv-lat").is_visible() and "›" in txt_barra(m) and sem_rolagem(m), txt_barra(m))
    m.click('#nav-cam [data-m="u"]'); m.wait_for_selector("#nav-menu:not([hidden])")
    caixa = m.evaluate("(() => { const r = document.getElementById('nav-menu').getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth; })()")
    conf("celular: menu cabe na tela", caixa and sem_rolagem(m))
    m.keyboard.press("Escape")
    m.screenshot(path=str(SHOT / "shot_nav_celular.png"))
    for aba in ("#aba-m", "#aba-p"):
        m.click(aba); m.wait_for_timeout(500)
        conf(f"celular: {aba} com unidade escolhida sem rolagem lateral", sem_rolagem(m))
    m.close()

    # ---- 10. modo escuro
    d = nova(nav, color_scheme="dark"); lateral(d, g, u, e); d.wait_for_timeout(400)
    cor = d.evaluate("getComputedStyle(document.getElementById('arv-lat')).backgroundColor"); cor_sel = d.evaluate("getComputedStyle(document.querySelector('#arv-lat .lat-s[aria-current]')).backgroundColor")
    conf("modo escuro: árvore e destaque usam as cores do tema escuro", cor == "rgb(27, 33, 41)" and cor_sel == "rgb(110, 168, 255)", f"{cor} / {cor_sel}")
    d.click('#nav-cam [data-m="u"]'); d.wait_for_selector("#nav-menu:not([hidden])")
    d.screenshot(path=str(SHOT / "shot_nav_escuro.png")); d.keyboard.press("Escape"); d.close()

    # ---- 11. esconder a árvore no computador
    pg.click("#lat-fechar"); pg.wait_for_timeout(200)
    conf("computador: esconder e mostrar a árvore lateral", not pg.locator("#arv-lat").is_visible() and pg.get_attribute("#nav-arv", "aria-expanded") == "false")
    pg.click("#nav-arv"); pg.wait_for_timeout(200)
    conf("computador: botão Unidades mostra de novo", pg.locator("#arv-lat").is_visible() and pg.get_attribute("#nav-arv", "aria-expanded") == "true")
    nav.close()
print("erros de console:", erros or "nenhum")
if falhas or erros:
    print("FALHAS:", falhas); sys.exit(1)
print("RESULTADO: tudo certo")
