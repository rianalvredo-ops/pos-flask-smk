from datetime import UTC, datetime

from app.extensions import db


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    nomor = db.Column(db.String(30), unique=True, nullable=False, index=True)
    waktu = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False)
    kasir_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    pelanggan_id = db.Column(db.Integer, db.ForeignKey("pelanggan.id"), nullable=False)
    metode_bayar_id = db.Column(
        db.Integer, db.ForeignKey("metode_bayar.id"), nullable=False
    )
    subtotal = db.Column(db.Integer, nullable=False)
    tarif_pajak = db.Column(db.Integer, nullable=False, default=10)
    pajak = db.Column(db.Integer, nullable=False, default=0)
    total = db.Column(db.Integer, nullable=False)
    uang_diterima = db.Column(db.Integer, nullable=True)
    kembalian = db.Column(db.Integer, nullable=True)
    status = db.Column(
        db.String(20), nullable=False, default="selesai"
    )  # 'selesai', 'pengajuan_batal', 'dibatalkan'
    alasan_batal = db.Column(db.String(255), nullable=True)
    diajukan_oleh_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    dikonfirmasi_oleh_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=True
    )
    waktu_batal = db.Column(db.DateTime, nullable=True)

    # Relasi
    kasir = db.relationship("User", foreign_keys=[kasir_id], back_populates="orders")
    pelanggan = db.relationship(
        "Pelanggan", foreign_keys=[pelanggan_id], back_populates="orders"
    )
    metode_bayar = db.relationship(
        "MetodeBayar", foreign_keys=[metode_bayar_id], back_populates="orders"
    )
    items = db.relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    diajukan_oleh = db.relationship("User", foreign_keys=[diajukan_oleh_id])
    dikonfirmasi_oleh = db.relationship("User", foreign_keys=[dikonfirmasi_oleh_id])

    def __repr__(self):
        return f"<Order {self.nomor} - Rp{self.total}>"


class OrderItem(db.Model):
    __tablename__ = "order_item"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    produk_id = db.Column(db.Integer, db.ForeignKey("produk.id"), nullable=False)
    nama_produk = db.Column(db.String(150), nullable=False)
    harga_satuan = db.Column(db.Integer, nullable=False)
    jumlah = db.Column(db.Integer, nullable=False, default=1)
    subtotal = db.Column(db.Integer, nullable=False)

    order = db.relationship("Order", back_populates="items")
    produk = db.relationship("Produk", back_populates="order_items")

    def __repr__(self):
        return f"<OrderItem {self.nama_produk} x{self.jumlah}>"
