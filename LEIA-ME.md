# Painel da APS – Região Norte (InfoSaúde)

**Publicação:** repositório público `gapapsnorte/painel-aps-norte`, página em https://gapapsnorte.github.io/painel-aps-norte/ (GitHub Pages), atualizada pelo GitHub Actions duas vezes ao dia (agendado para 03h07 e 10h07; o GitHub costuma iniciar 4 a 7 horas depois, então a página muda de manhã e no meio da tarde). A página mostra os **nomes dos profissionais** (decisão da responsável, 08/11/2026); **matrícula, CPF e CNS nunca vão ao ar**: o CNS é embaralhado com um segredo (`APS_PEPPER`, guardado só no seu computador em `coleta/pepper.local` e nos Segredos do GitHub) e a matrícula nem é lida da planilha de RH. Para tirar a página do ar: no repositório, Settings > Pages > Unpublish, ou apagar a variável `PUBLICAR`.


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
- **Mapa de calor** equipes x meses (cor = mês contra a mediana da própria equipe), **ficha do servidor** (todas as equipes, séries somadas) e busca por nome.
- Indicadores: atendimentos (médicos, enfermeiros), visitas ACS, vacinas, atividades coletivas; por equipe: condições avaliadas, odontologia; **20 famílias de procedimentos** (`coleta/familias.py`, códigos SIGTAP) e **24 linhas de cuidado por CID** (`coleta/motivos.py`).
- Matrícula: não existe mais no painel (nem na versão local); `coleta/referencia_privada.json` deixou de existir. Veja a seção "Revisão de 23/11/2026".

## Abas (v3, 08/11/2026)
- **Prioridades:** equipes (eSF) e UBS com sinal no último mês completo, da mais para a menos urgente (zero atendimentos > bem abaixo do habitual > sem médico > queda sobre o ano anterior > ACS sem visita > sem registro de procedimento). "Habitual" = mediana de 12 meses da própria equipe.
- **Comparar equipes:** cada eSF é um ponto, por UBS e GSAP, contra a faixa central (25% a 75%) e a mediana da Região; usa o indicador escolhido no topo.
- **Acesso:** tipo de atendimento (no dia, agendada, programada, urgência, escuta) e quem atendeu (médico, enfermeiro, outros), por Região, GSAP, UBS e equipe, com descida por clique e comparação com o mesmo mês do ano anterior.
- **eSF que mudou de UBS** (mesma INE para de registrar numa UBS e segue em outra) é tratada como "mudou de UBS" e sai de Prioridades, Comparar e Mapa, para não virar falso alarme de equipe parada. Hoje: Amarela - SOB (maio/2026).

## Regras que importam
- **Atendimentos individuais = soma de `fAtendimentos.i_qtd_atendimento_prof`** (confere com o painel do InfoSaúde: UBS 5 Planaltina 47.351 em 2026; região 498.780 × 498.763). Filtrar o ano na tabela-fato com a medida do painel dá zero.
- Cada consulta devolve no máximo 30 mil linhas, **sem erro**: a coleta é por mês e aborta se bater no teto.
- O CNS (embaralhado) serve só para ligar profissional à lotação e **nunca vai para a página**; CPF e matrícula nem são lidos.
- Alertas (último mês completo): eSF sem atendimento (média anterior ≥ 100), sem médico (média ≥ 30), queda ≥ 30% sobre o mesmo mês do ano anterior (base ≥ 150 na equipe, ≥ 600 na UBS), ACS lotado sem visita, produção sem equipe ≥ 30% na UBS. São sinais para conferir, não conclusões.
- Motivos (CID e, na falta dele, CIAP; desde 16/11/2026): um atendimento pode ter mais de um código. ~4 em 10 registros vêm sem CID, mas a maioria tem CIAP (`fam_ciap()` em `coleta/motivos.py`, coleta em `dados/brutos/motivos_ciap.json`); só ~6% ficam sem nenhum dos dois. Ler como perfil, não como contagem exata.
- Mês em consolidação (16/11/2026): nos 10 primeiros dias do mês a página avisa que o último mês completo ainda pode mudar (`CONSOL` em `site/index.html`, calculado da data de geração). O GitHub grava a cada rodada `historico_consolidacao.csv` (total de atendimentos da Região nos 3 últimos meses), para medir em quantos dias o InfoSaúde fecha o mês.
- Fora da v1: ICSAP (filtro por residência na Norte só vai até fev/2025), procedimentos, Cobertura/Previne/Bolsa Família (painéis parados no InfoSaúde).

