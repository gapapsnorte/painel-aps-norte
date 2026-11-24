"""Biblioteca mínima para ler painéis públicos do Power BI do InfoSaúde."""
import base64, json, re, time
import requests

BASE = "https://wabi-brazil-south-api.analysis.windows.net/public/reports"
S = requests.Session(); S.headers["User-Agent"] = "Mozilla/5.0 (painel GAPAPS Norte)"


def com_tentativas(fn, tentativas=3, espera=5):
    """Chama fn até `tentativas` vezes, esperando `espera` s entre elas; falha transitória do InfoSaúde não derruba a rodada."""
    for t in range(tentativas):
        try:
            return fn()
        except Exception:
            if t == tentativas - 1: raise
            time.sleep(espera)


class Painel:
    def __init__(self, url_infosaude, tentativas=3):
        com_tentativas(lambda: self._abrir(url_infosaude), tentativas)

    def _abrir(self, url_infosaude):
        pg = S.get(url_infosaude, timeout=60).text
        m = re.search(r'src="https://app\.powerbi\.com/view\?r=([^"&]+)', pg)
        if not m:
            raise RuntimeError(f"iframe do Power BI não encontrado em {url_infosaude} (a página mudou?)")
        r = m.group(1)
        cfg = json.loads(base64.b64decode(r + "=" * (-len(r) % 4)))
        self.k = cfg["k"]
        self.H = {"X-PowerBI-ResourceKey": self.k, "Content-Type": "application/json", "Accept": "application/json"}
        self.base = BASE
        for cl in ("wabi-brazil-south-api", "wabi-south-central-us-api", "wabi-brazil-south-redirect", "wabi-us-east2-api", "wabi-us-north-central-api"):
            self.base = f"https://{cl}.analysis.windows.net/public/reports"
            resp = S.get(f"{self.base}/{self.k}/modelsAndExploration?preferReadOnlySession=true", headers=self.H, timeout=120)
            if resp.ok: break
        if not resp.ok:
            raise RuntimeError(f"modelsAndExploration falhou: HTTP {resp.status_code}")
        self.me = resp.json()
        m = self.me["models"][0]
        self.model_id, self.db = m["id"], m["dbName"]
        self.report_id = self.me["exploration"].get("reportId") or self.me["exploration"].get("id")

    def consulta(self, entidades, select, where=None, limite=100000, tentativas=3):
        """entidades: {alias: Entity}; select: [(nome, expr)]; where: lista de Conditions. Repete a consulta se falhar."""
        return com_tentativas(lambda: self._consultar(entidades, select, where, limite), tentativas)

    def _consultar(self, entidades, select, where, limite):
        sq = {"Version": 2,
              "From": [{"Name": a, "Entity": e, "Type": 0} for a, e in entidades.items()],
              "Select": [dict(expr, Name=name) for name, expr in select]}
        if where: sq["Where"] = where
        body = {"version": "1.0.0", "cancelQueries": [], "modelId": self.model_id,
                "queries": [{"Query": {"Commands": [{"SemanticQueryDataShapeCommand": {
                    "Query": sq,
                    "Binding": {"Primary": {"Groupings": [{"Projections": list(range(len(select)))}]},
                                "DataReduction": {"DataVolume": 4, "Primary": {"Window": {"Count": limite}}},
                                "Version": 1}}}]},
                    "QueryId": "", "ApplicationContext": {"DatasetId": self.db, "Sources": [{"ReportId": self.report_id}]}}]}
        resp = S.post(f"{self.base}/querydata?synchronous=true", headers=self.H, json=body, timeout=600)
        if not resp.ok:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:600]}")
        return decodificar(resp.json(), [n for n, _ in select], limite)


def col(src, prop): return {"Column": {"Expression": {"SourceRef": {"Source": src}}, "Property": prop}}
def soma(src, prop): return {"Aggregation": {"Expression": col(src, prop), "Function": 0}}
def conta(src, prop): return {"Aggregation": {"Expression": col(src, prop), "Function": 5}}   # CountNonNull
def conta_distinta(src, prop): return {"Aggregation": {"Expression": col(src, prop), "Function": 2}}
def lit_txt(s): return {"Literal": {"Value": "'" + s.replace("'", "''") + "'"}}
def lit_int(n): return {"Literal": {"Value": f"{int(n)}L"}}
def em(expr, literais): return {"Condition": {"In": {"Expressions": [expr], "Values": [[l] for l in literais]}}}


def decodificar(js, nomes, limite=None):
    """Formato DSR do Power BI -> lista de dicionários. Trata linhas com C/R/Ø e dicionários de valores.

    Com `limite`, recusa resposta cortada antes dele: o serviço marca o corte com o token de continuação "RT".
    Chegar ao limite não é erro aqui; quem chama decide dividir a consulta."""
    res = js["results"][0]["result"]["data"]
    ds = res["dsr"]["DS"][0]
    dicts = ds.get("ValueDicts", {})
    if not ds.get("PH"): return []          # consulta sem nenhuma linha
    ph = ds["PH"][0]
    chave = next((k for k in ph if k.startswith("DM")), None)
    if chave is None:
        return []
    linhas, anterior, schema = [], None, None
    ncol = len(nomes)
    for row in ph[chave]:
        if "S" in row: schema = row["S"]
        if not any(k in row for k in ("C", "R", "Ø")):
            continue
        C = row.get("C", []); R = row.get("R", 0); NULL = row.get("Ø", 0)
        out, ci = [], 0
        for i in range(ncol):
            if R >> i & 1:                  # repete a linha anterior: já está decodificado
                out.append(anterior[i]); continue
            if NULL >> i & 1:
                out.append(None); continue
            v = C[ci] if ci < len(C) else None; ci += 1
            dn = schema[i].get("DN") if schema and i < len(schema) else None
            if dn and isinstance(v, int) and not isinstance(v, bool) and dn in dicts and 0 <= v < len(dicts[dn]):
                v = dicts[dn][v]
            out.append(v)
        anterior = out
        linhas.append(dict(zip(nomes, out)))
    if limite and "RT" in ds and len(linhas) < limite:
        raise RuntimeError(f"resposta do Power BI cortada em {len(linhas)} linhas, abaixo do limite pedido ({limite})")
    return linhas
