import sys as _s, pathlib as _p; _s.path.insert(0, str(_p.Path(__file__).parent))
"""Lote 2: queda em níveis, primeira verificação, planilha de providências e ficha do servidor por cargo.
Uso: python -X utf8 testes/testar_lote2.py   (senha vem de coleta/senha.local; não imprime nomes nem CNS)"""
import json, re, statistics, pathlib
from playwright.sync_api import sync_playwright
from _entrar import entrar, planilha

RAIZ = pathlib.Path(__file__).resolve().parent.parent
URL = (RAIZ / "site" / "index.html").as_uri()
P = json.load(open(RAIZ / "dados" / "painel.json", encoding="utf-8")); N = json.load(open(RAIZ / "dados" / "nominal.json", encoding="utf-8"))
iu = P["meses"].index(P["ultimo_mes_completo"]); erros, falhas = [], []


def conf(nome, ok, det=""):
    print(("OK   " if ok else "FALHA"), nome, ("| " + str(det)) if det != "" else "")
    if not ok: falhas.append(nome)


br = lambda n: f"{int(n + 0.5):,}".replace(",", ".")
s12 = lambda v: sum(v[iu - 11: iu + 1])
med12 = lambda s: statistics.median(s[max(iu - 12, 0):iu])

# ---- esperado em Python: equipes eSF e UBS com queda (mesma regra, a partir de painel.json)
verm, amar = set(), set()


def avalia(cam, s):
    m = med12(s)
    if m < 150 or not s[iu] > 0 or not s[iu] / m < 0.7: return
    (verm if s[iu - 1] / m < 0.7 else amar).add(cam)


for g in P["gsaps"]:
    for u in g["ubs"]:
        avalia(f"{g['nome']} › {u['nome']}", u["serie"].get("atend", [0] * len(P["meses"])))
        for e in u["equipes"]:
            if e["ine"] and e["tipo"] == "eSF" and not e.get("migrou"): avalia(f"{g['nome']} › {u['nome']} › {e['nome']}", e["serie"].get("atend", [0] * len(P["meses"])))

# ---- pessoas (agrega vínculos por id)
pess = {}
for eq in N["prof"].values():
    for p in eq:
        x = pess.setdefault(p["id"], {"cat": "", "cargo": None, "chs": None, "ativo": False, "s": {}, "tp": [0] * 5, "tem_tp": False})
        x["cat"] = x["cat"] or p.get("cat") or ""; x["cargo"] = x["cargo"] or p.get("cargo"); x["chs"] = x["chs"] or p.get("chs"); x["ativo"] |= bool(p.get("ativo"))
        for k, v in p["serie"].items():
            a = x["s"].setdefault(k, [0] * len(v))
            for i, y in enumerate(v): a[i] += y or 0
        if p.get("tp"):
            x["tem_tp"] = True
            for j, n in enumerate(p["tp"]): x["tp"][j] += n
eh_med = lambda x: re.match(r"m[eé]dic", x["cat"], re.I) is not None

