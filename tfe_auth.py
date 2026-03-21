from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import streamlit as st


USER_STORE_PATH = Path("tfe_users.json")
PBKDF2_ITERATIONS = 210_000
SESSION_KEY = "tfe_auth_session"


@dataclass(frozen=True)
class AuthUser:
    username: str
    role: str
    is_active: bool
    is_test_user: bool
    access_expires_at: Optional[str]


def _write_private_json(path: Path, payload: Dict[str, Any]) -> None:
    """
    Persist JSON with private permissions (0600) for auth-sensitive data.
    """
    data = json.dumps(payload, indent=2)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(data)
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass


def _utcnow_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii")


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data.encode("ascii"))


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algo, iter_text, salt_text, digest_text = stored_hash.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(iter_text)
        salt = _unb64(salt_text)
        expected = _unb64(digest_text)
    except Exception:
        return False

    probe = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(probe, expected)


def _default_store() -> Dict[str, Any]:
    admin_username = os.getenv("TFE_ADMIN_USERNAME", "admin")
    admin_password = os.getenv("TFE_ADMIN_PASSWORD", "admin-change-me")
    user_username = os.getenv("TFE_USER_USERNAME", "member")
    user_password = os.getenv("TFE_USER_PASSWORD", "member-change-me")

    return {
        "version": 1,
        "created_at": _utcnow_iso(),
        "users": [
            {
                "username": admin_username,
                "password_hash": hash_password(admin_password),
                "role": "admin",
                "is_active": True,
                "is_test_user": False,
                "access_expires_at": None,
                "created_at": _utcnow_iso(),
            },
            {
                "username": user_username,
                "password_hash": hash_password(user_password),
                "role": "member",
                "is_active": True,
                "is_test_user": False,
                "access_expires_at": None,
                "created_at": _utcnow_iso(),
            },
        ],
    }


def _load_store() -> Dict[str, Any]:
    if not USER_STORE_PATH.exists():
        store = _default_store()
        _write_private_json(USER_STORE_PATH, store)
        return store

    raw = USER_STORE_PATH.read_text(encoding="utf-8")
    try:
        os.chmod(USER_STORE_PATH, 0o600)
    except Exception:
        pass
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Invalid user store format: root is not an object.")
    if "users" not in data or not isinstance(data["users"], list):
        raise ValueError("Invalid user store format: 'users' list missing.")
    return data


def _find_user(username: str) -> Optional[Dict[str, Any]]:
    data = _load_store()
    lookup = username.strip().lower()
    for record in data["users"]:
        record_name = str(record.get("username", "")).strip().lower()
        if record_name == lookup:
            return record
    return None


def _is_access_expired(access_expires_at: Optional[str]) -> bool:
    if not access_expires_at:
        return False
    try:
        expires = datetime.fromisoformat(access_expires_at)
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return expires <= datetime.now(tz=timezone.utc)
    except Exception:
        return True


def authenticate_user(username: str, password: str) -> Optional[AuthUser]:
    record = _find_user(username)
    if not record:
        return None

    if not bool(record.get("is_active", False)):
        return None

    stored_hash = str(record.get("password_hash", ""))
    if not verify_password(password, stored_hash):
        return None

    access_expires_at = record.get("access_expires_at")
    if _is_access_expired(access_expires_at):
        return None

    return AuthUser(
        username=str(record.get("username", "")).strip(),
        role=str(record.get("role", "member")).strip().lower(),
        is_active=bool(record.get("is_active", False)),
        is_test_user=bool(record.get("is_test_user", False)),
        access_expires_at=access_expires_at,
    )


def init_auth_session() -> None:
    if SESSION_KEY not in st.session_state:
        st.session_state[SESSION_KEY] = None


def get_current_user() -> Optional[AuthUser]:
    init_auth_session()
    value = st.session_state.get(SESSION_KEY)
    return value if isinstance(value, AuthUser) else None


def is_authenticated() -> bool:
    return get_current_user() is not None


def is_admin_user() -> bool:
    user = get_current_user()
    return bool(user and user.role == "admin")


def login(username: str, password: str) -> bool:
    user = authenticate_user(username=username, password=password)
    if not user:
        return False
    st.session_state[SESSION_KEY] = user
    return True


def logout() -> None:
    st.session_state[SESSION_KEY] = None


def render_login_form() -> None:
    st.subheader("Sign In")
    st.caption("Use your TFE account credentials.")

    with st.form("tfe_login_form", clear_on_submit=False):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign In")

    if submitted:
        ok = login(username=username, password=password)
        if ok:
            st.success("Signed in successfully.")
            st.rerun()
        else:
            st.error("Sign in failed. Check username/password or access status.")


def render_auth_sidebar() -> None:
    user = get_current_user()
    if not user:
        return

    st.sidebar.markdown("---")
    st.sidebar.write(f"Signed in as: **{user.username}**")
    st.sidebar.write(f"Role: **{user.role}**")
    if user.is_test_user:
        st.sidebar.warning("TEST USER")

    if st.sidebar.button("Sign Out"):
        logout()
        st.rerun()


def require_authenticated_user() -> None:
    if is_authenticated():
        render_auth_sidebar()
        return

    st.title("Tao Financial Engine")
    st.info("Please sign in to continue.")
    render_login_form()
    st.stop()


def require_admin_user() -> None:
    require_authenticated_user()
    if is_admin_user():
        return

    st.error("Access denied. Admin role required.")
    st.stop()
