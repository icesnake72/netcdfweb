import os

from flask import Flask, render_template, g
from . import db

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        UPLOAD_FOLDER=os.path.join(app.static_folder, 'ncfiles'),
        DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite'),
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # initialize the database
    db.init_app(app)

    # register the blueprint
    from . import nclist, nctodb
    app.register_blueprint(nclist.bp)
    app.register_blueprint(nctodb.bp)

    # a simple page that says hello
    @app.route('/')
    def index():        
        return render_template("index.html")

    return app


'''
# 가상환경 만들기
python -m venv .venv
.venv/scripts/activate.bat

# 필요한 모듈들 설치하기
pip install -r requirements.txt

# start app command
flask --app netcdfweb run --debug
'''
