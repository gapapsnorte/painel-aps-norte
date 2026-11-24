"""Monta coleta/referencia.json a partir da planilha oficial de RH: CNES -> UBS/GSAP, INE -> equipe, lotação por equipe.

Uso: python -X utf8 montar_referencia.py "<planilha.xlsx>" referencia.json ["<nome da aba>"]

Só entra o que o painel usa. Da pessoa: nome, categoria, cargo, carga horária, vínculo e o CNS EMBARALHADO
(sigilo.hc), que serve apenas para ligar a lotação à produção do InfoSaúde. CPF, matrícula, observações e
qualquer outra coluna da planilha NÃO são lidos: o script pega as colunas pelo nome, uma a uma (COLUNAS).
"""
import json
import pathlib
import re
import sys
from collections import Counter, defaultdict

import openpyxl

from sigilo import hc

ABA_PADRAO = "RH APS Norte"
CHS_MAXIMA = 60     # acima disso é erro de digitação; fica sem carga horária
# campo do painel -> título da coluna na planilha (os títulos são os da planilha, inclusive com erro de grafia)
COLUNAS = {
    "cnes": "CNES",
    "ubs": "Unidade de Saúde (CNES - Nome Fantasia)",
    "ra": "Região Adminstrativa",
    "gerencia": "Diretoria/Gerência/Núcleo",
    "ine": "INE da equipe",
    "equipe": "Equipe (CNES)/Setor na UBS",
    "tipo": "Tipo de Equipe",
    "situacao": "Situação da equipe",
    "zona": "Urbana/Rural",
    "cns": "CNS",
    "nome": "Nome Completo",
    "cat": "Categoria Provimento",
    "cargo": "Cargo - SIGRH",
    "vinculo": "Vínculo",
    "chs": "CHS de Lotação",
}


def gsap_curta(gerencia):
    """'Gerência de Serviços de Atenção Primária Nº 3 de Planaltina' -> 'GSAP 3 Planaltina'."""
    texto = str(gerencia or "")
    m = re.search(r"N[ºo°]?\s*(\d+)\s+de\s+(.+)$", texto, re.I)
    return f"GSAP {m.group(1)} {m.group(2).strip()}" if m else texto.strip()


def ine_da_equipe(valor):
    """INE com 10 dígitos; '' para setor sem equipe (a planilha traz 'N/A', vazio ou zero)."""
    texto = str(valor or "").strip()
    if not texto.replace(".0", "").isdigit() or int(float(texto)) <= 0:
        return ""
    return texto.split(".")[0].zfill(10)


def so_texto(valor):
    """Só texto com letras. Número solto num campo de texto é descartado: a planilha já trouxe um número de
    11 dígitos (com cara de CPF) digitado na coluna Vínculo."""
    return valor.strip() if isinstance(valor, str) and re.search(r"[A-Za-zÀ-ú]", valor) else None


def carga_horaria(valor):
    return valor if isinstance(valor, (int, float)) and 0 < valor <= CHS_MAXIMA else None


def ler_planilha(arquivo, aba):
    """Devolve as linhas como dicionários, só com as colunas de COLUNAS."""
    ws = openpyxl.load_workbook(arquivo, read_only=True, data_only=True)[aba]
    linhas = ws.iter_rows(values_only=True)
    cabecalho = [str(c).strip() if c else "" for c in next(linhas)]
    faltam = [titulo for titulo in COLUNAS.values() if titulo not in cabecalho]
    if faltam:
        raise SystemExit(f"A aba '{aba}' não tem a(s) coluna(s): {', '.join(faltam)}. A planilha mudou de formato?")
    posicao = {campo: cabecalho.index(titulo) for campo, titulo in COLUNAS.items()}
    for linha in linhas:
        yield {campo: linha[i] if i < len(linha) else None for campo, i in posicao.items()}


def montar(arquivo, aba):
    ubs, equipes, lotacao = {}, {}, defaultdict(list)
    descartes = Counter()
    for r in ler_planilha(arquivo, aba):
        if not r["cnes"]:
            continue
        cnes = str(int(r["cnes"])).zfill(7)      # a planilha perde os zeros à esquerda
        ine = ine_da_equipe(r["ine"])
        ubs.setdefault(cnes, {"cnes": cnes, "nome_rh": r["ubs"], "ra": r["ra"], "gsap": gsap_curta(r["gerencia"])})
        if ine:
            equipes.setdefault(ine, {"ine": ine, "cnes": cnes, "nome": r["equipe"], "tipo": r["tipo"],
                                     "situacao": r["situacao"], "zona": r["zona"]})
        chs = carga_horaria(r["chs"])
        if r["chs"] not in (None, "") and chs is None:
            descartes["carga horária fora de 1 a 60 h (ficou sem carga)"] += 1
        if not r["cns"]:
            descartes["sem CNS (liga à produção só pelo nome)"] += 1
        # quem está na UBS sem equipe fica sob a chave "UBS:<cnes>"
        lotacao[ine or f"UBS:{cnes}"].append({
            "nome": so_texto(r["nome"]) or "", "cat": so_texto(r["cat"]), "cargo": so_texto(r["cargo"]),
            "chs": chs, "vinculo": so_texto(r["vinculo"]), "cns": hc(int(r["cns"])) if r["cns"] else "",
        })
    return {"fonte": f"{pathlib.Path(arquivo).name}, aba {aba}", "ubs": ubs, "equipes": equipes, "lotacao": lotacao}, descartes


def resumo(ref, descartes):
    """Conferência na tela: só contagens e nomes de unidades, nenhum nome de pessoa."""
    pessoas = [p for lista in ref["lotacao"].values() for p in lista]
    print(len(ref["ubs"]), "UBS |", len(ref["equipes"]), "equipes |", len(pessoas), "profissionais")
    print("GSAPs:", dict(Counter(u["gsap"] for u in ref["ubs"].values())))
    print("tipos de equipe:", dict(Counter(e["tipo"] for e in ref["equipes"].values())))
    print("categorias:", Counter(p["cat"] for p in pessoas).most_common(12))
    for gsap in sorted({u["gsap"] for u in ref["ubs"].values()}):
        print(" ", gsap, "->", sorted(u["nome_rh"] for u in ref["ubs"].values() if u["gsap"] == gsap))
    for motivo, n in descartes.items():
        print(f"atenção: {n} linha(s) {motivo}")


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    arquivo, saida = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    aba = sys.argv[3] if len(sys.argv) > 3 else ABA_PADRAO
    ref, descartes = montar(arquivo, aba)
    saida.write_text(json.dumps(ref, ensure_ascii=False, indent=1, default=str), "utf-8")
    resumo(ref, descartes)


if __name__ == "__main__":
    main()
