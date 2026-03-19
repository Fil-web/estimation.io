import streamlit as st

from admin import create_department, create_user, get_departments, get_users


def require_admin():
    user = st.session_state.get("user")
    if not user:
        st.switch_page("app.py")
    if user["role"] != "admin":
        st.error("Доступ только для администратора")
        st.stop()


require_admin()

st.title("Управление пользователями и кафедрами")

departments = get_departments()
department_options = {dept["name"]: dept["id"] for dept in departments}

col1, col2 = st.columns(2)

with col1:
    st.subheader("Добавить кафедру")
    department_name = st.text_input("Название кафедры")
    if st.button("Сохранить кафедру"):
        if department_name.strip():
            create_department(department_name)
            st.success("Кафедра сохранена")
            st.rerun()
        else:
            st.warning("Введите название кафедры")

with col2:
    st.subheader("Добавить пользователя")
    full_name = st.text_input("ФИО")
    username = st.text_input("Логин")
    password = st.text_input("Пароль", type="password")
    role = st.selectbox(
        "Роль",
        options=["teacher", "head", "admin"],
        format_func=lambda value: {
            "teacher": "Преподаватель",
            "head": "Заведующий кафедрой",
            "admin": "Администратор",
        }[value],
    )
    position = st.text_input("Должность")
    if department_options:
        department_name_for_user = st.selectbox(
            "Кафедра",
            options=list(department_options.keys()),
            index=0,
        )
    else:
        department_name_for_user = None
        st.caption("Сначала добавьте кафедру")

    if st.button("Создать пользователя", type="primary"):
        if not departments:
            st.warning("Сначала добавьте хотя бы одну кафедру")
        elif not all([full_name.strip(), username.strip(), password]):
            st.warning("Заполните ФИО, логин и пароль")
        else:
            try:
                create_user(
                    username=username,
                    password=password,
                    role=role,
                    full_name=full_name,
                    department_id=department_options[department_name_for_user],
                    position=position,
                )
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.success("Пользователь создан")
                st.rerun()

st.divider()
st.subheader("Список пользователей")
st.dataframe(get_users(), use_container_width=True, hide_index=True)
