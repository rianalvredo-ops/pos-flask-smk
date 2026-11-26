import re

from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, ValidationError


def validate_username_format(form, field):
    """Username hanya boleh huruf kecil, angka, dan garis bawah, 3-30 karakter."""
    val = field.data.strip().lower()
    if not (3 <= len(val) <= 30):
        raise ValidationError(
            "Username hanya boleh huruf kecil, angka, dan garis bawah, 3-30 karakter."
        )
    if not re.match(r"^[a-z0-9_]+$", val):
        raise ValidationError(
            "Username hanya boleh huruf kecil, angka, dan garis bawah, 3-30 karakter."
        )


def validate_min_password(form, field):
    """Password minimal 8 karakter (AC-12)."""
    if not field.data or len(field.data) < 8:
        raise ValidationError("Password minimal 8 karakter.")


class TambahPenggunaForm(FlaskForm):
    nama = StringField(
        "Nama Lengkap",
        validators=[DataRequired(message="Nama wajib diisi.")],
    )
    username = StringField(
        "Username",
        validators=[
            DataRequired(message="Username wajib diisi."),
            validate_username_format,
        ],
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(message="Password wajib diisi."),
            validate_min_password,
        ],
    )
    peran = SelectField(
        "Peran",
        choices=[("kasir", "Kasir"), ("admin", "Admin")],
        default="kasir",
        validators=[DataRequired()],
    )
    aktif = BooleanField("Akun aktif", default=True)
    submit = SubmitField("Simpan pengguna")


class UbahPenggunaForm(FlaskForm):
    nama = StringField(
        "Nama Lengkap",
        validators=[DataRequired(message="Nama wajib diisi.")],
    )
    username = StringField(
        "Username",
        render_kw={"readonly": True},
    )
    peran = SelectField(
        "Peran",
        choices=[("kasir", "Kasir"), ("admin", "Admin")],
        validators=[DataRequired()],
    )
    aktif = BooleanField("Akun aktif")
    submit = SubmitField("Simpan pengguna")


class ResetPasswordForm(FlaskForm):
    password_baru = PasswordField(
        "Password Baru",
        validators=[
            DataRequired(message="Password wajib diisi."),
            validate_min_password,
        ],
    )
    submit = SubmitField("Ganti password")
