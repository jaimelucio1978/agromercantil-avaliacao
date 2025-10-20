-- ============================================
-- QUERIES DE NEGÓCIO (NÍVEL SÊNIOR) – CEPEA
-- Autor: Jaime (processo Agromercantil)
-- Base: cepea_preco_diario (data, commodity, regiao, valor_brl, valor_usd)
-- Convenções:
--  - Datas em ordem crescente
--  - Funções de janela para análises temporais
--  - Comparação MILHO x SOJA usando SOJA (BRASIL) como referência
--  - Moeda padrão para análises: R$ (valor_brl)
-- ============================================

-- ============================================
-- BLOCO 1 — Tendência e Evolução
-- ============================================

-- 01) Série histórica (base)
-- Use WHERE para filtrar commodity/região conforme necessário.
SELECT
  data,
  commodity,
  regiao,
  valor_brl,
  valor_usd
FROM cepea_preco_diario
ORDER BY data, commodity, regiao;

-- 02) Evolução % acumulada desde o 1º preço por série (commodity+região)
WITH base AS (
  SELECT
    data, commodity, regiao, valor_brl,
    FIRST_VALUE(valor_brl) OVER (PARTITION BY commodity, regiao ORDER BY data) AS preco_inicial
  FROM cepea_preco_diario
)
SELECT
  data,
  commodity,
  regiao,
  valor_brl,
  preco_inicial,
  CASE WHEN preco_inicial > 0 THEN (valor_brl / preco_inicial - 1.0) * 100 ELSE NULL END AS evolucao_pct_desde_inicio
FROM base
ORDER BY commodity, regiao, data;

-- 03) Variação diária % (D-1) por série
SELECT
  data,
  commodity,
  regiao,
  valor_brl,
  LAG(valor_brl) OVER (PARTITION BY commodity, regiao ORDER BY data) AS valor_brl_d1,
  CASE
    WHEN LAG(valor_brl) OVER (PARTITION BY commodity, regiao ORDER BY data) > 0
    THEN (valor_brl / LAG(valor_brl) OVER (PARTITION BY commodity, regiao ORDER BY data) - 1.0) * 100
    ELSE NULL
  END AS variacao_pct_d1
FROM cepea_preco_diario
ORDER BY commodity, regiao, data;

-- 04) Tendência de longo prazo: média móvel de 90 dias (MM90)
SELECT
  data,
  commodity,
  regiao,
  valor_brl,
  AVG(valor_brl) OVER (PARTITION BY commodity, regiao ORDER BY data ROWS BETWEEN 89 PRECEDING AND CURRENT ROW) AS mm90_brl
FROM cepea_preco_diario
ORDER BY commodity, regiao, data;

-- ============================================
-- BLOCO 2 — Comparação Milho x Soja (referência: SOJA BRASIL)
-- ============================================

-- 05) Correlação estatística MILHO (BRASIL) x SOJA (BRASIL)
-- Nota: corr(y, x) é um agregado estatístico nativo do PostgreSQL.
WITH milho AS (
  SELECT data, valor_brl AS milho_brl
  FROM cepea_preco_diario
  WHERE commodity = 'MILHO' AND regiao = 'BRASIL'
),
soja_br AS (
  SELECT data, valor_brl AS soja_brl
  FROM cepea_preco_diario
  WHERE commodity = 'SOJA' AND regiao = 'BRASIL'
),
pareado AS (
  SELECT m.data, m.milho_brl, s.soja_brl
  FROM milho m
  JOIN soja_br s USING (data)
)
SELECT
  COUNT(*) AS dias_pareados,
  corr(milho_brl, soja_brl) AS correlacao_milho_soja_brl
FROM pareado;

-- 06) Spread diário (Milho R$ – Soja BRASIL R$)
WITH milho AS (
  SELECT data, valor_brl AS milho_brl
  FROM cepea_preco_diario
  WHERE commodity = 'MILHO' AND regiao = 'BRASIL'
),
soja_br AS (
  SELECT data, valor_brl AS soja_brl
  FROM cepea_preco_diario
  WHERE commodity = 'SOJA' AND regiao = 'BRASIL'
)
SELECT
  m.data,
  m.milho_brl,
  s.soja_brl,
  (m.milho_brl - s.soja_brl) AS spread_brl
FROM milho m
JOIN soja_br s USING (data)
ORDER BY m.data;