## Aba Consultas por mil hab. (11/11/2026)
- Indicador RIPSA COB.1.01 (3ª ed., jun/2026): consultas de médico na APS por população. Ao lado, enfermeiro e médico + enfermeiro (acréscimo do painel). Aqui “por mil” = razão da ficha (por 100) × 10; a ficha não traz meta.
- **Região, DF e regiões de saúde:** numerador = atendimentos individuais do InfoSaúde (categoria MÉDICO inclui residentes, ~3%); denominador = série de população por RA do painel Cobertura (`base_populacional`). Brasil = tabela da ficha RIPSA (2022–2024), só para médico. Decisão dela (11/11): série do InfoSaúde, não o Censo fixo (que daria Norte ~9% maior).
- **GSAP, UBS e equipe:** denominador = população **cadastrada** (`base_cadastros`, última competência **abr/2025**, parada no InfoSaúde), com aviso na tela; não se compara com a tabela de cima. Variação = 12 meses contra os 12 anteriores, mesmo denominador.
- Coleta em `coleta\razao.py` (~1 min); `montar.py` grava `razao` no painel.json e `cad` por UBS/equipe; `validar.py` barra se faltar. Teste: `testes\testar_razao.py` (confere os números da tela contra o JSON).
- **Filtro "População (denominador)" (11/11/2026, pedido dela):** série do InfoSaúde por RA (padrão), Censo 2022 (fixo; só Norte 345.286 e DF 2.817.381, as outras regiões ficam "–") ou população cadastrada (abr/2025, por região). Vale para a tabela Brasil/DF/regiões; a tabela GSAP/UBS/equipe sempre usa a cadastrada. Coleta extra: `cadastros_regiao.json`.

## Área dos gestores (nomes sob senha) — preparado em 11/11/2026, ainda não publicado

- **O que é aberto:** Região → GSAP → UBS → equipe, com todos os indicadores agregados, alertas com contagem ("1 de 3 ACS sem visita") e todas as abas.
- **O que fica sob senha:** tabela de profissionais de cada equipe, ficha do servidor, busca por nome, coluna de profissional no CSV e o texto dos alertas com nomes.
- **Como funciona:** `coleta/montar.py` grava `site/painel.js` (só agregados, sem nenhum nome) e `site/nominal.js` (bloco nominal comprimido e cifrado com AES-GCM; a chave sai da senha por PBKDF2-SHA256 com 600 mil iterações). A página só baixa o `nominal.js` quando alguém clica em **Entrar**, e decifra no navegador (Web Crypto). Senha errada não abre nada.
- **Senha:** variável `APS_SENHA` (Segredo do GitHub) ou arquivo `coleta/senha.local` (fora do git), mínimo de 12 caracteres. Sem senha, o painel sai só com a parte aberta e o botão Entrar some. Para trocar a senha: trocar o Segredo e o arquivo local e rodar a atualização; quem tinha "lembrar neste navegador" precisa digitar a nova.
- **"Lembrar neste navegador"** guarda a chave derivada (não a senha) só naquele navegador; **Sair** apaga.
- **Travas:** `montar.py` não grava nada se achar nome de servidor, sequência de 11+ dígitos ou campo nominal na parte aberta, nem se houver matrícula ou CNS no bloco dos gestores. `validar.py` repete a conferência dos nomes antes de publicar. O resumo impresso (que fica no registro público das execuções) não tem nomes.
- **Identificador do profissional:** sequencial (p1, p2…), sem nada derivado do CNS. CNS, CPF e matrícula não vão para a versão publicada, nem cifrados.
- **Cópia em claro para testes:** `dados/nominal.json`, só no computador (a pasta `dados/` é ignorada pelo git; no GitHub o arquivo não é criado).
- **Testes:** `testes/testar_restrito.py` (sem senha não há nome em nenhuma aba nem em nenhum arquivo de `site/`; senha errada; senha certa; lembrar; sair; celular). Os testes antigos entram com a senha por `testes/_entrar.py`. Rodar com `APS_SENHA` definida ou com `coleta/senha.local`.
- **Limites:** senha única não registra quem entrou e só se revoga trocando a senha de todos; o arquivo cifrado é público, então a proteção depende de a senha ser longa; o InfoSaúde continua público com nomes.

