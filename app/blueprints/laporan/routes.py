import csv
import io
from datetime import UTC, datetime, timedelta, timezone

from flask import (
    Response,
    render_template,
    request,
)
from flask_login import login_required

from app.blueprints.auth.utils import admin_required
from app.blueprints.laporan import bp
from app.blueprints.order.routes import parse_wib_date_range
from app.extensions import db
from app.models.metode_bayar import MetodeBayar
from app.models.mutasi_stok import MutasiStok
from app.models.order import Order
from app.models.produk import Produk

WIB_TZ = timezone(timedelta(hours=7))


def format_wib(dt: datetime | None, format_str="%d/%m/%Y %H:%M") -> str:
    if not dt:
        return "-"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    wib_dt = dt.astimezone(WIB_TZ)
    return wib_dt.strftime(format_str)


@bp.route("/")
@login_required
@admin_required
def index():
    """Halaman Laporan Akuntansi & Ringkasan Penjualan."""
    start_str = request.args.get("tanggal_mulai")
    end_str = request.args.get("tanggal_akhir")
    status = request.args.get("status", "semua").strip().lower()
    metode_id = request.args.get("metode_id", type=int)

    start_date, end_date, start_utc, end_utc = parse_wib_date_range(start_str, end_str)

    query = Order.query.filter(Order.waktu >= start_utc, Order.waktu <= end_utc)

    if status in ["selesai", "pengajuan_batal", "dibatalkan"]:
        query = query.filter(Order.status == status)
    if metode_id:
        query = query.filter(Order.metode_bayar_id == metode_id)

    orders = query.order_by(Order.waktu.desc()).all()

    # Hitung metrik akuntansi
    orders_valid = [o for o in orders if o.status != "dibatalkan"]
    total_omzet = sum(o.total for o in orders_valid)
    total_subtotal = sum(o.subtotal for o in orders_valid)
    total_pajak = sum(o.pajak for o in orders_valid)
    total_transaksi = len(orders_valid)
    total_batal = sum(1 for o in orders if o.status == "dibatalkan")

    # Rincian per Metode Bayar
    metode_stats = {}
    for o in orders_valid:
        nama_metode = o.metode_bayar.nama if o.metode_bayar else "Lainnya"
        if nama_metode not in metode_stats:
            metode_stats[nama_metode] = {
                "nama": nama_metode,
                "jumlah_order": 0,
                "total_nominal": 0,
            }
        metode_stats[nama_metode]["jumlah_order"] += 1
        metode_stats[nama_metode]["total_nominal"] += o.total

    metode_list = MetodeBayar.query.filter_by(aktif=True).all()

    return render_template(
        "laporan/index.html",
        orders=orders,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
        status=status,
        metode_id=metode_id,
        metode_list=metode_list,
        total_omzet=total_omzet,
        total_subtotal=total_subtotal,
        total_pajak=total_pajak,
        total_transaksi=total_transaksi,
        total_batal=total_batal,
        metode_stats=list(metode_stats.values()),
    )


@bp.route("/penjualan/ekspor")
@login_required
@admin_required
def ekspor_penjualan():
    """Ekspor laporan transaksi penjualan ke file CSV (kompatibel Excel)."""
    start_str = request.args.get("tanggal_mulai")
    end_str = request.args.get("tanggal_akhir")
    status = request.args.get("status", "semua").strip().lower()
    metode_id = request.args.get("metode_id", type=int)

    start_date, end_date, start_utc, end_utc = parse_wib_date_range(start_str, end_str)

    query = Order.query.filter(Order.waktu >= start_utc, Order.waktu <= end_utc)

    if status in ["selesai", "pengajuan_batal", "dibatalkan"]:
        query = query.filter(Order.status == status)
    if metode_id:
        query = query.filter(Order.metode_bayar_id == metode_id)

    orders = query.order_by(Order.waktu.asc()).all()

    output = io.StringIO()
    # Tulis BOM UTF-8 agar Excel membuka karakter dengan benar
    output.write("\ufeff")
    writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)

    # Header CSV
    writer.writerow(
        [
            "No. Order",
            "Waktu (WIB)",
            "Kasir",
            "Pelanggan",
            "Metode Bayar",
            "Subtotal (Rp)",
            "Tarif Pajak (%)",
            "Pajak (Rp)",
            "Total (Rp)",
            "Status",
            "Alasan Batal",
            "Dikonfirmasi Oleh",
        ]
    )

    for o in orders:
        status_label = (
            "Selesai"
            if o.status == "selesai"
            else ("Pengajuan Batal" if o.status == "pengajuan_batal" else "Dibatalkan")
        )
        writer.writerow(
            [
                o.nomor,
                format_wib(o.waktu),
                o.kasir.nama if o.kasir else "-",
                o.pelanggan.nama if o.pelanggan else "Umum",
                o.metode_bayar.nama if o.metode_bayar else "-",
                o.subtotal,
                o.tarif_pajak,
                o.pajak,
                o.total,
                status_label,
                o.alasan_batal or "-",
                o.dikonfirmasi_oleh.nama if o.dikonfirmasi_oleh else "-",
            ]
        )

    filename = f"Laporan_Penjualan_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
    response = Response(output.getvalue(), mimetype="text/csv; charset=utf-8")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response


