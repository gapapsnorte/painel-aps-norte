"""Lote 3, fatia 1 (22/11/2026): tipo de UBS e equipe (porte, zona, IVT) e aba "Força de trabalho" (só com a senha).
Confere: (1) a parte aberta não tem IVT nem campo nominal da força de trabalho; (2) porte e IVT recalculados aqui, de forma independente,
batem com o que a página mostra; (3) sem a senha a aba só tem o cadeado; (4) depois de entrar, os números da tela são os do JSON e
a lotação do JSON bate com a planilha de RH; (5) ordenar, Excel e CSV. Uso: python -X utf8 testes/testar_lote3.py
(a senha vem de coleta/senha.local; não imprime nomes, CNS nem a senha)."""
import json, math, pathlib, re, sys, unicodedata
from collections import Counter, defaultdict
from playwright.sync_api import sync_playwright
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _entrar import entrar, planilha

RAIZ = pathlib.Path(__file__).resolve().parent.parent
URL = (RAIZ / "site" / "index.html").as_uri()
P = json.load(open(RAIZ / "dados" / "painel.json", encoding="utf-8")); N = json.load(open(RAIZ / "dados" / "nominal.json", encoding="utf-8"))
REF = json.load(open(RAIZ / "coleta" / "referencia.json", encoding="utf-8"))
IVT = {x["ine"]: x for x in json.load(open(RAIZ / "coleta" / "ivt_apsdf_2024.json", encoding="utf-8"))}
erros, falhas = [], []


def conf(nome, ok, det=""):
    print(("OK   " if ok else "FALHA"), nome, ("| " + str(det)) if det != "" else "")
    if not ok: falhas.append(nome)


def num(t): return float(t.replace(".", "").replace(",", ".")) if re.fullmatch(r"[\d.,]+", t) else None
nn = lambda s: re.sub(r"[^A-Z]", "", unicodedata.normalize("NFD", str(s or "")).upper())
FAIXAS = ["Baixa", "Média", "Alta"]
UBS = [(g, u) for g in P["gsaps"] for u in g["ubs"]]

# ---------------- 1. parte aberta sem IVT e sem campo nominal
pj = (RAIZ / "site" / "painel.js").read_text("utf-8"); ht = (RAIZ / "site" / "index.html").read_text("utf-8"); nj = (RAIZ / "site" / "nominal.js").read_text("utf-8")
conf("painel.js sem a palavra IVT", not re.search(r"(?<![a-z])ivt(?![a-z])", pj, re.I))
conf("painel.js sem campos da força de trabalho (ft, vinc, vinculo, chs, cargo)", not re.search(r'"(ft|vinc|vinculo|chs|cargo|prof|mat|cns)":', pj))
conf("index.html sem INE que tenha IVT", not any(i in ht for i in IVT), f"{len(IVT)} INE conferidos")
conf("index.html sem valor de IVT por equipe", not re.search(r'"ivt"\s*:\s*\d', ht))
conf("nominal.js continua cifrado (AES-GCM, sem gzip nem JSON legível)", '"ct"' in nj[:400] and '"iv"' in nj[:400] and '"ct":"H4sI' not in nj and '"ivt"' not in nj and '"ft"' not in nj)
conf("JSON aberto (painel.json) sem IVT", not re.search(r"(?<![a-z])ivt(?![a-z])", json.dumps(P), re.I))
conf("nominal.json tem IVT e força de trabalho", bool(N.get("ivt")) and bool(N.get("ft")), f"{len(N['ft'])} linhas de força de trabalho")
txt_aberto = json.dumps(P, ensure_ascii=False)
conf("parte aberta sem vínculo (texto do RH)", not any(v in txt_aberto for v in ("Servidor Estatutário", "Residente - FIOCRUZ", "Mais Médicos")))

