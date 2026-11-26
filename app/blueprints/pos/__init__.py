from flask import Blueprint

bp = Blueprint("pos", __name__)

from app.blueprints.pos import routes  # noqa: F401
