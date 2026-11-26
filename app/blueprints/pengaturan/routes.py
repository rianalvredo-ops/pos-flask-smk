from flask import flash, redirect, render_template, url_for
from flask_login import login_required

from app.blueprints.auth.utils import admin_required
from app.blueprints.pengaturan import bp
from app.blueprints.pengaturan.forms import PengaturanForm
from app.extensions import db
from app.models.pengaturan import Pengaturan


@bp.route("/pengaturan", methods=["GET", "POST"])
@login_required
@admin_required
def index():
    pengaturan = Pengaturan.query.first()
    if not pengaturan:
        pengaturan = Pengaturan(
            nama_toko="SMK Mart POS",
            alamat_toko="Laboratorium RPL SMK",
            tarif_pajak=10,
            ambang_stok_menipis=5,
        )
        db.session.add(pengaturan)
        db.session.commit()

    form = PengaturanForm(obj=pengaturan)
    if form.validate_on_submit():
        pengaturan.nama_toko = form.nama_toko.data.strip()
        pengaturan.alamat_toko = (
            form.alamat_toko.data.strip() if form.alamat_toko.data else None
        )
        pengaturan.tarif_pajak = form.tarif_pajak.data
        pengaturan.ambang_stok_menipis = form.ambang_stok_menipis.data

        db.session.commit()
        flash("Pengaturan tersimpan.", "success")
        return redirect(url_for("pengaturan.index"))

    return render_template("pengaturan/index.html", form=form, pengaturan=pengaturan)
