"""Alat bantu belajar: menampilkan tabel dan jumlah barisnya di database."""

import sqlite3
from pathlib import Path

DB = Path(__file__).parent / "instance" / "pos_smk.db"


def main():
    if not DB.exists():
        print("Database belum ada. Jalankan dulu: flask init-db")
        return
    con = sqlite3.connect(DB)
    daftar = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    for (nama,) in daftar:
        jumlah = con.execute(f"SELECT COUNT(*) FROM {nama}").fetchone()[0]
        print(f"{nama:15} {jumlah:>5} baris")
    con.close()


if __name__ == "__main__":
    main()
