from flask import (current_app, Blueprint, request, flash, 
                   redirect, url_for, render_template)

from source import logger
from helper_functions import auto, create_pulumi_program_vms


blue_print = Blueprint("virtual_machines", __name__, url_prefix="/vms")
instance_types = ["t2.micro"]


@blue_print.route("/new", methods=["GET", "POST"])
def create_vms():
    """
    View handler for creating new VMS
    """
    if request.method == "POST":
        stack_name = request.form.get("vm-id")
        keydata = request.form.get("vm-keypair")
        instance_type = request.form.get("instance_type")

        def pulumi_program():
            return create_pulumi_program_vms(keydata, instance_type)
        
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

            flash(f"Successfully created VM '{stack_name}'", category="success")
        
        except auto.StackAlreadyExistsError:
            logger.info(f"{stack_name} already exists")
            flash(f"VM with name '{stack_name}' already exists, pick a unique name", category="danger")
        
        return redirect(url_for("virtual_machines.list_vms"))

    return render_template("virtual_machines/create.html", instance_types=instance_types, curr_instance_type=None)


@blue_print.route("/", methods=["GET"])
def list_vms():
    """
    View handler to lists all VMS
    """
    vms = []
    org_name = current_app.config["PULUMI_ORG"]
    project_name = current_app.config("PROJECT_NAME")

    try:
        ws = auto.LocalWorkspace(
            project_settings=auto.ProjectSettings(
                name=project_name, runtime="python"
            )
        )

        all_stack = ws.list_stacks()
        for stack in all_stack:
            stack = auto.select_stack(
                stack_name=stack.name,
                project_name=project_name,
                # no-op program, just to get outputs
                program=lambda: None
            )

            outs = stack.outputs()
            if "public_dns" in outs:
                vms.append({
                    "name": stack.name,
                    "url": f"http://{outs['public_dns'].value}",
                    "console_url": f"https://app.pulumi.com/{org_name}/{project_name}/{stack.name}"
                })
    
    except Exception as err:
        logger.critical(f"An error occurred while fetching all VMS -> {err}")
        flash(str(err), category="danger")
    
    return render_template("virtual_machines/index.html", vms=vms)


@blue_print.route("/<string:id>/update", methods=["GET", "POST"])
def update_vm(id: str):
    """
    View handler to delete a vm
    :param id: vm id
    """
    stack_name = id

    if request.method == "POST":
        keydata = request.form.get("vm-keypair")
        instance_type = request.form.get("instance_type")

        def pulumi_program():
            return create_pulumi_program_vms(keydata, instance_type)
        
        try:
            stack = auto.select_stack(
                stack_name=str(stack_name),
                project_name=current_app.config["PROJECT_NAME"],
                program=pulumi_program
            )
            stack.set_config("aws:region", auto.ConfigValue("us-east-1"))

            # deploy the stack, tailing the log to stdout
            stack.up(on_output=logger.info)

            flash(f"VM '{stack_name}' successfully updated", category="success")
        
        except auto.ConcurrentUpdateError:
            logger.info(f"{stack_name} already has an udpate in progress")
            flash(f"VM '{stack_name}' already has an udpate in progress", category="danger")

        except Exception as err:
            logger.critical(f"An error occurred while updating {stack_name} VM -> {err}")
            flash(str(err), category="danger")

        return redirect(url_for("virtual_machines.list_vms"))

    stack = auto.select_stack(
        stack_name=stack_name,
        program_name=current_app.config["PROJECT_NAME"],
        # no-op program, just to get outputs
        program=lambda: None
    )

    outs = stack.outputs()
    public_key = outs.get("public_keys")
    pk = public_key.value if public_key else None
    instance_type = outs.get("instance_type")

    return render_template("virtual_machines/update.html", name=stack_name, public_key=pk,
                           instance_types=instance_types, curr_instance_type=instance_type.value)


@blue_print.route("/<string:id>/delete")
def delete_vm(id: str):
    """
    View handler to delete a vm
    :param id: vm id
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
        flash(f"VM '{stack_name}' successfully deleted!", category="success")
    
    except auto.ConcurrentUpdateError:
        logger.info(f"{stack_name} deletion is in progress")
        flash(f"Error: VM '{stack_name}' already has an deletion in progress", category="danger")
    
    except Exception as err:
        logger.critical(f"An error occurred while deleting the stack {stack_name} -> {err}")
        flash(str(err), category="danger")
 
    return redirect(url_for("virtual_machines.list_vms"))
