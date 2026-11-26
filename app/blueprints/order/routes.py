from datetime import UTC, datetime, time, timedelta, timezone

from flask import (
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from app.blueprints.order import bp
from app.extensions import db
from app.models.mutasi_stok import MutasiStok
from app.models.order import Order
from app.models.produk import Produk
from app.models.user import User

WIB_TZ = timezone(timedelta(hours=7))


def parse_wib_date_range(start_date_str: str | None, end_date_str: str | None):
    """Mengonversi rentang tanggal WIB (YYYY-MM-DD) ke batas datetime UTC."""
    today_wib = datetime.now(WIB_TZ).date()

    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str.strip(), "%Y-%m-%d").date()
        except ValueError:
            start_date = today_wib
    else:
        start_date = today_wib

    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str.strip(), "%Y-%m-%d").date()
        except ValueError:
            end_date = today_wib
    else:
        end_date = today_wib

    # Jika start_date > end_date, tukar posisinya
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    # Batas awal: 00:00:00.000000 WIB dikonversi ke UTC
    start_dt_wib = datetime.combine(start_date, time.min, tzinfo=WIB_TZ)
    start_utc = start_dt_wib.astimezone(UTC).replace(tzinfo=None)

    # Batas akhir: 23:59:59.999999 WIB dikonversi ke UTC
    end_dt_wib = datetime.combine(end_date, time.max, tzinfo=WIB_TZ)
    end_utc = end_dt_wib.astimezone(UTC).replace(tzinfo=None)

    return start_date, end_date, start_utc, end_utc


@bp.route("/")
@login_required
def index():
    """Daftar Riwayat Order (SCR-05)."""
    # Parameter filter
    start_str = request.args.get("tanggal_mulai")
    end_str = request.args.get("tanggal_akhir")
    status = request.args.get("status", "semua").strip().lower()
    q = (request.args.get("q") or "").strip()
    kasir_id = request.args.get("kasir_id", type=int)
    page = request.args.get("page", 1, type=int)

    # Parse tanggal WIB
    start_date, end_date, start_utc, end_utc = parse_wib_date_range(start_str, end_str)

    # Query dasar
    query = Order.query.filter(Order.waktu >= start_utc, Order.waktu <= end_utc)

    # Batasan hak akses: Kasir hanya melihat order buatannya sendiri (AC-86)
    if not current_user.is_admin:
        query = query.filter(Order.kasir_id == current_user.id)
    elif kasir_id:
        query = query.filter(Order.kasir_id == kasir_id)

    # Filter status
    if status in ["selesai", "pengajuan_batal", "dibatalkan"]:
        query = query.filter(Order.status == status)

    # Filter pencarian nomor order
    if q:
        query = query.filter(Order.nomor.ilike(f"%{q}%"))

    # Urutkan dari yang terbaru
    query = query.order_by(Order.waktu.desc(), Order.id.desc())

    # Paginasi 25 baris per halaman
    pagination = query.paginate(page=page, per_page=25, error_out=False)
    orders = pagination.items

    # Daftar kasir untuk filter Admin
    kasir_list = (
        User.query.filter_by(aktif=True).order_by(User.nama.asc()).all()
        if current_user.is_admin
        else []
    )

    # Jumlah pengajuan pembatalan yang menunggu (AC-105, banner pengingat)
    pengajuan_batal_count = (
        Order.query.filter_by(status="pengajuan_batal").count()
        if current_user.is_admin
        else 0
    )

    return render_template(
        "order/index.html",
        orders=orders,
        pagination=pagination,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
        status=status,
        q=q,
        kasir_id=kasir_id,
        kasir_list=kasir_list,
        pengajuan_batal_count=pengajuan_batal_count,
    )