## Lotação (RH) fora do repositório público

- `coleta/referencia.json` (lotação com nomes) deixa de ser versionado aqui (está no `.gitignore`). Ele mora no repositório **privado** `gapapsnorte/painel-aps-norte-rh`; o workflow o busca com uma chave só de leitura (Segredo `RH_CHAVE`) antes da coleta.
- **Quando sair RH novo:**
  1. `python -X utf8 coleta/montar_referencia.py "<caminho da planilha>" coleta/referencia.json "<nome da aba>"`
  2. `python -X utf8 enviar_rh.py` (confere que o destino é privado e envia; `--simular` só mostra)
  3. opcional, para não esperar o horário: `gh workflow run atualizar.yml --repo gapapsnorte/painel-aps-norte`
- A planilha original do RH continua só no computador.

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
- **Habitual:** uma regra só, na página (`habitual()`) e no gerador (`med12()`): mediana dos 12 meses anteriores ao último mês completo. Desde 16/11/2026 o mapa de calor usa a MÉDIA dos mesmos 12 meses (`media12()`), a pedido; as etiquetas seguem na mediana; o mapa não muda mais com o período escolhido.
- **Seletor de indicador:** 10 grupos, seguindo as boas práticas do cofinanciamento (`GRP_KS` em `site/index.html`). Um indicador pode estar em dois grupos. É produção registrada, não o indicador oficial.
- **Procedimentos** (`coleta/familias.py`): DIU e implante separados; pressão arterial, glicemia capilar, peso/altura/antropometria e avaliação da pessoa idosa em famílias próprias. Hemoglobina glicada não existe no InfoSaúde (catálogo conferido em 12/11/2026). Rastreio de mama entrou como condição avaliada.
- **Aviso na equipe:** equipe abaixo de 70% do habitual em UBS com atendimento sem equipe mostra o quadro "Antes de concluir, confira". Nada é redistribuído.
- **Link:** o endereço guarda aba, indicador, período, filtro e unidade aberta (`#v=&i=&p=&f=&g=&u=&e=`).
- **Providências:** botão "Baixar planilha de providências" gera um CSV no computador de quem clica (uma linha por alerta; com senha, também por inconsistência). A página não grava nada.
- **Relatório:** 13 partes; entraram produção por boa prática, perfil de 12 meses, inconsistências e quadro de providências.
- **Rótulos:** "já saiu" virou "vínculo atual não confirmado"; variação diz contra qual mês; taxa por mil cadastrados leva o selo "comparação exploratória".
- **Testes:** `testes/testar_lote.py` cobre o lote; os demais foram ajustados às abas novas.
- **Cópia de antes:** `_backup_2026-11-12_antes_lote`.

## Revisão de 13/11/2026 (código, metodologia, depuração, valor de uso)

- Relatório: `_analise_2026-11/revisao_2026-11-13/REVISAO_geral.md` (+ `1_codigo_python.md`, `2_codigo_pagina.md`, `3_debug.md`, `4_bibliografia.md`). Estado anterior em `_backup_2026-11-13_antes_revisao`.
- Corrigido: lotados na UBS sem equipe deixam de aparecer como "não consta na lotação"; "registros" das inconsistências soma só séries que não se sobrepõem (`BASE_REG` em `montar.py`); equipes com o mesmo nome na mesma UBS ganham "(INE …)"; cadastro de equipe que mudou de UBS fica só na UBS atual; `usuarios.py` junta as pessoas da mesma INE em duas UBS; coleta vazia vira erro; `validar.py` exige as séries principais, barra mês do meio pela metade, arquivo estranho em `site/` e geração no GitHub sem a área dos gestores; hora de geração sempre de Brasília; textos de alerta com "out/26"; na página: dica no celular, "lembrar" que resiste a falha de rede, link com valor inválido, busca por número, mensagem quando `painel.js` não carrega.
- Alertas (último mês completo): o "habitual" é a **mediana** dos 12 meses anteriores (o texto antigo deste arquivo fala em média).
- Pendente de decisão: regra de queda (2 meses seguidos abaixo de 70% do habitual dá 8 sinais/mês com 73% de confirmação, contra 25 e 51% da regra atual); mês "em consolidação" nos primeiros dias; CIAP nos motivos de consulta (só 6% dos registros não têm CID nem CIAP); as duas INE da "eSF 0369/33 - Azul" (UBS 4 Planaltina).

