"""Alat bantu: menampilkan alamat IP komputer ini di jaringan lokal.

Jalankan:  python ip_lan.py [port]
"""

import socket
import sys


def ip_lan() -> str:
    """Mencari IP yang dipakai komputer ini untuk keluar ke jaringan."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Tidak ada data yang benar-benar dikirim; ini hanya cara
        # meminta sistem operasi memilih antarmuka jaringan yang aktif.
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "127.0.0.1"
    finally:
        s.close()


if __name__ == "__main__":
    port = sys.argv[1] if len(sys.argv) > 1 else "5001"
    print(f"Alamat untuk tim lain: http://{ip_lan()}:{port}")
