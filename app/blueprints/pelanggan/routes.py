from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.blueprints.pelanggan import bp
from app.blueprints.pelanggan.forms import PelangganForm
from app.extensions import db
from app.models.pelanggan import Pelanggan


@bp.route("/pelanggan")
@login_required
def index():
    q = request.args.get("q", "").strip()
    query = Pelanggan.query
    if q:
        query = query.filter(
            (Pelanggan.nama.ilike(f"%{q}%")) | (Pelanggan.telepon.ilike(f"%{q}%"))
        )
    pelanggans = query.order_by(Pelanggan.bawaan.desc(), Pelanggan.id.asc()).all()
    total_pelanggan = Pelanggan.query.filter_by(bawaan=False).count()

    return render_template(
        "pelanggan/index.html",
        pelanggans=pelanggans,
        total_pelanggan=total_pelanggan,
        q=q,
    )


@bp.route("/pelanggan/tambah", methods=["GET", "POST"])
@login_required
def tambah():
    form = PelangganForm()
    if form.validate_on_submit():
        p = Pelanggan(
            nama=form.nama.data.strip(),
            telepon=form.telepon.data.strip() if form.telepon.data else None,
            alamat=form.alamat.data.strip() if form.alamat.data else None,
            bawaan=False,
        )
        db.session.add(p)
        db.session.commit()

        flash(f"Pelanggan {p.nama} tersimpan.", "success")
        return redirect(url_for("pelanggan.index"))

    return render_template("pelanggan/tambah.html", form=form)


@bp.route("/pelanggan/<int:pelanggan_id>/ubah", methods=["GET", "POST"])
@login_required
def ubah(pelanggan_id):
    p = db.session.get(Pelanggan, pelanggan_id)
    if not p:
        flash("Pelanggan tidak ditemukan.", "danger")
        return redirect(url_for("pelanggan.index"))

    # AC-32: Pelanggan "Umum" tidak bisa diubah
    if p.bawaan:
        flash("Pelanggan Umum tidak bisa diubah atau dihapus.", "danger")
        return redirect(url_for("pelanggan.index"))

    form = PelangganForm(obj=p)
    if form.validate_on_submit():
        p.nama = form.nama.data.strip()
        p.telepon = form.telepon.data.strip() if form.telepon.data else None
        p.alamat = form.alamat.data.strip() if form.alamat.data else None

        db.session.commit()
        flash(f"Pelanggan {p.nama} tersimpan.", "success")
        return redirect(url_for("pelanggan.index"))

    return render_template("pelanggan/ubah.html", form=form, pelanggan=p)


@bp.route("/pelanggan/<int:pelanggan_id>/hapus", methods=["POST"])
@login_required
def hapus(pelanggan_id):
    # AC-34: Kasir dilarang menghapus pelanggan (403)
    if not current_user.is_admin:
        abort(403)

    p = db.session.get(Pelanggan, pelanggan_id)
    if not p:
        flash("Pelanggan tidak ditemukan.", "danger")
        return redirect(url_for("pelanggan.index"))

    # AC-32: Pelanggan "Umum" tidak bisa dihapus
    if p.bawaan:
        flash("Pelanggan Umum tidak bisa diubah atau dihapus.", "danger")
        return redirect(url_for("pelanggan.index"))

    # AC-33: Pelanggan yang sudah punya order tidak bisa dihapus
    if p.orders.count() > 0:
        flash(
            f"Pelanggan {p.nama} tidak bisa dihapus karena sudah punya order.",
            "danger",
        )
        return redirect(url_for("pelanggan.index"))

    # AC-35: Pelanggan tanpa order berhasil dihapus
    nama = p.nama
    db.session.delete(p)
    db.session.commit()
    flash(f"Pelanggan {nama} dihapus.", "success")
    return redirect(url_for("pelanggan.index"))
