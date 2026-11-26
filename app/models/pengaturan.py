from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db


class Pengaturan(db.Model):
    __tablename__ = "pengaturan"

    id = db.Column(db.Integer, primary_key=True)
    nama_toko = db.Column(db.String(100), nullable=False)
    alamat_toko = db.Column(db.String(255), nullable=True)
    tarif_pajak = db.Column(db.Integer, nullable=False, default=10)
    ambang_stok_menipis = db.Column(db.Integer, nullable=False, default=5)

    @classmethod
    def get_solo(cls):
        """Mengambil baris tunggal pengaturan toko, atau membuat default jika belum ada."""
        obj = cls.query.first()
        if not obj:
            obj = cls(
                nama_toko="SMK Mart",
                alamat_toko="",
                tarif_pajak=10,
                ambang_stok_menipis=5,
            )
            db.session.add(obj)
            try:
                db.session.commit()
            except SQLAlchemyError:
                db.session.rollback()
        return obj

    def __repr__(self):
        return f"<Pengaturan {self.nama_toko}>"
