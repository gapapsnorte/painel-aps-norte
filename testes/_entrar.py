"""Apoio aos testes: senha da área dos gestores e entrada na página.
A senha vem da variável APS_SENHA ou de coleta/senha.local (fora do git); nunca fica escrita nos testes."""
import os, pathlib

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def senha():
    s = os.environ.get("APS_SENHA")
    if not s:
        f = RAIZ / "coleta" / "senha.local"
        if f.exists(): s = f.read_text(encoding="utf-8")
    s = (s or "").strip()
    if not s: raise SystemExit("Defina APS_SENHA ou crie coleta/senha.local com a mesma senha usada no montar.py.")
    return s


def entrar(pg, lembrar=False):
    pg.wait_for_selector("#btn-entrar"); pg.click("#btn-entrar"); pg.wait_for_selector("#dlg-senha[open]")
    pg.fill("#senha", senha())
    if lembrar: pg.check("#senha-lembrar")
    pg.click("#senha-ok"); pg.wait_for_selector("body.aberto", timeout=30000)


def planilha(caminho):
    """Linhas de uma planilha .xlsx baixada da página (células vazias viram ""), conferindo que o arquivo abre."""
    import openpyxl, warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore"); ws = openpyxl.load_workbook(open(caminho, "rb")).active   # o arquivo baixado pelo teste não tem extensão
    return [["" if c is None else c for c in l] for l in ws.iter_rows(values_only=True)]
def planilha_txt(caminho): return chr(10).join(";".join(str(c) for c in l) for l in planilha(caminho))
