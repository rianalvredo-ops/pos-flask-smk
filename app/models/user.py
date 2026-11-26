from datetime import UTC, datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(30), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    peran = db.Column(db.String(10), nullable=False)  # 'admin' atau 'kasir'
    aktif = db.Column(db.Boolean, default=True, nullable=False)
    dibuat_pada = db.Column(
        db.DateTime, default=lambda: datetime.now(UTC), nullable=False
    )

    orders = db.relationship(
        "Order", foreign_keys="Order.kasir_id", back_populates="kasir", lazy="dynamic"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.aktif is None:
            self.aktif = True

    def set_password(self, password: str) -> None:
        """Membuat hash password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Memeriksa kecocokan password."""
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self) -> bool:
        """Kesesuaian dengan Flask-Login UserMixin."""
        return self.aktif

    @property
    def is_admin(self) -> bool:
        return self.peran == "admin"

    @property
    def is_kasir(self) -> bool:
        return self.peran == "kasir"


def __repr__(self) -> str:
    return f"<User {self.username} ({self.peran})>"
