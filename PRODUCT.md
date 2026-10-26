# Product

<!-- impeccable:product-schema 1 -->

> Nota de procedência: o usuário optou por pular perguntas. Os campos abaixo foram **inferidos do briefing explícito**
> (mensagens da conversa de 2026-10-26) e estão marcados como `[inferido]` quando não vieram literalmente dele.

## Platform

web

## Stack

Delegado ao assistente (o usuário pediu para decidir com embasamento): React + Vite + TypeScript + Tailwind + Apache
ECharts no front; ETL em Python (uv, pandas, pydantic) que publica um snapshot JSON estático; deploy no GitHub Pages.

## Users

- **Quem vai avaliar o projeto** (recrutadores, gestores técnicos, times de dados/produto de empresas): abrem o link ou o
  README por poucos minutos e decidem se o autor entrega com qualidade. `[inferido]`
- **Quem usa o painel de verdade** (pessoa física curiosa sobre economia, gestor financeiro de PME): quer saber
  "como está o cenário macro hoje e o que isso significa para o meu dinheiro". `[inferido]`

## Product Purpose

Acompanhar a situação macroeconômica do Brasil (juros, inflação, câmbio e expectativas de mercado) em um painel de
leitura imediata, com dashboards muito visuais, insights explicáveis e orientações/dicas educativas. Sucesso = em poucos
segundos a pessoa entende o cenário e a lógica por trás de cada leitura; para o portfólio, demonstra engenharia de dados
(ETL agendado, validação de contrato), visualização e cuidado de produto. (Do briefing do usuário.)

## Positioning

Diferente de painéis que só despejam séries: cada número vem com a **regra que o explica** ("o que isso significa" +
"dica prática"), em linguagem simples, e tudo é reproduzível (sem IA generativa, sem caixa-preta). `[inferido]`

## Operating Context

Dados 100% públicos, sem chave: BCB (SGS e Olinda: PTAX, Focus) e IBGE (agregados). Atualização diária em dias úteis
por GitHub Actions; o site é estático (GitHub Pages). Idioma pt-BR.

## Capabilities and Constraints

- Sem LLM, sem segredos no front-end, sem servidor; o front só lê um JSON estático validado.
- Nunca "compre/venda": o conteúdo é educativo; aviso explícito de que não é recomendação de investimento.
- Dados reais apenas na interface (fixtures só em testes).
- Indecidido: monetização/hospedagem própria (fora do escopo; é projeto de portfólio).

## Brand Commitments

Nenhuma identidade pré-existente. Nome do projeto: **Radar Macro Brasil**. Autor: Herick Silva.

## Evidence on Hand

Nenhum cliente, depoimento ou métrica de uso existe e nenhum deve ser inventado. As fontes de dados públicas acima são a
única evidência factual.

## Product Principles

1. **Explicável antes de impressionante**: todo insight mostra a evidência e a regra usada.
2. **Honestidade de dados**: mostra data da última atualização e fonte; falha alto em vez de publicar dado velho.
3. **Educar, não aconselhar**: orientações genéricas e prudentes, sem recomendação individual de investimento.
4. **Leitura em 30 segundos**: o semáforo e os KPIs respondem "como está o cenário"; o detalhe fica um nível abaixo.

## Accessibility & Inclusion

Contraste AA, uso nunca só de cor (ícone + rótulo), alternativa em tabela para gráficos, respeito a
`prefers-reduced-motion` e a `prefers-color-scheme`. `[inferido]`
