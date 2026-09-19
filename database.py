import os
import psycopg

def get_connection():
    return psycopg.connect(os.getenv("DATABASE_URL"))