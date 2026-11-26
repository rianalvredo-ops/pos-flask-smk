from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, StringField, SubmitField
from wtforms.validators import DataRequired, InputRequired, NumberRange


class ProdukForm(FlaskForm):
    kode = StringField(
        "Kode Produk",
        validators=[DataRequired(message="Kode produk wajib diisi.")],
    )
    nama = StringField(
        "Nama Produk",
        validators=[DataRequired(message="Nama produk wajib diisi.")],
    )
    kategori = StringField("Kategori")
    harga = IntegerField(
        "Harga (Rp)",
        validators=[
            InputRequired(message="Harga harus berupa angka dan minimal 0."),
            NumberRange(min=0, message="Harga harus berupa angka dan minimal 0."),
        ],
    )
    stok = IntegerField(
        "Stok",
        validators=[
            InputRequired(message="Stok harus berupa angka dan minimal 0."),
            NumberRange(min=0, message="Stok harus berupa angka dan minimal 0."),
        ],
    )
    aktif = BooleanField("Produk aktif", default=True)
    submit = SubmitField("Simpan produk")
