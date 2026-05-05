import streamlit as st
import requests
import pandas as pd
import os

st.set_page_config(page_title="Certificate Verification", layout="wide")

BACKEND_URL = "http://backend:5001"

# ================= CERT DISPLAY =================
def show_certificate(result):
    st.success("✅ VALID CERTIFICATE")

    st.markdown(f"""
    ### 🎓 {result['student_name']}
    📚 Course: **{result['course']}**
    """)

    col1, col2, col3 = st.columns(3)

    col1.metric("🆔 Certificate ID", result["certificate_id"])
    col2.metric("🔍 Verifications", result["verification_count"])
    col3.metric("📅 Upload Date", str(result["upload_date"])[:10])

    st.markdown("---")

    with st.expander("🔐 View Hash"):
        st.code(result["hash"])

    qr = result.get("qr_code")
    if qr:
        try:
            qr_res = requests.get(f"{BACKEND_URL}/{qr}")
            if qr_res.status_code == 200:
                st.image(qr_res.content, caption="📱 Scan QR")
            else:
                st.warning("QR code not found on server.")
        except Exception as e:
            st.error(f"Failed to load QR code: {e}")

    with st.expander("📜 Verification Logs"):
        logs = result.get("verification_logs", [])
        if logs:
            for log in logs:
                st.write(f"📅 {log['date']} | 🌐 {log['ip']}")
        else:
            st.info("No logs yet")

# ================= QR VERIFY (TOP PRIORITY) =================
query_params = st.query_params

if "verify" in query_params:
    hash_value = query_params["verify"]

    st.title("🔍 Certificate Verification Result")

    try:
        res = requests.post(
            f"{BACKEND_URL}/verify-hash",
            json={"hash": hash_value}
        )

        if res.status_code == 200 and res.json().get("valid"):
            show_certificate(res.json()["certificate"])
        else:
            st.error("❌ INVALID CERTIFICATE")

    except Exception as e:
        st.error(f"Server error: {e}")

    st.stop()   # 🔥 VERY IMPORTANT

# ================= SESSION =================
if "role" not in st.session_state:
    st.session_state.role = None

# ================= LOGIN =================
if st.session_state.role is None:
    st.title("🔐 Certificate Verification System")

    role = st.radio("Select Role", ["Verifier", "Admin"])

    if role == "Admin":
        password = st.text_input("Enter Admin Password", type="password")

        if st.button("Login"):
            if password == "admin123":
                st.session_state.role = "Admin"
                st.rerun()
            else:
                st.error("Wrong Password")

    else:
        if st.button("Continue as Verifier"):
            st.session_state.role = "Verifier"
            st.rerun()

    st.stop()

# ================= LOGOUT =================
if st.sidebar.button("Logout"):
    st.session_state.role = None
    st.rerun()

st.title("🔐 Certificate Verification System")

# ================= MENU =================
if st.session_state.role == "Admin":
    menu = st.sidebar.selectbox("Menu", ["Upload", "Dashboard"])
else:
    menu = "Verify"

# ================= UPLOAD =================
if menu == "Upload":
    st.header("📤 Upload Certificate")

    name = st.text_input("👤 Student Name")
    course = st.text_input("📚 Course")
    file = st.file_uploader("📄 Upload File")

    if st.button("Upload"):
        if file and name and course:
            files = {"file": (file.name, file.getvalue(), file.type)}
            data = {"student_name": name, "course": course}

            res = requests.post(f"{BACKEND_URL}/upload", files=files, data=data)

            if res.status_code in [200, 201]:
                show_certificate(res.json())
            else:
                st.error(res.text)
        else:
            st.warning("Fill all fields")

# ================= VERIFY =================
elif menu == "Verify":
    st.header("✅ Verify Certificate")

    file = st.file_uploader("Upload Certificate")

    if st.button("Verify"):
        if file:
            files = {"file": (file.name, file.getvalue(), file.type)}
            res = requests.post(f"{BACKEND_URL}/verify", files=files)

            if res.status_code == 200:
                result = res.json()

                if result.get("valid"):
                    show_certificate(result["certificate"])
                else:
                    st.error("❌ Invalid Certificate")
            else:
                st.error(res.text)
        else:
            st.warning("Upload file first")

# ================= DASHBOARD =================
elif menu == "Dashboard":
    st.header("📊 Admin Dashboard")

    res = requests.get(f"{BACKEND_URL}/certificates")

    if res.status_code == 200:
        data = res.json()

        if data:
            df = pd.DataFrame(data)

            col1, col2 = st.columns(2)
            col1.metric("📄 Certificates", len(df))
            col2.metric("🔍 Total Verifications", df["verification_count"].sum())

            st.markdown("---")

            for _, row in df.iterrows():
                show_certificate(row.to_dict())
                st.markdown("---")
        else:
            st.info("No data found")
    else:
        st.error("Failed to load data")
