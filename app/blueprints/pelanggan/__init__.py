from flask import Blueprint

bp = Blueprint("pelanggan", __name__)

from app.blueprints.pelanggan import routes  # noqa: F401
