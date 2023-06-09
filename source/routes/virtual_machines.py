from flask import (current_app, Blueprint, request, flash,
                   redirect, url_for, render_template)
from flask_login import login_required, current_user

from source import logger, database
from source.helper_functions import auto, create_pulumi_program_vms
from source.models import VirtualMachines


vm_blue_print = Blueprint("virtual_machines", __name__, url_prefix="/vms")
instance_types = ["t2.micro"]


@vm_blue_print.route("/", methods=["GET"])
@login_required
def list_vms():
    """
    View handler to lists all VMS
    """
    # get all virtual machines of user from the database
    vms = current_user.virtual_machines
    return render_template("virtual_machines/index.html", vms=vms, sub_title="Virtual Machines")


@vm_blue_print.route("/new", methods=["GET", "POST"])
@login_required
def create_vm():
    """
    View handler for creating new VMS
    """
    if request.method == "POST":
        stack_name = request.form.get("vm-id")
        keydata = request.form.get("vm-keypair")
        instance_type = request.form.get("instance_type")
        org_name = current_app.config["PULUMI_ORG"]
        project_name = current_app.config["PROJECT_NAME"]

        def pulumi_program():
            return create_pulumi_program_vms(keydata, instance_type)

        try:
            # create a new stack, genrating our pulumi program on the fly from the POST body
            stack = auto.create_stack(
                stack_name=str(stack_name),
                project_name=project_name,
                program=pulumi_program
            )
            stack.set_config("aws:region", auto.ConfigValue("us-east-1"))

            # deploy the stack, tailing the log to stdout
            stack.up(on_output=logger.info)

            # store the newly created stack into VirtualMachines model
            outs = stack.outputs()
            new_vm = VirtualMachines(
                name=stack_name,
                dns_name=f"{outs['public_dns'].value}",
                console_url=f"https://app.pulumi.com/{org_name}/{project_name}/{stack_name}",
                refrence_key=current_user.id
            )
            database.session.add(new_vm)
            database.session.commit()

            flash(
                f"Successfully created VM '{stack_name}'", category="success")

        except auto.StackAlreadyExistsError:
            logger.info(f"{stack_name} already exists")
            flash(
                f"VM with name '{stack_name}' already exists, pick a unique name", category="danger")

        return redirect(url_for("virtual_machines.list_vms"))

    return render_template("virtual_machines/create.html", instance_types=instance_types, curr_instance_type=None)


@vm_blue_print.route("/<string:id>/update", methods=["GET", "POST"])
@login_required
def update_vm(id: str):
    """
    View handler to update a vm
    :param id: vm id
    """
    stack_name = id

    if request.method == "POST":
        keydata = request.form.get("vm-keypair")
        instance_type = request.form.get("instance_type")
        project_name = current_app.config["PROJECT_NAME"]
        org_name = current_app.config["PULUMI_ORG"]

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

            # update the VirtualMachines model
            outs = stack.outputs()
            vm = VirtualMachines.query.filter_by(name=stack_name).first()

            if vm:
                vm.name = stack_name
                vm.dns_name = f"{outs['public_dns'].value}"
                vm.console_url = f"https://app.pulumi.com/{org_name}/{project_name}/{stack_name}"
                database.session.commit()
            else:
                logger.critical(f"{stack_name} stack name not found on Virtual Machine model")

            flash(f"VM '{stack_name}' successfully updated",
                  category="success")

        except auto.ConcurrentUpdateError:
            logger.info(f"{stack_name} already has an udpate in progress")
            flash(f"VM '{stack_name}' already has an udpate in progress", category="danger")

        except Exception as err:
            logger.critical(f"An error occurred while updating {stack_name} VM -> {err}")
            flash("Something went wrong", category="danger")

        return redirect(url_for("virtual_machines.list_vms"))

    stack = auto.select_stack(
        stack_name=stack_name,
        project_name=current_app.config["PROJECT_NAME"],
        # no-op program, just to get outputs
        program=lambda: None
    )

    outs = stack.outputs()
    public_key = outs.get("public_keys")
    pk = public_key.value if public_key else None
    instance_type = outs.get("instance_type")

    return render_template("virtual_machines/update.html", name=stack_name, public_key=pk,
                           instance_types=instance_types, curr_instance_type=instance_type.value)


@vm_blue_print.route("/<string:id>/delete", methods=["POST"])
@login_required
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

        # delete the stack from VirtualMachines model
        vm = VirtualMachines.query.filter_by(name=stack_name).first()
        database.session.delete(vm)
        database.session.commit()

        flash(f"VM '{stack_name}' successfully deleted!", category="success")

    except auto.ConcurrentUpdateError:
        logger.info(f"{stack_name} deletion is in progress")
        flash(f"Error: VM '{stack_name}' already has an deletion in progress", category="danger")

    except Exception as err:
        logger.critical(f"An error occurred while deleting the stack {stack_name} -> {err}")
        flash("Something went wrong", category="danger")

    return redirect(url_for("virtual_machines.list_vms"))
