# NetCDF Web 프로젝트 설계 문서

> 작성일: 2026-03-16
> 현재 진행 상황: 약 40% 완성

---

## 1. 프로젝트 개요

### 목적
GK2A 위성 관측 데이터(NetCDF 형식)를 웹을 통해 업로드하고, 메타정보를 데이터베이스에 저장하여 검색·조회·시각화할 수 있는 웹 애플리케이션

### 기술 스택
| 구분 | 기술 |
|------|------|
| 웹 프레임워크 | Flask 3.1.2 |
| DB | MySQL + PyMySQL 1.1.2 |
| NetCDF 처리 | netCDF4 1.7.4 |
| 수치 계산 | numpy 2.4.2 |
| 템플릿 | Jinja2 |
| 프론트엔드 | HTML/CSS/JS (바닐라) |

---

## 2. 현재 구현 상태

### ✅ 완료된 기능
- Flask 앱 기본 설정 및 라우팅 구조
- MySQL 데이터베이스 연결 관리 (`db.py`)
- NetCDF 파일 웹 업로드 (다중 파일 선택)
- 파일명 패턴 파싱 및 메타정보 추출 (`extract_netcdf_file_info`)
  - 형식 A: `satellite_sensor_data_level_variable_id_region_code_region_name_datetime.nc`
  - 형식 B: `gk2a{sensor}{data_level}{variable_id}{region_code}datetime.nc`
- NetCDF 파일 내용 분석 (`extract_netcdf_data`)
  - 변수/차원/Global Attributes 추출
- 데이터베이스 스키마 (`db.sql`)
  - `netcdf_files` 테이블
  - `netcdf_images` 테이블

### ❌ 미완성 기능
- `insert_netcdf_file()`: 추출한 메타정보를 DB에 실제 저장
- `extract_netcdf_data()`: 위도/경도 범위(lat_min/max, lon_min/max) 계산
- `/nclist/`: DB에서 파일 목록 조회
- `nclist.html`: 파일 목록 표시 UI

---

## 3. 전체 아키텍처

```
[사용자 브라우저]
      │
      ▼
[Flask Web App]
  ├── / (홈)
  ├── /nctodb/ (업로드 페이지)
  ├── /nctodb/upload (업로드 처리)
  ├── /nclist/ (파일 목록)
  └── /ncview/<id> (상세보기 - 예정)
      │
      ├──[MySQL DB]
      │    ├── netcdf_files (메타정보)
      │    └── netcdf_images (이미지 정보)
      │
      └──[static/ncfiles/] (업로드된 .nc 파일 저장)
```

---

## 4. 개발 로드맵

### Phase 1 — 핵심 기능 완성 (현재 단계)

#### 1-1. DB 저장 구현 (`nctodb.py`)
**파일**: `netcdfweb/nctodb.py`
**함수**: `insert_netcdf_file(filename)`

할 일:
- `extract_netcdf_file_info()` 결과와 `extract_netcdf_data()` 결과를 합쳐서 `netcdf_files` 테이블에 INSERT
- 위도/경도 범위 계산 로직 추가 (`lat_min`, `lat_max`, `lon_min`, `lon_max`)
- 중복 파일 업로드 예외 처리 (파일명 기준 UNIQUE 처리)

```python
# 예상 INSERT 쿼리
INSERT INTO netcdf_files (
    filename, filepath, satellite, sensor, data_level, variable_id,
    region_code, region_name, observation_datetime, observation_date,
    observation_time, file_size, variables, dimensions, global_attributes,
    variable_count, dimension_count, has_coordinates,
    lat_min, lat_max, lon_min, lon_max
) VALUES (...)
```

#### 1-2. 파일 목록 조회 구현 (`nclist.py`)
**파일**: `netcdfweb/nclist.py`
**라우트**: `GET /nclist/`

