from flask import Blueprint

bp = Blueprint("pengaturan", __name__)

from app.blueprints.pengaturan import routes  # noqa: F401
