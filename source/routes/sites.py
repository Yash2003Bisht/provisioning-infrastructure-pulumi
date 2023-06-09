import requests
from flask import (current_app, Blueprint, request, flash,
                   redirect, url_for, render_template)
from flask_login import login_required, current_user

from source import logger, database
from source.helper_functions import create_pulumi_program_s3, auto
from source.models import Sites

sites_blue_print = Blueprint("sites", __name__, url_prefix="/sites")


@sites_blue_print.route("/", methods=["GET"])
@login_required
def list_sites():
    """
    View handler to lists all sites
    """
    # get all sites of user from the database
    sites = current_user.sites
    return render_template("sites/index.html", sites=sites, sub_title="Sites")


@sites_blue_print.route("/new", methods=["GET", "POST"])
@login_required
def create_site():
    """
    View handler for creating new sites
    """
    if request.method == "POST":
        stack_name = request.form.get("site-id")
        file_url = request.form.get("file-url")
        org_name = current_app.config["PULUMI_ORG"]
        project_name = current_app.config["PROJECT_NAME"]

        if file_url:
            site_content = requests.get(file_url).text
        else:
            site_content = request.form.get("site-content")

        def pulumi_program():
            return create_pulumi_program_s3(str(site_content))

        try:
            # create a new stack, genrating our pulumi program on the fly from the POST body
            stack = auto.create_stack(
                stack_name=str(stack_name),
                project_name=current_app.config["PROJECT_NAME"],
                program=pulumi_program
            )
            stack.set_config("aws:region", auto.ConfigValue("us-east-1"))

            # deploy the stack, tailing the log to stdout
            stack.up(on_output=logger.info)

            # store the newly created stack into Sites model
            outs = stack.outputs()
            new_site = Sites(
                name=stack.name,
                url=f"http://{outs['website_url'].value}",
                console_url=f"https://app.pulumi.com/{org_name}/{project_name}/{stack.name}"
            )
            database.session.add(new_site)
            database.session.commit()

            flash(f"Successfully created site '{stack_name}'", category="success")

        except auto.StackAlreadyExistsError:
            logger.info(f"{stack_name} already exists")
            flash(f"Site with name '{stack_name}' already exists, pick a unique name", category="danger")

        return render_template(url_for("sites.list_sites"))

    return render_template("sites/create.html")


@sites_blue_print.route("/<string:id>/update", methods=["GET", "POST"])
@login_required
def update_site(id: str):
    stack_name = id

    if request.method == "POST":
        file_url = request.form.get("file-url")
        if file_url:
            site_content = requests.get(file_url).text
        else:
            site_content = str(request.form.get("site-content"))

        def pulumi_program():
            create_pulumi_program_s3(str(site_content))

        try:
            stack = auto.select_stack(
                stack_name=stack_name,
                project_name=current_app.config["PROJECT_NAME"],
                program=pulumi_program,
            )
            stack.set_config("aws:region", auto.ConfigValue("us-east-1"))

            # deploy the stack, tailing the logs to stdout
            stack.up(on_output=logger.info)

            # update the VirtualMachines model
            outs = stack.outputs()
            site = Sites.query.filter_by(name=stack_name).first()

            if site:
                site.name = stack.name
                site.url = f"http://{outs['website_url'].value}",
                site.console_url = f"https://app.pulumi.com/{org_name}/{project_name}/{stack.name}"
                database.session.commit()
            else:
                logger.critical(
                    f"{stack_name} stack name not found on Sites model")

            flash(f"Site '{stack_name}' successfully updated!", category="success")

        except auto.ConcurrentUpdateError:
            logger.info(f"{stack_name} already has an udpate in progress")
            flash(f"Site '{stack_name}' already has an udpate in progress", category="danger")

        except Exception as err:
            logger.critical(f"An error occurred while updating {stack_name} Site -> {err}")
            flash(str(err), category="danger")

        return redirect(url_for("sites.list_sites"))

    stack = auto.select_stack(
        stack_name=stack_name,
        project_name=current_app.config["PROJECT_NAME"],
        # noop just to get the outputs
        program=lambda: None,
    )
    outs = stack.outputs()
    content_output = outs.get("website_content")
    content = content_output.value if content_output else None
    return render_template("sites/update.html", name=stack_name, content=content)


@sites_blue_print.route("/<string:id>/delete", methods=["POST"])
@login_required
def delete_sites(id: str):
    """
    View handler to delete a site
    :param id: site id
    """
    stack_name = id

    try:
        stack = auto.select_stack(
            stack_name=stack_name,
            project_name=current_app.config["PROJECT_NAME"],
            # no-op program, just to get outputs
            program=lambda: None
        )

        # NOTE: stack.destroy will automatically delete the resource on aws
        stack.destroy(on_output=logger.info)
        stack.workspace.remove_stack(stack_name)

        # delete the stack from Sites model
        site = Sites.query.filter_by(name=stack_name).first()
        database.session.delete(site)
        database.session.commit()

        flash(f"Site '{stack_name}' successfully deleted!", category="success")

    except auto.ConcurrentUpdateError:
        logger.info(f"{stack_name} deletion is in progress")
        flash(f"Error: site '{stack_name}' already has an deletion in progress", category="danger")

    except Exception as err:
        logger.critical(f"An error occurred while deleting the stack {stack_name} -> {err}")
        flash(str(err), category="danger")

    return redirect(url_for("sites.list_sites"))
