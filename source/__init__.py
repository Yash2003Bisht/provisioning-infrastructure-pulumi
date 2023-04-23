import os
import logging

from flask import Flask, render_template
from dotenv import load_dotenv
from .helper_functions import ensure_plugins

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


def create_app():
    """
    Create the main app
    :return: Flask Appapp
    """
    # install required plugin
    logger.info("Installing plugin")
    ensure_plugins()

    # app config
    logger.info("Configuring APP")
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY"),
        PROJECT_NAME=os.environ.get("PROJECT_NAME"),
        PULUMI_ORG=os.environ("PULUMI_ORG")
    )

    @app.route("/", methods=["GET"])
    def index():
        return render_template("index.html")


    import sites, virtual_machines
    
    # register blueprint
    logger.info("Registering blueprints")
    app.register_blueprint(sites.blue_print)
    app.register_blueprint(virtual_machines.blue_print)

    return app