with sync_playwright() as pw:
    nav = pw.chromium.launch(channel="chrome", headless=True); ctx = nav.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True); pg = ctx.new_page()
    pg.on("console", lambda m: erros.append(m.text) if m.type == "error" else None); pg.on("pageerror", lambda e: erros.append(f"pageerror: {e}"))
    pg.goto(URL); pg.wait_for_selector("#arvore details.g"); entrar(pg)

    # ---------------- 1. queda em níveis
    sin = pg.evaluate("() => [...sinais()].map(([c, l]) => [c, l.map(x => [x.tipo, x.nivel, x.rot])])")
    hab = {c: [x for x in l if x[0] == "habitual"] for c, l in sin}
    p_verm = {c for c, l in hab.items() if any(x[1] == "alta" for x in l)}; p_amar = {c for c, l in hab.items() if any(x[1] == "media" for x in l)}
    conf("vermelhas (2 meses abaixo de 70%) na página = recálculo em Python", p_verm == verm, f"{len(p_verm)} x {len(verm)}")
    conf("amarelas (só o último mês) na página = recálculo em Python", p_amar == amar, f"{len(p_amar)} x {len(amar)}")
    conf("nenhuma unidade recebe duas etiquetas 'habitual' ao mesmo tempo", all(len(l) <= 1 for l in hab.values()))
    conf("rótulo da vermelha", all(x[2] == "2 meses seguidos abaixo de 70% do habitual" for l in hab.values() for x in l if x[1] == "alta"))
    conf("amarela com rótulo '% abaixo do habitual'", all(x[2].endswith("% abaixo do habitual") for l in hab.values() for x in l if x[1] == "media"))
    cont = {}
    for c, l in sin:
        for x in l: cont[(x[0], x[1])] = cont.get((x[0], x[1]), 0) + 1
    print("     sinais por tipo e nível:", dict(sorted(cont.items())))
    conf("zerada continua vermelha", all(x[1] == "alta" for c, l in sin for x in l if x[0] == "zerada"))
    # detalhe da vermelha traz os dois valores e o habitual
    if verm:
        cam = sorted(verm)[0]; det = pg.evaluate("c => sinais().get(c).find(x => x.tipo === 'habitual').det", cam)
        s = next((e["serie"]["atend"] for g in P["gsaps"] for u in g["ubs"] for e in u["equipes"] if f"{g['nome']} › {u['nome']} › {e['nome']}" == cam), None) or next(u["serie"]["atend"] for g in P["gsaps"] for u in g["ubs"] if f"{g['nome']} › {u['nome']}" == cam)
        conf("detalhe da vermelha com os dois valores e o habitual", br(s[iu - 1]) in det and br(s[iu]) in det and br(med12(s)) in det, det[:120])

    # ---------------- 2. dica com 3 meses e primeira verificação (hover de verdade)
    pg.select_option("#f-alerta", "habitual"); pg.wait_for_timeout(500)
    for _ in range(3):
        d = pg.locator("details.caixa:not([open]):visible").first
        if d.count(): d.locator("summary").first.click(); pg.wait_for_timeout(250)
    chip = pg.locator("#arvore .chip.alta:visible, #arvore .chip:not(.conta):visible").first
    chip.scroll_into_view_if_needed(); pg.wait_for_timeout(250); chip.hover(force=True); pg.wait_for_timeout(200)
    t = pg.evaluate("() => { const d = document.getElementById('dica'); return d && d.style.display === 'block' ? d.innerText : '' }")
    conf("dica da etiqueta: 'Primeira verificação' e 3 meses", "Primeira verificação:" in t and re.search(r"[a-z]{3}/\d\d [\d.]+ · [a-z]{3}/\d\d [\d.]+ · [a-z]{3}/\d\d [\d.]+", t) is not None, t.replace("\n", " | ")[:260])
    pg.select_option("#f-alerta", ""); pg.wait_for_timeout(200)
    # textos exatos por tipo
    esperado = {"zerada": "Conferir se a equipe funcionou no mês, a escala e se os registros do PEC foram enviados.",
                "habitual": "Rever dias de oferta, férias e afastamentos, composição da agenda e fechamento dos registros.",
                "medico": "Conferir escala médica, afastamentos e se o médico registrou em outra equipe ou sem equipe.",
                "queda": "Conferir mudanças de composição da equipe, de agenda e de forma de registro entre os dois períodos.",
                "acs": "Conferir lotação e afastamentos, roteiro de visitas e se o registro saiu com o INE correto.",
                "proc": "Conferir se o procedimento é ofertado, se há insumo e se está sendo registrado no campo de procedimento.",
                "semeq": "Verificar a identificação da equipe (INE) nos registros desta UBS.",
                "mudou": "Validar a data da mudança e onde a produção passou a ser registrada; conferir a lotação no RH."}
    conf("textos da primeira verificação idênticos ao pedido", pg.evaluate("() => PRIM_VERIF") == esperado)
    dicas = pg.evaluate("""() => { const o = {}; sinais().forEach((l, c) => l.forEach(x => { if (!o[x.tipo]) o[x.tipo] = dicaSinal(c, x); })); return o; }""")
    conf("toda dica, de todo tipo, traz a primeira verificação do tipo", all(("Primeira verificação: " + esperado[k]) in v for k, v in dicas.items() if k in esperado), sorted(dicas))
    conf("dicas dos tipos com série trazem 3 meses", all(re.search(r"[a-z]{3}/\d\d [\d.]+ · [a-z]{3}/\d\d [\d.]+ · [a-z]{3}/\d\d [\d.]+", v) for k, v in dicas.items() if k in ("zerada", "habitual", "medico", "queda", "acs")))

    # ---------------- 3. planilha de providências
    with pg.expect_download() as d: pg.click("#f-barra .btn-prov")
    lin = planilha(d.value.path()); cab = lin[0]
    conf("planilha: 4 colunas novas (Data de revisão já existia) e a última continua sendo a situação",
         all(c in cab for c in ("Primeira verificação", "Hipótese", "Medida a observar", "Data de revisão")) and cab.count("Data de revisão") == 1 and cab[-1].startswith("Situação (novo") and lin[1][-1] == "novo", f"{len(cab)} colunas")
    ic = cab.index("Primeira verificação")
    conf("planilha: todas as linhas de alerta com a primeira verificação preenchida; Hipótese e Medida em branco", all(l[ic] and not l[cab.index("Hipótese")] and not l[cab.index("Medida a observar")] for l in lin[1:] if l[2] == "Alerta") and len(lin) > 40)
    conf("planilha: mesmo número de colunas em todas as linhas", all(len(l) == len(cab) for l in lin))
    conf("planilha: texto da 1ª verificação confere com o tipo", any(l[ic] == esperado["habitual"] for l in lin[1:]) and any(l[ic] == esperado["zerada"] for l in lin[1:]))
    # relatório: alertas com a coluna
    html = pg.evaluate("() => relatorioHTML('r', ['alertas'])")
    conf("relatório, seção Alertas: coluna 'Primeira verificação' preenchida", "<th class=\"l\">Primeira verificação</th>" in html and esperado["habitual"] in html)

    # ---------------- 4. fichas
    def abrir(id_):
        pg.evaluate("id => abrirFicha(id)", id_); pg.wait_for_selector("#ficha[open]"); return pg.inner_text("#ficha-corpo")

    def id_de(f):
        return next((i for i, x in pess.items() if f(x)), None)

    # 4a. pares dos médicos
    n_med = sum(1 for x in pess.values() if eh_med(x) and x["ativo"] and "atend" in x["s"] and s12(x["s"]["atend"]) > 0)
    n_pag = pg.evaluate("() => paresDoCargo('Médicos', 'atend').length")
    conf("pares de médicos: n = todos os médicos ativos com produção", n_pag == n_med and n_med > 100, f"{n_pag} x {n_med}")
    cargos_med = {x["cargo"] for x in pess.values() if eh_med(x)}
    conf("médicos de vários cargos juntos num só grupo", len(cargos_med) >= 3, len(cargos_med))
    # médico com carga de 20 h (equivalente = 2x) e com 40 h
    med20 = max((i for i, x in pess.items() if eh_med(x) and x["ativo"] and x["chs"] == 20 and "atend" in x["s"]), key=lambda i: s12(pess[i]["s"]["atend"]), default=None)
    med40 = max((i for i, x in pess.items() if eh_med(x) and x["ativo"] and x["chs"] == 40 and "atend" in x["s"]), key=lambda i: s12(pess[i]["s"]["atend"]), default=None)
    semchs = next((i for i, x in pess.items() if eh_med(x) and x["ativo"] and not x["chs"] and "atend" in x["s"] and s12(x["s"]["atend"]) > 0), None)
    txt = abrir(med40)
    conf("ficha de médico: nota 'todos os médicos da Região Norte' e 'só informativo'", "todos os médicos da Região Norte" in txt and "só informativo" in txt)
    th = pg.locator("#ficha-corpo thead th").all_inner_texts()
    conf("coluna 'Equivalente em 40 h' na tabela de 12 meses", "Equivalente em 40 h" in th, th[:4])
    a = s12(pess[med40]["s"]["atend"]); lin_at = pg.locator("#ficha-corpo tr", has_text="Atendimentos individuais").first.locator("td").all_inner_texts()
    conf("40 h: equivalente = próprio valor", lin_at[1] == br(a) and lin_at[2] == br(a), lin_at[:3])
    if med20:
        a = s12(pess[med20]["s"]["atend"]); abrir(med20); lin_at = pg.locator("#ficha-corpo tr", has_text="Atendimentos individuais").first.locator("td").all_inner_texts()
        conf("20 h: equivalente = 12 meses x 40 / 20", lin_at[1] == br(a) and lin_at[2] == br(a * 2), f"{lin_at[1]} / {lin_at[2]} (esperado {br(a * 2)})")
    else: print("aviso: nenhum médico de 20 h com produção")
    if semchs:
        abrir(semchs); lin_at = pg.locator("#ficha-corpo tr", has_text="Atendimentos individuais").first.locator("td").all_inner_texts(); conf("sem carga horária: equivalente '–'", lin_at[2] == "–", lin_at[:3])
    # a comparação com pares não mudou de base: a mediana mostrada é a do valor bruto
    pares = sorted(s12(x["s"]["atend"]) for x in pess.values() if eh_med(x) and x["ativo"] and "atend" in x["s"] and s12(x["s"]["atend"]) > 0)
    med_pares = pares[round(.5 * (len(pares) - 1))]
    abrir(med40); lin_at = pg.locator("#ficha-corpo tr", has_text="Atendimentos individuais").first.inner_text()
    conf("mediana dos pares médicos = conta em Python (valor bruto)", br(med_pares) in lin_at, f"{br(med_pares)} em '{lin_at.strip()[:90]}'")

    # 4c. enfermeiro: 5 tipos, soma bate com nominal.json
    enf = max((i for i, x in pess.items() if re.match(r"enfermeiro", x["cat"], re.I) and x["ativo"] and x["tem_tp"]), key=lambda i: sum(pess[i]["tp"]))
    txt = abrir(enf); tp = pess[enf]["tp"]
    rot = ["Consulta no dia", "Consulta agendada", "Consulta agendada programada / cuidado continuado", "Atendimento de urgência", "Escuta inicial / orientação"]
    linhas_tp = [pg.locator("#ficha-corpo tr", has=pg.locator("td.l", has_text=re.compile("^" + re.escape(r) + "$"))).first.locator("td").all_inner_texts() for r in rot]
    conf("ficha de enfermeiro: bloco 'Tipo de atendimento (12 meses)' com os 5 tipos e a contagem do nominal.json", "Tipo de atendimento (12 meses)" in txt and all(l[1] == br(tp[j]) for j, l in enumerate(linhas_tp)), [l[1:] for l in linhas_tp])
    conf("percentuais somam 100% (±0,2)", abs(sum(float(l[2].replace("%", "").replace(",", ".")) for l in linhas_tp) - 100) < 0.2)
    ruins = [i for i, x in pess.items() if x["tem_tp"] and sum(x["tp"]) != s12(x["s"].get("atend", [0] * len(P["meses"])))]
    conf("soma dos 5 tipos = atendimentos de 12 meses da série individual (todos os médicos e enfermeiros)", not ruins, f"{len(ruins)} divergentes de {sum(1 for x in pess.values() if x['tem_tp'])}")
    mtp = max((i for i, x in pess.items() if eh_med(x) and x["tem_tp"]), key=lambda i: sum(pess[i]["tp"]))
    conf("ficha de médico também traz o bloco de tipos", "Tipo de atendimento (12 meses)" in abrir(mtp))

    # técnico
    tec = next((i for i, x in pess.items() if re.search(r"t[eé]cnic|auxiliar", x["cat"] + " " + str(x["cargo"]), re.I) and re.search("enferm", x["cat"] + " " + str(x["cargo"]), re.I) and x["ativo"] and "vacinas" in x["s"]), None)
    txt = abrir(tec)
    frase = "A escuta inicial não aparece para técnico de enfermagem nesta base (InfoSaúde, Atendimentos Individuais); o registro é feito pelo enfermeiro."
    conf("ficha de técnico: frase da escuta inicial", frase in txt)
    vazias = pg.evaluate("() => [...document.querySelectorAll('#ficha-corpo table')].filter(t => t.querySelector('th').textContent.startsWith('Produção') && t.querySelector('th:nth-child(2)').textContent === '12 meses').flatMap(t => [...t.querySelectorAll('tbody tr')].filter(r => r.cells[1].textContent.trim() === '0').map(r => r.cells[0].textContent))")
    conf("ficha de técnico: sem linha de atendimento vazia", not vazias and "Procedimentos e vacinas (12 meses)" in txt, vazias)

    # ACS
    acs = max((i for i, x in pess.items() if re.match(r"(agente|acs)", x["cat"], re.I) and x["ativo"] and "visitas" in x["s"]), key=lambda i: s12(pess[i]["s"]["visitas"]))
    txt = abrir(acs); r, ok = s12(pess[acs]["s"]["visitas"]), s12(pess[acs]["s"].get("visitas_ok", [0] * len(P["meses"])))
    cel = pg.locator("#ficha-corpo h3:has-text('Visitas (12 meses)') + .rolagem tbody td").all_inner_texts()
    conf("ficha de ACS: registradas, realizadas e % realizadas", cel == [br(r), br(ok), f"{ok / r * 100:.1f}".replace(".", ",") + "%"], f"{cel} esperado {br(r)}/{br(ok)}")

    # dentista: produção da eSB lotada
    eq_odo = {}
    for g in P["gsaps"]:
        for u in g["ubs"]:
            for e in u["equipes"]:
                if e["tipo"] == "eSB" and "odonto" in e["serie"]: eq_odo[(u["cnes"], e["ine"] or "SEM")] = s12(e["serie"]["odonto"])
    dent = None
    for k, l in N["prof"].items():
        cnes, ine = k.split("|")
        for p in l:
            if (cnes, ine) in eq_odo and p.get("lotado") and re.search(r"dentista", p.get("cat") or "", re.I): dent = (p["id"], eq_odo[(cnes, ine)])
        if dent: break
    txt = abrir(dent[0])
    conf("ficha de dentista: aviso de produção da equipe, não individual", "Produção da equipe de saúde bucal, não individual." in txt)
    cel = pg.locator("#ficha-corpo h3:has-text('Consultas odontológicas da equipe') ~ .rolagem tbody tr").first.locator("td").all_inner_texts()
    conf("ficha de dentista: consultas odontológicas de 12 meses da eSB = painel.json", cel[1] == br(dent[1]), f"{cel[1:]} esperado {br(dent[1])}")

    # celular com ficha aberta
    pg.set_viewport_size({"width": 390, "height": 844})
    for nome, id_ in (("médico", med40), ("enfermeiro", enf), ("técnico", tec), ("ACS", acs), ("dentista", dent[0])):
        abrir(id_); pg.wait_for_timeout(250)
        lat = pg.evaluate("() => [document.documentElement.scrollWidth > document.documentElement.clientWidth + 1, document.getElementById('ficha').scrollWidth > document.getElementById('ficha').clientWidth + 1]")
        conf(f"celular 390x844 com ficha de {nome}: sem rolagem lateral", not any(lat), lat)
        pg.evaluate("() => document.getElementById('ficha').close()")
    pg.set_viewport_size({"width": 1280, "height": 900})

    # PDF e Word: mesmos blocos, sem estourar a folha
    for nome, id_ in (("médico", med20 or med40), ("enfermeiro", enf), ("técnico", tec), ("ACS", acs), ("dentista", dent[0])):
        h = pg.evaluate("id => cabFicha() + fichaHTML(pessoas.get(id), true)", id_)
        marca = {"médico": "Tipo de atendimento (12 meses)", "enfermeiro": "Tipo de atendimento (12 meses)", "técnico": "A escuta inicial não aparece", "ACS": "Visitas (12 meses)", "dentista": "Produção da equipe de saúde bucal, não individual."}[nome]
        conf(f"PDF/Word ({nome}): bloco do cargo presente", marca in h and ("Equivalente em 40 h" in h or nome in ("dentista",)))
        pg.set_viewport_size({"width": 794, "height": 1100}); pg.emulate_media(media="print")
        larg = pg.evaluate("""h => { document.getElementById('rel-print').innerHTML = h; document.body.classList.add('imprimindo-rel'); const r = document.getElementById('rel-print');
            const o = [r.scrollWidth, r.clientWidth, document.documentElement.scrollWidth, document.documentElement.clientWidth]; return o; }""", h)
        conf(f"PDF ({nome}): nada passa da largura da folha", larg[0] <= larg[1] + 1 and larg[2] <= larg[3] + 1, larg)
        pg.evaluate("() => { document.body.classList.remove('imprimindo-rel'); document.getElementById('rel-print').innerHTML = ''; }")
        pg.emulate_media(media="screen"); pg.set_viewport_size({"width": 1280, "height": 900})
        tam = pg.evaluate("async h => (await relatorioWord(h, 't')).size", h)
        conf(f"Word ({nome}): arquivo gerado", tam > 3000, tam)

    conf("sem erro de console", not erros, erros[:3])
    nav.close()

