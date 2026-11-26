import os
import sys

import click
from flask.cli import with_appcontext

from app.extensions import db
from app.models import (  # noqa: F401 (impor memastikan semua model terdaftar)
    MetodeBayar,
    MutasiStok,
    Order,
    OrderItem,
    Pelanggan,
    Pengaturan,
    Produk,
    User,
)


@click.command("init-db")
@with_appcontext
def init_db_command():
    """Membuat tabel database jika belum ada."""
    db.create_all()
    click.echo("Tabel database berhasil diinisialisasi.")


@click.command("seed")
@with_appcontext
def seed_command():
    """Mengisi data awal aplikasi (idempotent)."""
    admin_password = os.environ.get("ADMIN_PASSWORD")
    kasir_password = os.environ.get("KASIR_PASSWORD")

    if not admin_password or not kasir_password:
        click.echo(
            "Error: ADMIN_PASSWORD dan KASIR_PASSWORD wajib diatur di dalam .env"
            " sebelum menjalankan seed.",
            err=True,
        )
        sys.exit(1)

    admin_username = os.environ.get("ADMIN_USERNAME", "admin").strip().lower()
    kasir_username = os.environ.get("KASIR_USERNAME", "kasir1").strip().lower()

    # 2. Seed Pengguna Admin
    admin = User.query.filter_by(username=admin_username).first()
    if not admin:
        admin = User(
            nama="Administrator",
            username=admin_username,
            peran="admin",
            aktif=True,
        )
        admin.set_password(admin_password)
        db.session.add(admin)
        click.echo(f"Akun Admin dibuat: {admin_username}")
    else:
        admin.set_password(admin_password)
        click.echo(f"Akun Admin sudah ada: {admin_username} (password diperbarui)")

    # 3. Seed Pengguna Kasir contoh
    kasir = User.query.filter_by(username=kasir_username).first()
    if not kasir:
        kasir = User(
            nama="Kasir Siswa",
            username=kasir_username,
            peran="kasir",
            aktif=True,
        )
        kasir.set_password(kasir_password)
        db.session.add(kasir)
        click.echo(f"Akun Kasir dibuat: {kasir_username}")
    else:
        kasir.set_password(kasir_password)
        click.echo(f"Akun Kasir sudah ada: {kasir_username} (password diperbarui)")

    db.session.commit()

    # 4. Seed Metode Bayar
    metode_list = [
        ("Tunai", "Tunai"),
        ("QRIS", "non_Tunai"),
        ("Transfer", "non_Tunai"),
    ]
    for nama_m, jenis_m in metode_list:
        m = MetodeBayar.query.filter_by(nama=nama_m).first()
        if not m:
            m = MetodeBayar(nama=nama_m, jenis=jenis_m, aktif=True)
            db.session.add(m)
            click.echo(f"Metode bayar ditambahkan: {nama_m}")
    db.session.commit()

    # 5. Seed Pelanggan Bawaan "Umum"
    pelanggan_umum = Pelanggan.query.filter_by(bawaan=True).first()
    if not pelanggan_umum:
        pelanggan_umum = Pelanggan(nama="Umum", telepon="-", alamat="-", bawaan=True)
        db.session.add(pelanggan_umum)
        click.echo("Pelanggan bawaan 'Umum' ditambahkan.")

    # 6. Seed Pengaturan Toko
    pengaturan = Pengaturan.query.first()
    nama_toko = os.environ.get("NAMA_TOKO", "SMK Mart POS")
    alamat_toko = os.environ.get("ALAMAT_TOKO", "Laboratorium RPL SMK")
    if not pengaturan:
        pengaturan = Pengaturan(
            nama_toko=nama_toko,
            alamat_toko=alamat_toko,
            tarif_pajak=10,
            ambang_stok_menipis=5,
        )
        db.session.add(pengaturan)
        click.echo("Pengaturan toko awal ditambahkan.")
    db.session.commit()

    # 7. Seed Contoh Produk (15 item beragam)
    produk_contoh = [
        ("MK01", "Roti Bakar Coklat Keju", "Makanan", 12000, 25),
        ("MK02", "Donat Cokelat Meses", "Makanan", 7000, 30),
        ("MK03", "Sandwich Daging Asap", "Makanan", 15000, 20),
        ("MK04", "Nasi Goreng Spesial SMK", "Makanan", 18000, 15),
        ("MK05", "Risol Mayo Beef", "Makanan", 5000, 40),
        ("MN01", "Kopi Susu Gula Aren", "Minuman", 10000, 50),
        ("MN02", "Es Teh Manis Jumbo", "Minuman", 5000, 60),
        ("MN03", "Matcha Latte Dingin", "Minuman", 14000, 30),
        ("MN04", "Air Mineral 600ml", "Minuman", 4000, 80),
        ("MN05", "Jus Alpukat Kocok", "Minuman", 12000, 25),
        ("AT01", "Buku Tulis Spiral A5", "Alat Tulis", 8000, 45),
        ("AT02", "Pulpen Gel Hitam 0.5mm", "Alat Tulis", 4500, 100),
        ("AT03", "Penghapus Pensil Joyko", "Alat Tulis", 2500, 75),
        ("AT04", "Tipe-X Kertas Pita", "Alat Tulis", 7500, 35),
        ("AT05", "Penggaris Besi 30cm", "Alat Tulis", 6000, 40),
    ]

    for kode, nama, kat, harga, stok in produk_contoh:
        p = Produk.query.filter_by(kode=kode).first()
        if not p:
            p = Produk(
                kode=kode,
                nama=nama,
                kategori=kat,
                harga=harga,
                stok=stok,
                aktif=True,
            )
            db.session.add(p)

    db.session.commit()
    click.echo("Data awal (seed) berhasil disimpan ke database.")


def register_commands(app):
    """Mendaftarkan perintah CLI ke aplikasi Flask."""
    app.cli.add_command(init_db_command)
    app.cli.add_command(seed_command)
