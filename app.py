import streamlit as st

from auth import login
from db import init_db

st.set_page_config(page_title="Система критериев эффективности", layout="wide")

init_db()

if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.title("Вход в систему")
    st.caption("Демо-учетная запись администратора: `admin / admin`")

    username = st.text_input("Логин")
    password = st.text_input("Пароль", type="password")

    if st.button("Войти", type="primary"):
        user = login(username, password)
        if user:
            st.session_state.user = user
            st.rerun()
        else:
            st.error("Неверный логин или пароль")
else:
    user = st.session_state.user
    role = user["role"]
    full_name = user.get("full_name") or user["username"]

    st.sidebar.success(f"{full_name} ({role})")
    if user.get("department_name"):
        st.sidebar.caption(user["department_name"])

    if st.sidebar.button("Выйти"):
        st.session_state.user = None
        st.rerun()

    if role == "admin":
        st.switch_page("pages/admin_dashboard.py")
    if role == "head":
        st.switch_page("pages/head_dashboard.py")
    st.switch_page("pages/teacher_dashboard.py")
