import re

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, ValidationError


def validate_telepon(form, field):
    if field.data:
        val = field.data.strip()
        if not re.match(r"^\+?[0-9\- ]+$", val) or not any(c.isdigit() for c in val):
            raise ValidationError("Nomor telepon hanya boleh angka dan tanda +.")


class PelangganForm(FlaskForm):
    nama = StringField(
        "Nama Pelanggan",
        validators=[DataRequired(message="Nama wajib diisi.")],
    )
    telepon = StringField(
        "Nomor Telepon",
        validators=[validate_telepon],
    )
    alamat = StringField("Alamat")
    submit = SubmitField("Simpan pelanggan")
