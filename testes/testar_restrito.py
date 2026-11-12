"""Área dos gestores: sem senha não aparece nenhum nome de servidor, nem na página nem nos arquivos publicados;
com a senha certa tudo volta. Uso: python -X utf8 testes/testar_restrito.py (APS_SENHA ou coleta/senha.local)"""
import base64, gzip, hashlib, json, pathlib, re, subprocess, sys, unicodedata
from playwright.sync_api import sync_playwright
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _entrar import senha, entrar

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SITE = RAIZ / "site"; URL = (SITE / "index.html").as_uri()
N = json.load(open(RAIZ / "dados" / "nominal.json", encoding="utf-8"))          # cópia em claro, só local
P = json.load(open(RAIZ / "dados" / "painel.json", encoding="utf-8"))
NOMES = sorted({p["nome"] for l in N["prof"].values() for p in l if p["nome"] and " " in p["nome"]})
falhas, erros = [], []


def norm(s): return re.sub(r"[^A-Z]", "", unicodedata.normalize("NFD", s).upper())


NOMES_N = [norm(n) for n in NOMES if len(norm(n)) >= 10]


def confere(nome, ok, detalhe=""):
    print(("OK   " if ok else "FALHA"), nome, ("| " + str(detalhe)) if detalhe != "" else "")
    if not ok: falhas.append(nome)


def nomes_em(texto):
    t = norm(texto); return [n for n in NOMES_N if n in t]


# ---------- 1. arquivos publicados ----------
print(f"{len(NOMES)} nomes de servidores conhecidos (lotação + produção)")
publicados = sorted(f for f in SITE.iterdir() if f.is_file())
print("arquivos em site/:", [f.name for f in publicados])
for f in publicados:
    t = f.read_text("utf-8", errors="ignore")
    confere(f"sem nome de servidor em site/{f.name}", not nomes_em(t), len(nomes_em(t)) or "")
    if f.name != "nominal.js":
        confere(f"sem sequência de 11+ dígitos em site/{f.name}", not re.search(r"(?<![0-9.])[0-9]{11,}", t))
pj = (SITE / "painel.js").read_text("utf-8")
confere("painel.js sem campos nominais (prof, mat, cns, cargo, chs)", not re.search(r'"(prof|mat|cns|cargo|chs|nome_rh)":', pj))
confere("senha não está escrita em nenhum arquivo de site/", all(senha() not in f.read_text("utf-8", errors="ignore") for f in publicados))
# o bloco cifrado abre com a senha e não traz CNS/CPF
NJ = json.loads((SITE / "nominal.js").read_text("utf-8").removeprefix("window.NOMINAL=").removesuffix(";"))
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
chave = hashlib.pbkdf2_hmac("sha256", unicodedata.normalize("NFC", senha()).encode(), base64.b64decode(NJ["sal"]), NJ["it"], 32)
claro = json.loads(gzip.decompress(AESGCM(chave).decrypt(base64.b64decode(NJ["iv"]), base64.b64decode(NJ["ct"]), b"aps-norte-v1")))
confere("bloco cifrado abre com a senha", len(claro["prof"]) > 100, f"{len(claro['prof'])} equipes, {NJ['it']} iterações")
ct = json.dumps(claro, ensure_ascii=False)
confere("bloco cifrado sem campo de CNS/CPF", not re.search(r'"(cns|cpf)":', ct))
confere("ids de profissional sequenciais (nada derivado do CNS)", all(re.fullmatch(r"p\d+", p["id"]) for l in claro["prof"].values() for p in l))
try:
    AESGCM(hashlib.pbkdf2_hmac("sha256", b"senha-errada-000000", base64.b64decode(NJ["sal"]), NJ["it"], 32)).decrypt(base64.b64decode(NJ["iv"]), base64.b64decode(NJ["ct"]), b"aps-norte-v1"); confere("senha errada não abre o bloco", False)
except Exception: confere("senha errada não abre o bloco", True)
# arquivos versionados no git (o que iria para o repositório público)
vers = subprocess.run(["git", "ls-files"], cwd=RAIZ, capture_output=True, text=True).stdout.split()
com_nome = [f for f in vers if (RAIZ / f).exists() and nomes_em((RAIZ / f).read_text("utf-8", errors="ignore"))]
print("  arquivos versionados com nomes:", com_nome or "nenhum", "(coleta/referencia.json sai do repositório público no plano de publicação)")
confere("nenhum arquivo versionado com nomes além do referencia.json", not [f for f in com_nome if f != "coleta/referencia.json"])


