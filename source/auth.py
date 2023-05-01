import re

from flask import Blueprint, flash, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import current_user, login_user, logout_user

from .models import User
from . import database, logger


auth_blue_print = Blueprint("auth", __name__)


@auth_blue_print.route("/login", methods=["GET", "POST"])
def login():
    email = ""

    if current_user.is_authenticated:
        return redirect(url_for("index"))
    
    elif request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        remember = True if request.form.get("remember") == "on" else False
        user = User.query.filter_by(email=email).first()

        if not user:
            flash("No user exists with this email!", category="danger")
        
        elif not check_password_hash(user.password, password):
            flash("Incorrect password!", category="danger")
        
        else:
            login_user(user, remember)
            return redirect(url_for("index"))

    return render_template("auth/login.html", email=email)


@auth_blue_print.route("/signup", methods=["GET", "POST"])
def signup():
    username = ""
    email = ""

    if current_user.is_authenticated:
        return redirect(url_for("routes.index"))
    
    elif request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirmpassword")

        if username == "" or email == "" or password == "":
            flash("Name, Email and Password can't be blank!", category="danger")

        elif not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email):
            flash("Please enter a valid email", category="danger")

        elif User.query.filter_by(email=email).first():
            flash("A User with this email is already exists!", category="danger")

        elif len(password) < 4:
            flash("Password should be 4 characters long!", category="danger")

        elif password != confirm_password:
            flash("Password does not match with confirm password!", category="danger")

        else:
            # create a user object and commit the changes into database
            user = User(
                name=username,
                email=email,
                password=generate_password_hash(password)
            )

            database.session.add(user)
            database.session.commit()

            login_user(user)

            logger.info(f"A new user with the {email} email has signup")
            return redirect(url_for("index"))

    return render_template("auth/signup.html", username=username, email=email)


@auth_blue_print.route("/logout", methods=["GET"])
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
