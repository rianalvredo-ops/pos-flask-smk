from datetime import UTC, datetime, timedelta, timezone

from flask import Flask, redirect, render_template, url_for
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect

from app.cli import register_commands
from app.extensions import db, migrate
from app.models.user import User

csrf = CSRFProtect()

login_manager = LoginManager()

login_manager.login_view = "auth.login"

login_manager.login_message = "Silakan login terlebih dahulu."

login_manager.login_message_category = "warning"


@login_manager.user_loader
def load_user(user_id):

    return User.query.get(int(user_id))


def create_app(config_class=None):

    app = Flask(__name__)

    if config_class is None:
        app.config.from_object("app.config.Config")

    else:
        if isinstance(config_class, str):
            from config import config as config_map

            config_class = config_map.get(config_class, config_class)
    app.config.from_object(config_class)

    db.init_app(app)

    migrate.init_app(app, db)

    csrf.init_app(app)

    login_manager.init_app(app)

    @app.route("/")
    def index():

        if current_user.is_authenticated:
            if current_user.is_admin:
                return redirect(url_for("dashboard.index"))

            return redirect(url_for("pos.index"))

        return redirect(url_for("auth.login"))

    from app.blueprints.auth import bp as auth_bp
    from app.blueprints.dashboard import bp as dashboard_bp
    from app.blueprints.laporan import bp as laporan_bp
    from app.blueprints.metode_bayar import bp as metode_bayar_bp
    from app.blueprints.order import bp as order_bp
    from app.blueprints.pelanggan import bp as pelanggan_bp
    from app.blueprints.pengaturan import bp as pengaturan_bp
    from app.blueprints.pengguna import bp as pengguna_bp
    from app.blueprints.pos import bp as pos_bp
    from app.blueprints.produk import bp as produk_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(laporan_bp)
    app.register_blueprint(pengguna_bp)
    app.register_blueprint(produk_bp)
    app.register_blueprint(pelanggan_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(metode_bayar_bp)
    app.register_blueprint(pengaturan_bp)
    app.register_blueprint(pos_bp)

    register_commands(app)

    # Jinja2 filter: Rupiah dan waktu WIB
    @app.template_filter("rupiah")
    def rupiah_filter(value):
        """Memformat integer menjadi format rupiah Indonesia: Rp 12.500."""
        if value is None:
            return "Rp 0"
        try:
            val = int(value)
            formatted = f"{val:,}".replace(",", ".")
            return f"Rp {formatted}"
        except (ValueError, TypeError):
            return "Rp 0"

    @app.template_filter("waktu_wib")
    def waktu_wib_filter(value, format_str="%d/%m/%Y %H:%M"):
        """Mengonversi waktu UTC ke WIB (UTC+7) dan memformatnya."""
        if not value:
            return "-"
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=UTC)
            wib_tz = timezone(timedelta(hours=7))
            wib_time = value.astimezone(wib_tz)
            return wib_time.strftime(format_str)
        return str(value)

    # Penanganan error: halaman yang ramah, tanpa jejak kesalahan (traceback)
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    return app
