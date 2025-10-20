# 📌 Agromercantil — CEPEA Data Pipeline

Pipeline completo para ingestão, armazenamento, análise e visualização de preços agrícolas do **CEPEA/ESALQ**, utilizando **Python, PostgreSQL e Streamlit**. O objetivo é fornecer uma base confiável e automatizável para análises financeiras, comparativos entre commodities, identificação de tendências e apoio à tomada de decisão no agronegócio.

---

## 📌 Arquitetura do Projeto



[ Scraper / ETL ] → [ PostgreSQL ] → [ Streamlit Dashboard ]


- **Python (Pandas/ETL):** trata, padroniza e carrega os dados
- **PostgreSQL:** armazena a série histórica em estrutura analítica
- **Streamlit:** exibe KPIs, gráficos e comparativos

---

## 🏗️ Banco de Dados (Etapa 1 — Concluída ✅)

A camada SQL está documentada em:  
📌 `/sql/README.md`

Principais características:

| Item | Status |
|--------|--------|
| Tabela única padronizada | ✅ `cepea_preco_diario` |
| Chave primária | ✅ `(data, commodity, regiao)` |
| Tipos numéricos com 4 casas decimais | ✅ |
| Índices de performance | ✅ |

---

## 📊 Dashboard (Streamlit)

O dashboard oferece:

✅ Série histórica  
✅ KPIs (máximo, mínimo, média, última cotação)  
✅ Variação diária (%)  
✅ Médias móveis (MM7, MM30, MM90)  
✅ Volatilidade (30 dias)  
✅ Ranking por região  
✅ Comparação entre commodities (ex: Milho x Soja)

---

## 🖼️ Screenshots do Dashboard

---

## ▶️ Como Executar o Projeto

### 1) Criar ambiente Python
```sh
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.txt

2) Configurar banco PostgreSQL

Criar a database:

CREATE DATABASE agromercantil;


Executar os scripts do diretório /sql na sequência:

01_create_table.sql

02_create_indexes.sql

3) Rodar o ETL (opcional por enquanto)
python src/etl/etl_cepea.py

4) Rodar o Streamlit
streamlit run src/app/streamlit_app.py

🛠️ Tecnologias Utilizadas
Categoria	Tecnologia
Banco	PostgreSQL
Backend / ETL	Python + Pandas
Visualização	Streamlit
Versão de Código	Git + GitHub
📌 Próximas Etapas (Roadmap)
Ordem	Etapa	Status
1	SQL / Modelagem	✅ Concluída
2	ETL Automatizado (cron/agendamento)	⏳
3	Logs e Data Quality	⏳
4	Deploy do Dashboard	⏳
👤 Autor

Jaime — Projeto Agromercantil
Contato e contribuições são bem-vindos.

✅ Status do Projeto

Módulo SQL finalizado e Dashboard funcional.
