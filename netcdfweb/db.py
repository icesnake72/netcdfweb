import pymysql
from pymysql.cursors import DictCursor
from flask import current_app, g
import click

# 기본 MySQL 접속 정보 (config 값이 없을 때 사용)
DB_DEFAULTS = {
  "host": "localhost",
  "port": 3306,
  "user": "root",
  "password": "1234",
  "database": "netcdf",
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

def init_db():
  '''
  데이터베이스 초기화
  '''
  db = get_db()
  with current_app.open_resource('db.sql') as f:
      sql = f.read().decode('utf8')

  # PyMySQL에는 executescript가 없으므로 문장 단위로 실행
  with db.cursor() as cursor:
    for statement in sql.split(';'):
      stmt = statement.strip()
      if not stmt:
        continue
      cursor.execute(stmt)

  db.commit()


@click.command('init-db')
def init_db_command():
  """
  Clear the existing data and create new tables.
  
  터미널에서 실행하는 명령어:
  flask --app netcdfweb init-db
  """
  # init_db()
  click.echo('Initialized the database.')

    
def init_app(app):
  '''
  앱 초기화
  '''
  app.teardown_appcontext(close_db)     # 앱 종료시 데이터베이스 연결 종료
  app.cli.add_command(init_db_command)  # 터미널에서 실행하는 명령어 추가


