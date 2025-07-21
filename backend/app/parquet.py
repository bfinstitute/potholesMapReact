import duckdb

duckdb.sql("""
    COPY (SELECT * FROM read_csv_auto('C:/Users/HP/Desktop/BFI/potholemap_and_chatbot-main/Data/potholes_cleaned.csv'))
    TO 'potholes.parquet' (FORMAT PARQUET)
""")