할 일:
- DB에서 `netcdf_files` 전체 목록 SELECT
- 페이지네이션 추가 (한 페이지 20개)
- `nclist.html`에 테이블 형태로 목록 렌더링

표시 컬럼:
| 컬럼 | 설명 |
|------|------|
| filename | 파일명 |
| satellite | 위성명 |
| sensor | 센서명 |
| variable_id | 변수/채널 |
| region_name | 지역명 |
| observation_datetime | 관측 시간 |
| file_size | 파일 크기 |
| has_preview | 미리보기 여부 |

---

### Phase 2 — 파일 상세 조회 및 시각화

#### 2-1. 파일 상세 페이지
**라우트**: `GET /nclist/<int:file_id>`
**파일**: `netcdfweb/nclist.py` 추가 라우트

표시 내용:
- 파일 기본 정보 (파일명, 크기, 업로드 일시)
- 위성/센서/채널/지역 메타정보
- 변수 목록 (이름, 타입, 차원, 단위)
- Global Attributes
- 위도/경도 범위

#### 2-2. NetCDF 데이터 시각화
**라우트**: `GET /ncview/<int:file_id>`
**새 파일**: `netcdfweb/ncview.py`

옵션 A (간단): matplotlib으로 서버 사이드 이미지 생성 → `netcdf_images` 테이블에 저장
옵션 B (고급): Leaflet.js + 지도 타일 생성으로 클라이언트 사이드 인터랙티브 지도

구현 순서:
1. matplotlib + cartopy로 위성 영상 PNG 생성
2. 생성된 이미지를 `static/images/` 저장
3. `netcdf_images` 테이블에 경로 저장
4. 파일 상세 페이지에서 이미지 표시

---

### Phase 3 — 검색 및 필터링

#### 3-1. 목록 페이지 검색 기능
**라우트**: `GET /nclist/?satellite=&sensor=&region=&date_from=&date_to=`

필터 조건:
- 위성명 (satellite)
- 센서명 (sensor)
- 지역 코드/명 (region_code, region_name)
- 관측 날짜 범위 (observation_date BETWEEN)
- 변수 ID (variable_id)

#### 3-2. 파일 삭제
**라우트**: `DELETE /nclist/<int:file_id>` 또는 `POST /nclist/<int:file_id>/delete`
- 파일시스템에서 .nc 파일 삭제
- DB에서 레코드 삭제 (CASCADE로 netcdf_images도 자동 삭제)

---

### Phase 4 — API 및 고도화 (선택 사항)

#### 4-1. REST API 엔드포인트
```
GET  /api/files          # 파일 목록 (JSON)
GET  /api/files/<id>     # 파일 상세 (JSON)
POST /api/files/upload   # 파일 업로드
DELETE /api/files/<id>   # 파일 삭제
GET  /api/files/<id>/data?variable=<var>  # 변수 데이터 조회
```

#### 4-2. 지도 타일 서비스
- XYZ 타일 형식으로 위성 영상 제공
- `tile_generated`, `tile_base_path`, `tile_min_zoom`, `tile_max_zoom` 컬럼 활용
- Leaflet.js로 웹 지도 표시

#### 4-3. 배치 처리
- 대용량 파일 비동기 처리 (Celery + Redis)
- 업로드 진행률 표시

---

## 5. 데이터베이스 스키마 (현재)