@bp.route("/kartu-stok")
@login_required
@admin_required
def kartu_stok():
    """Halaman Kartu Riwayat Mutasi Stok (Semua Produk atau Per Produk)."""
    produk_id = request.args.get("produk_id", type=int)
    tipe = request.args.get("tipe", "semua").strip().lower()
    page = request.args.get("page", 1, type=int)

    query = MutasiStok.query

    if produk_id:
        query = query.filter(MutasiStok.produk_id == produk_id)
    if tipe in ["masuk", "keluar", "batal", "penyesuaian"]:
        query = query.filter(MutasiStok.tipe == tipe)

    query = query.order_by(MutasiStok.waktu.desc(), MutasiStok.id.desc())

    pagination = query.paginate(page=page, per_page=30, error_out=False)
    mutasi_list = pagination.items

    produk_list = Produk.query.filter_by(aktif=True).order_by(Produk.nama.asc()).all()
    selected_produk = db.session.get(Produk, produk_id) if produk_id else None

    return render_template(
        "laporan/kartu_stok.html",
        mutasi_list=mutasi_list,
        pagination=pagination,
        produk_id=produk_id,
        tipe=tipe,
        produk_list=produk_list,
        selected_produk=selected_produk,
    )


@bp.route("/kartu-stok/ekspor")
@login_required
@admin_required
def ekspor_kartu_stok():
    """Ekspor Kartu Riwayat Mutasi Stok ke file CSV."""
    produk_id = request.args.get("produk_id", type=int)
    tipe = request.args.get("tipe", "semua").strip().lower()

    query = MutasiStok.query

    if produk_id:
        query = query.filter(MutasiStok.produk_id == produk_id)
    if tipe in ["masuk", "keluar", "batal", "penyesuaian"]:
        query = query.filter(MutasiStok.tipe == tipe)

    mutasi_list = query.order_by(MutasiStok.waktu.asc(), MutasiStok.id.asc()).all()

    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)

    writer.writerow(
        [
            "ID Mutasi",
            "Waktu (WIB)",
            "Kode Produk",
            "Nama Produk",
            "Tipe Mutasi",
            "Jumlah Perubahan",
            "Stok Sebelum",
            "Stok Sesudah",
            "Keterangan",
            "Petugas",
        ]
    )

    for m in mutasi_list:
        tipe_label = {
            "masuk": "Masuk / Restock",
            "keluar": "Keluar / Penjualan",
            "batal": "Batal / Retur",
            "penyesuaian": "Penyesuaian",
        }.get(m.tipe, m.tipe.capitalize())

        tanda = "+" if m.tipe in ["masuk", "batal"] else "-"

        writer.writerow(
            [
                m.id,
                format_wib(m.waktu),
                m.produk.kode if m.produk else "-",
                m.produk.nama if m.produk else "-",
                tipe_label,
                f"{tanda}{m.jumlah}",
                m.stok_sebelum,
                m.stok_sesudah,
                m.keterangan or "-",
                m.user.nama if m.user else "Sistem",
            ]
        )

    tgl_now = datetime.now(WIB_TZ).strftime("%Y%m%d")
    filename = f"Kartu_Mutasi_Stok_{tgl_now}.csv"
    response = Response(output.getvalue(), mimetype="text/csv; charset=utf-8")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response