-- 07) Diferença % MILHO vs SOJA BRASIL
WITH milho AS (
  SELECT data, valor_brl AS milho_brl
  FROM cepea_preco_diario
  WHERE commodity = 'MILHO' AND regiao = 'BRASIL'
),
soja_br AS (
  SELECT data, valor_brl AS soja_brl
  FROM cepea_preco_diario
  WHERE commodity = 'SOJA' AND regiao = 'BRASIL'
)
SELECT
  m.data,
  m.milho_brl,
  s.soja_brl,
  CASE WHEN s.soja_brl > 0 THEN (m.milho_brl / s.soja_brl - 1.0) * 100 ELSE NULL END AS dif_pct_milho_vs_soja
FROM milho m
JOIN soja_br s USING (data)
ORDER BY m.data;

-- ============================================
-- BLOCO 3 — Analytics Estatístico
-- ============================================

-- 08) Médias móveis 7 e 30 dias (MM7, MM30) por série
SELECT
  data,
  commodity,
  regiao,
  valor_brl,
  AVG(valor_brl) OVER (PARTITION BY commodity, regiao ORDER BY data ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)  AS mm7_brl,
  AVG(valor_brl) OVER (PARTITION BY commodity, regiao ORDER BY data ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS mm30_brl
FROM cepea_preco_diario
ORDER BY commodity, regiao, data;

-- 09) Volatilidade 30 dias (desvio padrão móvel) por série
SELECT
  data,
  commodity,
  regiao,
  valor_brl,
  STDDEV(valor_brl) OVER (PARTITION BY commodity, regiao ORDER BY data ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS vol30_brl
FROM cepea_preco_diario
ORDER BY commodity, regiao, data;

-- 10) Z-Score (normalização) por série (base histórica completa)
WITH stats AS (
  SELECT
    commodity,
    regiao,
    AVG(valor_brl)   AS media_brl,
    STDDEV(valor_brl) AS desvio_brl
  FROM cepea_preco_diario
  GROUP BY commodity, regiao
)
SELECT
  d.data,
  d.commodity,
  d.regiao,
  d.valor_brl,
  (d.valor_brl - s.media_brl) / NULLIF(s.desvio_brl, 0) AS zscore_brl
FROM cepea_preco_diario d
JOIN stats s USING (commodity, regiao)
ORDER BY d.commodity, d.regiao, d.data;

