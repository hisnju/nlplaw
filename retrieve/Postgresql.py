import psycopg2
from flask import Flask, request, abort
import os
from ngest_and_store_vector_data_into_PostgreSQL_using_pgvector import *
from psycopg2 import pool


connection_string = "dbname= user= password= host= port="
# 创建连接池
connection_pool = psycopg2.pool.SimpleConnectionPool(1, 10, connection_string)

def insert_user(user_id, user_name):
    # 从连接池中获取一个连接
    conn = connection_pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO users (user_id, user_name) VALUES (%s, %s) ON CONFLICT (user_id) DO NOTHING",
                    (user_id, user_name))
        conn.commit()
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # 归还连接到连接池
        connection_pool.putconn(conn)
        if cur is not None:
            cur.close()

def insert_conversation(user_id, question, answer):
    # 从连接池中获取一个连接
    conn = connection_pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO Conversation (user_id, question, answer) VALUES (%s, %s, %s)",
                    (user_id, question, answer))
        conn.commit()
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # 归还连接到连接池
        connection_pool.putconn(conn)
        if cur is not None:
            cur.close()

