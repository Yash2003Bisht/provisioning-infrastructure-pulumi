from source import database
from flask_login import UserMixin


class User(database.Model, UserMixin):
    id = database.Column(database.Integer, primary_key=True)
    name =  database.Column(database.String(300))
    email = database.Column(database.String(300), unique=True)
    password = database.Column(database.String(300))
    virtual_machines = database.relationship("VirtualMachines")
    sites = database.relationship("Sites")


class VirtualMachines(database.Model):
    id = database.Column(database.Integer, primary_key=True)
    name = database.Column(database.String(500), unique=True)
    dns_name = database.Column(database.String(500))
    console_url = database.Column(database.String(500))
    refrence_key = database.Column(database.Integer, database.ForeignKey("user.id"))


class Sites(database.Model):
    id = database.Column(database.Integer, primary_key=True)
    name = database.Column(database.String(500), unique=True)
    url = database.Column(database.String(500))
    console_url = database.Column(database.String(500))
    refrence_key = database.Column(database.Integer, database.ForeignKey("user.id"))
