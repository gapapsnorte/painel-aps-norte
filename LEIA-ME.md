# Painel da APS – Região Norte (InfoSaúde)

**Publicação:** repositório público `gapapsnorte/painel-aps-norte`, página em https://gapapsnorte.github.io/painel-aps-norte/ (GitHub Pages), atualizada pelo GitHub Actions às 07h15 e 14h30. A página mostra os **nomes dos profissionais** (decisão da responsável, 08/11/2026); **matrícula, CPF e CNS nunca vão ao ar**: o CNS é embaralhado com um segredo (`APS_PEPPER`, guardado só no seu computador em `coleta/pepper.local` e nos Segredos do GitHub) e a matrícula só existe na versão gerada localmente. Para tirar a página do ar: no repositório, Settings > Pages > Unpublish, ou apagar a variável `PUBLICAR`.


Painel estático: GSAP → UBS → equipe → lista de profissionais, com série mensal em cada caixa, alertas e busca.
Criado em 08/11/2026. **Ainda não publicado** (falta decidir onde: aba no site de filas ou site próprio).

## Como abrir
Dê duplo clique em `site\index.html` (funciona sem servidor; os dados vêm de `site\painel.js`).

## Como atualizar (3 passos, ~2 min)
```
cd coleta
python -X utf8 razao.py             # população, cadastros e consultas por região (aba Consultas por mil hab.)
python -X utf8 coleta.py 2024-01     # lê os painéis do InfoSaúde (API pública do Power BI), ~1 min
python -X utf8 montar.py             # agrega, calcula alertas, grava dados\painel.json e site\painel.js
```
Depois é só reabrir `site\index.html`. Não usar `python -I` (não acha `pbi_lib.py`).

## Arquivos
- `coleta\pbi_lib.py` – cliente do Power BI "Publish to web" (consulta + decodificador). A chave vem do iframe de cada painel do InfoSaúde.
- `coleta\paineis_aps.json` – os 16 painéis da Atenção Primária (URLs). `coleta\inventario.json` – tabelas/colunas de cada um.
- `coleta\coleta.py` – coleta mensal por profissional e equipe (atendimentos, visitas ACS, vacinas, atividades coletivas) e por equipe (condições avaliadas, odonto).
- `coleta\montar_referencia.py` + `referencia.json` – lotação (UBS, GSAP, equipe, profissionais) a partir de `02 MAPS Saúde Mental\RH APS NORTE 06 2026.xlsx`, aba Junho2026. Rodar de novo quando sair RH mais novo:
  `python -X utf8 montar_referencia.py "<caminho do RH>" referencia.json`.
  Desde 11/11/2026 a lotação vem de `PLANILHA OFICIAL - RH APS Norte - 10.2026.xlsx`, aba "RH APS Norte" (3º argumento = nome da aba). O rótulo "out/2026" do painel sai do nome do arquivo (MM.AAAA ou MM AAAA).