# ---------------- privacidade e tamanho
pj = (RAIZ / "site" / "painel.js").read_text("utf-8"); pjson = (RAIZ / "dados" / "painel.json").read_text("utf-8"); idx = (RAIZ / "site" / "index.html").read_text("utf-8")
conf("painel.js/painel.json sem os campos nominais novos (tp, tipos por profissional)", '"tp":' not in pj and '"tp":' not in pjson and '"prof":' not in pj)
n_tp = sum(1 for x in pess.values() if x["tem_tp"]); n_esp = sum(1 for x in pess.values() if (eh_med(x) or re.match(r"enfermeiro", x["cat"], re.I)) and s12(x["s"].get("atend", [0] * len(P["meses"]))) > 0)
conf("nominal.json tem o total de 12 meses por tipo de quem é médico ou enfermeiro com atendimento", n_tp >= 300 and abs(n_tp - n_esp) <= 5, f"{n_tp} com tipos, {n_esp} médicos/enfermeiros com atendimentos em 12 meses")
nov = (RAIZ / "_backup_2026-11-22_antes_lote2" / "index.html").read_text("utf-8")
conf("nenhum 'white-space:nowrap' novo no index.html", idx.count("nowrap") <= nov.count("nowrap"), f"{idx.count('nowrap')} x {nov.count('nowrap')}")
conf("o termo 'recepção' não aparece", "recepção" not in idx.lower() and "recepcao" not in idx.lower())
print("tamanhos: painel.js", (RAIZ / "site" / "painel.js").stat().st_size, "| nominal.js", (RAIZ / "site" / "nominal.js").stat().st_size)
print("\n" + ("TUDO OK" if not falhas else f"{len(falhas)} FALHA(S): {falhas}"))
raise SystemExit(1 if falhas else 0)