## Navegação única por unidade (16/11/2026, local)
- **Uma unidade para todas as abas:** a barra fixa abaixo das abas mostra o caminho `Região Norte › GSAP › UBS › equipe`, cada nível com um menu (▾) para trocar de irmão, e um campo de busca único (nome da equipe, INE, nome da UBS, CNES e, só com a senha, nome de servidor, que leva à equipe dele). À esquerda há uma árvore GSAP ▸ UBS ▸ equipes com a contagem de equipes com alerta (esconde no botão "Unidades"; no celular vira gaveta). A unidade escolhida (`estado.sel`, por índice) vai no endereço (`g`, `u`, `e`, e `so=1` para "mostrar só esta unidade") e não mexe em indicador, período nem filtro. Visão geral: abre as caixas até ela, rola e destaca. Mapa de calor e Inconsistências: só as linhas dela. Resumo por unidade, Tipo de atendimento, Pessoas atendidas e Consultas por mil hab.: entram já descidos até a UBS, com a equipe destacada; descer por clique dentro delas atualiza a escolha. O relatório já vem com a unidade. O bloco "Norte × DF" vai em `<section id="cmp-regioes">`, logo abaixo dos cartões da Visão geral.
- **Teste:** `testes/testar_navegacao.py` (capturas `testes/shot_nav_*.png`).

## Série desde 2022 e Norte × DF (16/11/2026)
- A coleta começa em **jan/2022** (`coleta.py 2022-01`; o InfoSaúde não tem produção de 2020–2021). Período "36 meses" e "Tudo (desde jan/22)" no seletor.
- `coleta/regioes.py` grava `dados/brutos/regioes.json`: total mensal por região de saúde (7 regiões) para 47 indicadores (todos menos motivos de consulta), mesmas regras de contagem da coleta da Norte (conferido: Norte bate 100% com os brutos). Serviços centralizados, contratados e privados ficam de fora; DF = soma das 7 regiões.
- `montar.py` → bloco `regioes` (séries + população por ano); `validar.py` barra se faltar. Workflow com passo novo.
- Visão geral: bloco `#cmp-regioes` "por mil habitantes – Norte × DF" para o indicador escolhido, com cartões de 12 meses e variação, e o quadro lateral "Comparar também com" (liga as outras 6 regiões; não vai para o link). Teste: `testes/testar_regioes.py`.

## Lote 2 (22/11/2026): queda em níveis, 1ª verificação, ficha por cargo
- **Queda em níveis** (`sinais()` na página): último mês abaixo de 70% do habitual = etiqueta amarela; último e anterior seguidos abaixo de 70% = vermelha ("2 meses seguidos abaixo de 70% do habitual"). Habitual segue a mediana de 12 meses.
- **Dica da etiqueta:** 3 últimos meses + "Primeira verificação" (textos revisados). São sinais para conferir, não conclusões.
- **Providências (CSV/Excel):** colunas novas "Primeira verificação", "Hipótese", "Medida a observar" (Data de revisão já existia).
- **Ficha por servidor:** médicos num grupo só (inclui residentes); coluna "Equivalente em 40 h" só informativa (CHS >= 20); tipo de atendimento por profissional no campo nominal `tp` (só bloco cifrado, travado no `validar.py`); blocos por cargo: técnico (sem escuta inicial, pois técnico não consta na base de Atendimentos Individuais; procedimentos e vacinas), ACS (visitas), saúde bucal (produção da eSB, dita como da equipe).
- **Teste:** `testes/testar_lote2.py`. Cópia de antes: `_backup_2026-11-22_antes_lote2`.

