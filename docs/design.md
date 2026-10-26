# Decisões de design e de engenharia

Este documento registra as escolhas do Radar Macro Brasil, o motivo de cada uma e o que ficou de fora. Ele é a
referência para quem quiser entender por que o projeto é como é.

## 1. Produto

- **Pergunta que o painel responde:** "como está o cenário macro hoje e o que isso significa para o meu dinheiro?"
- **Público:** quem avalia o projeto (recrutadores, gestores técnicos) e pessoas curiosas sobre economia.
- **Modo da interface:** leitura em 30 segundos (semáforo e indicadores) com detalhe um nível abaixo. O simulador é
  uma ferramenta de operação, então ganhou formulário e tabela além do gráfico.
- **Educar, não aconselhar.** Todo insight traz a evidência, a regra que o gerou e uma orientação genérica. Não há
  recomendação individual. O rodapé diz isso explicitamente.

## 2. Direção visual

- **Mundo visual: "boletim de dados" editorial.** Papel quente, tinta quase preta, uma serif de display (Fraunces) para
  o veredito e os números-chave, e uma sans (Inter) para leitura, com dígitos tabulares em todos os valores. A hierarquia
  vem de tamanho e de filetes horizontais, não de cartões.
- **Por que não cartões:** o layout com cartões de ícone + título + texto é o padrão de template de painel. Aqui a
  estrutura é de página de jornal: seções separadas por filete, veredito grande, leituras em colunas.
- **Paleta de dados:** os oito slots categóricos e a paleta de status são os validados pelo skill `dataviz`
  (`validate_palette.js`). Usei só os três primeiros slots categóricos (Selic azul, IPCA laranja, dólar em azul de
  dados), que são os validados para combinações todos-contra-todos. Cor nunca carrega o estado sozinha: sempre vem com
  ícone e rótulo.
- **Modo escuro:** selecionado, não invertido. Os passos escuros da paleta foram escolhidos para a superfície escura e
  valem nos dois temas, seguindo o `prefers-color-scheme` e o atributo `data-theme`.
- **Alternativas descartadas:** (a) o roll de direção do `impeccable concept-seed` sorteou mundos como "lona de caminhão
  com adesivos", "mergulho em recife" e "dobradura de papel". São bons mundos, mas não servem a um painel financeiro
  que precisa transmitir sobriedade e legibilidade. Mantive a regra do skill de que "a clareza do produto vence
  conflitos" e não adotei nenhum deles. (b) Tema de "terminal financeiro" com fundo preto e verde: descartado por ser
  o clichê do setor e por dar sensação de urgência onde o objetivo é leitura calma.
- **Decisão tomada sem o fluxo interativo de perguntas,** a pedido do usuário. Registro aqui para que ele possa
  reverter.

## 3. Arquitetura

```
ETL Python (etl/)  --->  public/data/macro.json  --->  React (Vite) estático  --->  GitHub Pages
  BCB, IBGE          validado por Pydantic            validado por Zod            só leitura
```

- **Contrato em um lugar:** os modelos Pydantic em `etl/src/radar_etl/models.py` são a fonte. O JSON Schema sai deles
  (`schema/macro.schema.json`), e um teste Python garante que o arquivo publicado não está desatualizado.
- **Espelho Zod no front** (`src/lib/schema.ts`), escrito à mão e travado por teste contra o `macro.json` real. Gerar o
  Zod a partir do JSON Schema foi considerado, mas a ferramenta disponível adicionava uma dependência de geração sem
  ganho proporcional para um contrato deste tamanho.
- **Validação por seção:** cada seção do snapshot é validada à parte. Se o Focus vier inválido, a seção de Focus mostra
  o motivo e o resto da página segue. Só o `meta` é obrigatório, porque sem ele não há data nem fonte para mostrar, e
  publicar dado sem data vai contra o princípio de honestidade do produto.
- **Sem servidor e sem chamadas em runtime:** o front só lê um JSON do mesmo domínio. Por isso `connect-src 'self'`.

## 4. Segurança

- **CSP por `<meta>`, injetada só no build de produção** (plugin do Vite). O dev server injeta um preâmbulo inline do
  React Refresh, que a CSP bloquearia.
- **Diretivas:** `script-src 'self'`, `style-src 'self' 'unsafe-inline'` (o ECharts define estilos inline no canvas e
  no DOM), `connect-src 'self'`, `font-src 'self'`, `object-src 'none'`, `base-uri 'self'`, `form-action 'none'`.
- **`frame-ancestors` fora da CSP:** só vale como header HTTP, e o GitHub Pages não permite definir headers. Essa
  proteção contra clickjacking não existe neste site. É uma limitação da plataforma, não uma omissão.
- **Fontes self-hosted** por `@fontsource-variable`. Nenhum CDN de fonte ou script em runtime.
- **Sem `dangerouslySetInnerHTML`** em lugar nenhum.
- **Workflows com `permissions` mínimas:** `contents: read` por padrão; `pages: write` e `id-token: write` só no job de
  publicação.