-- 11) Sinal de tendência (UP/DOWN/FLAT) via MM7 vs MM30
WITH mov AS (
  SELECT
    data,
    commodity,
    regiao,
    valor_brl,
    AVG(valor_brl) OVER (PARTITION BY commodity, regiao ORDER BY data ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)  AS mm7_brl,
    AVG(valor_brl) OVER (PARTITION BY commodity, regiao ORDERBY data ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS mm30_brl
  FROM cepea_preco_diario
)
SELECT
  data,
  commodity,
  regiao,
  valor_brl,
  mm7_brl,
  mm30_brl,
  CASE
    WHEN mm7_brl IS NULL OR mm30_brl IS NULL THEN NULL
    WHEN mm7_brl > mm30_brl THEN 'UP'
    WHEN mm7_brl < mm30_brl THEN 'DOWN'
    ELSE 'FLAT'
  END AS sinal_tendencia
FROM mov
ORDER BY commodity, regiao, data;

-- ============================================
-- BLOCO 4 — Sazonalidade e Tempo
-- ============================================

-- 12) Variação mensal (último dia do mês vs mês anterior) por série
WITH mensais AS (
  SELECT
    DATE_TRUNC('month', data)::date AS mes,
    commodity,
    regiao,
    LAST_VALUE(valor_brl) OVER (PARTITION BY commodity, regiao, DATE_TRUNC('month', data) ORDER BY data
                                RANGE BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS valor_fechamento_mes
  FROM cepea_preco_diario
),
fechamento AS (
  SELECT DISTINCT mes, commodity, regiao, valor_fechamento_mes
  FROM mensais
)
SELECT
  mes,
  commodity,
  regiao,
  valor_fechamento_mes,
  LAG(valor_fechamento_mes) OVER (PARTITION BY commodity, regiao ORDER BY mes) AS mes_anterior,
  CASE
    WHEN LAG(valor_fechamento_mes) OVER (PARTITION BY commodity, regiao ORDER BY mes) > 0
    THEN (valor_fechamento_mes / LAG(valor_fechamento_mes) OVER (PARTITION BY commodity, regiao ORDER BY mes) - 1.0) * 100
    ELSE NULL
  END AS variacao_pct_mensal
FROM fechamento
ORDER BY commodity, regiao, mes;

-- 13) Variação anual (fechamento ano vs ano anterior) por série
WITH anuais AS (
  SELECT
    DATE_TRUNC('year', data)::date AS ano,
    commodity,
    regiao,
    LAST_VALUE(valor_brl) OVER (PARTITION BY commodity, regiao, DATE_TRUNC('year', data) ORDER BY data
                                RANGE BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS valor_fechamento_ano
  FROM cepea_preco_diario
),
fechamento AS (
  SELECT DISTINCT ano, commodity, regiao, valor_fechamento_ano
  FROM anuais
)
SELECT
  ano,
  commodity,
  regiao,
  valor_fechamento_ano,
  LAG(valor_fechamento_ano) OVER (PARTITION BY commodity, regiao ORDER BY ano) AS ano_anterior,
  CASE
    WHEN LAG(valor_fechamento_ano) OVER (PARTITION BY commodity, regiao ORDER BY ano) > 0
    THEN (valor_fechamento_ano / LAG(valor_fechamento_ano) OVER (PARTITION BY commodity, regiao ORDER BY ano) - 1.0) * 100
    ELSE NULL
  END AS variacao_pct_anual
FROM fechamento
ORDER BY commodity, regiao, ano;

-- 14) Melhor mês médio histórico por commodity (sazonalidade)
-- Resultado: para cada commodity, qual mês historicamente tem maior preço médio?
WITH saz AS (
  SELECT
    commodity,
    EXTRACT(MONTH FROM data)::int AS mes,
    AVG(valor_brl) AS preco_medio_mes
  FROM cepea_preco_diario
  GROUP BY commodity, EXTRACT(MONTH FROM data)
),
ranked AS (
  SELECT
    commodity,
    mes,
    preco_medio_mes,
    RANK() OVER (PARTITION BY commodity ORDER BY preco_medio_mes DESC) AS rk
  FROM saz
)
SELECT
  commodity,
  mes,
  preco_medio_mes
FROM ranked
WHERE rk = 1
ORDER BY commodity;

-- ============================================
-- BLOCO 5 — Business Insights (Executivo)
-- ============================================

-- 15) Último preço por série + variação D-1 + ranking por commodity
-- Inclui "alerta" quando |variação| > 3% (ajuste conforme necessidade).
WITH ult AS (
  SELECT
    *,
    ROW_NUMBER() OVER (PARTITION BY commodity, regiao ORDER BY data DESC) AS rn
  FROM cepea_preco_diario
),
ultimos AS (
  SELECT data, commodity, regiao, valor_brl
  FROM ult
  WHERE rn = 1
),
d1 AS (
  SELECT
    a.commodity,
    a.regiao,
    a.valor_brl AS valor_ultimo,
    b.valor_brl AS valor_d1,
    a.data      AS data_ultimo
  FROM ultimos a
  LEFT JOIN cepea_preco_diario b
    ON b.commodity = a.commodity
   AND b.regiao    = a.regiao
   AND b.data = (
     SELECT MAX(data) FROM cepea_preco_diario
     WHERE commodity = a.commodity AND regiao = a.regiao AND data < a.data
   )
),
calc AS (
  SELECT
    commodity,
    regiao,
    data_ultimo,
    valor_ultimo,
    valor_d1,
    CASE WHEN valor_d1 > 0 THEN (valor_ultimo / valor_d1 - 1.0) * 100 ELSE NULL END AS variacao_pct_d1
  FROM d1
),
ranked AS (
  SELECT
    *,
    RANK() OVER (PARTITION BY commodity ORDER BY valor_ultimo DESC) AS ranking_regiao_por_preco
  FROM calc
)
SELECT
  commodity,
  regiao,
  data_ultimo,
  valor_ultimo,
  valor_d1,
  variacao_pct_d1,
  CASE WHEN variacao_pct_d1 IS NOT NULL AND ABS(variacao_pct_d1) > 3 THEN 'ALERTA' ELSE 'OK' END AS alerta,
  ranking_regiao_por_preco
FROM ranked
ORDER BY commodity, ranking_regiao_por_preco;