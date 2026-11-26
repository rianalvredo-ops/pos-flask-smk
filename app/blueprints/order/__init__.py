from flask import Blueprint

bp = Blueprint("order", __name__, url_prefix="/order")

from app.blueprints.order import routes  # noqa: F401