# ---------------- 2. porte e IVT recalculados fora do montar.py
cads = sorted(u["cad"] for g, u in UBS if u["cad"])
c1, c2 = cads[math.ceil(len(cads) / 3) - 1], cads[math.ceil(2 * len(cads) / 3) - 1]
conf("cortes de porte (terços) conferem", P["tipo_ubs"]["cortes"] == [c1, c2], f"{P['tipo_ubs']['cortes']} em {len(cads)} UBS")
conf("porte de cada UBS confere", all(u["porte"] == (None if not u["cad"] else "Pequeno" if u["cad"] <= c1 else "Médio" if u["cad"] <= c2 else "Grande") for g, u in UBS))
cont_porte = Counter(u["porte"] for g, u in UBS)
conf("cada terço tem cerca de um terço das UBS", max(cont_porte[k] for k in ("Pequeno", "Médio", "Grande")) - min(cont_porte[k] for k in ("Pequeno", "Médio", "Grande")) <= 2, dict(cont_porte))
conf("zona da equipe vem da planilha de RH", all((e.get("zona") or None) == (REF["equipes"].get(e["ine"], {}).get("zona") if e["ine"] in REF["equipes"] else None) for g, u in UBS for e in u["equipes"]))
esperado_ubs = {}
for g, u in UBS:
    cont = {f: 0 for f in FAIXAS}; sem = 0
    for e in u["equipes"]:
        if e["tipo"] != "eSF" or not e["ine"] or e.get("migrou"): continue
        if e["ine"] in IVT: cont[IVT[e["ine"]]["classe"]] += 1
        else: sem += 1
    mx = max(cont.values()); top = [f for f in FAIXAS if cont[f] == mx] if mx else []
    esperado_ubs[u["cnes"]] = (cont, sem, top)
conf("IVT por UBS (faixa mais frequente e contagem) confere", all(N["ivt"]["ubs"][c]["c"] == v[0] and N["ivt"]["ubs"][c]["sem"] == v[1] and ((N["ivt"]["ubs"][c]["faixa"] and [N["ivt"]["ubs"][c]["faixa"]]) or N["ivt"]["ubs"][c]["empate"] or []) == v[2] for c, v in esperado_ubs.items()))
conf("IVT por equipe: só eSF com INE na lista", all(k.split("|")[1] in IVT and N["ivt"]["eq"][k][1] == IVT[k.split("|")[1]]["classe"] and N["ivt"]["eq"][k][0] == IVT[k.split("|")[1]]["ivt"] for k in N["ivt"]["eq"]), f"{len(N['ivt']['eq'])} equipes")
conf("nenhum IVT estimado: eSF sem INE na lista não tem valor", all(f"{u['cnes']}|{e['ine']}" not in N["ivt"]["eq"] for g, u in UBS for e in u["equipes"] if e["tipo"] == "eSF" and e["ine"] and e["ine"] not in IVT))
# lotação do JSON x planilha de RH (independente)
ok_lot = True; n_conf = 0
for g, u in UBS:
    for e in u["equipes"]:
        if not e["ine"] or e["ine"] not in REF["equipes"] or REF["equipes"][e["ine"]]["cnes"] != u["cnes"]: continue
        esp = len({x["cns"] or nn(x["nome"]) for x in REF["lotacao"].get(e["ine"], [])}); got = N["ft"][f"E|{u['cnes']}|{e['ine']}"]["n"]; n_conf += 1
        if esp != got: ok_lot = False
conf("lotados por equipe (JSON) = planilha de RH", ok_lot, f"{n_conf} equipes")
conf("lotados na UBS sem equipe (JSON) = planilha de RH", all(N["ft"][f"S|{u['cnes']}"]["n"] == len({x["cns"] or nn(x["nome"]) for x in REF["lotacao"].get("UBS:" + u["cnes"], [])}) for g, u in UBS))
conf("categorias somam os lotados em todas as linhas", all(sum(v["cat"].values()) == v["n"] and v["com"] + v["sem"] == v["n"] for v in N["ft"].values()))

