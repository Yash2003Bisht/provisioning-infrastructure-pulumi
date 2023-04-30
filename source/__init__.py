import os
import logging

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required
from dotenv import load_dotenv
import redis

# load env
load_dotenv()

# logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# console handler
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# formatter
formatter = logging.Formatter("[%(levelname)s] - %(asctime)s - %(name)s - %(message)s")

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)

# redis instance
redis_instance = redis.Redis(host=os.environ["REDIS_HOST"], port=os.environ["REDIS_PORT"],
                             db=os.environ["REDIS_DB"], decode_responses=True)

# database
database = SQLAlchemy()

# main app
app = Flask(__name__, instance_relative_config=True)

# enviroment
debug = os.environ["DEBUG"]


def create_app():
    """
    Create the main app
    :return: Flask Appapp
    """
    # install required plugin
    from .helper_functions import ensure_plugins
    logger.info("Installing plugin")
    ensure_plugins()

    # app config
    logger.info("Configuring APP")
    app.config.from_mapping(
        SECRET_KEY=os.environ["SECRET_KEY"],
        PROJECT_NAME=os.environ["PROJECT_NAME"],
        PULUMI_ORG=os.environ["PULUMI_ORG"],
        SQLALCHEMY_DATABASE_URI=os.environ["SQLALCHEMY_DATABASE_URI"].format(os.path.join(os.getcwd(), "database.db")),
    )

    # initialize the database
    logger.info("Initializing database")
    database.init_app(app)

    from .sites import sites_blue_print
    from .virtual_machines import vm_blue_print
    from .auth import auth_blue_print
    
    # register blueprint
    logger.info("Registering blueprints")
    app.register_blueprint(sites_blue_print)
    app.register_blueprint(vm_blue_print)
    app.register_blueprint(auth_blue_print)

    # models
    from .models import User, VirtualMachines

    # create database
    if not os.path.exists("database.db"):
        logger.info("Creating database")
        with app.app_context():
            database.create_all()

    # login manager
    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return database.get_or_404(User, id)

    return app


@app.route("/", methods=["GET"])
@login_required
def index():
    return render_template("index.html")