## Lote 3, fatia 1 (22/11/2026), local, não publicado
Tipo de UBS e de equipe, mais a aba **Força de trabalho** (com cadeado, só para quem entrou com a senha). Nada foi commitado nem publicado. Cópia de antes: `_backup_2026-11-22_antes_lote3` (montar.py, validar.py, index.html, atualizar.yml). `coleta/ivt_apsdf_2024.json` continua **não rastreado**: sem ele no repositório o GitHub gera o painel sem IVT (o montar aceita a falta do arquivo; o validar não reclama), então só entra na publicação se for versionado de propósito.
- **Porte (parte aberta, agregado):** terços da população cadastrada da UBS (`base_cadastros`, **abr/2025**, parada no InfoSaúde; o rótulo diz isso). Cortes calculados no `montar.py` por posição nos terços (`painel.tipo_ubs.cortes`): pequeno até 3.335, médio de 3.336 a 9.584, grande acima de 9.584 (36 UBS com cadastro, 12 em cada porte). A equipe herda o porte da UBS.
- **Zona (parte aberta):** a planilha de RH tem a coluna "Urbana/Rural" por equipe (`referencia.json`, campo `zona`); é o único campo confiável e é o que se usa. UBS = zona das suas eSF, ou "Mista" com a contagem (hoje 22 urbanas, 13 rurais, 1 mista). Nada de zona estimada.
- **IVT (SÓ no bloco cifrado, `nominal.ivt`):** IVT-APSDF 2024 (Nota Técnica 5/2024 SES/SAIS/COAPS), por INE da eSF (99 eSF casadas, igual a `_analise_2026-11/IVT/ivt_norte.json`: 38 baixa, 53 média, 8 alta). eSF que não está na lista aparece como "sem IVT (equipe criada depois de 2024)"; não se estima. eSB, eMulti e eCR: "IVT não se aplica (só eSF)". **IVT da UBS = faixa mais frequente entre as eSF da UBS**, com a contagem por faixa; empate fica como "empatado entre X e Y" (hoje 2 UBS), sem regra de desempate. eSF que mudou de UBS não conta.
- **Onde aparece:** linha discreta "Tipo: …" na ficha da UBS e da equipe (Visão geral) e na aba nova, ambas só com a senha. Comparar equipes, pares da ficha e Consultas por mil **não foram mexidos**.
- **Aba Força de trabalho** (`#aba-f`, `#vista-f`, `renderForca()`): segue a unidade da barra (Região > uma linha por GSAP; GSAP > uma por UBS; UBS ou equipe > as equipes da UBS mais a linha "Lotados na UBS, sem equipe"; a linha de total fica fixa no topo). Colunas: lotados por categoria (médico, enfermeiro, técnico de enfermagem, ACS, cirurgião-dentista, THD/ASB, outros; residentes ficam dentro da categoria e aparecem também numa coluna), com e sem produção nos 12 meses (qualquer registro de BASE_REG em qualquer equipe), lotados em "UBS:" sem equipe, carga horária semanal somada, equivalente em 40 h (só CHS >= 20, informativo), vínculo e situação da equipe (com produção / sem produção / mudou de UBS, janela de 3 meses como em Inconsistências). Tabela ordenável, botão Excel + CSV (`baixarPlanilha`, sem mescladas). Tudo vem de `nominal.ft` (cifrado); o texto de vínculo do RH nunca vai para a parte aberta.
- **Travas novas:** `montar.py` aborta se houver "ivt", `"ft"` ou `"vinc"` na parte aberta. `validar.py` barra "ivt" em `painel.js`, INE com IVT em `index.html`, campos `vinculo|vinc|ft|ivt` nos arquivos abertos e a falta dos cortes de porte. Testadas: acrescentar "ivt" ao `painel.js` faz o validar falhar.
- **Decisões provisórias (dela rever):** (1) IVT só sob senha; (2) porte e zona existem na parte aberta, mas por ora só aparecem sob senha; (3) UBS de IVT empatado fica "empatado"; (4) "sem produção" na aba inclui dentista/THD, cuja odontologia só é registrada por equipe, e quem está de férias (a nota da aba diz isso); (5) a situação da equipe do RH ("Completa", "Incompleta: CD…") não entrou: é texto livre.
- **Teste:** `testes/testar_lote3.py` (parte aberta sem IVT; porte e IVT recalculados fora do montar; aba com cadeado; depois de entrar, números da tela = JSON e lotação do JSON = planilha de RH; ordenar; Excel e CSV; celular).

