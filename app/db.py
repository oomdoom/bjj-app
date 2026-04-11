import psycopg2
import os

def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME", "bjj"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS")
    )