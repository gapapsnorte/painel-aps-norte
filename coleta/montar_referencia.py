"""Monta referencia.json a partir da planilha de RH (aba Junho2026): CNES -> UBS/GSAP, INE -> equipe, lotação por INE.
Guarda nome, categoria, cargo, CHS e o CNS EMBARALHADO (hc) — o CNS real nunca é gravado; serve só para ligar à produção."""
import json, re, sys, pathlib, hashlib, openpyxl
import os
def _pepper():
    p = os.environ.get("APS_PEPPER")
    if not p:
        f = pathlib.Path(__file__).parent / "pepper.local"
        if f.exists(): p = f.read_text(encoding="utf-8").strip()
    if not p: raise SystemExit("Falta o segredo APS_PEPPER (variável de ambiente, ou arquivo coleta/pepper.local).")
    return p
PEPPER = _pepper()
def hc(c): return hashlib.sha256((PEPPER + "|" + str(c)).encode()).hexdigest()[:12] if c else ""   # igual nos dois scripts
from collections import defaultdict, Counter
SRC = pathlib.Path(sys.argv[1]); OUT = pathlib.Path(sys.argv[2]); ABA = sys.argv[3] if len(sys.argv) > 3 else "Junho2026"
ws = openpyxl.load_workbook(SRC, read_only=True, data_only=True)[ABA]
linhas = list(ws.iter_rows(values_only=True)); cab = [str(c).strip() if c else "" for c in linhas[0]]
ix = {n: cab.index(n) for n in cab if n}
def v(r, n): return r[ix[n]]
def gsap_curta(s):
    s = str(s or "")
    m = re.search(r"N[ºo°]?\s*(\d+)\s+de\s+(.+)$", s, re.I)
    return f"GSAP {m.group(1)} {m.group(2).strip()}" if m else s.strip()
ubs, equipes, lot = {}, {}, defaultdict(list)
privada = {}   # CNS embaralhado -> matrícula (arquivo local, NUNCA versionado)
for r in linhas[1:]:
    cnes = v(r, "CNES")
    if not cnes: continue
    cnes = str(int(cnes)).zfill(7); _i = str(v(r, "INE da equipe") or "").strip(); ine = _i.split(".")[0].zfill(10) if _i.replace(".0", "").isdigit() and int(float(_i)) > 0 else ""   # "N/A" = setor sem equipe
    ubs.setdefault(cnes, {"cnes": cnes, "nome_rh": v(r, "Unidade de Saúde (CNES - Nome Fantasia)"), "ra": v(r, "Região Adminstrativa"),
                          "gsap": gsap_curta(v(r, "Diretoria/Gerência/Núcleo")), "gsap_longa": v(r, "Diretoria/Gerência/Núcleo")})
    if ine:
        equipes.setdefault(ine, {"ine": ine, "cnes": cnes, "nome": v(r, "Equipe (CNES)/Setor na UBS"), "tipo": v(r, "Tipo de Equipe"),
                                 "situacao": v(r, "Situação da equipe"), "zona": v(r, "Urbana/Rural")})
    cns = hc(str(int(v(r, "CNS")))) if v(r, "CNS") else ""
    mat = v(r, "Matrícula")
    if cns and isinstance(mat, (int, float)) and mat > 0: privada[cns] = str(int(mat))
    def texto(x): return x.strip() if isinstance(x, str) and re.search(r"[A-Za-zÀ-ú]", x) else None   # só texto com letras: descarta números soltos (ex.: CPF digitado na coluna errada)
    chs = v(r, "CHS de Lotação"); chs = chs if isinstance(chs, (int, float)) and 0 < chs <= 60 else None
    lot[ine or f"UBS:{cnes}"].append({"nome": texto(v(r, "Nome Completo")) or "", "cat": texto(v(r, "Categoria Provimento")), "cargo": texto(v(r, "Cargo - SIGRH")),
                                      "chs": chs, "vinculo": texto(v(r, "Vínculo")), "cns": cns})
ref = {"fonte": f"{SRC.name}, aba {ABA}", "ubs": ubs, "equipes": equipes, "lotacao": lot}
OUT.write_text(json.dumps(ref, ensure_ascii=False, indent=1, default=str), "utf-8")
(OUT.parent / "referencia_privada.json").write_text(json.dumps(privada, ensure_ascii=False), "utf-8")
print(len(privada), "matrículas gravadas em referencia_privada.json (local, fora do git)")
print(len(ubs), "UBS |", len(equipes), "equipes |", sum(len(x) for x in lot.values()), "profissionais")
print("GSAPs:", Counter(u["gsap"] for u in ubs.values()))
print("tipos de equipe:", Counter(e["tipo"] for e in equipes.values()))
print("categorias:", Counter(p["cat"] for l in lot.values() for p in l).most_common(12))
for g in sorted({u["gsap"] for u in ubs.values()}): print(" ", g, "->", sorted(u["nome_rh"] for u in ubs.values() if u["gsap"] == g))
