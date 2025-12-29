import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash

from netcdfweb.db import get_db

bp = Blueprint('nclist', __name__, url_prefix='/nclist')


@bp.route('/')
def nclist():
  print('nclist 데이터베이스에서 목록을 불러와서 노출')
  return render_template('nclist.html')


