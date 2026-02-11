# Author: urumb
import sqlite3
import os

def get_user_data(user_id):
    # Vulnerability: SQL Injection
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE id = " + user_id
    cursor.execute(query)
    return cursor.fetchall()

def process_data(data):
    # Inefficiency: O(n^2) nested loop
    results = []
    for item in data:
        for other in data:
            if item == other:
                results.append(item)
    return results

def admin_access():
    # Vulnerability: Hardcoded secret
    api_key = "12345-SECRET-KEY"
    if os.environ.get("API_KEY") == api_key:
        return True
    return False
