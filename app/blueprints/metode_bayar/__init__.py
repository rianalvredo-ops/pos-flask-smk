from flask import Blueprint

bp = Blueprint("metode_bayar", __name__)

from app.blueprints.metode_bayar import routes  # noqa: F401
