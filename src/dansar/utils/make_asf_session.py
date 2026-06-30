import argparse
import sys
from getpass import getpass


def make_asf_session(username=None, password=None):
    """
    Create and return an authenticated ASF session using Earthdata credentials.

    Parameters
    ----------
    username : str, optional
        Earthdata username. If not provided, the user is prompted.

    password : str, optional
        Earthdata password. If not provided, the user is prompted securely.

    Returns
    -------
    asf_search.ASFSession
        Authenticated ASF session.

    Raises
    ------
    ModuleNotFoundError
        If asf_search is not installed.

    ValueError
        If username or password are empty.

    RuntimeError
        If authentication fails.
    """

    try:
        import asf_search as asf
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Could not import asf_search. Install it with:\n\n"
            "    pip install asf-search\n"
        ) from exc

    if username is None:
        username = input("Earthdata username: ")

    if password is None:
        password = getpass("Earthdata password: ")

    if not isinstance(username, str):
        raise TypeError(
            f"username must be a string, not {type(username).__name__}"
        )

    if not isinstance(password, str):
        raise TypeError(
            f"password must be a string, not {type(password).__name__}"
        )

    username = username.strip()

    if not username:
        raise ValueError("Earthdata username is empty.")

    if not password:
        raise ValueError("Earthdata password is empty.")

    try:
        session = asf.ASFSession()
        session.auth_with_creds(username, password)

    except Exception as exc:
        raise RuntimeError(
            "ASF/Earthdata authentication failed. "
            "Check your username, password, and network connection."
        ) from exc

    return session


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Create an authenticated ASF/Earthdata session. "
            "This script is mainly a login test; it does not download data."
        )
    )

    parser.add_argument(
        "-u",
        "--username",
        help=(
            "Earthdata username. If omitted, you will be prompted. "
            "Avoid passing passwords directly on the command line."
        ),
    )

    parser.add_argument(
        "--no-login-test",
        action="store_true",
        help=(
            "Show that the script can run, but do not prompt for credentials "
            "or authenticate."
        ),
    )

    args = parser.parse_args()

    if args.no_login_test:
        print("make_asf_session.py is available. No login attempted.")
        return 0

    try:
        session = make_asf_session(username=args.username)
        print("ASF/Earthdata authentication succeeded.")
        return 0

    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())