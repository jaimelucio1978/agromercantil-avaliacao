import psycopg2
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CURATED = ROOT / "data" / "curated" / "preco_diario_curated.csv"

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    dbname="agromercantil",
    user="postgres",
    password="123456"
)

df = pd.read_csv(CURATED)

cursor = conn.cursor()

for _, row in df.iterrows():
    cursor.execute("""
        INSERT INTO cepea_preco_diario (data, commodity, regiao, valor_brl, valor_usd)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (data, commodity, regiao) DO NOTHING;
    """, (row["data"], row["commodity"], row["regiao"], row["valor_brl"], row["valor_usd"]))

conn.commit()
cursor.close()
conn.close()

print("\n✅ CARGA FINALIZADA COM SUCESSO NO POSTGRESQL!\n")