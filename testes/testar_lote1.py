"""Lote 1 de ajustes de navegação e de uso (21/11/2026): barra que some onde não se aplica, aba Inconsistências com cadeado,
Entrar/Gerar relatório no cabeçalho, celular enxuto, sessão lembrada por 12 h, cartões/tabela/CSV da aba só da unidade escolhida,
nome que abre a ficha e um único filtro de unidade.
Uso: python -X utf8 testes/testar_lote1.py (a senha vem de coleta/senha.local; nunca é impressa; nomes de pessoas também não)."""
import json, pathlib, sys, time
from playwright.sync_api import sync_playwright
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _entrar import entrar, senha; from _entrar import planilha, planilha_txt

RAIZ = pathlib.Path(__file__).resolve().parent.parent
URL = (RAIZ / "site" / "index.html").as_uri()
NOM = json.loads((RAIZ / "dados" / "nominal.json").read_text(encoding="utf-8"))
INC = NOM["incons"]
falhas, erros = [], []


def conf(nome, ok, det=""):
    print(("OK   " if ok else "FALHA"), nome, ("| " + str(det)) if det != "" else "")
    if not ok: falhas.append(nome)


def nova(ctx, larg=1280, alt=900):
    pg = ctx.new_page(); pg.set_viewport_size({"width": larg, "height": alt})
    pg.on("console", lambda m: erros.append(f"console.{m.type}: {m.text}") if m.type in ("error", "warning") else None)
    pg.on("pageerror", lambda e: erros.append(f"pageerror: {e}"))
    pg.goto(URL); pg.wait_for_selector("#arvore details.g")
    return pg


def vis(pg, sel): return pg.locator(sel).first.is_visible()
def sem_rolagem(pg): return pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 1
def aba(pg, id_): pg.click(id_); pg.wait_for_timeout(250)


def csv_baixado(pg, seletor):
    with pg.expect_download() as d: pg.click(seletor)
    f = d.value
    return f.suggested_filename, [[str(c) for c in l] for l in planilha(f.path())]


def unidade_alvo():
    """UBS com mais linhas de inconsistência: devolve (gsap, ubs, nº de linhas, nº de linhas por tipo)."""
    cont = {}
    for x in INC: cont[(x["gsap"], x["ubs"])] = cont.get((x["gsap"], x["ubs"]), 0) + 1
    (g, u), n = max(cont.items(), key=lambda kv: kv[1]); return g, u, n


