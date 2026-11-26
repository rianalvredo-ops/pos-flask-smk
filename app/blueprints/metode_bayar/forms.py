from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired


class MetodeBayarForm(FlaskForm):
    nama = StringField(
        "Nama Metode Bayar",
        validators=[DataRequired(message="Nama metode bayar wajib diisi.")],
    )
    jenis = SelectField(
        "Jenis Pembayaran",
        choices=[("tunai", "Tunai"), ("non_tunai", "Non-Tunai (Transfer / QRIS)")],
        validators=[DataRequired()],
    )
    aktif = BooleanField("Metode aktif", default=True)
    submit = SubmitField("Simpan metode bayar")
