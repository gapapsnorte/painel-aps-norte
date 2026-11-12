"""Relatório da área dos gestores (PDF pela impressão, Word como .doc).
Uso: python -X utf8 testes/testar_relatorio.py   (APS_SENHA ou coleta/senha.local)
O arquivo Word de exemplo fica em testes/_dicas/ (pasta fora do git, porque contém nomes)."""
import base64, json, pathlib, re, sys, unicodedata
from playwright.sync_api import sync_playwright
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _entrar import entrar

RAIZ = pathlib.Path(__file__).resolve().parent.parent
URL = (RAIZ / "site" / "index.html").as_uri()
N = json.load(open(RAIZ / "dados" / "nominal.json", encoding="utf-8"))
P = json.load(open(RAIZ / "dados" / "painel.json", encoding="utf-8"))
SAIDA = RAIZ / "testes" / "_dicas"; SAIDA.mkdir(exist_ok=True)
falhas, erros = [], []


def norm(s): return re.sub(r"[^A-Z]", "", unicodedata.normalize("NFD", s).upper())


def confere(nome, ok, det=""):
    print(("OK   " if ok else "FALHA"), nome, ("| " + str(det)) if det != "" else "")
    if not ok: falhas.append(nome)


g0 = P["gsaps"][0]; u0 = g0["ubs"][0]
e0 = next(e for e in u0["equipes"] if e["ine"] and any(p["ativo"] for p in N["prof"].get(f"{u0['cnes']}|{e['ine']}", [])))
nome0 = next(p["nome"] for p in N["prof"][f"{u0['cnes']}|{e0['ine']}"] if p["ativo"] and " " in p["nome"])
NOMES_N = [norm(p["nome"]) for l in N["prof"].values() for p in l if p["nome"] and len(norm(p["nome"])) >= 10]