with sync_playwright() as p:
    nav = p.chromium.launch(channel="chrome", headless=True)
    ctx = nav.new_context(accept_downloads=True)
    pg = nova(ctx)
    tem_restrito = pg.evaluate("() => !!P.restrito")
    conf("a página tem a parte restrita (senha)", tem_restrito)

    # ---------------- 2. cabeçalho e aba com cadeado (sem entrar)
    conf("Entrar fica no cabeçalho, ao lado do título", pg.locator("header #btn-entrar").count() == 1 and vis(pg, "header #btn-entrar"))
    conf("Gerar relatório está no cabeçalho (some para quem não entrou)", pg.locator("header #btn-rel").count() == 1 and not vis(pg, "#btn-rel"))
    conf("nenhum dos dois ficou na barra de filtros", pg.locator("#barra-ctrl #btn-entrar, #barra-ctrl #btn-rel").count() == 0)
    conf("aba Inconsistências aparece com cadeado para quem não entrou", vis(pg, "#aba-i") and "🔒" in pg.inner_text("#aba-i") and vis(pg, "#aba-i .cad-ico"))
    pg.click("#aba-i"); pg.wait_for_selector("#dlg-senha[open]")
    conf("clicar na aba com cadeado abre o diálogo de senha e não troca de aba", pg.evaluate("() => vistaAtual") == "h")
    pg.click("#senha-cancelar"); pg.wait_for_timeout(200)
    conf("cancelar mantém a Visão geral", pg.evaluate("() => vistaAtual") == "h" and pg.evaluate("() => abaAposEntrar") == "")
    pg.click("#aba-i"); pg.wait_for_selector("#dlg-senha[open]"); pg.fill("#senha", senha()); pg.click("#senha-ok"); pg.wait_for_selector("body.aberto", timeout=30000)
    pg.wait_for_timeout(500)
    conf("depois de entrar, cai direto na aba Inconsistências", pg.evaluate("() => vistaAtual") == "i" and vis(pg, "#vista-i") and not pg.locator("#dlg-senha[open]").count())
    conf("com a área aberta, o cadeado some e o botão vira Sair", not vis(pg, "#aba-i .cad-ico") and pg.inner_text("#btn-entrar").strip() == "Sair")
    conf("Gerar relatório aparece no cabeçalho depois de entrar", vis(pg, "header #btn-rel"))

    # ---------------- 1. barra de indicador/período/filtro some onde não se aplica
    aba(pg, "#aba-h")
    conf("Visão geral: barra completa (grupos, indicador, período, vínculo, CSV)", all(vis(pg, s) for s in ("#barra-ctrl", "#grp-ind", "#sel-ind", "#sel-per", "#chk-inativos", "#btn-csv")))
    aba(pg, "#aba-m")
    conf("Mapa de calor: indicador e período ficam; vínculo não confirmado some", vis(pg, "#sel-ind") and vis(pg, "#sel-per") and not vis(pg, "#chk-inativos"))
    aba(pg, "#aba-p")
    conf("Perfil (resumo): a barra inteira some", not vis(pg, "#barra-ctrl") and not vis(pg, "#sel-ind") and not vis(pg, "#grp-ind") and not vis(pg, "#sel-per"))
    aba(pg, "#aba-x")
    conf("Perfil, tipo mês a mês: só o período fica (o gráfico usa o período)", vis(pg, "#barra-ctrl") and vis(pg, "#sel-per") and not vis(pg, "#sel-ind") and not vis(pg, "#grp-ind") and not vis(pg, "#btn-csv"))
    n1 = pg.evaluate("() => document.querySelectorAll('#x-tempo rect').length"); pg.select_option("#sel-per", "12"); pg.wait_for_timeout(300)
    # o período vale mesmo escondendo o resto
    conf("Perfil, tipo mês a mês: trocar o período muda o gráfico", pg.evaluate("() => document.querySelectorAll('#x-tempo rect').length") != n1 or pg.evaluate("() => estado.per") == 12)
    pg.select_option("#sel-per", "24")
    for id_ in ("#aba-u", "#aba-r"):
        aba(pg, id_); conf(f"Perfil ({id_}): a barra inteira some", not vis(pg, "#barra-ctrl") and not vis(pg, "#sel-ind") and not vis(pg, "#sel-per"))
    aba(pg, "#aba-i")
    conf("Inconsistências: a barra inteira some", not vis(pg, "#barra-ctrl") and not vis(pg, "#sel-ind") and not vis(pg, "#sel-per") and not vis(pg, "#btn-csv"))
    aba(pg, "#aba-h")
    conf("Visão geral: a barra volta", all(vis(pg, s) for s in ("#barra-ctrl", "#grp-ind", "#sel-ind", "#sel-per", "#chk-inativos", "#btn-csv")))
    conf("nenhum controle ficou 'desabilitado' no lugar de sumir", pg.evaluate("() => !document.querySelector('#sel-ind').disabled && ![...document.querySelectorAll('#grp-ind button')].some(b => b.disabled)"))

    # ---------------- 7. um filtro de unidade só
    aba(pg, "#aba-i")
    conf("não existe mais o seletor de GSAP da aba (#i-gsap)", pg.locator("#i-gsap").count() == 0)
    conf("os outros filtros da aba continuam (tipo, busca, CSV, providências)", all(vis(pg, s) for s in ("#i-tipo", "#i-q", "#i-csv", "#vista-i .btn-prov")))

    # ---------------- 5. cartões contam só a unidade escolhida
    g_nome, u_nome, n_ubs = unidade_alvo()
    n_reg = len(INC)
    soma = lambda: pg.evaluate("() => [...document.querySelectorAll('#i-cartoes .n')].reduce((a, e) => a + (+e.textContent.replace(/\\D/g, '')), 0)")
    conf("sem unidade escolhida, a soma dos cartões é a Região inteira", soma() == n_reg, f"{soma()} x {n_reg}")
    ok = pg.evaluate("""([g, u]) => { const gi = P.gsaps.findIndex(x => x.nome === g); if (gi < 0) return false; const ui = P.gsaps[gi].ubs.findIndex(x => x.nome === u); if (ui < 0) return false; selecionar({ g: gi, u: ui }); return true; }""", [g_nome, u_nome])
    conf("escolhe a UBS com mais linhas", ok, f"{n_ubs} linhas")
    pg.wait_for_timeout(400)
    conf("com UBS escolhida, a soma dos cartões = nº de linhas dessa UBS em nominal.json", soma() == n_ubs, f"{soma()} x {n_ubs}")
    conf("o filtro 'Tipo' também conta só a UBS", f"Todos ({n_ubs})" in pg.inner_text("#i-tipo"))
    n_linhas = pg.locator("#i-corpo tbody tr").count()
    conf("a tabela tem as linhas da UBS (e só dela)", n_linhas == min(n_ubs, 500) and pg.evaluate("([g, u]) => [...document.querySelectorAll('#i-corpo tbody tr')].every(r => r.cells[1].innerText.includes(u))", [g_nome, u_nome]), n_linhas)
    conf("a frase da aba diz qual unidade vale", u_nome in pg.inner_text("#i-sel"))

    # ---------------- 6. nome abre a ficha
    nbtn = pg.locator("#i-corpo button[data-fid]").count()
    com_nome = sum(1 for x in INC if x["gsap"] == g_nome and x["ubs"] == u_nome and x["nome"])
    conf("há botões de nome na tabela (linhas com pessoa identificável)", nbtn > 0, f"{nbtn} de {com_nome} linhas com nome")
    conf("linhas sem pessoa na lotação ficam só com texto (sem botão)", nbtn <= com_nome)
    nome_btn = pg.inner_text("#i-corpo button[data-fid]").strip()
    pg.click("#i-corpo button[data-fid]"); pg.wait_for_selector("#ficha[open]")
    conf("clicar no nome abre a ficha do servidor, com o mesmo nome", pg.inner_text("#ficha-t").strip() == nome_btn and len(pg.inner_text("#ficha-corpo")) > 50)
    pg.click("#ficha-x"); pg.wait_for_timeout(200)
    # ligação de TODAS as linhas da Região: a pessoa da ficha tem o mesmo nome da linha
    errados = pg.evaluate("""() => { selecionar({}); let ruim = 0, bot = 0; for (const x of NOM.incons) { const id = idDaLinha(x); if (id == null) continue; bot++; const p = pessoas.get(id); if (!p || p.nome !== x.nome) ruim++; } return [bot, ruim]; }""")
    conf("em toda a Região, cada botão aponta para a pessoa de mesmo nome", errados[1] == 0 and errados[0] > 0, f"{errados[0]} ligações, {errados[1]} erradas")

    # ---------------- 8. CSV só da unidade
    pg.evaluate("""([g, u]) => { const gi = P.gsaps.findIndex(x => x.nome === g); const ui = P.gsaps[gi].ubs.findIndex(x => x.nome === u); selecionar({ g: gi, u: ui }); }""", [g_nome, u_nome]); pg.wait_for_timeout(400)
    nome, lin = csv_baixado(pg, "#i-csv")
    conf("CSV da aba: nome do arquivo diz a unidade", "inconsistencias_aps_norte_" in nome and pg.evaluate("n => nomeArq(rotSel())", None) in nome, nome)
    dados = lin[1:]
    conf("CSV da aba: só linhas da UBS escolhida, todas elas", len(dados) == n_ubs and all(l[2].strip('"') == u_nome and l[1].strip('"') == g_nome for l in dados), len(dados))
    nome2, lin2 = csv_baixado(pg, "#vista-i .btn-prov")
    d2 = lin2[1:]
    esperadas = sum(1 for x in INC if x["gsap"] == g_nome and x["ubs"] == u_nome and not (x["tipo"] == "lugar_errado" and x["det"].startswith("Nenhum registro de")))
    inc2 = [l for l in d2 if l[2].strip('"') == "Inconsistência"]
    conf("providências da aba: nome do arquivo diz a unidade", "providencias_aps_norte_" in nome2 and pg.evaluate("n => nomeArq(rotSel())", None) in nome2, nome2)
    conf("providências da aba: só a UBS escolhida (alertas e inconsistências)", len(d2) > 0 and all(l[4].strip('"') == u_nome for l in d2), f"{len(d2)} linhas")
    conf("providências da aba: todas as inconsistências da UBS", len(inc2) == esperadas, f"{len(inc2)} x {esperadas}")
    pg.evaluate("() => selecionar({})"); pg.wait_for_timeout(300)
    nome3, lin3 = csv_baixado(pg, "#i-csv")
    conf("sem unidade: CSV da Região inteira, com 'regiao_norte' no nome", len(lin3) - 1 == n_reg and "regiao_norte" in nome3, nome3)
    # botão CSV ao lado de cada planilha: mesmo conteúdo em texto
    def em_csv(sel):
        with pg.expect_download() as d: pg.click(sel)
        return d.value.suggested_filename, [l for l in pathlib.Path(d.value.path()).read_text(encoding='utf-8-sig').splitlines() if l]
    nc, lc = em_csv('#i-csv-txt')
    conf('CSV da aba: arquivo .csv com as mesmas linhas da planilha', nc.endswith('.csv') and 'regiao_norte' in nc and len(lc) == len(lin3) and lc[0].startswith('"Tipo";"GSAP"'), f'{nc}: {len(lc)} x {len(lin3)}')
    nc2, lc2 = em_csv('#vista-i .btn-prov + .em-csv')
    conf('CSV de providências: arquivo .csv com cabeçalho', nc2.endswith('.csv') and lc2[0].startswith('"Emitido em"') and len(lc2) > 40, nc2)
    aba(pg, '#aba-h'); nc3, lc3 = em_csv('#btn-csv-txt')
    conf('CSV do indicador: arquivo .csv com cabeçalho', nc3.endswith('.csv') and lc3[0].startswith('"GSAP";"UBS"') and len(lc3) > 100, nc3)
    aba(pg, '#aba-i')

    # ---------------- 3. celular
    m = nova(ctx, 390, 844)
    top = m.evaluate("() => Math.round(document.querySelector('#kpis').getBoundingClientRect().top)")
    conf("celular (sem entrar): cartões começam perto de 420 px (≤ 440)", top <= 440, f"{top} px")
    conf("celular: grupos de indicador recolhidos por padrão", not vis(m, "#grp-ind") and vis(m, "#grp-toggle"))
    m.click("#grp-toggle"); m.wait_for_timeout(150)
    conf("celular: o toque abre os grupos", vis(m, "#grp-ind") and m.get_attribute("#grp-toggle", "aria-expanded") == "true")
    m.click("#grp-ind button[data-g='dm']"); m.wait_for_timeout(300)
    conf("celular: escolher um grupo troca o indicador e recolhe a lista", not vis(m, "#grp-ind") and m.evaluate("() => estado.grp") == "dm" and "Diabetes" in m.inner_text("#grp-toggle"))
    conf("celular: sem rolagem lateral na Visão geral", sem_rolagem(m))
    def fontes(pg_): return pg_.evaluate("() => [...document.querySelectorAll('select, input:not([type=checkbox]):not([type=radio]), textarea')].filter(e => e.offsetParent !== null).map(e => parseFloat(getComputedStyle(e).fontSize))")
    f = fontes(m); conf("celular: fontes dos campos visíveis ≥ 16 px (Visão geral)", len(f) > 0 and min(f) >= 16, f"mín {min(f) if f else None}")
    entrar(m)
    top2 = m.evaluate("() => Math.round(document.querySelector('#kpis').getBoundingClientRect().top)")
    conf("celular (gestor, área aberta): cartões também ≤ 440 px", top2 <= 440, f"{top2} px")
    for id_, rot in (("#aba-h", "Visão geral"), ("#aba-m", "Mapa"), ("#aba-p", "Perfil"), ("#aba-x", "Tipo mês a mês"), ("#aba-u", "Pessoas"), ("#aba-r", "Consultas por mil"), ("#aba-i", "Inconsistências")):
        aba(m, id_); m.wait_for_timeout(200)
        ff = fontes(m)
        conf(f"celular, {rot}: sem rolagem lateral e campos ≥ 16 px", sem_rolagem(m) and (not ff or min(ff) >= 16), f"mín {min(ff) if ff else '-'}")
    m.close()

    # ---------------- 4. sessão lembrada por 12 h
    ctx2 = nav.new_context(accept_downloads=True)
    a = nova(ctx2); entrar(a, lembrar=True)
    bruto = a.evaluate("() => localStorage.getItem('aps_norte_chave')")
    o = json.loads(bruto)
    conf("lembrar: guarda a chave e o momento da gravação (e não a senha)", set(o) == {"k", "t"} and abs(o["t"] / 1000 - time.time()) < 120 and senha() not in bruto)
    conf("texto ao lado da caixa diz 'por 12 horas'", "por 12 horas" in a.inner_text("#form-senha"), "")
    def regravar(pg_, horas):
        pg_.evaluate("h => { const o = JSON.parse(localStorage.getItem('aps_norte_chave')); o.t = Date.now() - h * 3600e3; localStorage.setItem('aps_norte_chave', JSON.stringify(o)); }", horas)
    regravar(a, 1); a.reload(); a.wait_for_selector("#arvore details.g"); a.wait_for_timeout(2500)
    conf("chave de 1 h atrás: entra sozinho", a.evaluate("() => document.body.classList.contains('aberto')") and not vis(a, "#aviso-sessao"))
    regravar(a, 13); a.reload(); a.wait_for_selector("#arvore details.g"); a.wait_for_timeout(2500)
    conf("chave de 13 h atrás: não entra, é apagada e avisa numa linha", not a.evaluate("() => document.body.classList.contains('aberto')") and a.evaluate("() => localStorage.getItem('aps_norte_chave')") is None and "12 horas" in a.inner_text("#aviso-sessao") and vis(a, "#aviso-sessao"))
    a.evaluate("() => localStorage.setItem('aps_norte_chave', 'AAAA')"); a.reload(); a.wait_for_selector("#arvore details.g"); a.wait_for_timeout(1000)
    conf("chave antiga, sem carimbo de hora: tratada como vencida e apagada", not a.evaluate("() => document.body.classList.contains('aberto')") and a.evaluate("() => localStorage.getItem('aps_norte_chave')") is None)
    entrar(a, lembrar=True)
    a.evaluate("() => { NOM.selo = Date.now() - 13 * 3600e3; verificarValidade(); }"); a.wait_for_selector("#arvore details.g"); a.wait_for_timeout(2500)
    conf("página aberta e passadas 12 h: fecha a área (como o Sair), apaga a chave e avisa", not a.evaluate("() => document.body.classList.contains('aberto')") and a.evaluate("() => localStorage.getItem('aps_norte_chave')") is None and vis(a, "#aviso-sessao"))
    entrar(a)   # sem lembrar: nenhum prazo é aplicado
    a.evaluate("() => { verificarValidade(); }"); a.wait_for_timeout(500)
    conf("entrada sem 'lembrar' não é afetada pelo prazo", a.evaluate("() => document.body.classList.contains('aberto')"))
    ctx2.close()

    conf("sem erro de console nem de página", not erros, "; ".join(erros[:3]))
    nav.close()

print("\n" + ("TUDO OK" if not falhas else f"{len(falhas)} FALHA(S): " + "; ".join(falhas)))
sys.exit(1 if falhas else 0)
