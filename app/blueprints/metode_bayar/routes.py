from flask import flash, redirect, render_template, url_for
from flask_login import login_required

from app.blueprints.auth.utils import admin_required
from app.blueprints.metode_bayar import bp
from app.blueprints.metode_bayar.forms import MetodeBayarForm
from app.extensions import db
from app.models.metode_bayar import MetodeBayar


@bp.route("/metode-bayar")
@login_required
@admin_required
def index():
    metode_list = MetodeBayar.query.order_by(MetodeBayar.id.asc()).all()
    return render_template("metode_bayar/index.html", metode_list=metode_list)


@bp.route("/metode-bayar/tambah", methods=["GET", "POST"])
@login_required
@admin_required
def tambah():
    form = MetodeBayarForm()
    if form.validate_on_submit():
        nama = form.nama.data.strip()
        existing = MetodeBayar.query.filter_by(nama=nama).first()
        if existing:
            flash(f"Nama {nama} sudah dipakai.", "danger")
            form.nama.errors.append(f"Nama {nama} sudah dipakai.")
            return render_template("metode_bayar/tambah.html", form=form), 200

        m = MetodeBayar(
            nama=nama,
            jenis=form.jenis.data,
            aktif=form.aktif.data,
        )
        db.session.add(m)
        db.session.commit()

        flash(f"Metode bayar {m.nama} tersimpan.", "success")
        return redirect(url_for("metode_bayar.index"))

    return render_template("metode_bayar/tambah.html", form=form)


@bp.route("/metode-bayar/<int:metode_id>/ubah", methods=["GET", "POST"])
@login_required
@admin_required
def ubah(metode_id):
    m = db.session.get(MetodeBayar, metode_id)
    if not m:
        flash("Metode bayar tidak ditemukan.", "danger")
        return redirect(url_for("metode_bayar.index"))

    form = MetodeBayarForm(obj=m)
    if form.validate_on_submit():
        nama_baru = form.nama.data.strip()
        existing = (
            MetodeBayar.query.filter_by(nama=nama_baru)
            .filter(MetodeBayar.id != m.id)
            .first()
        )
        if existing:
            flash(f"Nama {nama_baru} sudah dipakai.", "danger")
            form.nama.errors.append(f"Nama {nama_baru} sudah dipakai.")
            return render_template("metode_bayar/ubah.html", form=form, metode=m), 200

        # AC-42: Cek metode aktif terakhir jika dinonaktifkan
        baru_aktif = form.aktif.data
        if m.aktif and not baru_aktif:
            aktif_lain = MetodeBayar.query.filter(
                MetodeBayar.aktif == True,
                MetodeBayar.id != m.id,
            ).count()
            if aktif_lain == 0:
                flash(
                    "Metode bayar aktif terakhir tidak bisa dinonaktifkan. Aktifkan metode lain dulu.",
                    "danger",
                )
                return render_template(
                    "metode_bayar/ubah.html", form=form, metode=m
                ), 200

        m.nama = nama_baru
        m.jenis = form.jenis.data
        m.aktif = baru_aktif

        db.session.commit()
        flash(f"Metode bayar {m.nama} tersimpan.", "success")
        return redirect(url_for("metode_bayar.index"))

    return render_template("metode_bayar/ubah.html", form=form, metode=m)
