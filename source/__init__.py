import os
import logging

from flask import Flask, render_template
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
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ["SECRET_KEY"],
        PROJECT_NAME=os.environ["PROJECT_NAME"],
        PULUMI_ORG=os.environ["PULUMI_ORG"]
    )

    @app.route("/", methods=["GET"])
    def index():
        return render_template("index.html")


    from .sites import sites_blue_print
    from .virtual_machines import vm_blue_print
    
    # register blueprint
    logger.info("Registering blueprints")
    app.register_blueprint(sites_blue_print)
    app.register_blueprint(vm_blue_print)

    return app