### `netcdf_files` 테이블
```sql
CREATE TABLE netcdf_files (
    id                   INT AUTO_INCREMENT PRIMARY KEY,
    filename             VARCHAR(255) NOT NULL,
    filepath             VARCHAR(500),
    satellite            VARCHAR(50),
    sensor               VARCHAR(50),
    data_level           VARCHAR(50),
    variable_id          VARCHAR(50),
    region_code          VARCHAR(50),
    region_name          VARCHAR(50),
    observation_datetime DATETIME,
    observation_date     DATE,
    observation_time     TIME,
    created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_size            BIGINT,
    data_start           DATETIME,
    data_end             DATETIME,
    variables            TEXT,        -- JSON
    dimensions           JSON,
    global_attributes    JSON,
    variable_count       INT,
    dimension_count      INT,
    has_coordinates      TINYINT(1),
    updated_at           TIMESTAMP,
    has_preview          TINYINT(1) DEFAULT 0,
    tile_generated       TINYINT(1) DEFAULT 0,
    tile_base_path       VARCHAR(500),
    tile_min_zoom        INT,
    tile_max_zoom        INT,
    preview_count        INT DEFAULT 0,
    lat_min              DOUBLE,
    lat_max              DOUBLE,
    lon_min              DOUBLE,
    lon_max              DOUBLE
);
```

### `netcdf_images` 테이블
```sql
CREATE TABLE netcdf_images (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    file_id       INT NOT NULL,
    image_path    VARCHAR(500),
    image_type    VARCHAR(50),    -- 'preview', 'thumbnail'
    variable_name VARCHAR(100),
    description   TEXT,
    width         INT,
    height        INT,
    file_size     BIGINT,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES netcdf_files(id) ON DELETE CASCADE
);
```

---

## 6. 파일 구조 (목표 상태)

```
netcdfweb/
├── __init__.py          # Flask 앱 팩토리
├── db.py                # DB 연결 관리
├── nctodb.py            # 파일 업로드 + 메타정보 추출 + DB 저장
├── nclist.py            # 파일 목록 + 상세 조회
├── ncview.py            # (예정) 시각화
├── templates/
│   ├── base.html        # (예정) 공통 레이아웃
│   ├── index.html       # 홈페이지
│   ├── nctodb.html      # 업로드 페이지
│   ├── nclist.html      # 파일 목록 페이지
│   ├── ncdetail.html    # (예정) 파일 상세 페이지
│   └── ncview.html      # (예정) 시각화 페이지
└── static/
    ├── ncfiles/         # 업로드된 .nc 파일 저장
    ├── images/          # 생성된 시각화 이미지
    └── js/              # 클라이언트 스크립트
```

---

## 7. 다음 작업 우선순위

| 순위 | 작업 | 파일 | 난이도 |
|------|------|------|--------|
| 1 | `insert_netcdf_file()` DB 저장 구현 | `nctodb.py` | 중 |
| 2 | 위도/경도 범위 계산 | `nctodb.py` | 중 |
| 3 | `nclist.py` 목록 조회 구현 | `nclist.py` | 하 |
| 4 | `nclist.html` 테이블 UI | `nclist.html` | 하 |
| 5 | 파일 상세 페이지 | `nclist.py`, `ncdetail.html` | 중 |
| 6 | matplotlib 시각화 | `ncview.py` | 상 |
| 7 | 검색/필터 기능 | `nclist.py` | 중 |
| 8 | 파일 삭제 기능 | `nclist.py` | 하 |

---

## 8. 주요 구현 참고사항

### 파일명 파싱 규칙 (현재 지원)
```
형식 A: {satellite}_{sensor}_{data_level}_{variable_id}_{region_code}_{region_name}_{datetime}.nc
형식 B: gk2a{sensor}{data_level}{variable_id}{region_code}{datetime}.nc

datetime 형식: YYYYMMDDHHMMSS 또는 YYYYMMDDHHMM
```

### NetCDF 좌표계 처리
- 위도/경도 직접 포함 (`lat`, `lon`, `latitude`, `longitude`)
- 투영 좌표계 (`x`, `y`, `xc`, `yc`) → 변환 필요
- GK2A는 주로 투영 좌표계 사용 → `pyproj` 라이브러리로 변환 고려

### 에러 처리 원칙
- 잘못된 파일명 형식: 메타정보 없이 기본 정보만 저장
- 손상된 NetCDF 파일: 업로드는 허용, DB 저장 실패로 처리
- 중복 파일: 덮어쓰기 또는 버전 관리 선택 필요
