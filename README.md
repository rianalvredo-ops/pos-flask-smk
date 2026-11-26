# SMK Mart POS

Aplikasi kasir (Point of Sale) berbasis web untuk latihan di laboratorium RPL.
Dibuat dengan Flask, SQLAlchemy (SQLite), Flask-Login, dan Tailwind CSS.

## Fitur
- Login dengan dua peran: Admin dan Kasir
- Master data: produk, pelanggan, metode bayar, pengguna, pengaturan toko
- Kasir (POS) dengan keranjang, pajak, dan struk cetak 58/80 mm
- Riwayat order dan alur pembatalan dua langkah (kasir mengajukan, admin mengonfirmasi)
- Dashboard, laporan penjualan, kartu stok, ekspor CSV untuk Excel

## Cara menjalankan
1. Buat dan aktifkan virtual environment, lalu: pip install -r requirements.txt
2. Salin .env, isi SECRET_KEY dengan nilai acak.
3. Siapkan database: flask init-db, lalu flask seed
4. Jalankan: flask run
5. Buka http://127.0.0.1:5000 (akun awal ada di .env)

## Pengujian dan kualitas kode
    pytest
    ruff check .
    ruff format .

## Struktur singkat
    app/models/       tabel database
    app/blueprints/   satu folder per fitur (routes, forms, services)
    app/templates/    tampilan Jinja2
    tests/            test otomatis (pytest)