- `coleta/usuarios.py` – pessoas diferentes atendidas e uso muito frequente (12 meses fechados), por equipe, UBS, GSAP e Região. Lê o identificador da pessoa só em memória e grava apenas contagens por faixa em `dados/brutos/usuarios.json`; `montar.py` leva para o bloco `usuarios`, `validar.py` barra se faltar. Aba "Pessoas atendidas"; teste `testes/testar_usuarios.py`. A base soma cerca de 5% menos atendimentos que a série das outras abas (causa não verificada).
- Dica com os números ao passar o mouse: vale para qualquer elemento com `<title>` (SVG) ou atributo `title`; teste `testes/testar_dicas.py`.
- `coleta\montar.py` – hierarquia, estatísticas e alertas.
- `dados\brutos\` – saída da coleta. `testes\testar_site.py` – teste da página (Playwright).

## O que o painel mostra (v2, 08/11/2026)
- Hierarquia GSAP > UBS > equipe > profissionais, com série mensal, gráfico da equipe contra a mediana das eSF e o ano anterior.
- **Mapa de calor** equipes x meses (cor = mês contra a mediana da própria equipe), **ficha do servidor** (todas as equipes, séries somadas) e busca por nome ou **matrícula**.
- Indicadores: atendimentos (médicos, enfermeiros), visitas ACS, vacinas, atividades coletivas; por equipe: condições avaliadas, odontologia; **20 famílias de procedimentos** (`coleta/familias.py`, códigos SIGTAP) e **24 linhas de cuidado por CID** (`coleta/motivos.py`).
- Matrícula: `montar_referencia.py` grava `coleta/referencia_privada.json` (CNS embaralhado -> matrícula). **Esse arquivo é só local e está no .gitignore**: no GitHub o painel sai sem matrícula. Para ter a matrícula, gere o painel no seu computador.

## Abas (v3, 08/11/2026)
- **Prioridades:** equipes (eSF) e UBS com sinal no último mês completo, da mais para a menos urgente (zero atendimentos > bem abaixo do habitual > sem médico > queda sobre o ano anterior > ACS sem visita > sem registro de procedimento). "Habitual" = mediana de 12 meses da própria equipe.
- **Comparar equipes:** cada eSF é um ponto, por UBS e GSAP, contra a faixa central (25% a 75%) e a mediana da Região; usa o indicador escolhido no topo.
- **Acesso:** tipo de atendimento (no dia, agendada, programada, urgência, escuta) e quem atendeu (médico, enfermeiro, outros), por Região, GSAP, UBS e equipe, com descida por clique e comparação com o mesmo mês do ano anterior.
- **eSF que mudou de UBS** (mesma INE para de registrar numa UBS e segue em outra) é tratada como "mudou de UBS" e sai de Prioridades, Comparar e Mapa, para não virar falso alarme de equipe parada. Hoje: Amarela - SOB (maio/2026).

## Regras que importam
- **Atendimentos individuais = soma de `fAtendimentos.i_qtd_atendimento_prof`** (confere com o painel do InfoSaúde: UBS 5 Planaltina 47.351 em 2026; região 498.780 × 498.763). Filtrar o ano na tabela-fato com a medida do painel dá zero.
- Cada consulta devolve no máximo 30 mil linhas, **sem erro**: a coleta é por mês e aborta se bater no teto.
- CNS/CPF/matrícula são usados só para ligar profissional à lotação e **nunca vão para a página**.
- Alertas (último mês completo): eSF sem atendimento (média anterior ≥ 100), sem médico (média ≥ 30), queda ≥ 30% sobre o mesmo mês do ano anterior (base ≥ 150 na equipe, ≥ 600 na UBS), ACS lotado sem visita, produção sem equipe ≥ 30% na UBS. São sinais para conferir, não conclusões.
- Motivos (CID): um atendimento pode ter mais de um CID e ~4 em 10 vêm sem CID; ler como perfil, não como contagem exata.
- Fora da v1: ICSAP (filtro por residência na Norte só vai até fev/2025), procedimentos, Cobertura/Previne/Bolsa Família (painéis parados no InfoSaúde).

## Aba Consultas por mil hab. (11/11/2026)
- Indicador RIPSA COB.1.01 (3ª ed., jun/2026): consultas de médico na APS por população. Ao lado, enfermeiro e médico + enfermeiro (acréscimo do painel). Aqui “por mil” = razão da ficha (por 100) × 10; a ficha não traz meta.
- **Região, DF e regiões de saúde:** numerador = atendimentos individuais do InfoSaúde (categoria MÉDICO inclui residentes, ~3%); denominador = série de população por RA do painel Cobertura (`base_populacional`). Brasil = tabela da ficha RIPSA (2022–2024), só para médico. Decisão dela (11/11): série do InfoSaúde, não o Censo fixo (que daria Norte ~9% maior).
- **GSAP, UBS e equipe:** denominador = população **cadastrada** (`base_cadastros`, última competência **abr/2025**, parada no InfoSaúde), com aviso na tela; não se compara com a tabela de cima. Variação = 12 meses contra os 12 anteriores, mesmo denominador.
- Coleta em `coletaazao.py` (~1 min); `montar.py` grava `razao` no painel.json e `cad` por UBS/equipe; `validar.py` barra se faltar. Teste: `testes	estar_razao.py` (confere os números da tela contra o JSON).
- **Filtro "População (denominador)" (11/11/2026, pedido dela):** série do InfoSaúde por RA (padrão), Censo 2022 (fixo; só Norte 345.286 e DF 2.817.381, as outras regiões ficam "–") ou população cadastrada (abr/2025, por região). Vale para a tabela Brasil/DF/regiões; a tabela GSAP/UBS/equipe sempre usa a cadastrada. Coleta extra: `cadastros_regiao.json`.

## Área dos gestores (nomes sob senha) — preparado em 11/11/2026, ainda não publicado

- **O que é aberto:** Região → GSAP → UBS → equipe, com todos os indicadores agregados, alertas com contagem ("1 de 3 ACS sem visita") e todas as abas.
- **O que fica sob senha:** tabela de profissionais de cada equipe, ficha do servidor, busca por nome, coluna de profissional no CSV e o texto dos alertas com nomes.
- **Como funciona:** `coleta/montar.py` grava `site/painel.js` (só agregados, sem nenhum nome) e `site/nominal.js` (bloco nominal comprimido e cifrado com AES-GCM; a chave sai da senha por PBKDF2-SHA256 com 600 mil iterações). A página só baixa o `nominal.js` quando alguém clica em **Entrar**, e decifra no navegador (Web Crypto). Senha errada não abre nada.
- **Senha:** variável `APS_SENHA` (Segredo do GitHub) ou arquivo `coleta/senha.local` (fora do git), mínimo de 12 caracteres. Sem senha, o painel sai só com a parte aberta e o botão Entrar some. Para trocar a senha: trocar o Segredo e o arquivo local e rodar a atualização; quem tinha "lembrar neste navegador" precisa digitar a nova.
- **"Lembrar neste navegador"** guarda a chave derivada (não a senha) só naquele navegador; **Sair** apaga.
- **Travas:** `montar.py` não grava nada se achar nome de servidor, sequência de 11+ dígitos ou campo nominal na parte aberta, e aborta se houver matrícula numa geração feita no GitHub. `validar.py` repete a conferência dos nomes antes de publicar. O resumo impresso (que fica no registro público das execuções) não tem nomes.
- **Identificador do profissional:** sequencial (p1, p2…), sem nada derivado do CNS. CNS, CPF e matrícula não vão para a versão publicada, nem cifrados; a matrícula só aparece quando o painel é gerado no computador (com `coleta/referencia_privada.json`).
- **Cópia em claro para testes:** `dados/nominal.json`, só no computador (a pasta `dados/` é ignorada pelo git; no GitHub o arquivo não é criado).
- **Testes:** `testes/testar_restrito.py` (sem senha não há nome em nenhuma aba nem em nenhum arquivo de `site/`; senha errada; senha certa; lembrar; sair; celular). Os testes antigos entram com a senha por `testes/_entrar.py`. Rodar com `APS_SENHA` definida ou com `coleta/senha.local`.
- **Limites:** senha única não registra quem entrou e só se revoga trocando a senha de todos; o arquivo cifrado é público, então a proteção depende de a senha ser longa; o InfoSaúde continua público com nomes.

## Lotação (RH) fora do repositório público

- `coleta/referencia.json` (lotação com nomes) deixa de ser versionado aqui (está no `.gitignore`). Ele mora no repositório **privado** `gapapsnorte/painel-aps-norte-rh`; o workflow o busca com uma chave só de leitura (Segredo `RH_CHAVE`) antes da coleta.
- **Quando sair RH novo:**
  1. `python -X utf8 coleta/montar_referencia.py "<caminho da planilha>" coleta/referencia.json "<nome da aba>"`
  2. `python -X utf8 enviar_rh.py` (confere que o destino é privado e envia; `--simular` só mostra)
  3. opcional, para não esperar o horário: `gh workflow run atualizar.yml --repo gapapsnorte/painel-aps-norte`
- A planilha original do RH e o `coleta/referencia_privada.json` (matrícula) continuam só no computador.

## Ajustes de 12/11/2026 (local, ainda não publicado)
- **Seletor de indicador em dois passos:** cinco botões de grupo (Atendimentos e produção, Condições avaliadas, Motivos de consulta, Procedimentos, Perfil de acesso) e, abaixo, o indicador do grupo. Odontologia fica em Atendimentos e produção. Cada grupo lembra o último indicador usado.
- **Comparação de equipes dentro dos cards:** ao abrir uma GSAP ou UBS, uma faixa mostra as equipes dali como pontos contra a mediana e a faixa central da Região. A aba "Comparar equipes" virou botão ("Ver comparação detalhada" no card; "Comparar todas as equipes da Região" na Visão geral).
- **Lotação:** repositório privado `gapapsnorte/painel-aps-norte-rh` criado e abastecido; chave só de leitura gravada no Segredo `RH_CHAVE` (cópia local em `coleta/chave_rh`, fora do git). Falta o Segredo `APS_SENHA` e a limpeza do histórico do repositório público.
- Esboços para decisão: `_analise_2026-11/variacoes_acesso.html` (juntar Acesso, Pessoas atendidas e Consultas por mil) e `variacoes_grafico_mensal.html`.
- **Gráfico mensal (pedido dela, 12/11):** uma linha por ano, de janeiro a dezembro, no lugar das barras com bolinha (Região, GSAP, UBS e ficha). O seletor Período define quantos anos aparecem.
- **Relatório (só com senha):** botão "Gerar relatório" → escolhe a unidade (Região, GSAP ou UBS), marca o que entra (9 itens; a lista nominal vem desmarcada) e o formato. PDF usa a impressão do navegador ("Salvar como PDF"); Word baixa um `.doc` (página web de arquivo único, com os gráficos convertidos em imagem) que o Word abre e salva como `.docx`. Tudo é montado no navegador; nada é enviado a servidor. Teste: `testes/testar_relatorio.py` (os arquivos de exemplo ficam em `testes/_dicas/`, fora do git, porque têm nomes).
- **Motivos de consulta, marcação múltipla:** no grupo Motivos aparece "Comparar com outros motivos" (até 5 além do escolhido); Região, GSAP, UBS e equipe abertas mostram as linhas juntas e uma tabela.
- **Ordem das abas:** Visão geral, Mapa de calor, Acesso, Pessoas atendidas, Consultas por mil hab.
- **Senha dos gestores:** definida por ela em `coleta/senha.local` e gravada no Segredo `APS_SENHA` (12/11).

## Lote de 12/11/2026 (tarde) — vale sobre o que estiver escrito acima

Feito a partir da avaliação externa do painel e das escolhas dela. Tudo local; nada publicado.

- **Abas:** Visão geral, Mapa de calor, Perfil dos atendimentos e Inconsistências (esta só aparece depois de entrar com a senha).
- **Perfil dos atendimentos** (`#aba-p`): uma linha por unidade com cinco medidas de 12 meses (consulta no dia, atendido por médico, atendimentos por pessoa, pessoas com 12 ou mais, consultas de médico por mil cadastrados) e botão "detalhe". Os botões abaixo da aba abrem as partes completas: tipo de atendimento mês a mês (antiga Acesso), Pessoas atendidas e Consultas por mil hab.
- **Inconsistências** (`#aba-i`): gerada em `montar.py` e gravada só no bloco cifrado (`nominal.incons`). Tipos: produção sem INE, lotado numa equipe e registrando em outra, lotado sem registro em 3 meses, registra e não consta no RH, INE fora da planilha de RH, equipe do RH sem registro, equipe que mudou de UBS, registro provável em lugar errado.
- **Habitual:** uma regra só, na página (`habitual()`) e no gerador (`med12()`): mediana dos 12 meses anteriores ao último mês completo. Etiquetas e mapa de calor usam a mesma; o mapa não muda mais com o período escolhido.
- **Seletor de indicador:** 10 grupos, seguindo as boas práticas do cofinanciamento (`GRP_KS` em `site/index.html`). Um indicador pode estar em dois grupos. É produção registrada, não o indicador oficial.
- **Procedimentos** (`coleta/familias.py`): DIU e implante separados; pressão arterial, glicemia capilar, peso/altura/antropometria e avaliação da pessoa idosa em famílias próprias. Hemoglobina glicada não existe no InfoSaúde (catálogo conferido em 12/11/2026). Rastreio de mama entrou como condição avaliada.
- **Aviso na equipe:** equipe abaixo de 70% do habitual em UBS com atendimento sem equipe mostra o quadro "Antes de concluir, confira". Nada é redistribuído.
- **Link:** o endereço guarda aba, indicador, período, filtro e unidade aberta (`#v=&i=&p=&f=&g=&u=&e=`).
- **Providências:** botão "Baixar planilha de providências" gera um CSV no computador de quem clica (uma linha por alerta; com senha, também por inconsistência). A página não grava nada.
- **Relatório:** 13 partes; entraram produção por boa prática, perfil de 12 meses, inconsistências e quadro de providências.
- **Rótulos:** "já saiu" virou "vínculo atual não confirmado"; variação diz contra qual mês; taxa por mil cadastrados leva o selo "comparação exploratória".
- **Testes:** `testes/testar_lote.py` cobre o lote; os demais foram ajustados às abas novas.
- **Cópia de antes:** `_backup_2026-11-12_antes_lote`.