with sync_playwright() as pw:
    nav = pw.chromium.launch(channel="chrome", headless=True); ctx = nav.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True); pg = ctx.new_page()
    pg.on("console", lambda m: erros.append(m.text) if m.type == "error" else None); pg.on("pageerror", lambda e: erros.append(f"pageerror: {e}"))
    pg.goto(URL); pg.wait_for_selector("#arvore details.g")

    # ---------------- 3. sem a senha: só o cadeado
    conf("aba Força de trabalho aparece com cadeado", pg.locator("#aba-f").is_visible() and pg.locator("#aba-f .cad-ico").is_visible())
    pg.click("#aba-f"); pg.wait_for_selector("#dlg-senha[open]", timeout=5000)
    conf("clique na aba sem senha abre a janela da senha", True)
    conf("a aba não abriu sem a senha", pg.locator("#vista-f").is_hidden())
    pg.keyboard.press("Escape")
    corpo = pg.evaluate("document.body.innerText")
    conf("sem senha: nada de IVT, lotados nem vínculo na tela", not re.search(r"IVT|Servidor Estatut|Lotados na UBS|Sem produção em 12", corpo))
    pg.evaluate("selecionar({g: 0, u: 0})"); pg.wait_for_timeout(300)
    conf("sem senha: ficha da unidade sem linha de tipo", pg.locator(".tipo-linha").count() == 0)
    conf("sem senha: página sem NOM.ft nem NOM.ivt", pg.evaluate("!NOM.ft && !NOM.ivt"))

    # ---------------- 4. com a senha
    entrar(pg)
    conf("depois de entrar o cadeado da aba some", pg.locator("#aba-f .cad-ico").is_hidden())
    pg.evaluate("selecionar({g: null})"); pg.click("#aba-f"); pg.wait_for_selector("#f-corpo table")
    conf("a aba abre depois de entrar", pg.locator("#vista-f").is_visible() and pg.locator("#aba-f").get_attribute("aria-selected") == "true")

    def tabela():
        return pg.eval_on_selector_all("#f-corpo tbody tr", "rs => rs.map(r => [r.className, ...[...r.cells].map(c => c.innerText.trim())])")

    def confere_linha(cel, r, rotulo):
        """cel: células da tela (sem a classe); r: linha do JSON."""
        esp = [r["n"], *[r["cat"][c] for c in ("Médico", "Enfermeiro", "Técnico de enfermagem", "ACS", "Cirurgião-dentista", "THD/ASB", "Outros")], r["res"], r["com"], r["sem"]]
        got = [num(x) for x in cel[2:2 + 11]]
        return got == [float(x) for x in esp]

    # Região
    T = tabela(); cab = pg.eval_on_selector_all("#f-corpo thead th", "hs => hs.map(h => h.innerText.trim())")
    conf("cabeçalho da tabela tem as colunas esperadas", cab[:3] == ["Unidade", "Tipo", "Lotados"] and "Com produção em 12 meses" in cab and "Vínculo" in cab and "Situação da equipe" in cab and len(cab) == 18, len(cab))
    conf("Região: 1 linha de total + 1 por GSAP", len(T) == 1 + len(P["gsaps"]), len(T))
    conf("Região: total da tela = JSON", confere_linha(T[0][1:], N["ft"]["R"], "R"))
    conf("Região: cada GSAP da tela = JSON", all(confere_linha(t[1:], N["ft"]["G|" + t[1].split("\n")[0]], "G") for t in T[1:]))
    # GSAP escolhida
    gi = max(range(len(P["gsaps"])), key=lambda i: len(P["gsaps"][i]["ubs"])); G = P["gsaps"][gi]
    pg.evaluate(f"selecionar({{g: {gi}}})"); pg.wait_for_timeout(300); T = tabela()
    conf("GSAP: total + uma linha por UBS", len(T) == 1 + len(G["ubs"]), f"{len(T)} linhas")
    conf("GSAP: números das UBS = JSON", all(confere_linha(t[1:], N["ft"]["U|" + next(u["cnes"] for u in G["ubs"] if u["nome"] == t[1].split("\n")[0])], "U") for t in T[1:]))
    conf("GSAP: coluna Tipo traz porte e IVT de cada UBS", all(re.search(r"porte (pequeno|médio|grande)", t[2]) and "IVT" in t[2] for t in T[1:]))
    # UBS escolhida (a de maior número de equipes)
    gi, ui = max(((a, b) for a, g in enumerate(P["gsaps"]) for b, u in enumerate(g["ubs"])), key=lambda t: len(P["gsaps"][t[0]]["ubs"][t[1]]["equipes"])); U = P["gsaps"][gi]["ubs"][ui]
    pg.evaluate(f"selecionar({{g: {gi}, u: {ui}}})"); pg.wait_for_timeout(300); T = tabela()
    eqs = [e for e in U["equipes"] if e["ine"]]
    conf("UBS: total + equipes + linha dos lotados sem equipe", len(T) == 1 + len(eqs) + 1, f"{len(T)} linhas")
    conf("UBS: total da tela = JSON", confere_linha(T[0][1:], N["ft"]["U|" + U["cnes"]], "U"))
    conf("UBS: linha dos lotados sem equipe = JSON", confere_linha(T[-1][1:], N["ft"]["S|" + U["cnes"]], "S"))
    por_nome = {t[1].split("\n")[0]: t for t in T}
    conf("UBS: cada equipe da tela = JSON", all(confere_linha(por_nome[e["nome"]][1:], N["ft"][f"E|{U['cnes']}|{e['ine']}"], "E") for e in eqs))
    conf("UBS: situação da equipe só usa os três valores", all(por_nome[e["nome"]][-1] in ("com produção", "sem produção", "mudou de UBS") for e in eqs), Counter(por_nome[e["nome"]][-1] for e in eqs))
    esf = [e for e in eqs if e["tipo"] == "eSF"]
    def ivt_txt(e):
        if e["ine"] in IVT and not e.get("migrou"): return "IVT " + str(IVT[e["ine"]]["ivt"]).replace(".", ",") + " (" + IVT[e["ine"]]["classe"].lower() + ")"
        return "sem IVT (equipe criada depois de 2024)" if not e.get("migrou") else "sem IVT"
    conf("UBS: IVT de cada eSF na tela = arquivo do IVT", all(ivt_txt(e) in por_nome[e["nome"]][2] for e in esf), f"{len(esf)} eSF")
    conf("UBS: eSB e eMulti dizem que o IVT não se aplica", all("IVT não se aplica" in por_nome[e["nome"]][2] for e in eqs if e["tipo"] != "eSF"))
    conf("UBS: linha de tipo no topo da aba", "porte" in pg.inner_text("#f-tipo") and "IVT" in pg.inner_text("#f-tipo"))
    # ficha da unidade (Visão geral)
    pg.click("#aba-h"); pg.wait_for_timeout(500)
    conf("ficha da unidade (Visão geral) tem a linha de tipo sob senha", pg.locator(".tipo-linha").count() >= 1 and "porte" in pg.locator(".tipo-linha").first.inner_text())
    pg.click("#aba-f"); pg.wait_for_selector("#f-corpo table")

    # ordenar pelo cabeçalho: total fica no topo
    antes = [t[1].split("\n")[0] for t in tabela()]
    pg.click("#f-corpo thead th:nth-child(3)"); pg.wait_for_timeout(200); a = tabela()
    v1 = [num(t[3]) for t in a[1:] if num(t[3]) is not None]
    pg.click("#f-corpo thead th:nth-child(3)"); pg.wait_for_timeout(200); b = tabela()
    v2 = [num(t[3]) for t in b[1:] if num(t[3]) is not None]
    conf("ordenar por Lotados: 1º clique crescente, 2º decrescente, total fixo no topo", v1 == sorted(v1) and v2 == sorted(v2, reverse=True) and "dest" in a[0][0] and "dest" in b[0][0], f"{v1[:4]}… / {v2[:4]}…")
    conf("ordenar por Tipo (texto) não quebra", (pg.click("#f-corpo thead th:nth-child(2)"), pg.wait_for_timeout(150))[0] is None and len(tabela()) == len(antes))

    # Excel e CSV
    esp_linhas = pg.evaluate("[COLS_FT.map(c => c[0]), ...linhasForca().map(x => valoresForca(x).map(c => c == null ? '' : c))]")
    with pg.expect_download() as d: pg.click("#f-csv")
    f = d.value; L = planilha(f.path())
    conf("Excel: nome do arquivo e linhas", f.suggested_filename.startswith("forca_de_trabalho_aps_norte_") and f.suggested_filename.endswith(".xlsx") and len(L) == len(esp_linhas), f.suggested_filename)
    conf("Excel: cabeçalho e números = tabela da tela", L[0] == esp_linhas[0] and all([x for x in l[2:16]] == [x if x != "" else "" for x in e[2:16]] for l, e in zip(L[1:], esp_linhas[1:])))
    import openpyxl, warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore"); ws = openpyxl.load_workbook(open(f.path(), "rb")).active
    conf("Excel: sem células mescladas", not ws.merged_cells.ranges)
    with pg.expect_download() as d: pg.click("#f-csv-txt")
    f2 = d.value; t = open(f2.path(), "rb").read().decode("utf-8-sig")
    lin = t.split("\r\n")
    conf("CSV: mesmo número de linhas e colunas", f2.suggested_filename.endswith(".csv") and len(lin) == len(esp_linhas) and all(len(l.split('";"')) == 18 for l in lin), f2.suggested_filename)
    conf("planilha traz lotados em UBS sem equipe e vínculo (texto do RH só aqui, sob senha)", any("sem equipe" in str(c) for l in L for c in l[:1]) and any("Estatut" in str(l[16]) for l in L[1:]))

    # link com a aba (cadeado também por link)
    pg.evaluate("selecionar({g: null})"); pg.wait_for_timeout(200)
    conf("link guarda a aba (v=f)", "v=f" in pg.evaluate("location.hash"))
    # Sair: volta a fechar
    pg.click("#btn-entrar"); pg.wait_for_selector("#arvore details.g"); pg.wait_for_timeout(500)
    conf("depois de Sair a aba volta a ter cadeado", pg.locator("#aba-f .cad-ico").is_visible())
    # celular
    pg.set_viewport_size({"width": 390, "height": 800}); pg.wait_for_timeout(300)
    conf("celular sem rolagem lateral da página", pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 1)
    nav.close()

conf("sem erros no console", not erros, erros[:3])
print("\nFALHAS:", falhas if falhas else "nenhuma")
sys.exit(1 if falhas else 0)
