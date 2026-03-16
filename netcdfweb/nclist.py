import math

from flask import (
    Blueprint, render_template, request
)

from netcdfweb.db import get_db

bp = Blueprint('nclist', __name__, url_prefix='/nclist')

# 한 페이지에 표시할 파일 개수
PER_PAGE = 20


@bp.route('/')
def nclist():
  '''
  NetCDF 파일 목록을 데이터베이스에서 조회하여 페이지네이션과 함께 표시
  쿼리 파라미터: page (페이지 번호, 기본값 1)
  '''
  db = get_db()
  cursor = db.cursor()

  # 현재 페이지 번호 (기본값 1, 1 미만이면 1로 보정)
  page = request.args.get('page', 1, type=int)
  if page < 1:
    page = 1

  # 전체 파일 개수 조회 — 페이지네이션 계산에 사용
  cursor.execute('SELECT COUNT(*) AS total FROM netcdf_files')
  total = cursor.fetchone()['total']

  # 전체 페이지 수 계산 (올림 처리)
  total_pages = max(1, math.ceil(total / PER_PAGE))

  # 현재 페이지가 최대 페이지를 초과하면 마지막 페이지로 보정
  if page > total_pages:
    page = total_pages

  # OFFSET 계산 — 현재 페이지에 해당하는 데이터 시작 위치
  offset = (page - 1) * PER_PAGE

  # 파일 목록 조회 — 최신 관측 시간 순으로 정렬
  cursor.execute('''
    SELECT id, filename, satellite, sensor, variable_id,
           region_code, region_name, observation_datetime,
           file_size, has_preview, variable_count
    FROM netcdf_files
    ORDER BY observation_datetime DESC
    LIMIT %s OFFSET %s
  ''', (PER_PAGE, offset))

  files = cursor.fetchall()

  return render_template('nclist.html',
    files=files,
    page=page,
    total_pages=total_pages,
    total=total,
  )
