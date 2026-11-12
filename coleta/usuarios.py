"""Pessoas diferentes atendidas e hiperfrequentadores (painel Atendimentos Individuais, tabela fUsuarios_unicos).
Para cada equipe (INE) e UBS conta, nos últimos 12 meses fechados, quantas pessoas distintas foram atendidas e quantos atendimentos
cada uma teve; guarda só CONTAGENS por faixa de frequência. A chave da pessoa (cns_cpf) é lida em memória, agregada e descartada:
nada identificável é gravado. Saída: ../dados/brutos/usuarios.json.  Uso: python usuarios.py"""
import json, sys, pathlib, time, datetime as dt
from collections import defaultdict
from pbi_lib import Painel, col, conta_distinta, lit_txt, lit_int, em

AQUI = pathlib.Path(__file__).parent
OUT = AQUI.parent / "dados" / "brutos"; OUT.mkdir(parents=True, exist_ok=True)
URL = {i["titulo"]: i["url"] for i in json.load(open(AQUI / "paineis_aps.json", encoding="utf-8"))}
TETO = 30000
FAIXAS = [(1, 1), (2, 3), (4, 5), (6, 11), (12, 23), (24, 10**9)]     # atendimentos por pessoa em 12 meses
ROT = ["1", "2–3", "4–5", "6–11", "12–23", "24+"]


def meses_janela(n=12, hoje=None):
    hoje = hoje or dt.date.today(); a, m = hoje.year, hoje.month
    out = []
    for _ in range(n):
        m -= 1
        if m == 0: a, m = a - 1, 12
        out.append((a, m))
    return sorted(out)


def tentar(fn, *a, **k):
    for t in range(3):
        try: return fn(*a, **k)
        except Exception:
            if t == 2: raise
            time.sleep(5)


def main():
    ref = json.load(open(AQUI / "referencia.json", encoding="utf-8"))
    ubs = ref["ubs"]; eq = ref["equipes"]
    meses = meses_janela(); ini, fim = meses[0], meses[-1]
    p = Painel(URL["Atendimentos Individuais na APS"]); ent = {"u": "fUsuarios_unicos"}
    por_ano = defaultdict(list)
    for a, m in meses: por_ano[a].append(m)
    # (cnes, ine) -> {pessoa: atendimentos}; pessoa só existe em memória
    pess = defaultdict(lambda: defaultdict(int)); sem_id = defaultdict(int); lidas = 0
    for cnes in ubs:
        for ano, ms in por_ano.items():
            where = [em(col("u", "i_estab_cnes"), [lit_txt(cnes)]), em(col("u", "i_ano_compt"), [lit_int(ano)]),
                     em(col("u", "i_mes_compt"), [lit_txt(f"{m:02d}") for m in ms])]
            r = tentar(p.consulta, ent, [("ine", col("u", "i_ine")), ("cns", col("u", "cns_cpf")), ("n", conta_distinta("u", "linha_id"))], where, limite=TETO)
            if len(r) >= TETO: raise RuntimeError(f"UBS {cnes} {ano} bateu no teto; dividir por mês")
            for l in r:
                lidas += 1
                ine = str(l["ine"] or "-"); ine = ine.zfill(10) if ine.isdigit() else "-"
                k = str(l["cns"] or "").strip()
                if not k or k in ("-", "0") or not any(ch.isdigit() for ch in k): sem_id[(cnes, ine)] += int(l["n"] or 0); continue
                pess[(cnes, ine)][k] += int(l["n"] or 0)
        print(cnes, ubs[cnes].get("nome_rh"), flush=True)

    def resumo(contagens, extra_sem=0):
        v = sorted(contagens, reverse=True); n = len(v); at = sum(v)
        fp = [0] * len(FAIXAS); fa = [0] * len(FAIXAS)
        for c in v:
            for i, (lo, hi) in enumerate(FAIXAS):
                if lo <= c <= hi: fp[i] += 1; fa[i] += c; break
        k = max(1, round(n * 0.10)) if n else 0
        return {"pess": n, "atend": at, "fp": fp, "fa": fa, "top10": sum(v[:k]), "max": v[0] if v else 0, "sem_id": extra_sem}

    por_eq, por_ubs, por_gsap, regiao = {}, {}, {}, defaultdict(int)
    ubs_p = defaultdict(lambda: defaultdict(int)); gsap_p = defaultdict(lambda: defaultdict(int)); sem_u = defaultdict(int); sem_g = defaultdict(int)
    for (cnes, ine), d in pess.items():
        if ine != "-": por_eq[ine] = resumo(d.values(), sem_id.get((cnes, ine), 0))
        g = ubs[cnes].get("gsap")
        for k, n in d.items():
            ubs_p[cnes][k] += n; gsap_p[g][k] += n; regiao[k] += n
    for (cnes, ine), n in sem_id.items(): sem_u[cnes] += n; sem_g[ubs[cnes].get("gsap")] += n
    for c, d in ubs_p.items(): por_ubs[c] = resumo(d.values(), sem_u.get(c, 0))
    for g, d in gsap_p.items(): por_gsap[g] = resumo(d.values(), sem_g.get(g, 0))
    reg = resumo(regiao.values(), sum(sem_id.values()))
    out = {"janela": [f"{a}-{m:02d}" for a, m in (ini, fim)], "faixas": ROT, "regiao": reg, "gsap": por_gsap, "ubs": por_ubs, "equipe": por_eq}
    (OUT / "usuarios.json").write_text(json.dumps(out, ensure_ascii=False), "utf-8")
    print(f"[usuarios] {lidas} linhas pessoa×equipe lidas; janela {out['janela']}; região: {reg['pess']} pessoas, {reg['atend']} atendimentos, sem id {reg['sem_id']}")


if __name__ == "__main__":
    main()
