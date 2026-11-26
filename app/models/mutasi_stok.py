from datetime import UTC, datetime

from app.extensions import db


class MutasiStok(db.Model):
    __tablename__ = "mutasi_stok"

    id = db.Column(db.Integer, primary_key=True)
    produk_id = db.Column(
        db.Integer, db.ForeignKey("produk.id"), nullable=False, index=True
    )
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    waktu = db.Column(
        db.DateTime,
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
    tipe = db.Column(
        db.String(20), nullable=False
    )  # 'masuk', 'keluar', 'batal', 'penyesuaian'
    jumlah = db.Column(db.Integer, nullable=False)
    stok_sebelum = db.Column(db.Integer, nullable=False)
    stok_sesudah = db.Column(db.Integer, nullable=False)
    keterangan = db.Column(db.String(255), nullable=True)

    produk = db.relationship(
        "Produk",
        backref=db.backref(
            "mutasi_list", lazy="dynamic", order_by="desc(MutasiStok.waktu)"
        ),
    )
    user = db.relationship("User", backref=db.backref("mutasi_dibuat", lazy="dynamic"))

    def __repr__(self):
        return f"<MutasiStok Produk #{self.produk_id} {self.tipe} {self.jumlah}>"
