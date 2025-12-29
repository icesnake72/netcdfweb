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
    file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], safe_name))
  

  print('upload', [f.filename for f in files])
  return redirect(url_for('nclist.nclist'))  # nclist 블루프린트로 이동



  