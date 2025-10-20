-- =====================================================================
-- 03) QUERIES OFICIAIS DO DASHBOARD CEPEA (PostgreSQL)
-- Projeto: Agromercantil / CEPEA
-- Objetivo: Fornecer indicadores e séries históricas para o Streamlit
-- Tabelas utilizadas: cepea_preco_diario
-- =====================================================================

-- 01) Série histórica básica (gráfico principal)
SELECT
    data,
    commodity,
    regiao,
    valor_brl,
    valor_usd
FROM cepea_preco_diario
WHERE commodity = :commodity
ORDER BY data ASC;

-- 02) KPIs — preço atual, máximo, mínimo e média no período
SELECT
    MAX(valor_brl) AS max_brl,
    MIN(valor_brl) AS min_brl,
    AVG(valor_brl) AS avg_brl
FROM cepea_preco_diario
WHERE commodity = :commodity;

-- 03) Último preço disponível por região (snapshot)
WITH ult AS (
    SELECT
        data,
        commodity,
        regiao,
        valor_brl,
        ROW_NUMBER() OVER (PARTITION BY commodity, regiao ORDER BY data DESC) AS rn
    FROM cepea_preco_diario
)
SELECT data, commodity, regiao, valor_brl
FROM ult
WHERE rn = 1
ORDER BY valor_brl DESC;

-- 04) Variação diária (%D-1)
SELECT
    data,
    commodity,
    regiao,
    valor_brl,
    LAG(valor_brl) OVER (PARTITION BY commodity, regiao ORDER BY data) AS valor_d1,
    CASE
        WHEN LAG(valor_brl) OVER (PARTITION BY commodity, regiao ORDER BY data) > 0
        THEN (valor_brl / LAG(valor_brl) OVER (PARTITION BY commodity, regiao ORDER BY data) - 1.0) * 100
        ELSE NULL
    END AS variacao_pct_d1
FROM cepea_preco_diario
WHERE commodity = :commodity
ORDER BY regiao, data;

-- 05) Médias móveis (MM7 / MM30 / MM90)
SELECT
    data,
    commodity,
    regiao,
    valor_brl,
    AVG(valor_brl) OVER (PARTITION BY commodity, regiao ORDER BY data ROWS BETWEEN 6 PRECEDING  AND CURRENT ROW) AS mm7,
    AVG(valor_brl) OVER (PARTITION BY commodity, regiao ORDER BY data ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS mm30,
    AVG(valor_brl) OVER (PARTITION BY commodity, regiao ORDER BY data ROWS BETWEEN 89 PRECEDING AND CURRENT ROW) AS mm90
FROM cepea_preco_diario
WHERE commodity = :commodity
ORDER BY data;

-- 06) Volatilidade (desvio padrão 30 dias)
SELECT
    data,
    commodity,
    regiao,
    valor_brl,
    STDDEV(valor_brl) OVER (PARTITION BY commodity, regiao ORDER BY data ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS vol30
FROM cepea_preco_diario
WHERE commodity = :commodity
ORDER BY data ASC;