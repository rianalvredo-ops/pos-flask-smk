"""Alat bantu belajar: membuat transaksi contoh 7 hari terakhir.

Jalankan SETELAH `flask init-db` dan `flask seed`:
    python isi_transaksi_contoh.py

Catatan: nomor order tetap memakai tanggal hari ini (hanya `waktu` yang
dimundurkan), cukup untuk mengisi dashboard dan laporan saat belajar.
"""

import random
from datetime import UTC, datetime, timedelta

from app import create_app
from app.blueprints.pos.services import proses_checkout
from app.extensions import db
from app.models import MetodeBayar, Produk, User

random.seed(7)


def main():
    app = create_app()
    with app.app_context():
        kasir = User.query.filter_by(peran="kasir").first()
        tunai = MetodeBayar.query.filter_by(jenis="tunai").first()
        produk = Produk.query.filter_by(aktif=True).all()
        if not kasir or not tunai or not produk:
            print("Jalankan dulu: flask init-db lalu flask seed")
            return

        dibuat = 0
        for hari_lalu in range(6, -1, -1):
            for _ in range(random.randint(2, 5)):
                pilihan = random.sample(produk, k=random.randint(1, 3))
                item = [
                    {"produk_id": p.id, "jumlah": random.randint(1, 2)} for p in pilihan
                ]
                ok, hasil, _kode = proses_checkout(
                    kasir.id,
                    {
                        "items": item,
                        "metode_bayar_id": tunai.id,
                        "uang_diterima": 1_000_000,
                    },
                )
                if ok:
                    mundur = timedelta(days=hari_lalu, hours=random.randint(0, 5))
                    hasil.waktu = datetime.now(UTC) - mundur
                    dibuat += 1
        db.session.commit()
        print(f"{dibuat} transaksi contoh dibuat.")


if __name__ == "__main__":
    main()
