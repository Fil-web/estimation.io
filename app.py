import streamlit as st

from auth import login
from db import init_db
from ui import inject_base_styles, render_sidebar
from views import admin_criteria, admin_dashboard, admin_users, head_dashboard, teacher_dashboard

st.set_page_config(page_title="Система критериев эффективности", layout="wide")

init_db()

if "user" not in st.session_state:
    st.session_state.user = None

if "current_page" not in st.session_state:
    st.session_state.current_page = None

inject_base_styles(show_sidebar=bool(st.session_state.user))

if not st.session_state.user:
    st.markdown("<div class='auth-shell'><div class='auth-layout'>", unsafe_allow_html=True)
    st.markdown(
        "<div class='auth-brand'>"
        "<div class='auth-header'>"
        "<img class='auth-logo' src='https://sun1-95.userapi.com/s/v1/ig2/TGeoiTrjVgYZe2ZWxbf-THSKAnY_x2dhXfqi6yK659yvV4f1BlItnZL8bs3soxYnf_pgCAYE4JgjIzECH8mFCbYP.jpg?size=800x800&quality=95&crop=100,100,800,800&ava=1' alt='Логотип'>"
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div class='auth-form-wrap'>", unsafe_allow_html=True)

    with st.form("login_form", border=False):
        username = st.text_input("Логин")
        password = st.text_input("Пароль", type="password")

        submitted = st.form_submit_button("Войти", type="primary", use_container_width=True)

    if submitted:
        user = login(username, password)
        if user:
            st.session_state.user = user
            st.session_state.current_page = {
                "admin": "admin_dashboard",
                "head": "head_dashboard",
                "teacher": "teacher_dashboard",
            }.get(user["role"], "teacher_dashboard")
            st.rerun()
        else:
            st.error("Неверный логин или пароль")

    st.markdown("</div></div>", unsafe_allow_html=True)
else:
    user = st.session_state.user
    role = user["role"]
    allowed_pages = {
        "admin": {"admin_dashboard", "admin_users", "admin_criteria"},
        "head": {"head_dashboard", "teacher_dashboard"},
        "teacher": {"teacher_dashboard"},
    }
    default_page = {
        "admin": "admin_dashboard",
        "head": "head_dashboard",
        "teacher": "teacher_dashboard",
    }[role]

    current_page = st.session_state.current_page or default_page
    if current_page not in allowed_pages[role]:
        current_page = default_page
        st.session_state.current_page = current_page

    render_sidebar(user, current_page)

    if current_page == "admin_dashboard":
        admin_dashboard.render_page()
    elif current_page == "admin_users":
        admin_users.render_page(user)
    elif current_page == "admin_criteria":
        admin_criteria.render_page(user)
    elif current_page == "head_dashboard":
        head_dashboard.render_page(user)
    else:
        teacher_dashboard.render_page(user)
