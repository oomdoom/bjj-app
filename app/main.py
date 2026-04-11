from fastapi import FastAPI
import logging
import os
import psycopg2
import json
import boto3

app = FastAPI()
logging.basicConfig(level=logging.INFO)

def get_secret():
    secret_name = os.getenv("SECRET_NAME")
    region = os.getenv("AWS_REGION")

    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response["SecretString"])

def get_conn():
    secret = get_secret()

    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME", "bjj"),
        user=secret["username"],
        password=secret["password"]
    )

@app.get("/health")
def health():
    logging.info("Health check called")
    return {"status": "ok"}

@app.post("/init")
def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS techniques (
            id SERIAL PRIMARY KEY,
            name TEXT,
            position TEXT
        );
    """)

    cur.execute("""
        INSERT INTO techniques (name, position)
        VALUES
        ('Armbar', 'Guard'),
        ('Triangle', 'Guard'),
        ('Kimura', 'Side Control');
    """)

    conn.commit()
    cur.close()
    conn.close()

    return {"message": "initialized"}

@app.get("/techniques")
def get_techniques():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT name, position FROM techniques;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

@app.get("/metrics")
def metrics():
    return {"status": "ok"}