## Revisão de 23/11/2026 (privacidade e limpeza)

- **O que o painel guarda da planilha de RH:** só unidade, gerência, equipe, tipo, situação e zona e, de cada pessoa, nome, categoria, cargo, carga horária, vínculo e um código embaralhado do CNS. CPF, matrícula e observações não são lidos.
- **Matrícula:** o arquivo `coleta\referencia_privada.json` deixou de existir; não há mais matrícula em nenhuma versão do painel.
- **CNS embaralhado já na coleta:** `coleta\coleta.py` grava o CNS do profissional já embaralhado (`coleta\sigilo.py`); o número real não chega ao disco. Por isso o passo de coleta do workflow agora também recebe o Segredo `APS_PEPPER` (no computador, vale o arquivo `coleta\pepper.local`).
- **Envio da lotação:** `enviar_rh.py` recusa enviar se houver campo a mais no arquivo ou CNS sem embaralhar.
- **Conferência antes de publicar:** `validar.py` confere também os nomes de quem registrou produção (não só os da lotação) e o formato do arquivo cifrado dos gestores.
- **Workflow:** cada tarefa tem só as permissões de que precisa; as versões dos pacotes ficam fixas em `coleta\requirements.txt`.
- **Como gerar a referência (lotação):** `python -X utf8 coleta\montar_referencia.py "<planilha>" coleta\referencia.json "RH APS Norte"`.
- **O que mudou nesta limpeza (os números do painel ficaram iguais; foi conferido comparando antes e depois):**
  - o decodificador do Power BI (`pbi_lib.py`) não decodifica mais duas vezes o valor repetido; teste em `coleta\teste_pbi_lib.py`;
  - a nova tentativa em caso de falha (3 vezes, 5 s) ficou num lugar só, dentro da consulta, e também vale para abrir o painel; se a página do InfoSaúde mudar, o erro diz que o iframe do Power BI não foi achado;
  - o que estava copiado em vários scripts (pastas, teto de linhas, endereços dos painéis, filtro de mês, data de Brasília) foi para `coleta\comum.py`; a "data de hoje" agora é sempre a de Brasília;
  - tirados códigos e variáveis sem uso; imports no topo; resumo impresso do `montar.py` sem artifícios;
  - `validar.py`: limiares com nome e comentário no topo, linha final quebrada;
  - profissional sem CNS e sem nome não vira "uma pessoa só": a linha é pulada e a contagem aparece no resumo (só se for maior que zero);
  - população: ano sem população usa o último ano disponível, como diz a nota publicada (hoje nenhum ano cai nesse caso);
  - docstring e comentários do `montar.py` atualizados.
- **Página (`site\index.html`), sem mudança no que aparece na tela (capturas antes × depois iguais):**
  - entrar: a mensagem de senha incorreta ficou separada da de arquivo restrito incompleto; a chave lembrada só é esquecida quando a senha de fato não confere;
  - entrar sem marcar "lembrar" apaga a chave guardada antes; **Sair** fecha a área dos gestores também nas outras abas abertas do mesmo navegador e tira os nomes da memória;
  - CSV: texto que começa com `=`, `+`, `-` ou `@` ganha um apóstrofo na frente, para o Excel não tratar como fórmula (número continua número);
  - relatório só com fichas individuais leva o mesmo aviso de dados nominais dos outros;
  - política de segurança de conteúdo (`Content-Security-Policy`) no cabeçalho: a página só carrega arquivos da própria pasta e não envia dados a outro endereço; conferida no Chrome e no Edge, pela internet e por duplo clique;
  - a caixa "Período" tem largura mínima: antes abria ora estreita, ora larga, e empurrava os botões de baixar para outra linha;
  - tirado o código sem uso (funções, estilos e todo o tratamento de matrícula, que deixou de existir).
- **Testes:** `testes\testar_sessao.py` (senha errada × arquivo incompleto, Sair entre abas, nomes fora da página depois de sair, CSV sem fórmula). Para esperar uma condição da página, os testes usam `esperar` (em `testes\_entrar.py`) no lugar de `wait_for_function`, que a política de segurança barra.
