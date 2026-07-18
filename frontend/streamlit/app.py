"""
Optional Streamlit UI for AI Legal Copilot.

Prefer the built-in web UI at the API root (/).
Run:
  streamlit run frontend/streamlit/app.py
"""

import os
from datetime import datetime

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8010").rstrip("/")

st.set_page_config(
    page_title="AI Legal Copilot",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

DISCLAIMER_SHORT = (
    "This tool is **not legal advice** and does not create an attorney–client "
    "relationship. Always consult a licensed attorney for important decisions."
)


# ── Session defaults ──────────────────────────────────────────────
defaults = {
    "token": None,
    "user": None,
    "documents": [],
    "active_document_id": None,
    "messages": [],
    "auth_mode": "login",
    "last_error": None,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def _headers() -> dict:
    if not st.session_state.token:
        return {}
    return {"Authorization": f"Bearer {st.session_state.token}"}


def api_request(method: str, path: str, **kwargs):
    """Call API and return (json|None, status, error_detail)."""
    url = f"{API_URL}{path}"
    timeout = kwargs.pop("timeout", 60)
    try:
        response = requests.request(
            method,
            url,
            headers={**_headers(), **kwargs.pop("headers", {})},
            timeout=timeout,
            **kwargs,
        )
        try:
            data = response.json()
        except Exception:
            data = {"detail": response.text or "Empty response"}
        if response.status_code >= 400:
            detail = data.get("detail", data)
            if isinstance(detail, list):
                detail = "; ".join(
                    str(item.get("msg", item)) for item in detail
                )
            return data, response.status_code, str(detail)
        return data, response.status_code, None
    except requests.exceptions.ConnectionError:
        return None, 0, (
            f"Cannot reach API at {API_URL}. "
            "Start it with: PYTHONPATH=backend uvicorn src.api.main:app --port 8010"
        )
    except requests.exceptions.Timeout:
        return None, 0, "Request timed out. Try again."
    except Exception as exc:
        return None, 0, str(exc)


def refresh_documents():
    data, status, err = api_request("GET", "/documents")
    if status == 200 and isinstance(data, list):
        st.session_state.documents = data
    elif err:
        st.session_state.last_error = err


def load_messages(document_id: str):
    data, status, err = api_request(
        "GET", f"/documents/{document_id}/messages"
    )
    if status == 200 and isinstance(data, list):
        st.session_state.messages = [
            {
                "role": m["role"],
                "content": m["content"],
                "metadata": {
                    "question_type": m.get("question_type"),
                    "processing_time": m.get("processing_time"),
                },
            }
            for m in data
        ]
    elif err:
        st.session_state.last_error = err
        st.session_state.messages = []


def logout():
    for key, value in defaults.items():
        st.session_state[key] = value


def check_api() -> bool:
    data, status, _ = api_request("GET", "/health", timeout=3)
    return status == 200


# ── Auth screens ──────────────────────────────────────────────────
def render_auth():
    st.markdown("## AI Legal Copilot")
    st.info(DISCLAIMER_SHORT)

    if not check_api():
        st.error(f"API offline at `{API_URL}`")
        st.code("uvicorn src.api.main:app --reload --port 8000")
        st.stop()

    tabs = st.tabs(["Sign in", "Create account", "Forgot password", "Privacy"])

    with tabs[0]:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", type="primary")
        if submitted:
            data, status, err = api_request(
                "POST",
                "/auth/login",
                json={"email": email, "password": password},
            )
            if status == 200:
                st.session_state.token = data["access_token"]
                me, _, me_err = api_request("GET", "/auth/me")
                if me:
                    st.session_state.user = me
                refresh_documents()
                st.rerun()
            else:
                st.error(err or "Login failed")

    with tabs[1]:
        with st.form("register_form"):
            full_name = st.text_input("Full name (optional)")
            email = st.text_input("Email", key="reg_email")
            password = st.text_input(
                "Password (min 8 characters)",
                type="password",
                key="reg_password",
            )
            role = st.selectbox(
                "I am a…",
                options=[
                    "individual",
                    "lawyer",
                    "chartered_accountant",
                    "business_owner",
                    "hr_professional",
                    "student",
                ],
                format_func=lambda r: {
                    "individual": "Individual",
                    "lawyer": "Lawyer",
                    "chartered_accountant": "Chartered Accountant",
                    "business_owner": "Business Owner",
                    "hr_professional": "HR Professional",
                    "student": "Student",
                }.get(r, r),
            )
            accept = st.checkbox(
                "I understand this is not legal advice and I accept the disclaimer "
                "and privacy policy."
            )
            submitted = st.form_submit_button("Create account", type="primary")
        if submitted:
            if not accept:
                st.error("You must accept the disclaimer to register.")
            else:
                data, status, err = api_request(
                    "POST",
                    "/auth/register",
                    json={
                        "email": email,
                        "password": password,
                        "full_name": full_name or None,
                        "role": role,
                        "accept_disclaimer": True,
                    },
                )
                if status == 201:
                    st.session_state.token = data["access_token"]
                    me, _, _ = api_request("GET", "/auth/me")
                    if me:
                        st.session_state.user = me
                    st.success("Account created — check logs/emails.log for verification link if enabled")
                    st.rerun()
                else:
                    st.error(err or "Registration failed")

    with tabs[2]:
        with st.form("forgot_form"):
            email = st.text_input("Account email", key="forgot_email")
            submitted = st.form_submit_button("Send reset link")
        if submitted:
            _, status, err = api_request(
                "POST", "/auth/forgot-password", json={"email": email}
            )
            if status == 200:
                st.success("If that email exists, a reset link was sent (see logs/emails.log in dev).")
            else:
                st.error(err or "Request failed")
        with st.form("reset_form"):
            token = st.text_input("Reset token")
            new_password = st.text_input("New password", type="password")
            reset_submitted = st.form_submit_button("Set new password")
        if reset_submitted:
            _, status, err = api_request(
                "POST",
                "/auth/reset-password",
                json={"token": token, "new_password": new_password},
            )
            if status == 200:
                st.success("Password updated — sign in with your new password.")
            else:
                st.error(err or "Reset failed")

    with tabs[3]:
        privacy, _, _ = api_request("GET", "/account/privacy")
        disclaimer, _, _ = api_request("GET", "/account/disclaimer")
        if disclaimer:
            st.subheader(disclaimer.get("title", "Disclaimer"))
            st.caption(f"Version: {disclaimer.get('version', '')}")
            st.write(disclaimer.get("content", ""))
        if privacy:
            st.subheader(privacy.get("title", "Privacy"))
            st.caption(f"Version: {privacy.get('version', '')}")
            st.text(privacy.get("content", ""))


# ── Main product UI ───────────────────────────────────────────────
def render_app():
    user = st.session_state.user or {}

    with st.sidebar:
        st.markdown("### ⚖️ Your workspace")
        st.caption(user.get("email", ""))
        if user.get("full_name"):
            st.caption(user["full_name"])
        if user.get("role_label"):
            st.caption(f"Role: {user['role_label']}")
        if user.get("welcome_message"):
            st.info(user["welcome_message"])

        st.warning(DISCLAIMER_SHORT)

        if not check_api():
            st.error("API offline")
            st.stop()

        usage, _, _ = api_request("GET", "/account/usage")
        if usage:
            st.markdown("#### Usage (last hour)")
            st.caption(
                f"Questions: {usage['questions_last_hour']}/{usage['questions_limit']}"
            )
            st.caption(
                f"Uploads: {usage['uploads_last_hour']}/{usage['uploads_limit']}"
            )
            st.caption(
                f"Documents: {usage['documents_owned']}/{usage['documents_limit']}"
            )

        st.markdown("---")
        st.markdown("#### Upload document")
        uploaded = st.file_uploader("PDF or TXT", type=["pdf", "txt"])
        if uploaded and st.button("Process document", type="primary"):
            with st.spinner("Processing…"):
                files = {
                    "file": (uploaded.name, uploaded.getvalue(), uploaded.type)
                }
                data, status, err = api_request(
                    "POST", "/documents/upload", files=files, timeout=120
                )
            if status == 200:
                st.success("Document ready")
                refresh_documents()
                doc = data.get("document", {})
                st.session_state.active_document_id = doc.get("id")
                load_messages(doc["id"])
                st.rerun()
            else:
                st.error(err or "Upload failed")

        st.markdown("---")
        st.markdown("#### Your documents")
        if st.button("Refresh list"):
            refresh_documents()

        docs = st.session_state.documents
        if not docs:
            st.caption("No documents yet.")
        else:
            labels = {
                d["id"]: f"{d['original_filename']} ({d['num_chunks']} chunks)"
                for d in docs
            }
            ids = list(labels.keys())
            current = st.session_state.active_document_id
            index = ids.index(current) if current in ids else 0
            chosen = st.radio(
                "Select document",
                ids,
                index=index,
                format_func=lambda i: labels[i],
            )
            if chosen != st.session_state.active_document_id:
                st.session_state.active_document_id = chosen
                load_messages(chosen)
                st.rerun()

            if st.button("Delete selected document"):
                doc_id = st.session_state.active_document_id
                _, status, err = api_request("DELETE", f"/documents/{doc_id}")
                if status == 200:
                    st.session_state.active_document_id = None
                    st.session_state.messages = []
                    refresh_documents()
                    st.rerun()
                else:
                    st.error(err or "Delete failed")

        st.markdown("---")
        if st.session_state.active_document_id:
            if st.button("Reset conversation"):
                doc_id = st.session_state.active_document_id
                api_request(
                    "POST",
                    f"/documents/{doc_id}/conversation/reset",
                )
                st.session_state.messages = []
                st.rerun()

            export, status, err = api_request(
                "GET",
                f"/documents/{st.session_state.active_document_id}/export",
            )
            if status == 200 and export:
                st.download_button(
                    "Export conversation",
                    data=export["content"],
                    file_name=export.get(
                        "filename", "conversation.txt"
                    ),
                    mime="text/plain",
                )

        st.markdown("---")
        with st.expander("Account"):
            if st.button("Sign out"):
                logout()
                st.rerun()
            st.caption("Delete account permanently removes all your data.")
            confirm = st.text_input("Type DELETE to confirm account deletion")
            if st.button("Delete my account", type="secondary"):
                if confirm.strip() != "DELETE":
                    st.error("Type DELETE to confirm")
                else:
                    _, status, err = api_request("DELETE", "/account")
                    if status == 200:
                        logout()
                        st.rerun()
                    else:
                        st.error(err or "Could not delete account")

    # Main pane
    st.markdown("# AI Legal Copilot")
    st.caption(
        f"Signed in · {datetime.utcnow().strftime('%Y-%m-%d')} UTC · Not legal advice"
    )

    if st.session_state.last_error:
        st.error(st.session_state.last_error)
        st.session_state.last_error = None

    doc_id = st.session_state.active_document_id
    if not doc_id:
        st.info("Upload or select a document in the sidebar to start asking questions.")
        return

    active = next(
        (d for d in st.session_state.documents if d["id"] == doc_id),
        None,
    )
    if active:
        st.subheader(active["original_filename"])

    for message in st.session_state.messages:
        avatar = "⚖️" if message["role"] == "assistant" else None
        with st.chat_message(message["role"], avatar=avatar):
            st.write(message["content"])
            meta = message.get("metadata") or {}
            bits = []
            if meta.get("question_type"):
                bits.append(meta["question_type"].upper())
            if meta.get("processing_time") is not None:
                bits.append(f"{meta['processing_time']}s")
            if bits:
                st.caption(" · ".join(bits))

    if question := st.chat_input("Ask about this document…"):
        st.session_state.messages.append(
            {"role": "user", "content": question}
        )
        with st.chat_message("user"):
            st.write(question)

        with st.chat_message("assistant", avatar="⚖️"):
            with st.spinner("Analyzing…"):
                result, status, err = api_request(
                    "POST",
                    "/ask",
                    json={"question": question, "document_id": doc_id},
                    timeout=90,
                )
            if status == 200:
                st.write(result["answer"])
                st.caption(
                    f"{result.get('question_type', 'general').upper()} · "
                    f"{result.get('processing_time', 0)}s"
                )
                for src in result.get("sources") or []:
                    page = src.get("page")
                    page_bit = f" · page {page}" if page else ""
                    st.caption(
                        f"📎 {src.get('filename', 'document')}{page_bit} "
                        f"({src.get('content_type', 'text')})"
                    )
                    if src.get("snippet"):
                        st.caption(src["snippet"][:180] + "…")
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": result["answer"],
                        "metadata": result,
                    }
                )
            else:
                st.error(err or "Failed to get answer")
                st.session_state.messages.pop()

    # Compare two documents
    docs = st.session_state.documents
    if len(docs) >= 2:
        st.markdown("---")
        st.markdown("#### Compare contracts")
        ids = {d["id"]: d["original_filename"] for d in docs}
        c1, c2 = st.columns(2)
        with c1:
            a = st.selectbox("Document A", list(ids.keys()), format_func=lambda i: ids[i], key="cmp_a")
        with c2:
            b = st.selectbox("Document B", list(ids.keys()), format_func=lambda i: ids[i], index=min(1, len(ids)-1), key="cmp_b")
        cmp_q = st.text_input(
            "Compare focus",
            value="Compare payment, termination, and liability terms.",
        )
        if st.button("Run comparison") and a and b and a != b:
            with st.spinner("Comparing…"):
                result, status, err = api_request(
                    "POST",
                    "/compare",
                    json={
                        "document_id_a": a,
                        "document_id_b": b,
                        "question": cmp_q,
                    },
                    timeout=120,
                )
            if status == 200:
                st.write(result["answer"])
                for src in result.get("sources") or []:
                    page = src.get("page")
                    st.caption(
                        f"📎 {src.get('filename')} · page {page}" if page else f"📎 {src.get('filename')}"
                    )
            else:
                st.error(err or "Compare failed")


# ── Entry ─────────────────────────────────────────────────────────
if st.session_state.token:
    if not st.session_state.user:
        me, status, err = api_request("GET", "/auth/me")
        if status == 200:
            st.session_state.user = me
            refresh_documents()
        else:
            logout()
            st.error(err or "Session expired — please sign in again")
            render_auth()
            st.stop()
    render_app()
else:
    render_auth()
