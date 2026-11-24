"""Teste sintético do decodificador do Power BI (sem rede). Sai com código diferente de 0 se algo falhar.
Uso (de dentro de coleta/): python -X utf8 teste_pbi_lib.py"""
import sys
from pbi_lib import decodificar


def resposta(linhas, dicts, schema):
    """Monta o formato DSR mínimo que decodificar() lê."""
    dm = [{"S": schema, **linhas[0]}] + linhas[1:]
    return {"results": [{"result": {"data": {"dsr": {"DS": [{"ValueDicts": dicts, "PH": [{"DM0": dm}]}]}}}}]}


def teste_dicionario_de_inteiros_com_repeticao():
    """Valor repetido (bit R) não pode ser decodificado duas vezes: com D0=[1,0,3] o índice 1 vira 0 uma vez só."""
    js = resposta([{"C": [1, 7]}, {"R": 1, "C": [8]}], {"D0": [1, 0, 3]}, [{"DN": "D0"}, {}])
    obtido = decodificar(js, ["a", "b"])
    esperado = [{"a": 0, "b": 7}, {"a": 0, "b": 8}]
    assert obtido == esperado, f"{obtido} != {esperado}"


def teste_dicionario_de_texto_com_repeticao_e_nulo():
    js = resposta([{"C": [0, 5]}, {"R": 1, "C": [6]}, {"C": [1], "R": 2}, {"Ø": 1, "C": [2]}], {"D0": ["Região Norte", "Região Sul", "Região Leste"]}, [{"DN": "D0"}, {}])
    obtido = decodificar(js, ["reg", "n"])
    esperado = [{"reg": "Região Norte", "n": 5}, {"reg": "Região Norte", "n": 6},
                {"reg": "Região Sul", "n": 6}, {"reg": None, "n": 2}]
    assert obtido == esperado, f"{obtido} != {esperado}"


def teste_consulta_vazia():
    js = {"results": [{"result": {"data": {"dsr": {"DS": [{}]}}}}]}
    assert decodificar(js, ["a"]) == []


if __name__ == "__main__":
    falhas = 0
    for nome, fn in sorted(globals().items()):
        if nome.startswith("teste_") and callable(fn):
            try:
                fn(); print("ok  ", nome)
            except AssertionError as e:
                falhas += 1; print("FALHOU", nome, e)
    sys.exit(1 if falhas else 0)
