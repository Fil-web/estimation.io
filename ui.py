import streamlit as st

ROLE_LABELS = {
    "admin": "Администратор",
    "head": "Заведующий кафедрой",
    "teacher": "Преподаватель",
}

REPORT_STATUS_LABELS = {
    "draft": "Черновик",
    "returned": "На доработке",
    "submitted": "На проверке",
    "reviewed": "Проверен",
}

ITEM_STATUS_LABELS = {
    "pending": "Ожидает решения",
    "approved": "Подтвержден",
    "rejected": "Отклонен",
}


def role_label(role):
    return ROLE_LABELS.get(role, role)


def report_status_label(status):
    return REPORT_STATUS_LABELS.get(status, status)


def item_status_label(status):
    return ITEM_STATUS_LABELS.get(status, status)


def inject_base_styles(show_sidebar=False):
    sidebar_styles = """
        [data-testid="stSidebarNav"] {
            display: none;
        }
        [data-testid="stSidebar"] * {
            color: inherit;
        }
        [data-testid="stSidebar"] button[kind="secondary"] {
            background: transparent;
            color: inherit;
            border: 1px solid rgba(127, 127, 127, 0.35);
            font-weight: 600;
        }
        [data-testid="stSidebar"] button[kind="secondary"]:hover {
            background: transparent;
            color: inherit;
            border-color: rgba(127, 127, 127, 0.5);
        }
        [data-testid="stSidebar"] button[kind="primary"] {
            background: #c62828;
            color: #ffffff;
            border: 1px solid #c62828;
            font-weight: 700;
        }
        [data-testid="stSidebar"] button[kind="primary"]:hover {
            background: #a81f1f;
            color: #ffffff;
            border-color: #a81f1f;
        }
    """ if show_sidebar else """
        [data-testid="stSidebar"] {
            display: none;
        }
    """

    st.markdown(
        f"""
        <style>
            {sidebar_styles}
            .sidebar-card {{
                padding: 1rem;
                border-radius: 16px;
                background: transparent;
                border: 1px solid rgba(127, 127, 127, 0.35);
                margin-bottom: 1rem;
            }}
            .sidebar-kicker {{
                font-size: 0.78rem;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                opacity: 0.75;
                margin-bottom: 0.35rem;
            }}
            .sidebar-title {{
                font-size: 1.1rem;
                font-weight: 700;
                line-height: 1.3;
            }}
            .sidebar-subtitle {{
                margin-top: 0.35rem;
                opacity: 0.82;
                font-size: 0.92rem;
            }}
            .block-container {{
                padding-top: 2rem;
            }}
            .auth-shell {{
                position: fixed;
                inset: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 24px;
                background: transparent;
            }}
            .auth-layout {{
                width: 640px;
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 20px;
            }}
            .auth-brand {{
                width: 100%;
                text-align: center;
            }}
            .auth-header {{
                margin: 0 auto;
                max-width: 600px;
            }}
            .auth-logo {{
                width: 140px;
                height: 140px;
                display: block;
                margin: 0 auto 8px auto;
                object-fit: cover;
                border-radius: 50%;
            }}
            .auth-title {{
                font-size: 2rem;
                font-weight: 800;
                color: inherit;
                margin-bottom: 0.95rem;
                line-height: 1.12;
                text-align: center;
            }}
            .auth-subtitle {{
                color: inherit;
                font-size: 1rem;
                line-height: 1.7;
                margin: 0;
                max-width: 560px;
                text-align: center;
            }}
            div[data-testid="stForm"] {{
                width: 100%;
                max-width: 380px;
                margin: 0 auto;
            }}
            div[data-testid="stForm"] form {{
                display: flex;
                flex-direction: column;
                gap: 12px;
            }}
            div[data-testid="stForm"] label {{
                text-align: center;
                width: 100%;
            }}
            .auth-form-wrap {{
                width: 100%;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 0;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(user, current_page):
    inject_base_styles(show_sidebar=True)

    full_name = user.get("full_name") or user["username"]
    role = role_label(user.get("role"))
    department = user.get("department_name") or "Кафедра не указана"
    is_admin = user.get("role") == "admin"

    if is_admin:
        st.sidebar.markdown(
            f"""
            <div class="sidebar-card">
                <div class="sidebar-title">{role}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.sidebar.markdown(
            f"""
            <div class="sidebar-card">
                <div class="sidebar-title">{full_name}</div>
                <div class="sidebar-subtitle">{role}</div>
                <div class="sidebar-subtitle">{department}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.sidebar.markdown("### Разделы")

    def nav_button(page_key, label, icon):
        if st.sidebar.button(
            f"{icon} {label}",
            key=f"nav_{page_key}",
            use_container_width=True,
            type="secondary",
        ):
            st.session_state.current_page = page_key
            st.rerun()

    if user["role"] == "admin":
        nav_button("admin_dashboard", "Обзор и расчеты", "📊")
        nav_button("admin_users", "Пользователи и кафедры", "👥")
        nav_button("admin_criteria", "Критерии", "🧩")
    elif user["role"] == "head":
        nav_button("head_dashboard", "Проверка отчетов", "📝")
        nav_button("teacher_dashboard", "Личный кабинет", "📘")
    else:
        nav_button("teacher_dashboard", "Мой отчет", "📘")

    st.sidebar.divider()
    if st.sidebar.button("Выйти из системы", use_container_width=True, type="primary"):
        st.session_state.user = None
        st.session_state.current_page = None
        st.rerun()
