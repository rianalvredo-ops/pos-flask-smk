from datetime import UTC, datetime, time, timedelta, timezone

from flask import render_template
from flask_login import login_required
from sqlalchemy import func

from app.blueprints.auth.utils import admin_required
from app.blueprints.dashboard import bp
from app.extensions import db
from app.models.order import Order, OrderItem
from app.models.pengaturan import Pengaturan
from app.models.produk import Produk

WIB_TZ = timezone(timedelta(hours=7))


@bp.route("/dashboard")
@login_required
@admin_required
def index():
    """Layar Dashboard Admin (SCR-02)."""
    now_wib = datetime.now(WIB_TZ)
    today_wib = now_wib.date()

    # 1. Batas Hari Ini WIB dikonversi ke UTC
    start_dt_wib = datetime.combine(today_wib, time.min, tzinfo=WIB_TZ)
    start_utc = start_dt_wib.astimezone(UTC).replace(tzinfo=None)

    end_dt_wib = datetime.combine(today_wib, time.max, tzinfo=WIB_TZ)
    end_utc = end_dt_wib.astimezone(UTC).replace(tzinfo=None)

    # Order hari ini (AC-100: dibatalkan tidak dihitung, pengajuan_batal dihitung)
    orders_today = Order.query.filter(
        Order.waktu >= start_utc,
        Order.waktu <= end_utc,
        Order.status != "dibatalkan",
    ).all()

    omzet_hari_ini = sum(o.total for o in orders_today)
    jumlah_order_hari_ini = len(orders_today)
    rata_rata_order = (
        round(omzet_hari_ini / jumlah_order_hari_ini)
        if jumlah_order_hari_ini > 0
        else 0
    )

    # 2. Grafik Omzet 7 Hari Terakhir (AC-102)
    nama_hari_map = {
        0: "Sen",
        1: "Sel",
        2: "Rab",
        3: "Kam",
        4: "Jum",
        5: "Sab",
        6: "Min",
    }
    grafik_7_hari = []
    total_omzet_7_hari = 0

    for i in range(6, -1, -1):
        d = today_wib - timedelta(days=i)
        d_start = (
            datetime.combine(d, time.min, tzinfo=WIB_TZ)
            .astimezone(UTC)
            .replace(tzinfo=None)
        )
        d_end = (
            datetime.combine(d, time.max, tzinfo=WIB_TZ)
            .astimezone(UTC)
            .replace(tzinfo=None)
        )

        day_orders = Order.query.filter(
            Order.waktu >= d_start,
            Order.waktu <= d_end,
            Order.status != "dibatalkan",
        ).all()

        day_omzet = sum(o.total for o in day_orders)
        total_omzet_7_hari += day_omzet
        day_label = "Hari ini" if i == 0 else nama_hari_map[d.weekday()]

        grafik_7_hari.append(
            {
                "tanggal": d.strftime("%Y-%m-%d"),
                "label": day_label,
                "omzet": day_omzet,
                "is_today": (i == 0),
            }
        )

    max_omzet = max((g["omzet"] for g in grafik_7_hari), default=0)
    for g in grafik_7_hari:
        g["height_pct"] = int((g["omzet"] / max_omzet) * 85) if max_omzet > 0 else 0

    # 3. 5 Produk Terlaris 30 Hari Terakhir (AC-102: tanpa order dibatalkan)
    start_30d_wib = today_wib - timedelta(days=29)
    start_30d_utc = (
        datetime.combine(start_30d_wib, time.min, tzinfo=WIB_TZ)
        .astimezone(UTC)
        .replace(tzinfo=None)
    )

    top_products_query = (
        db.session.query(
            OrderItem.nama_produk,
            func.sum(OrderItem.jumlah).label("total_terjual"),
            func.sum(OrderItem.subtotal).label("total_omzet"),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .filter(
            Order.waktu >= start_30d_utc,
            Order.waktu <= end_utc,
            Order.status != "dibatalkan",
        )
        .group_by(OrderItem.nama_produk)
        .order_by(func.sum(OrderItem.jumlah).desc())
        .limit(5)
        .all()
    )

    top_products = [
        {
            "nama": row.nama_produk,
            "terjual": int(row.total_terjual or 0),
            "omzet": int(row.total_omzet or 0),
        }
        for row in top_products_query
    ]

    # 4. Daftar Stok Menipis (AC-103)
    pengaturan = Pengaturan.get_solo()
    ambang = pengaturan.ambang_stok_menipis
    stok_menipis = (
        Produk.query.filter(
            Produk.aktif.is_(True),
            Produk.stok <= ambang,
        )
        .order_by(Produk.stok.asc(), Produk.nama.asc())
        .all()
    )

    # 5. Counter Pengajuan Pembatalan Menunggu (AC-105)
    pengajuan_batal_count = Order.query.filter_by(status="pengajuan_batal").count()

    # 6. 5 Order Terbaru
    order_terbaru = (
        Order.query.order_by(Order.waktu.desc(), Order.id.desc()).limit(5).all()
    )

    return render_template(
        "dashboard/index.html",
        omzet_hari_ini=omzet_hari_ini,
        jumlah_order_hari_ini=jumlah_order_hari_ini,
        rata_rata_order=rata_rata_order,
        grafik_7_hari=grafik_7_hari,
        total_omzet_7_hari=total_omzet_7_hari,
        top_products=top_products,
        stok_menipis=stok_menipis,
        ambang=ambang,
        pengajuan_batal_count=pengajuan_batal_count,
        order_terbaru=order_terbaru,
    )
