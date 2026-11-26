from app.extensions import db


class MetodeBayar(db.Model):
    __tablename__ = "metode_bayar"

    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(50), unique=True, nullable=False)
    jenis = db.Column(db.String(20), nullable=False)  # 'tunai' atau 'non_tunai'
    aktif = db.Column(db.Boolean, default=True, nullable=False)

    orders = db.relationship("Order", back_populates="metode_bayar", lazy="dynamic")

    def __repr__(self):
        return f"<MetodeBayar {self.nama} ({self.jenis})>"
