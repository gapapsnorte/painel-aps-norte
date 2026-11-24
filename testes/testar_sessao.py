"""Sessão da área dos gestores e CSV seguro: senha errada x arquivo que não abre, chave lembrada, "Sair" em várias abas,
nada nominal no DOM depois de sair, CSV sem texto que o Excel leia como fórmula.
Uso: python -X utf8 testes/testar_sessao.py (a senha vem de coleta/senha.local; não imprime nomes nem a senha)."""
import csv, io, json, pathlib, sys
from playwright.sync_api import sync_playwright
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _entrar import entrar, esperar, senha

RAIZ = pathlib.Path(__file__).resolve().parent.parent
URL = (RAIZ / "site" / "index.html").as_uri()
NOMINAL_JS = (RAIZ / "site" / "nominal.js").read_text("utf-8")
NOM = json.loads((RAIZ / "dados" / "nominal.json").read_text(encoding="utf-8"))
# amostra de nomes lida só em memória: sem aspas, &, < ou > (que o HTML escreveria de outro jeito)
NOMES = sorted({p["nome"] for ps in NOM["prof"].values() for p in ps if p["nome"] and not set(p["nome"]) & set("&<>\"'")})[:400:4]
CHAVE = "aps_norte_chave"
MSG_SENHA = "Senha incorreta."
falhas, erros = [], []


def conf(nome, ok, det=""):
    print(("OK   " if ok else "FALHA"), nome, ("| " + str(det)) if det != "" else "")
    if not ok: falhas.append(nome)


def nova(ctx):
    pg = ctx.new_page(); pg.set_viewport_size({"width": 1280, "height": 900})
    pg.on("console", lambda m: erros.append(f"console.{m.type}: {m.text}") if m.type in ("error", "warning") else None)
    pg.on("pageerror", lambda e: erros.append(f"pageerror: {e}"))
    pg.goto(URL); pg.wait_for_selector("#arvore details.g")
    return pg


def tem_area(pg): return pg.evaluate("() => document.body.classList.contains('aberto')")
def chave(pg): return pg.evaluate(f"() => localStorage.getItem('{CHAVE}')")
def nomes_no_dom(pg): return pg.evaluate("n => { const h = document.documentElement.outerHTML; return n.filter(x => h.includes(x)).length; }", NOMES)


def tentar_senha(pg, valor):
    pg.click("#btn-entrar"); pg.wait_for_selector("#dlg-senha[open]")
    pg.fill("#senha", valor); pg.click("#senha-ok")
    esperar(pg, "() => !document.querySelector('#senha-ok').disabled")
    return pg.inner_text("#senha-erro").strip() if pg.locator("#senha-erro").is_visible() else ""