- **Sem commit de volta pelo bot.** O snapshot é gerado no runner e publicado como artefato. Isso dá menos privilégio
  (nada precisa de `contents: write`) e mantém o histórico limpo. O custo é que o `macro.json` versionado no repositório
  é apenas o último snapshot de desenvolvimento, e não o do dia.
- **Dependabot** para npm, uv (`/etl`) e GitHub Actions, em atualizações semanais agrupadas por minor/patch.

## 5. ETL e agendamento

- **Cron em dias úteis, 12:30 UTC** (09:30 em Brasília), depois da divulgação diária do BCB.
- **Falha mantém o deploy anterior.** O job `etl` sai com erro se alguma fonte falhar ou se o contrato for violado. O
  job `site` depende dele (`needs: etl`), então nada é publicado, e o GitHub Pages continua servindo a versão anterior.
- **Retry com backoff e User-Agent descritivo** nas chamadas HTTP; respeito aos limites de cada API.
- **Sem chaves de API.** Todas as fontes são públicas.

## 6. Insights e semáforo

- **Insights por regras, sem IA generativa.** Cada regra é uma função pura do ETL, testada com dados inventados
  apenas dentro de `etl/tests/`.
- **Semáforo por pior estado:** cada frente (juros, inflação, câmbio) herda o pior estado de seus insights, e o
  semáforo geral é o pior entre as frentes. Pior estado é mais fácil de auditar do que média ponderada.
- **Juro real ex-ante** (Selic meta contra o IPCA esperado do Focus) para o insight; o gráfico usa o **juro real
  ex-post** (Selic do fim do mês contra o IPCA acumulado em 12 meses). São duas definições diferentes e a página
  explica as duas.

## 7. Simulador

- **Premissas explícitas e fixas:** poupança com 0,5% a.m. quando a Selic está acima de 8,5% a.a. e 70% da Selic em
  outros casos; CDB com a tabela regressiva de IR (22,5%, 20%, 17,5% e 15%, por dias corridos); LCI/LCA isentas.
- **Limitações assumidas:** a TR não é coletada pelo ETL, então a poupança sai sem TR. IOF, taxas de corretagem,
  come-cotas e custos de fundos não entram. A inflação para o valor de hoje é a expectativa do Focus, não a inflação
  pessoal de quem usa.
- **Formulário sem submit real:** o cálculo é reativo e os campos validam antes de calcular, com mensagem em
  `role="alert"`.

## 8. Acessibilidade

- Tokens de texto separados dos tokens de dado, para que a cor de série nunca seja usada como cor de texto. Os contrastes foram conferidos na paleta, mas não há teste automatizado de contraste.
- Todo gráfico tem `role="img"` com `aria-label` e uma descrição em `figcaption`. Cada gráfico tem também uma tabela
  alternativa em `<details>`.
- Foco visível com o token `--focus`; link de "pular para o conteúdo".
- `prefers-reduced-motion` desliga animações (CSS e animação do ECharts).

## 9. Testes e qualidade

- **Front (Vitest + jsdom):** contrato Zod contra o `macro.json` real; degradação por seção; simulador (tabela de IR,
  poupança, LCI sem IR, deflação); formatação pt-BR.
- **ETL (pytest):** transformações, regras de insight, checagens de qualidade, modelos, parsers com cliente falso e
  consistência entre o schema publicado e o código.
- **Lint:** ESLint com `strictTypeChecked` do typescript-eslint e regras de hooks do React; ruff no ETL.
- **Verificação visual:** capturas em 1440x900 e 390x844 do `vite preview` (porta 4171), sem erros de console nem de CSP.

## 10. Alternativas descartadas (resumo)

| Tema | Escolhido | Descartado | Motivo |
|---|---|---|---|
| Framework | React + Vite | Next.js | Site estático puro; não há necessidade de renderização no servidor. |
| Gráficos | Apache ECharts (importação modular) | Recharts, D3 | ECharts cobre séries temporais, bandas e marcações com menos código próprio. |
| Estilo | Tailwind v4 + tokens CSS | CSS-in-JS | Tokens em CSS permitem trocar o tema sem recompilar. |
| Validação front | Zod | Só tipos TS | Dado externo precisa de validação em tempo de execução. |
| Deploy | GitHub Actions + Pages | Servidor próprio | Projeto de portfólio, sem custo e sem segredos. |

## 11. Limitações conhecidas

- O ETL não coleta a TR nem o IPCA por região; o simulador mostra isso.
- O gráfico de grupos do IPCA usa a última referência disponível do IBGE, que pode estar alguns meses atrás.
- `frame-ancestors` não é aplicável (ver seção 4).
- O bundle de JavaScript tem cerca de 900 kB sem compressão, quase todo do ECharts, e o build emite aviso de chunk
  grande. Carregar o simulador e os gráficos sob demanda seria o próximo passo.
- Não há testes end-to-end automatizados; a verificação visual foi manual, com capturas registradas.
- A tabela do simulador rola horizontalmente dentro do próprio contêiner em telas de 390 px.
