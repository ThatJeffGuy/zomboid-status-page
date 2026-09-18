#!/usr/bin/env python3
import getpass
import secrets
import sys

try:
    import bcrypt
except ImportError:
    sys.exit("bcrypt is not installed in this environment -- run with `pip install bcrypt` first.")


def main() -> None:
    password = getpass.getpass("Choose the admin password: ")
    confirm = getpass.getpass("Confirm: ")
    if password != confirm:
        sys.exit("passwords did not match")
    if len(password) < 8:
        sys.exit("use at least 8 characters")

    password_hash = bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")
    session_secret = secrets.token_urlsafe(48)

    print("\nADMIN_PASSWORD_HASH and SESSION_SECRET:\n")
    print(f"ADMIN_PASSWORD_HASH={password_hash}")
    print(f"SESSION_SECRET={session_secret}")


if __name__ == "__main__":
    main()