def servir(corpo): return lambda rota, _req: rota.fulfill(status=200, content_type="application/javascript", body=corpo)
def fragmento_inicial(js): return js[: max(80, len(js) // 3)]   # arquivo cortado no meio: JavaScript inválido


with sync_playwright() as p:
    nav = p.chromium.launch(channel="chrome", headless=True)

    # ---------------- (a) senha errada
    ctx = nav.new_context(accept_downloads=True); pg = nova(ctx)
    msg = tentar_senha(pg, senha() + "x")
    conf("(a) senha errada: mensagem de senha incorreta e a área continua fechada", msg == MSG_SENHA and not tem_area(pg), msg)
    conf("(a) senha errada: nada gravado no navegador", chave(pg) is None)
    ctx.close()

    # ---------------- (b) arquivo restrito que não abre: outra mensagem, e a chave lembrada fica
    ctx = nav.new_context(accept_downloads=True); pg = nova(ctx); entrar(pg, lembrar=True)
    guardada = chave(pg); conf("(b) pré-condição: entrou lembrando", bool(guardada) and tem_area(pg))
    pg.close()
    for rot, corpo in (("truncado", fragmento_inicial(NOMINAL_JS)), ("sem os campos da cifra", 'window.NOMINAL = {"v": 1};')):
        ctx.route("**/nominal.js*", servir(corpo))
        pg = nova(ctx); pg.wait_for_timeout(2000)
        conf(f"(b) arquivo {rot}, página aberta com a chave lembrada: não entra e a chave NÃO é apagada", not tem_area(pg) and chave(pg) == guardada)
        msg = tentar_senha(pg, senha())
        conf(f"(b) arquivo {rot}, entrando com a senha certa: mensagem de 'não foi possível', diferente da de senha", msg.startswith("Não foi possível") and msg != MSG_SENHA and not tem_area(pg), msg[:60])
        conf(f"(b) arquivo {rot}: a chave lembrada continua guardada", chave(pg) == guardada)
        pg.close(); ctx.unroute("**/nominal.js*")
    # a falha de autenticação (chave lembrada que já não serve) continua apagando a chave
    pg = nova(ctx); pg.evaluate(f"() => localStorage.setItem('{CHAVE}', JSON.stringify({{k: btoa('x'.repeat(32)), t: Date.now()}}))")
    pg.reload(); pg.wait_for_selector("#arvore details.g"); pg.wait_for_timeout(2500)
    conf("(b) chave lembrada que não autentica (senha trocada): não entra e é apagada", not tem_area(pg) and chave(pg) is None)
    ctx.close()

    erros.clear()   # o JavaScript cortado de propósito em (b) gera erros de página esperados
    # ---------------- entrar sem "lembrar" apaga a chave lembrada de uma entrada anterior
    ctx = nav.new_context(accept_downloads=True); pg = nova(ctx)
    pg.evaluate(f"() => localStorage.setItem('{CHAVE}', JSON.stringify({{k: 'AAAA', t: Date.now()}}))")
    entrar(pg, lembrar=False)
    conf("(S4) entrar sem marcar 'lembrar' apaga a chave lembrada de antes", tem_area(pg) and chave(pg) is None)
    ctx.close()

    # ---------------- (c) Sair numa aba fecha a área nas outras, sem recarregar à mão
    ctx = nav.new_context(accept_downloads=True); a = nova(ctx); entrar(a, lembrar=True)
    b = nova(ctx); esperar(b, "() => document.body.classList.contains('aberto')")
    conf("(c) a segunda aba abre sozinha com a chave lembrada", tem_area(a) and tem_area(b))
    b.click("#aba-i"); b.wait_for_selector("#vista-i:not([hidden])")
    conf("(d) com a área aberta há nomes no DOM (a amostra é detectável)", nomes_no_dom(b) > 0, f"{nomes_no_dom(b)} de {len(NOMES)}")
    a.click("#btn-entrar")   # Sair
    esperar(b, "() => !document.body.classList.contains('aberto')", timeout=15000)
    a.wait_for_selector("#arvore details.g"); a.wait_for_timeout(500)
    conf("(c) Sair na 1ª aba: a 2ª perde a área nominal sem ninguém recarregar", not tem_area(b) and not tem_area(a))
    conf("(c) a chave lembrada foi apagada", chave(a) is None)
    b.wait_for_selector("#arvore details.g")
    conf("(c) a aba Inconsistências da 2ª aba não fica aberta", not b.locator("#vista-i").is_visible())
    # ---------------- (d) nada nominal sobra
    for rot, pgx in (("aba onde clicou em Sair", a), ("outra aba", b)):
        mem = pgx.evaluate("() => ({ inc: (NOM.incons || []).length, prof: P.gsaps.reduce((s, g) => s + g.ubs.reduce((t, u) => t + u.equipes.reduce((r, e) => r + e.prof.length, 0), 0), 0), ficha: !!document.querySelector('#ficha[open]'), rel: document.querySelector('#rel-print').innerHTML.length })")
        conf(f"(d) {rot}: nenhum nome de profissional no DOM", nomes_no_dom(pgx) == 0, f"{nomes_no_dom(pgx)} de {len(NOMES)}")
        conf(f"(d) {rot}: estruturas nominais vazias, sem ficha aberta nem relatório em preparo", mem == {"inc": 0, "prof": 0, "ficha": False, "rel": 0}, mem)
    ctx.close()

    # ---------------- (e) CSV sem texto que o Excel leia como fórmula
    ctx = nav.new_context(accept_downloads=True); pg = nova(ctx); entrar(pg)
    unit = pg.evaluate("() => ({ a: textoCsv('=1+1'), b: textoCsv('+1'), c: textoCsv('-x'), d: textoCsv('@x'), e: textoCsv('\\tx'), f: textoCsv(-5), g: textoCsv('abc'), h: textoCsv(null), i: textoCsv(37.5) })")
    conf("(e) textoCsv: texto perigoso ganha apóstrofo; número, texto comum e vazio ficam como estão",
         unit == {"a": "'=1+1", "b": "'+1", "c": "'-x", "d": "'@x", "e": "'\tx", "f": "-5", "g": "abc", "h": "", "i": "37.5"}, unit)

    def celulas(sel):
        with pg.expect_download() as d: pg.click(sel)
        txt = pathlib.Path(d.value.path()).read_text(encoding="utf-8-sig")
        return [c for l in csv.reader(io.StringIO(txt), delimiter=";") for c in l]

    def perigosas(cels): return [c for c in cels if c[:1] in ("=", "+", "@", "\t", "\r")]
    pg.evaluate("() => { NOM.incons[0].nome = '=1+1'; NOM.incons[0].det = '@SOMA(1)'; }")
    pg.click("#aba-i"); pg.wait_for_selector("#vista-i:not([hidden])"); pg.wait_for_timeout(300)
    pg.fill("#i-q", ""); pg.evaluate("() => { is.q = ''; is.tipo = ''; renderIncons(); }")
    c1 = celulas("#i-csv-txt")
    conf("(e) CSV das inconsistências: nenhuma célula começa com = + @", not perigosas(c1) and "'=1+1" in c1 and "'@SOMA(1)" in c1, f"{len(c1)} células")
    c2 = celulas("#vista-i .btn-prov + .em-csv")
    conf("(e) CSV de providências: nenhuma célula começa com = + @", not perigosas(c2) and "'=1+1" in c2, f"{len(c2)} células")
    pg.click("#aba-h"); pg.wait_for_timeout(250)
    c3 = celulas("#btn-csv-txt")
    conf("(e) CSV do indicador: nenhuma célula começa com = + @, e os números continuam números", not perigosas(c3) and any(c.replace(".", "").isdigit() for c in c3), f"{len(c3)} células")
    conf("(e) nenhuma célula de texto começa com '-' (só números negativos legítimos)", all(c[:1] != "-" or c[1:].replace(".", "", 1).replace(",", "", 1).isdigit() for c in c1 + c2 + c3))
    ctx.close()

    conf("sem erro de console nem de página", not erros, "; ".join(erros[:3]))
    nav.close()

print("\n" + ("TUDO OK" if not falhas else f"{len(falhas)} FALHA(S): " + "; ".join(falhas)))
sys.exit(1 if falhas else 0)
