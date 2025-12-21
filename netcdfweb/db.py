import pymysql
from pymysql.cursors import DictCursor
from flask import current_app, g

# 기본 MySQL 접속 정보 (config 값이 없을 때 사용)
DB_DEFAULTS = {
  "host": "localhost",
  "port": 3306,
  "user": "root",
  "password": "1234",
  "database": "netcdfweb",
}


def _mysql_config():
  cfg = current_app.config
  return {
    "host": cfg.get("DB_HOST", DB_DEFAULTS["host"]),
    "port": int(cfg.get("DB_PORT", DB_DEFAULTS["port"])),
    "user": cfg.get("DB_USER", DB_DEFAULTS["user"]),
    "password": cfg.get("DB_PASSWORD", DB_DEFAULTS["password"]),
    "database": cfg.get("DB_NAME", DB_DEFAULTS["database"]),
    "cursorclass": DictCursor,
    "charset": "utf8mb4",
    "autocommit": True,
  }


def get_db():
  if "db" not in g:
    g.db = pymysql.connect(**_mysql_config())
  return g.db


def close_db(e=None):
  db = g.pop("db", None)
  if db is not None:
    db.close()
