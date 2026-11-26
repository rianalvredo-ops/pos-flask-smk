from flask import flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.blueprints.auth.utils import admin_required
from app.blueprints.pengguna import bp
from app.blueprints.pengguna.forms import (
    ResetPasswordForm,
    TambahPenggunaForm,
    UbahPenggunaForm,
)
from app.extensions import db
from app.models.user import User


@bp.route("/pengguna")
@login_required
@admin_required
def index():
    users = User.query.order_by(User.id.asc()).all()
    reset_form = ResetPasswordForm()
    return render_template("pengguna/index.html", users=users, reset_form=reset_form)


@bp.route("/pengguna/tambah", methods=["GET", "POST"])
@login_required
@admin_required
def tambah():
    form = TambahPenggunaForm()
    if form.validate_on_submit():
        username = form.username.data.strip().lower()

        # Cek username duplikat (AC-11)
        existing = User.query.filter_by(username=username).first()
        if existing:
            flash(f"Username {username} sudah dipakai.", "danger")
            form.username.errors.append(f"Username {username} sudah dipakai.")
            return render_template("pengguna/tambah.html", form=form), 200

        user = User(
            nama=form.nama.data.strip(),
            username=username,
            peran=form.peran.data,
            aktif=form.aktif.data,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash(f"Pengguna {user.nama} tersimpan.", "success")
        return redirect(url_for("pengguna.index"))

    return render_template("pengguna/tambah.html", form=form)


@bp.route("/pengguna/<int:user_id>/ubah", methods=["GET", "POST"])
@login_required
@admin_required
def ubah(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash("Pengguna tidak ditemukan.", "danger")
        return redirect(url_for("pengguna.index"))

    form = UbahPenggunaForm(obj=user)
    form.username.data = user.username  # Selalu tampilkan username asli

    if form.validate_on_submit():
        baru_aktif = form.aktif.data
        baru_peran = form.peran.data

        # AC-14: Admin tidak bisa menonaktifkan akun sendiri
        if user.id == current_user.id and not baru_aktif:
            flash("Anda tidak bisa menonaktifkan akun Anda sendiri.", "danger")
            return render_template("pengguna/ubah.html", form=form, user=user), 200

        # AC-14: Harus ada minimal satu Admin aktif
        if user.is_admin and (not baru_aktif or baru_peran != "admin"):
            admin_aktif_lain = User.query.filter(
                User.peran == "admin",
                User.aktif == True,
                User.id != user.id,
            ).count()
            if admin_aktif_lain == 0:
                flash("Harus ada minimal satu Admin aktif.", "danger")
                return render_template("pengguna/ubah.html", form=form, user=user), 200

        # AC-16: Username tidak berubah meski payload mengirim username lain
        user.nama = form.nama.data.strip()
        user.peran = baru_peran
        user.aktif = baru_aktif

        db.session.commit()
        flash(f"Pengguna {user.nama} tersimpan.", "success")
        return redirect(url_for("pengguna.index"))

    return render_template("pengguna/ubah.html", form=form, user=user)


@bp.route("/pengguna/<int:user_id>/reset-password", methods=["POST"])
@login_required
@admin_required
def reset_password(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash("Pengguna tidak ditemukan.", "danger")
        return redirect(url_for("pengguna.index"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password_baru.data)
        db.session.commit()
        flash(f"Password {user.nama} diganti.", "success")
    else:
        for err in form.password_baru.errors:
            flash(err, "danger")

    return redirect(url_for("pengguna.index"))
