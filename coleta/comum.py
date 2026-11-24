"""Pedaços que os scripts de coleta e o montar.py usavam em cópia: pastas, teto de linhas, endereços dos painéis,
data de Brasília e o filtro de mês do Power BI. Um lugar só, para as cópias não divergirem."""
import datetime as dt
import json
import pathlib

from pbi_lib import col, em, lit_int, lit_txt

AQUI = pathlib.Path(__file__).parent
RAIZ = AQUI.parent
OUT = RAIZ / "dados" / "brutos"; OUT.mkdir(parents=True, exist_ok=True)
TETO = 30000     # limite de linhas pedido por consulta: resposta desse tamanho pode estar cortada, então a coleta para
BRT = dt.timezone(dt.timedelta(hours=-3))      # Brasília (sem horário de verão); no GitHub o relógio é UTC
URL = {i["titulo"]: i["url"] for i in json.load(open(AQUI / "paineis_aps.json", encoding="utf-8"))}


def hoje_brt():
    """Data de hoje em Brasília: o mês corrente não pode virar o seguinte às 21h só porque o relógio do GitHub é UTC."""
    return dt.datetime.now(BRT).date()


def mes_where(alias, c_ano, c_mes, a, m, inteiro=False):
    """Filtro de ano e mês; as colunas são texto ('2026', '03') na maioria das tabelas e inteiro nas demais."""
    if inteiro: return [em(col(alias, c_ano), [lit_int(a)]), em(col(alias, c_mes), [lit_int(m)])]
    return [em(col(alias, c_ano), [lit_txt(str(a))]), em(col(alias, c_mes), [lit_txt(str(m).zfill(2))])]


def lit_dt(a, m):
    """Literal de data (1º dia do mês) para colunas de data do Power BI."""
    return {"Literal": {"Value": f"datetime'{a}-{m:02d}-01T00:00:00'"}}
