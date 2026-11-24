"""Embaralhamento do CNS dos profissionais: ponto único usado pela coleta, pela referência do RH e pelo montar.

O CNS real nunca é gravado em disco. Ele só serve para ligar a lotação (planilha de RH) à produção
(InfoSaúde), e para isso basta que os dois lados apliquem a mesma função. O segredo (pepper) impede
que alguém refaça a tabela CNS -> código a partir de uma lista de CNS.

Segredo: variável de ambiente APS_PEPPER (GitHub Actions) ou arquivo coleta/pepper.local (computador).
"""
import hashlib
import os
import pathlib
import re

_ARQUIVO = pathlib.Path(__file__).parent / "pepper.local"
_TAMANHO = 12                                   # caracteres hexadecimais guardados
_RE_CODIGO = re.compile(rf"[0-9a-f]{{{_TAMANHO}}}")
_pepper = None


def pepper():
    """Lê o segredo uma vez; sem ele nada é gravado (melhor parar do que guardar CNS em claro)."""
    global _pepper
    if _pepper is None:
        valor = os.environ.get("APS_PEPPER", "").strip()
        if not valor and _ARQUIVO.exists():
            valor = _ARQUIVO.read_text(encoding="utf-8-sig").strip()
        if not valor:
            raise SystemExit("Falta o segredo APS_PEPPER (variável de ambiente, ou arquivo coleta/pepper.local).")
        _pepper = valor
    return _pepper


def hc(cns):
    """CNS -> código de 12 caracteres. Vazio continua vazio; código já embaralhado passa direto."""
    texto = str(cns or "").strip()
    if not texto:
        return ""
    if _RE_CODIGO.fullmatch(texto):
        return texto
    return hashlib.sha256(f"{pepper()}|{texto}".encode()).hexdigest()[:_TAMANHO]


def embaralhar_linhas(linhas, campo="cns"):
    """Troca, no lugar, o CNS de cada linha pelo código. Devolve a própria lista."""
    for linha in linhas:
        if linha.get(campo):
            linha[campo] = hc(linha[campo])
    return linhas


def parece_cns(valor):
    """Verdadeiro para um número de 15 dígitos (CNS em claro)."""
    return bool(re.fullmatch(r"\d{15}", str(valor or "").strip()))
