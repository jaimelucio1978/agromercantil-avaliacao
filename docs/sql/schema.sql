-- Cria o database caso não exista
CREATE DATABASE agromercantil;

-- Conecta no database
\c agromercantil;

-- Cria a tabela final do CEPEA
CREATE TABLE IF NOT EXISTS cepea_preco_diario (
    data        DATE        NOT NULL,
    commodity   VARCHAR(20) NOT NULL,
    regiao      VARCHAR(20) NOT NULL,
    valor_brl   NUMERIC(12,4) NOT NULL,
    valor_usd   NUMERIC(12,4) NOT NULL,
    PRIMARY KEY (data, commodity, regiao)
);