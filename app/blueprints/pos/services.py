from datetime import UTC, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models.metode_bayar import MetodeBayar
from app.models.mutasi_stok import MutasiStok
from app.models.order import Order, OrderItem
from app.models.pelanggan import Pelanggan
from app.models.pengaturan import Pengaturan
from app.models.produk import Produk


def hitung_pajak_dan_total(subtotal: int, tarif_pajak: int) -> tuple[int, int]:
    """Menghitung pajak dengan pembulatan 0,5 ke atas (ROUND_HALF_UP) dan total akhir."""
    pajak_raw = Decimal(subtotal) * Decimal(tarif_pajak) / Decimal(100)
    pajak = int(pajak_raw.quantize(Decimal(1), rounding=ROUND_HALF_UP))
    total = subtotal + pajak
    return pajak, total


def generate_order_number() -> str:
    """Menghasilkan nomor order berformat POS-YYYYMMDD-NNNN yang urut per hari WIB."""
    wib_tz = timezone(timedelta(hours=7))
    now_wib = datetime.now(wib_tz)
    tgl_wib = now_wib.strftime("%Y%m%d")
    prefix = f"POS-{tgl_wib}-"

    latest_order = (
        Order.query.filter(Order.nomor.like(f"{prefix}%"))
        .order_by(Order.id.desc())
        .first()
    )

    if latest_order and latest_order.nomor.startswith(prefix):
        try:
            seq_str = latest_order.nomor[len(prefix) :]
            next_seq = int(seq_str) + 1
        except ValueError:
            next_seq = 1
    else:
        next_seq = 1

    return f"{prefix}{next_seq:04d}"


def proses_checkout(kasir_id: int, data: dict) -> tuple[bool, str | Order, int]:
    """Memproses checkout kasir secara atomik.

    Returns:
        (success: bool, result_or_message: str | Order, status_code: int)
    """
    raw_items = data.get("items") or []
    if not raw_items:
        return False, "Keranjang masih kosong.", 400

    # 1. Validasi Pelanggan
    pelanggan_id = data.get("pelanggan_id")
    pelanggan = None
    if pelanggan_id:
        pelanggan = db.session.get(Pelanggan, pelanggan_id)
    if not pelanggan:
        # Default ke pelanggan bawaan "Umum"
        pelanggan = Pelanggan.query.filter_by(bawaan=True).first()
        if not pelanggan:
            pelanggan = Pelanggan.query.filter_by(nama="Umum").first()
    if not pelanggan:
        return False, "Data pelanggan tidak valid.", 400

    # 2. Validasi Metode Bayar
    metode_bayar_id = data.get("metode_bayar_id")
    if not metode_bayar_id:
        return False, "Pilih metode bayar.", 400
    metode_bayar = db.session.get(MetodeBayar, metode_bayar_id)
    if not metode_bayar or not metode_bayar.aktif:
        return False, "Metode bayar tidak tersedia atau nonaktif.", 400

    # 3. Konsolidasi Item & Validasi Produk serta Stok Atomik
    # Agregasikan jumlah item jika ada duplikasi produk_id di keranjang
    item_map: dict[int, int] = {}
    for item in raw_items:
        pid = item.get("produk_id")
        qty = item.get("jumlah", 1)
        if not pid:
            continue
        try:
            qty = int(qty)
        except (ValueError, TypeError):
            return False, "Jumlah produk tidak valid.", 400
        if qty <= 0:
            return False, "Jumlah produk harus minimal 1.", 400
        item_map[pid] = item_map.get(pid, 0) + qty

    if not item_map:
        return False, "Keranjang masih kosong.", 400

    # Periksa stok dan status produk dalam database
    validated_items: list[tuple[Produk, int, int]] = []
    subtotal = 0

    # Sort produk_id untuk menghindari potensi deadlock di DB concurrent
    for pid in sorted(item_map.keys()):
        qty = item_map[pid]
        # Query produk langsung
        produk = db.session.get(Produk, pid)
        if not produk or not produk.aktif:
            return False, f"Produk {produk.nama if produk else ''} tidak aktif.", 400
        if produk.stok <= 0:
            return (
                False,
                f"Stok {produk.nama} habis.",
                400,
            )
        if qty > produk.stok:
            return False, f"Stok {produk.nama} hanya {produk.stok}.", 400

        # Snapshot harga langsung dari database (mencegah manipulasi harga dari client, AC-67)
        item_subtotal = produk.harga * qty
        subtotal += item_subtotal
        validated_items.append((produk, qty, item_subtotal))

    # 4. Hitung Pajak dan Total Berdasarkan Pengaturan
    pengaturan = Pengaturan.get_solo()
    tarif_pajak = pengaturan.tarif_pajak
    pajak, total = hitung_pajak_dan_total(subtotal, tarif_pajak)

    # 5. Validasi Nominal Pembayaran
    uang_diterima_val = None
    kembalian_val = None

    if metode_bayar.jenis == "tunai":
        raw_uang = data.get("uang_diterima")
        if raw_uang is None or raw_uang == "":
            return False, "Isi uang diterima.", 400
        try:
            uang_diterima_val = int(raw_uang)
        except (ValueError, TypeError):
            return False, "Nominal uang diterima tidak valid.", 400

        if uang_diterima_val < total:
            selisih = total - uang_diterima_val
            selisih_formatted = f"{selisih:,}".replace(",", ".")
            return False, f"Uang diterima kurang Rp {selisih_formatted}.", 400

        kembalian_val = uang_diterima_val - total
    else:
        # Non-tunai (Transfer, QRIS) tidak mencatat uang_diterima & kembalian (AC-72)
        uang_diterima_val = None
        kembalian_val = None

    # 6. Pembuatan Transaksi Atomik (Order & Pengurangan Stok)
    try:
        nomor_order = generate_order_number()

        order = Order(
            nomor=nomor_order,
            waktu=datetime.now(UTC),
            kasir_id=kasir_id,
            pelanggan_id=pelanggan.id,
            metode_bayar_id=metode_bayar.id,
            subtotal=subtotal,
            tarif_pajak=tarif_pajak,
            pajak=pajak,
            total=total,
            uang_diterima=uang_diterima_val,
            kembalian=kembalian_val,
            status="selesai",
        )
        db.session.add(order)
        db.session.flush()  # Dapatkan order.id

        # Kurangi stok produk, catat MutasiStok, dan buat OrderItem
        for produk, qty, item_subtotal in validated_items:
            # Periksa ulang stok sebelum kurangi
            if produk.stok < qty:
                db.session.rollback()
                return False, f"Stok {produk.nama} hanya {produk.stok}.", 400

            stok_sebelum = produk.stok
            produk.stok -= qty
            stok_sesudah = produk.stok

            mutasi = MutasiStok(
                produk_id=produk.id,
                user_id=kasir_id,
                waktu=datetime.now(UTC),
                tipe="keluar",
                jumlah=qty,
                stok_sebelum=stok_sebelum,
                stok_sesudah=stok_sesudah,
                keterangan=f"Penjualan POS Nota #{nomor_order}",
            )
            db.session.add(mutasi)

            order_item = OrderItem(
                order_id=order.id,
                produk_id=produk.id,
                nama_produk=produk.nama,
                harga_satuan=produk.harga,
                jumlah=qty,
                subtotal=item_subtotal,
            )
            db.session.add(order_item)

        db.session.commit()
        return True, order, 201

    except SQLAlchemyError as e:
        db.session.rollback()
        return False, f"Terjadi kesalahan saat memproses pembayaran: {e!s}", 500
