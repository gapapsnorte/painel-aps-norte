"""Envia a lotação (coleta/referencia.json, com nomes) para o repositório PRIVADO, de onde o GitHub Actions a busca.
O repositório público do painel não guarda mais esse arquivo.

Uso (na pasta do painel), sempre que sair planilha nova do RH:
    python -X utf8 coleta/montar_referencia.py "<caminho da planilha>" coleta/referencia.json "<nome da aba>"
    python -X utf8 enviar_rh.py            # envia
    python -X utf8 enviar_rh.py --simular  # só mostra o que faria

Precisa do gh (GitHub CLI) já autenticado na conta dona do repositório privado."""
import base64, json, pathlib, re, subprocess, sys

REPO = "gapapsnorte/painel-aps-norte-rh"
ARQ = pathlib.Path(__file__).parent / "coleta" / "referencia.json"
SIMULAR = "--simular" in sys.argv


def gh(*args, entrada=None):
    return subprocess.run(["gh", *args], input=entrada, capture_output=True, text=True, encoding="utf-8")


CAMPOS_DA_PESSOA = {"nome", "cat", "cargo", "chs", "vinculo", "cns"}      # o que o painel usa; nada além disso sobe


def conferir_conteudo(ref):
    """Para antes de enviar se o arquivo tiver campo pessoal a mais ou CNS que não esteja embaralhado."""
    pessoas = [p for lista in ref["lotacao"].values() for p in lista]
    a_mais = sorted({k for p in pessoas for k in p} - CAMPOS_DA_PESSOA)
    if a_mais:
        sys.exit(f"PARADO: a lotação tem campo(s) que o painel não usa: {a_mais}. Gere de novo com coleta/montar_referencia.py.")
    if not all(re.fullmatch(r"[0-9a-f]{12}", p["cns"]) for p in pessoas if p["cns"]):
        sys.exit("PARADO: há CNS fora do formato embaralhado; o arquivo pode ter CNS em claro.")
    demais = [str(v) for p in pessoas for k, v in p.items() if k != "cns"]     # o código do CNS pode calhar de só ter dígitos
    if any(re.search(r"\d{11,}", v) for v in demais):
        sys.exit("PARADO: há número de 11 ou mais dígitos na lotação (CPF, CNS ou matrícula?).")


ref = json.loads(ARQ.read_text("utf-8"))
conferir_conteudo(ref)
resumo = f"{len(ref['ubs'])} unidades, {len(ref['equipes'])} equipes, {sum(len(v) for v in ref['lotacao'].values())} lotados; fonte: {ref.get('fonte')}"
print("Arquivo:", ARQ, "|", resumo)

r = gh("api", f"repos/{REPO}", "--jq", ".private")
if r.returncode != 0: sys.exit(f"Não achei o repositório {REPO} (ou o gh não está autenticado nessa conta):\n{r.stderr.strip()}")
if r.stdout.strip() != "true": sys.exit(f"PARADO: {REPO} não é privado. A lotação tem nomes e não pode ir para repositório público.")

atual = gh("api", f"repos/{REPO}/contents/referencia.json", "--jq", ".sha")
sha = atual.stdout.strip() if atual.returncode == 0 else None
corpo = {"message": f"Lotação: {ref.get('fonte')}", "content": base64.b64encode(ARQ.read_bytes()).decode()}
if sha: corpo["sha"] = sha
print(("Substituir" if sha else "Criar"), f"referencia.json em {REPO} (privado)")
if SIMULAR: sys.exit("Simulação: nada foi enviado.")
e = gh("api", "--method", "PUT", f"repos/{REPO}/contents/referencia.json", "--input", "-", entrada=json.dumps(corpo))
if e.returncode != 0: sys.exit("Falhou o envio:\n" + e.stderr.strip())
print("Enviado. A próxima atualização automática do painel já usa a lotação nova; para não esperar:")
print("  gh workflow run atualizar.yml --repo gapapsnorte/painel-aps-norte")
