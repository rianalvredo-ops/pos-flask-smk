from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.blueprints.auth import bp
from app.blueprints.auth.forms import LoginForm
from app.models.pengaturan import Pengaturan
from app.models.user import User


def _aman_untuk_redirect(alamat):
    """Hanya izinkan alamat internal, bukan //situs-lain atau /\situs-lain."""
    return alamat.startswith("/") and not alamat.startswith(("//", "/\\"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("dashboard.index"))
        return redirect(url_for("pos.index"))

    form = LoginForm()
    pengaturan = Pengaturan.query.first()
    nama_toko = pengaturan.nama_toko if pengaturan else "SMK Mart POS"

    if form.validate_on_submit():
        username = form.username.data.strip().lower()
        password = form.password.data
        user = User.query.filter_by(username=username).first()

        if user is None or not user.check_password(password):
            flash("Username atau password salah.", "danger")
            # Kosongkan password saat render ulang (UX-01)
            form.password.data = ""
            return render_template(
                "auth/login.html", form=form, nama_toko=nama_toko
            ), 200

        if not user.aktif:
            flash("Akun Anda tidak aktif. Hubungi Admin.", "danger")
            form.password.data = ""
            return render_template(
                "auth/login.html", form=form, nama_toko=nama_toko
            ), 200

        # Login berhasil
        login_user(user)
        flash(f"Selamat datang, {user.nama}.", "success")

        # Cek parameter next
        next_page = request.args.get("next")
        if next_page and _aman_untuk_redirect(next_page):
            return redirect(next_page)

        if user.is_admin:
            return redirect(url_for("dashboard.index"))
        return redirect(url_for("pos.index"))

    return render_template("auth/login.html", form=form, nama_toko=nama_toko)


@bp.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    logout_user()
    flash("Anda berhasil keluar.", "info")
    return redirect(url_for("auth.login"))
