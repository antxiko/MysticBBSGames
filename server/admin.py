"""CLI admin: gestionar BBSes registradas y admins del panel web.

Uso:
  python -m server.admin add-bbs SHORTNAME "Full BBS Name"
  python -m server.admin list-bbs
  python -m server.admin disable-bbs SHORTNAME
  python -m server.admin enable-bbs SHORTNAME
  python -m server.admin rotate-token SHORTNAME
  python -m server.admin delete-bbs SHORTNAME
  python -m server.admin set-admin USERNAME       # pide pass por stdin
  python -m server.admin list-admin
"""
import argparse
import getpass
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


def cmd_delete_bbs(short_name: str):
    short = short_name.upper()
    bbs = db.find_bbs_by_short_name(short)
    if not bbs:
        print(f"ERROR: '{short}' no encontrada", file=sys.stderr)
        sys.exit(1)
    confirm = input(f"Borrar BBS '{short}' Y todos sus scores? Esto es irreversible. Escribe SI para confirmar: ").strip()
    if confirm != "SI":
        print("Cancelado.")
        return
    ok, scores = db.delete_bbs(short)
    if ok:
        print(f"BBS '{short}' borrada. {scores} scores eliminados.")
    else:
        print(f"ERROR: fallo al borrar '{short}'", file=sys.stderr)
        sys.exit(1)


def cmd_set_admin(username: str):
    """Crea o actualiza un admin del panel web. Pide pass por stdin sin echo."""
    p1 = getpass.getpass(f"Nueva password para admin '{username}': ")
    if len(p1) < 6:
        print("ERROR: minimo 6 caracteres.", file=sys.stderr)
        sys.exit(1)
    p2 = getpass.getpass("Confirmar: ")
    if p1 != p2:
        print("ERROR: las passwords no coinciden.", file=sys.stderr)
        sys.exit(1)
    pwhash = db.hash_password(p1)
    result = db.upsert_admin(username, pwhash)
    print(f"Admin '{username}': {result}")


def cmd_list_admin():
    rows = db.list_admins()
    if not rows:
        print("(no hay admins registrados)")
        return
    print(f"{'username':<20} {'created_at':<22}")
    for r in rows:
        print(f"{r['username']:<20} {r['created_at']:<22}")


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

    db_ = sub.add_parser("delete-bbs", help="Borrar BBS y todos sus scores (irreversible)")
    db_.add_argument("short_name")

    sa = sub.add_parser("set-admin", help="Crear/actualizar admin del panel web")
    sa.add_argument("username")

    sub.add_parser("list-admin", help="Listar admins del panel web")

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
    elif args.cmd == "delete-bbs":
        cmd_delete_bbs(args.short_name)
    elif args.cmd == "set-admin":
        cmd_set_admin(args.username)
    elif args.cmd == "list-admin":
        cmd_list_admin()


if __name__ == "__main__":
    main()
