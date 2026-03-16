import functools, os, json
import netCDF4
import numpy as np


from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app
)

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
  반환값: 성공 시 삽입된 레코드의 id, 실패 시 None
  '''
  try:
    file_meta = extract_netcdf_file_info(filename)  # 파일명으로부터 메타 정보 추출
    netcdf_data = extract_netcdf_data(filename)  # NetCDF 파일을 읽어서 데이터를 Global Attributes와 Variables에서 추출

    # 파일 메타정보와 NetCDF 데이터를 합쳐서 DB에 저장할 데이터 구성
    db = get_db()
    cursor = db.cursor()

    # INSERT 쿼리 실행 — netcdf_files 테이블에 메타정보 저장
    sql = '''
      INSERT INTO netcdf_files (
        filename, filepath, satellite, sensor, data_level, variable_id,
        region_code, region_name, observation_datetime, observation_date,
        observation_time, file_size, variables, dimensions, global_attributes,
        variable_count, dimension_count, has_coordinates,
        lat_min, lat_max, lon_min, lon_max
      ) VALUES (
        %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s,
        %s, %s, %s, %s, %s,
        %s, %s, %s,
        %s, %s, %s, %s
      )
    '''

    # 관측 시간 문자열을 datetime 형식으로 변환 (YYYY-MM-DD HH:MM:SS)
    obs_datetime = f"{file_meta['observation_date']} {file_meta['observation_time']}"

    # variables 리스트와 dimensions/global_attributes 딕셔너리를 JSON 문자열로 변환
    variables_json = json.dumps(netcdf_data['variables'], ensure_ascii=False)
    dimensions_json = json.dumps(netcdf_data['dimensions'], ensure_ascii=False)
    global_attrs_json = json.dumps(netcdf_data['global_attributes'], ensure_ascii=False)

    params = (
      file_meta['filename'],           # filename
      file_meta['filepath'],           # filepath
      file_meta['satellite'],          # satellite (위성명)
      file_meta['sensor'],             # sensor (센서명)
      file_meta['data_level'],         # data_level (데이터 레벨)
      file_meta['variable_id'],        # variable_id (변수/채널 ID)
      file_meta['region_code'],        # region_code (지역 코드)
      file_meta['region_name'],        # region_name (지역명)
      obs_datetime,                    # observation_datetime (관측 일시)
      file_meta['observation_date'],   # observation_date (관측 날짜)
      file_meta['observation_time'],   # observation_time (관측 시간)
      netcdf_data['file_size'],        # file_size (파일 크기)
      variables_json,                  # variables (변수 목록 JSON)
      dimensions_json,                 # dimensions (차원 정보 JSON)
      global_attrs_json,               # global_attributes (글로벌 속성 JSON)
      netcdf_data['variable_count'],   # variable_count (변수 개수)
      netcdf_data['dimension_count'],  # dimension_count (차원 개수)
      netcdf_data['has_coordinates'],  # has_coordinates (좌표계 포함 여부)
      netcdf_data['lat_min'],          # lat_min (위도 최소값)
      netcdf_data['lat_max'],          # lat_max (위도 최대값)
      netcdf_data['lon_min'],          # lon_min (경도 최소값)
      netcdf_data['lon_max'],          # lon_max (경도 최대값)
    )

    cursor.execute(sql, params)
    inserted_id = cursor.lastrowid  # 삽입된 레코드의 id
    print(f'DB 저장 완료: id={inserted_id}, filename={file_meta["filename"]}')
    return inserted_id

  except ValueError as e:
    print(f'파일 메타정보 추출 오류: {e}')
    return None
  except Exception as e:
    print(f'DB 저장 중 오류 발생: {e}')
    return None


def extract_netcdf_file_info(filename):
  basename = os.path.basename(filename) # 파일명만 추출
  basename = basename.replace('.nc', '') # .nc 제거
  
  datetime_str = ''
  
  # 파일명에 _가 있으면 파일명을 분리
  if '_' in basename:
    parts = basename.split('_') # 파일명을 _로 분리하여 리스트에 저장 , [ gk2aamile1bvi006ko005lcskorea202510201654 ]
    
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
    'file_size': None,  # 파일 사이즈
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
  
  # 파일 사이즈
  try:
    if os.path.exists(filename):
      metadata['file_size'] = os.path.getsize(filename)
  except Exception as e:
    print(f'파일 사이즈 정보 추출 실패: {e}')
    
  # netCDF4 모듈을 이용하여 메타 데이터 추출하기
  try:
    with netCDF4.Dataset(filename, 'r') as nc:
      # 변수 목록 추출
      metadata['variable_count'] = len(nc.variables)  # 변수 목록의 개수 저장
      metadata['variables'] = list(nc.variables.keys()) # 변수들의 키값들만 추출하여 저장
      
      # 차원정보
      metadata['dimension_count'] = len(nc.dimensions)  # 차원수
      dimension_info = {} # 차원 정보를 저장하기 위한 빈 딕셔너리 생성
      for dim_name, dim in nc.dimensions.items():
        dimension_info[dim_name] = {
          'size': dim.size,
          'isunlimited': dim.isunlimited()
        }
      metadata['dimensions'] = dimension_info
      
      # Global Variables 추출하기
      global_attrs = {} # Global Variables 저장할 빈 딕셔너리 생성
      for attr in nc.ncattrs():
        attr_value = getattr(nc, attr)
        if isinstance(attr_value, (int, float, str)):   # 이러한 메타데이터이므로
          global_attrs[attr] = str(attr_value)
      metadata['global_attributes'] = global_attrs
      
      # 좌표계 정보 확인 : coord_vars에 해당하는 항목이 nc.variables 중에 있다면
      # metadata['has_coordinates']은 True, 아니면 False
      coord_vars = ['lat', 'lon', 'latitude', 'longitude', 'x', 'y']
      metadata['has_coordinates'] = any(coord in nc.variables for coord in coord_vars)

      # 위도/경도 범위 계산 — lat/latitude, lon/longitude 변수에서 최소/최대값 추출
      lat_var_names = ['lat', 'latitude']  # 위도 변수명 후보
      lon_var_names = ['lon', 'longitude']  # 경도 변수명 후보

      for lat_name in lat_var_names:
        if lat_name in nc.variables:
          lat_data = nc.variables[lat_name][:]
          # numpy masked array 처리 — 결측값 제외하고 유효한 값만 사용
          if hasattr(lat_data, 'compressed'):
            lat_data = lat_data.compressed()
          if len(lat_data) > 0:
            metadata['lat_min'] = float(np.nanmin(lat_data))
            metadata['lat_max'] = float(np.nanmax(lat_data))
          break

      for lon_name in lon_var_names:
        if lon_name in nc.variables:
          lon_data = nc.variables[lon_name][:]
          # numpy masked array 처리 — 결측값 제외하고 유효한 값만 사용
          if hasattr(lon_data, 'compressed'):
            lon_data = lon_data.compressed()
          if len(lon_data) > 0:
            metadata['lon_min'] = float(np.nanmin(lon_data))
            metadata['lon_max'] = float(np.nanmax(lon_data))
          break
    
  except Exception as e:
    print(f'netcdf 메타 데이터 추출중 오류가 발생했습니다: {e}')

  return metadata
  