from datetime import UTC, datetime

from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.blueprints.auth.utils import admin_required
from app.blueprints.produk import bp
from app.blueprints.produk.forms import ProdukForm
from app.extensions import db
from app.models.mutasi_stok import MutasiStok
from app.models.pengaturan import Pengaturan
from app.models.produk import Produk


@bp.route("/produk")
@login_required
@admin_required
def index():
    pengaturan = Pengaturan.query.first()
    ambang = pengaturan.ambang_stok_menipis if pengaturan else 5

    query = Produk.query
    q = request.args.get("q", "").strip()
    kategori_filter = request.args.get("kategori", "").strip()
    status_filter = request.args.get("status", "").strip()

    if q:
        query = query.filter(
            (Produk.nama.ilike(f"%{q}%")) | (Produk.kode.ilike(f"%{q}%"))
        )
    if kategori_filter:
        query = query.filter(Produk.kategori == kategori_filter)
    if status_filter == "aktif":
        query = query.filter(Produk.aktif == True)
    elif status_filter == "nonaktif":
        query = query.filter(Produk.aktif == False)

    produks = query.order_by(Produk.id.asc()).all()

    # Data ringkasan / statistik
    semua_produk = Produk.query.all()
    total_aktif = sum(1 for p in semua_produk if p.aktif)
    total_nilai_stok = sum(p.harga * p.stok for p in semua_produk if p.aktif)
    total_menipis = sum(1 for p in semua_produk if p.aktif and p.stok <= ambang)
    kategori_set = sorted({p.kategori for p in semua_produk if p.kategori})

    return render_template(
        "produk/index.html",
        produks=produks,
        ambang=ambang,
        q=q,
        kategori_filter=kategori_filter,
        status_filter=status_filter,
        total_aktif=total_aktif,
        total_nilai_stok=total_nilai_stok,
        total_menipis=total_menipis,
        kategori_set=kategori_set,
    )


@bp.route("/produk/tambah", methods=["GET", "POST"])
@login_required
@admin_required
def tambah():
    form = ProdukForm()
    if form.validate_on_submit():
        kode = form.kode.data.strip().upper()
        existing = Produk.query.filter_by(kode=kode).first()
        if existing:
            flash(f"Kode {kode} sudah dipakai produk lain.", "danger")
            form.kode.errors.append(f"Kode {kode} sudah dipakai produk lain.")
            return render_template("produk/tambah.html", form=form), 200

        p = Produk(
            kode=kode,
            nama=form.nama.data.strip(),
            kategori=form.kategori.data.strip() if form.kategori.data else None,
            harga=form.harga.data,
            stok=form.stok.data,
            aktif=form.aktif.data,
        )
        db.session.add(p)
        db.session.commit()

        flash(f"Produk {p.nama} tersimpan.", "success")
        return redirect(url_for("produk.index"))

    return render_template("produk/tambah.html", form=form)


@bp.route("/produk/<int:produk_id>/ubah", methods=["GET", "POST"])
@login_required
@admin_required
def ubah(produk_id):
    p = db.session.get(Produk, produk_id)
    if not p:
        flash("Produk tidak ditemukan.", "danger")
        return redirect(url_for("produk.index"))

    form = ProdukForm(obj=p)
    if form.validate_on_submit():
        kode_baru = form.kode.data.strip().upper()
        existing = (
            Produk.query.filter_by(kode=kode_baru).filter(Produk.id != p.id).first()
        )
        if existing:
            flash(f"Kode {kode_baru} sudah dipakai produk lain.", "danger")
            form.kode.errors.append(f"Kode {kode_baru} sudah dipakai produk lain.")
            return render_template("produk/ubah.html", form=form, produk=p), 200

        p.kode = kode_baru
        p.nama = form.nama.data.strip()
        p.kategori = form.kategori.data.strip() if form.kategori.data else None
        p.harga = form.harga.data
        p.stok = form.stok.data
        p.aktif = form.aktif.data

        db.session.commit()
        flash(f"Produk {p.nama} tersimpan.", "success")
        return redirect(url_for("produk.index"))

    return render_template("produk/ubah.html", form=form, produk=p)


@bp.route("/produk/<int:produk_id>/tambah-stok", methods=["POST"])
@login_required
@admin_required
def tambah_stok_cepat(produk_id: int):
    """Restock Cepat: Menambahkan stok produk secara atomik dan mencatat ke MutasiStok."""
    p = db.session.get(Produk, produk_id)
    wants_json = (
        request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    )

    if not p:
        if wants_json:
            return (
                jsonify({"success": False, "message": "Produk tidak ditemukan."}),
                404,
            )
        flash("Produk tidak ditemukan.", "danger")
        return redirect(url_for("produk.index"))

    if request.is_json:
        data = request.get_json() or {}
        raw_jumlah = data.get("jumlah")
        keterangan = (data.get("keterangan") or "").strip()
    else:
        raw_jumlah = request.form.get("jumlah")
        keterangan = (request.form.get("keterangan") or "").strip()

    try:
        jumlah = int(raw_jumlah)
        if jumlah <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        msg = "Jumlah penambahan stok harus berupa angka bulat positif minimal 1."
        if wants_json:
            return jsonify({"success": False, "message": msg}), 400
        flash(msg, "danger")
        return redirect(url_for("produk.index"))

    stok_sebelum = p.stok
    p.stok += jumlah
    stok_sesudah = p.stok

    catatan = keterangan if keterangan else "Restock Cepat Inventaris"
    mutasi = MutasiStok(
        produk_id=p.id,
        user_id=current_user.id,
        waktu=datetime.now(UTC),
        tipe="masuk",
        jumlah=jumlah,
        stok_sebelum=stok_sebelum,
        stok_sesudah=stok_sesudah,
        keterangan=f"Restock (+{jumlah}): {catatan}",
    )
    db.session.add(mutasi)
    db.session.commit()

    msg = f"Berhasil menambah +{jumlah} stok untuk {p.nama}. Stok saat ini: {p.stok}."
    if wants_json:
        return (
            jsonify(
                {
                    "success": True,
                    "message": msg,
                    "stok_baru": p.stok,
                    "produk_id": p.id,
                }
            ),
            200,
        )

    flash(msg, "success")
    return redirect(url_for("produk.index"))


@bp.route("/produk/<int:produk_id>/kartu-stok")
@login_required
@admin_required
def kartu_stok_produk(produk_id: int):
    """Dialihkan ke halaman Kartu Stok Laporan terfilter produk ini."""
    return redirect(url_for("laporan.kartu_stok", produk_id=produk_id))
