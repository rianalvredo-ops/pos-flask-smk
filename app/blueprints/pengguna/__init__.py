from flask import Blueprint

bp = Blueprint("pengguna", __name__)

from app.blueprints.pengguna import routes  # noqa: F401
