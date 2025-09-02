def get_conn():
  import sqlite3, os
  os.makedirs('data', exist_ok=True)
  return sqlite3.connect('data/chap1.db')
