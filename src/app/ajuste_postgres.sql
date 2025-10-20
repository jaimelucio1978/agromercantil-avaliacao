-- docs/sql/ajuste_postgres.sql
CREATE TABLE IF NOT EXISTS cepea_precos (
    data        date        NOT NULL,
    commodity   text        NOT NULL,
    regiao      text        NOT NULL,
    preco_rs    double precision,
    preco_usd   double precision,
    Fonte       text        NOT NULL DEFAULT 'CEPEA/ESALQ'
);

-- Índices úteis
CREATE INDEX IF NOT EXISTS idx_cepea_precos_data ON cepea_precos(data);
CREATE INDEX IF NOT EXISTS idx_cepea_precos_dim ON cepea_precos(commodity, regiao);