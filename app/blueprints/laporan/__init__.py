from flask import Blueprint

bp = Blueprint("laporan", __name__, url_prefix="/laporan")

from app.blueprints.laporan import routes  # noqa: F401
