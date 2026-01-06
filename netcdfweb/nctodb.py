import functools, os

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app
)
from werkzeug.security import check_password_hash, generate_password_hash

from netcdfweb.db import get_db

# from .nclist import bp as nclist_bp  # nclist 블루프린트로 이동할 수 있도록 추가

bp = Blueprint('nctodb', __name__, url_prefix='/nctodb')


@bp.route('/')
def nctodb():
  print('nctodb')
  return render_template('nctodb.html')


@bp.route('/upload', methods=['POST'])
def upload():
  files = request.files.getlist('file')
  print('불러온 파일들 : ', files)

  # 파일이 없거나 이름이 비어있으면 오류 메시지 후 목록 페이지로 이동
  if not files or all(f.filename == '' for f in files):
    flash('업로드할 파일을 선택하세요.')  # 오류 메시지 표시
    print('upload error : 파일들이 없거나 파일명에 오류가 있습니다')
    return redirect(url_for('nctodb.nctodb'))
  
  # 파일이 진짜 nc 파일인지 확인
  for file in files:
    if not file.filename.lower().endswith('.nc'):
      continue
    
    safe_name = os.path.basename(file.filename) # 파일명에 경로 정보가 포함되어 있으면 제거하고 파일명만 추출
    nc_path = os.path.join(current_app.config['UPLOAD_FOLDER'], safe_name)
    file.save(nc_path)  # 파일 저장
    insert_netcdf_file(nc_path)
    

  print('upload', [f.filename for f in files])
  return redirect(url_for('nclist.nclist'))  # nclist 블루프린트로 이동


def insert_netcdf_file(filename):
  '''
  NetCDF 파일을 읽어서 메타 정보를 추출하여 데이터베이스에 저장
  '''
  try:
    file_meta = extract_netcdf_file_info(filename)  # 파일명으로부터 메타 정보 추출
    netcdf_data = extract_netcdf_data(filename)  # NetCDF 파일을 읽어서 데이터를 Global Attributes와 Variables에서 추출
    print(f'file_meta: {file_meta}')
  except ValueError as e:
    print(f'Error inserting netcdf file: {e}')
    return None
  except Exception as e:
    print(f'Error inserting netcdf file: {e}')
    return None


def extract_netcdf_file_info(filename):
  basename = os.path.basename(filename) # 파일명만 추출
  basename = basename.replace('.nc', '') # .nc 제거
  
  datetime_str = ''
  
  # 파일명에 _가 있으면 파일명을 분리
  if '_' in basename:
    parts = basename.split('_') # 파일명을 _로 분리하여 리스트에 저장
    
    if len(parts) < 7:
      raise ValueError(f'파일 형식이 올바르지 않습니다. {basename}')
  
    satellite = parts[0] # 위성명
    sensor = parts[1] # 센서명
    data_level = parts[2] # 데이터 레벨
    variable_id = parts[3] # 변수/채널 ID
    region_code = parts[4] # 지역 코드
    region_name = parts[5] # 지역명
    datetime_str = parts[6] # 관측 시간
  else:
    # _가 없으면..
    if not basename.startswith('gk2a'): # gk2a로 시작하지 않으면 오류
      raise ValueError(f'파일명이 gk2a로 시작하지 않습니다. {basename}')
    
    remaining = basename[4:] # gk2a 제외하고 나머지 문자열 추출
    
    # 날짜 추출
    datetime_str = remaining[-12:] # 날짜 추출
    remaining = remaining[:-12] # 날짜 제외하고 나머지 문자열 추출, ex) # amile1bsw038ko020lc
    
    # 나머지에서 정보 추출
    satellite = 'gk2a' # 위성명
    
    # 나머지에서 센서명 추출
    sensor = remaining[:3] # 센서명 추출
    remaining = remaining[3:] # 센서명 제외하고 나머지 문자열 추출, ex) le1bsw038ko020lc    
    
    # 나머지에서 데이터 레벨 추출
    data_level = remaining[:4] # 데이터 레벨 추출
    remaining = remaining[4:] # 데이터 레벨 제외하고 나머지 문자열 추출, ex) sw038ko020lc
    
    # 나머지에서 변수/채널 ID 추출
    variable_id = remaining[:5] # 변수/채널 ID 추출
    remaining = remaining[5:] # 변수/채널 ID 제외하고 나머지 문자열 추출, ex) ko020lc
    
    region_code = remaining
    region_name = 'unknown'    
    
  year = datetime_str[:4]
  month = datetime_str[4:6]
  day = datetime_str[6:8]
  hour = datetime_str[8:10]
  minute = datetime_str[10:]  
  
  return {
    'filename': os.path.basename(filename),    
    'filepath': filename,
    'satellite': satellite,
    'sensor': sensor,
    'data_level': data_level,
    'variable_id': variable_id,
    'region_code': region_code,
    'region_name': region_name,
    'observation_datetime': datetime_str,
    'observation_date': f'{year}-{month}-{day}',
    'observation_time': f'{hour}:{minute}:00',
  }
    
    
def extract_netcdf_data(filename):
  '''
  NetCDF 파일을 읽어서 데이터를 Global Attributes와 Variables에서 추출
  list[], tuple(), set{}, dict{}
  '''
  # 반환할 메타데이터 구조 정의 및 초기화
  metadata = {
    'file_size': None,
    'data_start': None,
    'data_end': None,
    'variable_count': 0,
    'dimension_count': 0,
    'variables': [],
    'dimensions': [],
    'global_attributes': {},
    'has_coordinates': False,
    'lat_min': None,
    'lat_max': None,
    'lon_min': None,
    'lon_max': None,
  }
  
    
    
    