@bp.route("/<int:order_id>")
@bp.route("/<int:order_id>/detail")
@login_required
def detail(order_id: int):
    """Detail Order (SCR-06)."""
    order = db.session.get(Order, order_id)
    if not order:
        abort(404, description="Order tidak ditemukan.")

    # Hak akses: Kasir dilarang membuka order milik kasir lain (AC-83)
    if not current_user.is_admin and order.kasir_id != current_user.id:
        abort(403)

    wants_json = (
        request.is_json
        or request.path.endswith("/detail")
        or request.headers.get("Accept") == "application/json"
        or "application/json" in request.headers.get("Accept", "")
        or request.args.get("format") == "json"
    )

    if wants_json:
        waktu_utc = (
            order.waktu.replace(tzinfo=UTC)
            if order.waktu and order.waktu.tzinfo is None
            else order.waktu
        )
        waktu_batal_utc = (
            order.waktu_batal.replace(tzinfo=UTC)
            if order.waktu_batal and order.waktu_batal.tzinfo is None
            else order.waktu_batal
        )

        return jsonify(
            {
                "id": order.id,
                "nomor": order.nomor,
                "waktu": waktu_utc.isoformat() if waktu_utc else None,
                "status": order.status,
                "kasir": order.kasir.nama if order.kasir else "Kasir",
                "pelanggan": order.pelanggan.nama if order.pelanggan else "Umum",
                "metode": order.metode_bayar.nama if order.metode_bayar else "Tunai",
                "subtotal": order.subtotal,
                "tarif_pajak": order.tarif_pajak,
                "pajak": order.pajak,
                "total": order.total,
                "uang_diterima": order.uang_diterima,
                "kembalian": order.kembalian,
                "alasan_batal": order.alasan_batal,
                "diajukan_oleh": (
                    order.diajukan_oleh.nama if order.diajukan_oleh else None
                ),
                "dikonfirmasi_oleh": (
                    order.dikonfirmasi_oleh.nama if order.dikonfirmasi_oleh else None
                ),
                "waktu_batal": (
                    waktu_batal_utc.isoformat() if waktu_batal_utc else None
                ),
                "items": [
                    {
                        "id": item.id,
                        "nama_produk": item.nama_produk,
                        "harga_satuan": item.harga_satuan,
                        "jumlah": item.jumlah,
                        "subtotal": item.subtotal,
                    }
                    for item in order.items
                ],
            }
        )

    return render_template("order/detail.html", order=order)


@bp.route("/<int:order_id>/ajukan-batal", methods=["POST"])
@login_required
def ajukan_batal(order_id: int):
    """Kasir mengajukan pembatalan pesanan (AC-87, AC-88, AC-89)."""
    order = db.session.get(Order, order_id)
    if not order:
        abort(404, description="Order tidak ditemukan.")

    # Kasir dilarang mengajukan batal untuk order kasir lain (AC-89)
    if not current_user.is_admin and order.kasir_id != current_user.id:
        abort(403)

    # Hanya order Selesai yang bisa diajukan (AC-89)
    if order.status != "selesai":
        msg = "Order sudah dalam status pengajuan atau sudah dibatalkan."
        if request.is_json:
            return jsonify({"success": False, "message": msg}), 400
        flash(msg, "warning")
        return redirect(url_for("order.index"))

    # Validasi alasan pembatalan minimal 5 karakter (AC-88)
    if request.is_json:
        data = request.get_json() or {}
        alasan = (data.get("alasan") or "").strip()
    else:
        alasan = (request.form.get("alasan") or "").strip()

    if len(alasan) < 5:
        msg = "Alasan wajib diisi, minimal 5 karakter."
        if request.is_json:
            return jsonify({"success": False, "message": msg}), 400
        flash(msg, "danger")
        return redirect(url_for("order.index"))

    # Simpan status pengajuan batal (stok TIDAK berubah, AC-87)
    order.status = "pengajuan_batal"
    order.alasan_batal = alasan
    order.diajukan_oleh_id = current_user.id
    db.session.commit()

    msg = f"Pengajuan pembatalan order {order.nomor} berhasil dikirim."
    if request.is_json:
        return jsonify({"success": True, "message": msg}), 200

    flash(msg, "success")
    return redirect(url_for("order.index"))


@bp.route("/<int:order_id>/konfirmasi-batal", methods=["POST"])
@login_required
def konfirmasi_batal(order_id: int):
    """Admin mengonfirmasi pembatalan pesanan dan mengembalikan stok (AC-90 s/d AC-92, AC-95)."""
    if not current_user.is_admin:
        abort(403)

    order = db.session.get(Order, order_id)
    if not order:
        abort(404, description="Order tidak ditemukan.")

    # Cek apakah order sudah dibatalkan sebelumnya (AC-92)
    if order.status == "dibatalkan":
        msg = "Order sudah dibatalkan sebelumnya."
        if request.is_json:
            return jsonify({"success": False, "message": msg}), 400
        flash(msg, "warning")
        return redirect(url_for("order.index"))

    # Hanya order status pengajuan_batal yang bisa dikonfirmasi lewat rute ini
    if order.status != "pengajuan_batal":
        msg = "Hanya order berstatus Pengajuan Batal yang dapat dikonfirmasi."
        if request.is_json:
            return jsonify({"success": False, "message": msg}), 400
        flash(msg, "warning")
        return redirect(url_for("order.index"))

    # Validasi checkbox pemeriksaan fisik (AC-91)
    if request.is_json:
        data = request.get_json() or {}
        cek_fisik = data.get("cek_fisik")
    else:
        cek_fisik = request.form.get("cek_fisik")

    if not cek_fisik or str(cek_fisik).lower() in ["false", "0", "off"]:
        msg = "Centang dulu bahwa barang sudah dicek secara fisik."
        if request.is_json:
            return jsonify({"success": False, "message": msg}), 400
        flash(msg, "danger")
        return redirect(url_for("order.index"))

    # Ubah status jadi dibatalkan dan kembalikan stok produk (AC-90)
    order.status = "dibatalkan"
    order.dikonfirmasi_oleh_id = current_user.id
    order.waktu_batal = datetime.now(UTC)

    for item in order.items:
        produk = db.session.get(Produk, item.produk_id)
        if produk:
            stok_sebelum = produk.stok
            produk.stok += item.jumlah
            stok_sesudah = produk.stok
            mutasi = MutasiStok(
                produk_id=produk.id,
                user_id=current_user.id,
                waktu=datetime.now(UTC),
                tipe="batal",
                jumlah=item.jumlah,
                stok_sebelum=stok_sebelum,
                stok_sesudah=stok_sesudah,
                keterangan=f"Retur Pembatalan Order #{order.nomor}",
            )
            db.session.add(mutasi)

    db.session.commit()

    msg = f"Pembatalan order {order.nomor} telah dikonfirmasi dan stok dikembalikan."
    if request.is_json:
        return jsonify({"success": True, "message": msg}), 200

    flash(msg, "success")
    return redirect(url_for("order.index"))


