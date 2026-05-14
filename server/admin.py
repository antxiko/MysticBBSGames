"""CLI admin: gestionar BBSes registradas.

Uso:
  python -m server.admin add-bbs SHORTNAME "Full BBS Name"
  python -m server.admin list-bbs
  python -m server.admin disable-bbs SHORTNAME
  python -m server.admin enable-bbs SHORTNAME
  python -m server.admin rotate-token SHORTNAME
"""
import argparse
import secrets
import sys

from . import db


def cmd_add_bbs(short_name: str, full_name: str | None):
    short_name = short_name.upper().strip()
    if not short_name or not short_name.isalnum():
        print("ERROR: short_name debe ser alfanumerico", file=sys.stderr)
        sys.exit(1)
    existing = db.find_bbs_by_short_name(short_name)
    if existing:
        print(f"ERROR: '{short_name}' ya existe", file=sys.stderr)
        sys.exit(1)
    token = secrets.token_urlsafe(32)
    bbs_id = db.insert_bbs(short_name, full_name or short_name, db.hash_token(token))
    print(f"BBS registrada con id={bbs_id} short_name={short_name}")
    print()
    print(f"TOKEN (apuntalo, no se podra recuperar):")
    print(f"  {token}")


def cmd_list_bbs():
    rows = db.list_bbses()
    if not rows:
        print("(no hay BBSes registradas)")
        return
    print(f"{'short_name':<16} {'enabled':<8} {'created_at':<22} full_name")
    for r in rows:
        print(f"{r['short_name']:<16} {str(bool(r['enabled'])):<8} {r['created_at']:<22} {r['full_name']}")


def cmd_set_enabled(short_name: str, enabled: bool):
    ok = db.set_bbs_enabled(short_name, enabled)
    if ok:
        print(f"{short_name}: enabled={enabled}")
    else:
        print(f"ERROR: '{short_name}' no encontrada", file=sys.stderr)
        sys.exit(1)


def cmd_rotate_token(short_name: str):
    if not db.find_bbs_by_short_name(short_name):
        print(f"ERROR: '{short_name}' no encontrada", file=sys.stderr)
        sys.exit(1)
    token = secrets.token_urlsafe(32)
    db.update_bbs_token(short_name, db.hash_token(token))
    print(f"Token rotado para {short_name.upper()}:")
    print(f"  {token}")
    print("El token anterior queda invalidado.")


def main():
    db.init_db()
    p = argparse.ArgumentParser(prog="server.admin", description="Admin CLI del scoreboard")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add-bbs", help="Registrar una BBS nueva")
    a.add_argument("short_name")
    a.add_argument("full_name", nargs="?", default=None)

    sub.add_parser("list-bbs", help="Listar BBSes registradas")

    d = sub.add_parser("disable-bbs", help="Desactivar una BBS")
    d.add_argument("short_name")

    e = sub.add_parser("enable-bbs", help="Reactivar una BBS")
    e.add_argument("short_name")

    r = sub.add_parser("rotate-token", help="Generar un token nuevo para una BBS")
    r.add_argument("short_name")

    args = p.parse_args()
    if args.cmd == "add-bbs":
        cmd_add_bbs(args.short_name, args.full_name)
    elif args.cmd == "list-bbs":
        cmd_list_bbs()
    elif args.cmd == "disable-bbs":
        cmd_set_enabled(args.short_name, False)
    elif args.cmd == "enable-bbs":
        cmd_set_enabled(args.short_name, True)
    elif args.cmd == "rotate-token":
        cmd_rotate_token(args.short_name)


if __name__ == "__main__":
    main()