with sync_playwright() as pw:
    nav = pw.chromium.launch(channel="chrome", headless=True)
    pg = nav.new_page(viewport={"width": 1280, "height": 900}); pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto(URL); pg.wait_for_selector("#arvore details.g")
    confere("sem senha: botão do relatório escondido", not pg.locator("#btn-rel").is_visible())
    pg.evaluate("abrirRelatorio()"); pg.wait_for_timeout(200)
    confere("sem senha: a janela do relatório não abre", pg.locator("#dlg-rel[open]").count() == 0)
    h = pg.evaluate("relatorioHTML('u:0:0', REL_SEC.map(x => x[0]))")
    confere("sem senha: relatório montado por fora não tem nenhum nome", not any(n in norm(h) for n in NOMES_N) and "Profissionais por equipe" not in h)

    entrar(pg)
    confere("com senha: botão 'Gerar relatório' aparece", pg.locator("#btn-rel").is_visible())
    pg.locator("#arvore > details.g > summary").first.click(); pg.wait_for_timeout(300); pg.locator("#g0u0 > summary").click(); pg.wait_for_timeout(300)
    pg.click("#btn-rel"); pg.wait_for_selector("#dlg-rel[open]")
    confere("a unidade sugerida é a UBS aberta na tela", pg.input_value("#rel-escopo") == "u:0:0")
    confere("13 itens para escolher; o nominal vem desmarcado", pg.locator("input[name='rel-sec']").count() == 13 and not pg.is_checked("input[name='rel-sec'][value='prof']"))
    pg.screenshot(path=str(SAIDA / "relatorio_janela.png"))
    pg.click("#rel-nenhuma"); pg.click("#rel-ok"); pg.wait_for_timeout(150)
    confere("nada marcado: avisa e não gera", "pelo menos um" in pg.inner_text("#rel-aviso") and pg.locator("#dlg-rel[open]").count() == 1)

    # PDF: a impressão é trocada por um marcador, e o conteúdo é lido na hora em que o navegador imprimiria
    pg.evaluate("() => { window.print = () => { window._imp = document.getElementById('rel-print').innerHTML; window._classe = document.body.classList.contains('imprimindo-rel'); }; }")
    pg.check("input[name='rel-sec'][value='resumo']"); pg.check("input[name='rel-sec'][value='alertas']")
    pg.click("#rel-ok"); pg.wait_for_function("window._imp !== undefined")
    imp = pg.evaluate("window._imp")
    confere("PDF: só os itens marcados entram", "Resumo dos indicadores principais" in imp and "Alertas de" in imp and "Pessoas atendidas" not in imp and "Profissionais por equipe" not in imp)
    confere("PDF: página entra no modo de impressão do relatório", pg.evaluate("window._classe") is True)
    confere("PDF: cabeçalho traz a unidade e o mês", u0["nome"] in imp and "Último mês completo" in imp)

    pg.evaluate("window._imp = undefined"); pg.click("#btn-rel"); pg.wait_for_selector("#dlg-rel[open]"); pg.click("#rel-todas"); pg.click("#rel-ok"); pg.wait_for_function("window._imp !== undefined")
    imp = pg.evaluate("window._imp")
    titulos = ["Resumo dos indicadores principais", "por mês", "Alertas de", "por equipe", "contra a Região", "Perfil dos atendimentos em", "Perfil dos atendimentos, ", "Produção por boa prática", "Pessoas atendidas", "por mil cadastrados", "Profissionais por equipe", "Inconsistências de código", "Quadro de providências"]
    confere("PDF com tudo marcado: as 13 partes", all(t in imp for t in titulos), [t for t in titulos if t not in imp])
    confere("PDF com tudo: lista nominal traz o profissional da equipe", norm(nome0) in norm(imp))
    confere("PDF com tudo: aviso de uso interno", "uso interno da gestão" in imp)
    confere("matrícula, CNS e CPF fora do relatório (versão publicada)", not re.search(r"(?<![0-9.])[0-9]{11,}", re.sub(r"<svg.*?</svg>", "", imp, flags=re.S)) and ("mat. " not in imp or bool(pg.evaluate("P.com_matricula"))))
    # confere um número da tabela contra o JSON
    iu = P["meses"].index(P["ultimo_mes_completo"]); v = u0["serie"]["atend"][iu]
    confere("número do resumo = JSON (atendimentos da UBS no mês)", f"{v:,}".replace(",", ".") in imp, v)
    pdf = SAIDA / "relatorio_exemplo.pdf"
    pg.evaluate("document.getElementById('rel-print').innerHTML = window._imp; document.body.classList.add('imprimindo-rel')")
    pg.pdf(path=str(pdf), format="A4", margin={"top": "15mm", "bottom": "15mm", "left": "12mm", "right": "12mm"})
    pg.evaluate("document.body.classList.remove('imprimindo-rel'); document.getElementById('rel-print').innerHTML = ''")
    confere("PDF de exemplo gravado", pdf.stat().st_size > 20000, f"{pdf.stat().st_size // 1024} KB")

    # Word
    pg.click("#btn-rel"); pg.wait_for_selector("#dlg-rel[open]"); pg.select_option("#rel-escopo", "g:0"); pg.click("#rel-todas"); pg.check("input[name='rel-fmt'][value='word']")
    with pg.expect_download(timeout=60000) as d: pg.click("#rel-ok")
    arq = SAIDA / d.value.suggested_filename; d.value.save_as(str(arq))
    bruto = arq.read_bytes().decode("utf-8")
    confere("Word: nome do arquivo traz a unidade e o mês", re.fullmatch(r"relatorio_aps_norte_gsap_1_planaltina_\d{4}-\d{2}\.doc", arq.name) is not None, arq.name)
    partes = bruto.split("------=_relatorio_aps_norte")
    html = base64.b64decode("".join(partes[1].split("\r\n\r\n", 1)[1].split())).decode("utf-8")
    n_img = sum(1 for p_ in partes if "Content-Type: image/png" in p_)
    confere("Word: gráficos viraram imagens (nenhum SVG sobrou)", n_img >= 2 and "<svg" not in html and html.count("<img") == n_img, f"{n_img} imagens")
    confere("Word: tabelas e lista nominal presentes", html.count("<table") >= 8 and norm(nome0) in norm(html), f"{html.count('<table')} tabelas")
    confere("Word: sem variáveis de cor soltas nem texto 'undefined'", "var(--" not in html and "undefined" not in html and "NaN" not in html)
    confere("a janela fecha depois de gerar", pg.locator("#dlg-rel[open]").count() == 0)

    # Região inteira (o maior relatório) não quebra
    h = pg.evaluate("relatorioHTML('r', REL_SEC.map(x => x[0]))")
    confere("Região inteira: monta com as 16 GSAPs", all(g["nome"] in h for g in P["gsaps"]) and "undefined" not in h and "NaN" not in h, f"{len(h) // 1024} KB de HTML")

    m = nav.new_page(viewport={"width": 390, "height": 800}); m.goto(URL); entrar(m); m.click("#btn-rel"); m.wait_for_selector("#dlg-rel[open]")
    confere("celular: janela cabe na tela", m.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth") and m.locator("#rel-ok").is_visible())
    m.screenshot(path=str(SAIDA / "relatorio_janela_celular.png"))
    nav.close()

print("arquivo Word de exemplo:", arq)
print("erros de console:", erros if erros else "nenhum")
print("RESULTADO:", "tudo certo" if not falhas and not erros else f"{len(falhas)} falha(s): {falhas}")
sys.exit(1 if falhas or erros else 0)