@bp.route("/<int:order_id>/tolak-batal", methods=["POST"])
@login_required
def tolak_batal(order_id: int):
    """Admin menolak pengajuan pembatalan pesanan (AC-93, AC-95)."""
    if not current_user.is_admin:
        abort(403)

    order = db.session.get(Order, order_id)
    if not order:
        abort(404, description="Order tidak ditemukan.")

    if order.status != "pengajuan_batal":
        msg = "Hanya order berstatus Pengajuan Batal yang dapat ditolak."
        if request.is_json:
            return jsonify({"success": False, "message": msg}), 400
        flash(msg, "warning")
        return redirect(url_for("order.index"))

    # Kembalikan status ke selesai, bersihkan catatan pengajuan, stok tetap (AC-93)
    order.status = "selesai"
    order.alasan_batal = None
    order.diajukan_oleh_id = None
    db.session.commit()

    msg = f"Pengajuan pembatalan order {order.nomor} ditolak."
    if request.is_json:
        return jsonify({"success": True, "message": msg}), 200

    flash(msg, "info")
    return redirect(url_for("order.index"))


@bp.route("/<int:order_id>/batalkan-langsung", methods=["POST"])
@login_required
def batalkan_langsung(order_id: int):
    """Admin membatalkan pesanan secara langsung dengan alasan dan cek fisik (AC-94, AC-95)."""
    if not current_user.is_admin:
        abort(403)

    order = db.session.get(Order, order_id)
    if not order:
        abort(404, description="Order tidak ditemukan.")

    if order.status != "selesai":
        msg = "Hanya order berstatus Selesai yang dapat dibatalkan langsung."
        if request.is_json:
            return jsonify({"success": False, "message": msg}), 400
        flash(msg, "warning")
        return redirect(url_for("order.index"))

    if request.is_json:
        data = request.get_json() or {}
        alasan = (data.get("alasan") or "").strip()
        cek_fisik = data.get("cek_fisik")
    else:
        alasan = (request.form.get("alasan") or "").strip()
        cek_fisik = request.form.get("cek_fisik")

    if len(alasan) < 5:
        msg = "Alasan wajib diisi, minimal 5 karakter."
        if request.is_json:
            return jsonify({"success": False, "message": msg}), 400
        flash(msg, "danger")
        return redirect(url_for("order.index"))

    if not cek_fisik or str(cek_fisik).lower() in ["false", "0", "off"]:
        msg = "Centang dulu bahwa barang sudah dicek secara fisik."
        if request.is_json:
            return jsonify({"success": False, "message": msg}), 400
        flash(msg, "danger")
        return redirect(url_for("order.index"))

    order.status = "dibatalkan"
    order.alasan_batal = alasan
    order.diajukan_oleh_id = current_user.id
    order.dikonfirmasi_oleh_id = current_user.id
    order.waktu_batal = datetime.now(UTC)

    # Kembalikan stok
    for item in order.items:
        produk = db.session.get(Produk, item.produk_id)
        if produk:
            stok_sebelum = produk.stok
            produk.stok += item.jumlah
            stok_sesudah = produk.stok
            mutasi = MutasiStok(
                produk_id=produk.id,
                user_id=current_user.id,
                waktu=datetime.now(UTC),
                tipe="batal",
                jumlah=item.jumlah,
                stok_sebelum=stok_sebelum,
                stok_sesudah=stok_sesudah,
                keterangan=f"Retur Batal Langsung Order #{order.nomor}",
            )
            db.session.add(mutasi)

    db.session.commit()

    msg = f"Order {order.nomor} berhasil dibatalkan dan stok dikembalikan."
    if request.is_json:
        return jsonify({"success": True, "message": msg}), 200

    flash(msg, "success")
    return redirect(url_for("order.index"))
