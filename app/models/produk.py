from app.extensions import db


class Produk(db.Model):
    __tablename__ = "produk"

    id = db.Column(db.Integer, primary_key=True)
    kode = db.Column(db.String(30), unique=True, nullable=False, index=True)
    nama = db.Column(db.String(150), nullable=False)
    kategori = db.Column(db.String(50), nullable=True)
    harga = db.Column(db.Integer, nullable=False, default=0)
    stok = db.Column(db.Integer, nullable=False, default=0)
    aktif = db.Column(db.Boolean, default=True, nullable=False)

    order_items = db.relationship("OrderItem", back_populates="produk", lazy="dynamic")

    def __repr__(self):
        return f"<Produk {self.kode} - {self.nama}>"