def abrir_tudo(pg):
    for _ in range(6):
        n = pg.evaluate("() => { let n = 0; document.querySelectorAll('details.caixa:not([open])').forEach(d => { d.open = true; n++; }); return n; }")
        pg.wait_for_timeout(700)
        if not n: break
    pg.evaluate("() => document.querySelectorAll('button.btn-sec[aria-expanded=false]').forEach(b => b.click())"); pg.wait_for_timeout(300)


def html_de_todas_as_abas(pg):
    out = []
    for aba in ["h", "c", "m", "p", "x", "r", "u"]:
        if aba == "c": pg.click("#aba-h"); pg.click("#f-barra .abrir-cmp")
        else: pg.click("#aba-" + aba)
        pg.wait_for_timeout(350)
        if aba == "h": abrir_tudo(pg)
        out.append(pg.evaluate("() => document.documentElement.outerHTML"))
    pg.click("#aba-h"); return "\n".join(out)


with sync_playwright() as p:
    nav = p.chromium.launch(channel="chrome", headless=True); ctx = nav.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True); pg = ctx.new_page()
    pg.on("console", lambda m: erros.append(m.text) if m.type == "error" else None); pg.on("pageerror", lambda e: erros.append(str(e)))
    # ---------- 2. sem senha ----------
    pg.goto(URL); pg.wait_for_selector("#arvore details.g")
    confere("botão Entrar visível", pg.locator("#btn-entrar").is_visible() and pg.inner_text("#btn-entrar") == "Entrar")
    confere("bloco nominal nem é baixado antes de entrar", pg.evaluate("() => typeof window.NOMINAL") == "undefined")
    h = html_de_todas_as_abas(pg); a = nomes_em(h)
    confere("sem senha: nenhum nome em nenhuma aba (árvore toda aberta)", not a, f"{len(a)} nomes" if a else f"{len(h) // 1000000} milhões de caracteres conferidos")
    confere("sem senha: equipes abertas", pg.locator("details.e[open]").count() > 150, pg.locator("details.e[open]").count())
    confere("sem senha: aviso de acesso restrito no lugar da tabela", pg.locator(".restrito-nota").count() > 150 and pg.locator("button.pess").count() == 0)
    acs = [x for x in P["alertas"] if x["tipo"] == "ACS sem visita"]
    confere("sem senha: alerta de ACS só com a contagem", all(re.fullmatch(r"\d+ de \d+ ACS lotados sem visita registrada em \d{4}-\d{2}", x["texto"]) for x in acs), f"{len(acs)} alertas")
    pg.select_option("#f-alerta", "acs"); pg.wait_for_timeout(900); h_f = pg.evaluate("() => document.documentElement.outerHTML")
    confere("sem senha: filtro de ACS ligado, etiquetas sem nomes", pg.locator("#arvore details.e").count() == len(acs) and not nomes_em(h_f), f"{len(acs)} equipes")
    pg.select_option("#f-alerta", ""); pg.wait_for_timeout(300)
    alvo = next(p_ for l in N["prof"].values() for p_ in l if p_["lotado"] and p_["serie"].get("atend"))
    pg.fill("#busca", " ".join(alvo["nome"].split()[:2])); pg.wait_for_timeout(500)
    confere("sem senha: busca por nome não acha servidor", "Profissional" not in pg.inner_text("#achados"), pg.inner_text("#achados")[:40].replace("\n", " "))
    pg.fill("#busca", ""); pg.select_option("#sel-ind", "atend")
    with pg.expect_download() as d: pg.click("#btn-csv")
    csv = pathlib.Path(d.value.path()).read_text("utf-8-sig", errors="ignore")
    confere("sem senha: CSV sem coluna de profissional e sem nomes", "Profissional" not in csv.splitlines()[0] and not nomes_em(csv), csv.splitlines()[0][:60])
    confere("sem senha: nada guardado no navegador", pg.evaluate("() => localStorage.length") == 0)
    # ---------- 3. senha errada ----------
    pg.click("#btn-entrar"); pg.fill("#senha", "senha-errada-000000"); pg.click("#senha-ok"); pg.wait_for_selector("#senha-erro:not([hidden])", timeout=30000)
    confere("senha errada: mensagem clara", pg.inner_text("#senha-erro") == "Senha incorreta.", pg.inner_text("#senha-erro"))
    confere("senha errada: continua fechado e sem nomes", not pg.evaluate("() => document.body.classList.contains('aberto')") and not nomes_em(pg.evaluate("() => document.documentElement.outerHTML")))
    pg.screenshot(path=str(RAIZ / "testes" / "_dicas" / "senha_errada.png"))
    pg.click("#senha-cancelar")
    # ---------- 4. senha certa (com lembrar) ----------
    entrar(pg, lembrar=True)
    confere("senha certa: botão vira Sair", pg.inner_text("#btn-entrar") == "Sair")
    for i in ("g0", "g0u0", "g0u0e0"):   # abre só o que estiver fechado (a página mantém abertas as caixas que já estavam)
        if pg.locator("#" + i).get_attribute("open") is None: pg.locator(f"#{i} > summary").click(); pg.wait_for_timeout(300)
    pg.wait_for_selector("#g0u0e0 button.pess")
    confere("senha certa: tabela de profissionais de volta", pg.locator("#g0u0e0 button.pess").count() > 0, pg.locator("#g0u0e0 button.pess").count())
    pg.fill("#busca", " ".join(alvo["nome"].split()[:2])); pg.wait_for_selector("#achados button[data-i]")
    confere("senha certa: busca por nome acha o servidor", "Profissional" in pg.inner_text("#achados"))
    pg.locator("#achados button[data-i]").first.click(); pg.wait_for_selector("dialog#ficha[open]")
    confere("senha certa: ficha do servidor abre", bool(pg.inner_text("#ficha-t").strip())); pg.click("#ficha-x"); pg.fill("#busca", "")
    pg.select_option("#f-alerta", "acs"); pg.wait_for_timeout(900)
    txt_al = pg.evaluate("() => [...document.querySelectorAll('#arvore .sinais .chip')].map(c => c.getAttribute('title') || c.dataset.dica || '').join(' | ')"); pg.select_option("#f-alerta", "")
    confere("senha certa: etiquetas de ACS trazem os nomes no detalhe", (not acs) or bool(nomes_em(txt_al)))
    pg.click("#aba-h")
    with pg.expect_download() as d: pg.click("#btn-csv")
    csv = pathlib.Path(d.value.path()).read_text("utf-8-sig", errors="ignore")
    confere("senha certa: CSV com coluna de profissional", "Profissional" in csv.splitlines()[0])
    guardado = pg.evaluate("() => localStorage.getItem('aps_norte_chave')")
    confere("lembrar: guarda a chave derivada, não a senha", bool(guardado) and senha() not in guardado and pg.evaluate("() => localStorage.length") == 1)
    pg.reload(); pg.wait_for_selector("body.aberto", timeout=30000)
    confere("lembrar: reabre sozinho ao recarregar", True)
    pg.click("#btn-entrar"); pg.wait_for_load_state("load"); pg.wait_for_selector("#arvore details.g"); pg.wait_for_timeout(800)
    confere("Sair: fecha, esquece a chave e some com os nomes", not pg.evaluate("() => document.body.classList.contains('aberto')") and pg.evaluate("() => localStorage.length") == 0
            and not nomes_em(pg.evaluate("() => document.documentElement.outerHTML")))
    # ---------- 5. celular ----------
    m = ctx.new_page(); m.set_viewport_size({"width": 390, "height": 800}); m.on("pageerror", lambda e: erros.append(str(e)))
    m.goto(URL); m.wait_for_selector("#arvore details.g"); m.click("#btn-entrar"); m.wait_for_selector("#dlg-senha[open]")
    cx = m.evaluate("() => { const r = document.getElementById('dlg-senha').getBoundingClientRect(); return [r.left, r.right, r.top, r.bottom]; }")
    confere("celular: janela da senha cabe na tela", cx[0] >= 0 and cx[1] <= 390 and cx[2] >= 0 and cx[3] <= 800, [round(v) for v in cx])
    m.screenshot(path=str(RAIZ / "testes" / "_dicas" / "senha_celular.png"))
    m.fill("#senha", senha()); m.click("#senha-ok"); m.wait_for_selector("body.aberto", timeout=30000)
    confere("celular: entra e não cria rolagem lateral", m.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 1)
    confere("celular: sem lembrar, nada fica guardado", m.evaluate("() => localStorage.length") == 0)
    nav.close()
print("erros de console:", erros or "nenhum")
if falhas or erros: print("FALHAS:", falhas); sys.exit(1)
print("RESULTADO: tudo certo")
