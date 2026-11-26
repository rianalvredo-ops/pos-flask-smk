from flask_wtf import FlaskForm
from wtforms import IntegerField, StringField, SubmitField
from wtforms.validators import DataRequired, InputRequired, NumberRange, ValidationError


def validate_tarif_range(form, field):
    if field.data is not None and not (0 <= field.data <= 100):
        raise ValidationError("Tarif pajak harus antara 0 sampai 100%.")


class PengaturanForm(FlaskForm):
    nama_toko = StringField(
        "Nama Toko",
        validators=[DataRequired(message="Nama toko wajib diisi.")],
    )
    alamat_toko = StringField("Alamat Toko")
    tarif_pajak = IntegerField(
        "Tarif Pajak (%)",
        validators=[
            InputRequired(message="Tarif pajak harus antara 0 sampai 100%."),
            validate_tarif_range,
        ],
    )
    ambang_stok_menipis = IntegerField(
        "Ambang Stok Menipis",
        validators=[
            InputRequired(message="Ambang stok menipis minimal 0."),
            NumberRange(min=0, message="Ambang stok menipis minimal 0."),
        ],
    )
    submit = SubmitField("Simpan pengaturan")
