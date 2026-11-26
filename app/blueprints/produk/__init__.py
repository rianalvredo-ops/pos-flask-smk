from flask import Blueprint

bp = Blueprint("produk", __name__)

from app.blueprints.produk import routes  # noqa: F401
