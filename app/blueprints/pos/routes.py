import json
import re

from flask import abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.blueprints.pos import bp
from app.blueprints.pos.services import proses_checkout
from app.extensions import db
from app.models.metode_bayar import MetodeBayar
from app.models.order import Order
from app.models.pelanggan import Pelanggan
from app.models.pengaturan import Pengaturan
from app.models.produk import Produk


@bp.route("/pos")
@login_required
def index():
    """Layar Kasir Utama (SCR-03)."""
    pengaturan = Pengaturan.get_solo()
    produk_list = Produk.query.filter_by(aktif=True).order_by(Produk.nama.asc()).all()
    kategori_set = {p.kategori for p in produk_list if p.kategori}
    kategori_list = sorted(kategori_set)

    pelanggan_list = Pelanggan.query.order_by(
        Pelanggan.bawaan.desc(), Pelanggan.nama.asc()
    ).all()
    metode_list = (
        MetodeBayar.query.filter_by(aktif=True).order_by(MetodeBayar.id.asc()).all()
    )

    return render_template(
        "pos/index.html",
        pengaturan=pengaturan,
        produk_list=produk_list,
        kategori_list=kategori_list,
        pelanggan_list=pelanggan_list,
        metode_list=metode_list,
    )


@bp.route("/pos/pelanggan-cepat", methods=["POST"])
@login_required
def tambah_pelanggan_cepat():
    """Menambahkan pelanggan baru cepat dari dialog kasir (AC-74, TSK-09)."""
    if request.is_json:
        data = request.get_json() or {}
        nama = (data.get("nama") or "").strip()
        telepon = (data.get("telepon") or "").strip()
    else:
        nama = (request.form.get("nama") or "").strip()
        telepon = (request.form.get("telepon") or "").strip()

    if not nama:
        return (
            jsonify({"success": False, "message": "Nama pelanggan wajib diisi."}),
            400,
        )

    if telepon and not re.match(r"^[0-9+\-\s]+$", telepon):
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Nomor telepon hanya boleh berisi angka dan tanda hubung.",
                }
            ),
            400,
        )

    pelanggan = Pelanggan(nama=nama, telepon=telepon or None, bawaan=False)
    db.session.add(pelanggan)
    db.session.commit()

    return (
        jsonify(
            {
                "success": True,
                "id": pelanggan.id,
                "nama": pelanggan.nama,
                "message": f"Pelanggan {pelanggan.nama} berhasil ditambahkan.",
            }
        ),
        201,
    )


@bp.route("/pos/checkout", methods=["POST"])
@login_required
def checkout():
    """Memproses transaksi pembayaran pesanan kasir."""
    if request.is_json:
        data = request.get_json() or {}
    else:
        # Form post standar
        data = {
            "pelanggan_id": request.form.get("pelanggan_id", type=int),
            "metode_bayar_id": request.form.get("metode_bayar_id", type=int),
            "uang_diterima": request.form.get("uang_diterima"),
        }
        raw_items = request.form.get("items")
        if raw_items:
            try:
                data["items"] = json.loads(raw_items)
            except (json.JSONDecodeError, TypeError, ValueError):
                data["items"] = []
        else:
            data["items"] = []

    success, result, status_code = proses_checkout(current_user.id, data)

    if request.is_json:
        if success:
            order: Order = result
            return (
                jsonify(
                    {
                        "success": True,
                        "order_id": order.id,
                        "nomor": order.nomor,
                        "total": order.total,
                        "kembalian": order.kembalian,
                        "redirect_url": url_for("pos.struk", order_id=order.id),
                    }
                ),
                201,
            )
        return jsonify({"success": False, "message": str(result)}), status_code

    # Non-JSON response
    if success:
        order: Order = result
        flash(f"Order {order.nomor} berhasil dibayar.", "success")
        return redirect(url_for("pos.struk", order_id=order.id))

    flash(str(result), "error")
    return redirect(url_for("pos.index"))


@bp.route("/pos/struk/<int:order_id>")
@bp.route("/struk/<int:order_id>")
@login_required
def struk(order_id: int):
    """Menampilkan struk pesanan untuk dicetak (SCR-04, AC-80 s/d AC-84)."""
    order = db.session.get(Order, order_id)
    if not order:
        abort(404, description="Order tidak ditemukan.")

    # Proteksi hak akses kasir: hanya boleh melihat order miliknya sendiri (AC-83)
    if not current_user.is_admin and order.kasir_id != current_user.id:
        abort(403)

    pengaturan = Pengaturan.get_solo()
    return render_template("pos/struk.html", order=order, pengaturan=pengaturan)
