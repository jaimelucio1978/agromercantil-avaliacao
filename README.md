# 📌 Módulo SQL — CEPEA (PostgreSQL)

Este módulo corresponde à **Etapa 1 do projeto Agromercantil / CEPEA**, responsável pela camada de persistência dos dados históricos de preços agrícolas provenientes do CEPEA/ESALQ.

O objetivo é fornecer uma base sólida, normalizada e performática para alimentar o **Streamlit, ETL e consultas analíticas**, garantindo integridade e velocidade nas operações.

---

## 🏛️ Modelagem do Banco de Dados

A tabela oficial deste módulo é:

| Campo       | Tipo             | Descrição |
|-------------|------------------|-----------|
| `data`      | DATE             | Data da cotação |
| `commodity` | VARCHAR(50)      | Nome do produto (ex: MILHO, SOJA, BOI) |
| `regiao`    | VARCHAR(150)     | Local de referência da cotação |
| `valor_brl` | NUMERIC(12,4)    | Preço em Real |
| `valor_usd` | NUMERIC(12,4)    | Preço em Dólar |
| `fonte`     | VARCHAR(50)      | Fonte do dado (default: CEPEA/ESALQ) |
| `dt_carga`  | TIMESTAMP        | Timestamp da carga |

A chave primária garante unicidade por **commodity + data + região**, evitando duplicidades em cargas recorrentes.

---

## 📌 Scripts incluídos neste módulo

| Arquivo | Objetivo |
|---------|----------|
| `01_create_table.sql` | Cria a tabela `cepea_preco_diario` |
| `02_create_indexes.sql` | Cria índices de performance para filtros e gráficos |
| `03_queries_dashboard.sql` | Contém queries oficiais usadas no Streamlit (KPIs e visualizações) |

---

## 🚀 Índices criados

Os índices otimizam os filtros mais comuns do dashboard:

```sql
commodity
data
(commodity, data)