import streamlit as st

from admin import (
    create_department,
    create_user,
    delete_user,
    get_departments,
    get_user_options,
    get_users,
    set_user_password,
)


def render_page(current_user=None):
    st.title("Управление пользователями и кафедрами")
    st.markdown(
        """
        <style>
            .delete-button-host {
                width: 100%;
            }
            .compact-table-header {
                font-size: 0.78rem;
                font-weight: 700;
                line-height: 1.1;
            }
            .compact-table-cell {
                font-size: 0.76rem;
                line-height: 1.15;
                padding-top: 0.2rem;
            }
            .delete-button-host div[data-testid="stButton"] > button {
                font-size: 0.76rem;
                padding: 0 0.3rem !important;
                min-height: 1.2rem;
                height: 1.2rem;
                line-height: 1;
                width: 5.6rem !important;
                min-width: 5.6rem !important;
                max-width: 5.6rem !important;
                border: 1px solid #c62828 !important;
                background: #c62828 !important;
                color: #ffffff !important;
                box-shadow: none !important;
                border-radius: 0.45rem !important;
                white-space: nowrap !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
            }
            .delete-button-host div[data-testid="stButton"] > button p {
                white-space: nowrap !important;
                font-size: 0.76rem !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    departments = get_departments()
    department_options = {dept["name"]: dept["id"] for dept in departments}
    user_options = get_user_options()
    user_labels = {
        f"{user['display_name']} ({user['username']})": user["id"]
        for user in user_options
    }

    @st.dialog("Назначить новый пароль", width="small")
    def reset_password_dialog():
        if not user_labels:
            st.info("Пользователи пока не созданы")
            return

        selected_user_label = st.selectbox(
            "Пользователь",
            options=list(user_labels.keys()),
            key="dialog_selected_user_label",
        )
        new_password = st.text_input("Новый пароль", type="password", key="dialog_reset_password")
        if st.button("Сохранить новый пароль", key="dialog_save_password", type="primary"):
            if not new_password:
                st.warning("Введите новый пароль")
            else:
                try:
                    set_user_password(
                        user_labels[selected_user_label],
                        new_password,
                        actor_id=(current_user or {}).get("id"),
                    )
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.success("Пароль обновлен")
                    st.rerun()

    @st.dialog("Добавить пользователя", width="large")
    def add_user_dialog():
        dialog_departments = get_departments()
        dialog_department_options = {dept["name"]: dept["id"] for dept in dialog_departments}

        full_name = st.text_input("ФИО", key="dialog_full_name")
        username = st.text_input("Логин", key="dialog_username")
        password = st.text_input("Пароль", type="password", key="dialog_password")
        role = st.selectbox(
            "Роль",
            options=["teacher", "head", "admin"],
            format_func=lambda value: {
                "teacher": "Преподаватель",
                "head": "Заведующий кафедрой",
                "admin": "Администратор",
            }[value],
            key="dialog_role",
        )
        position = st.text_input("Должность", key="dialog_position")
        if dialog_department_options:
            department_name_for_user = st.selectbox(
                "Кафедра",
                options=list(dialog_department_options.keys()),
                index=0,
                key="dialog_department_name_for_user",
            )
        else:
            department_name_for_user = None
            st.caption("Сначала добавьте кафедру")

        st.caption("Если нужной кафедры нет в списке, добавьте ее ниже.")
        new_department_name = st.text_input("Новая кафедра", key="dialog_new_department_name")
        if st.button("Добавить кафедру", key="dialog_add_department_button"):
            if new_department_name.strip():
                create_department(new_department_name, actor_id=(current_user or {}).get("id"))
                st.success("Кафедра сохранена")
                st.rerun()
            else:
                st.warning("Введите название кафедры")

        if st.button("Создать пользователя", key="dialog_create_user", type="primary"):
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
                        department_id=dialog_department_options[department_name_for_user],
                        position=position,
                        actor_id=(current_user or {}).get("id"),
                    )
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.success("Пользователь создан")
                    st.rerun()

    action_col1, action_col2 = st.columns(2)

    if action_col1.button("Назначить новый пароль", use_container_width=True):
        reset_password_dialog()
    if action_col2.button("Добавить пользователя", use_container_width=True):
        add_user_dialog()

    st.divider()
    st.subheader("Список пользователей")
    users_df = get_users().rename(
        columns={
            "full_name": "ФИО",
            "username": "Логин",
            "role": "Роль",
            "department": "Кафедра",
            "position": "Должность",
            "password_status": "Пароль",
        }
    )
    if users_df.empty:
        st.info("Пользователи пока не созданы")
    else:
        header_cols = st.columns([1.9, 0.95, 1.3, 1.35, 1.3, 0.75, 1.5])
        headers = ["ФИО", "Логин", "Роль", "Кафедра", "Должность", "Пароль", "Действие"]
        for col, title in zip(header_cols, headers):
            col.markdown(f"<div class='compact-table-header'>{title}</div>", unsafe_allow_html=True)

        for row in users_df.to_dict("records"):
            row_cols = st.columns([1.9, 0.95, 1.3, 1.35, 1.3, 0.75, 1.5])
            row_cols[0].markdown(f"<div class='compact-table-cell'>{row['ФИО']}</div>", unsafe_allow_html=True)
            row_cols[1].markdown(f"<div class='compact-table-cell'>{row['Логин']}</div>", unsafe_allow_html=True)
            row_cols[2].markdown(f"<div class='compact-table-cell'>{row['Роль']}</div>", unsafe_allow_html=True)
            row_cols[3].markdown(f"<div class='compact-table-cell'>{row['Кафедра']}</div>", unsafe_allow_html=True)
            row_cols[4].markdown(f"<div class='compact-table-cell'>{row['Должность']}</div>", unsafe_allow_html=True)
            row_cols[5].markdown(f"<div class='compact-table-cell'>{row['Пароль']}</div>", unsafe_allow_html=True)

            is_current_user = row["id"] == (current_user or {}).get("id")
            row_cols[6].markdown("<div class='delete-button-host'>", unsafe_allow_html=True)
            if row_cols[6].button(
                "Удалить",
                key=f"delete_user_row_{row['id']}",
                disabled=is_current_user,
                use_container_width=False,
            ):
                try:
                    delete_user(
                        row["id"],
                        current_admin_id=(current_user or {}).get("id"),
                        actor_id=(current_user or {}).get("id"),
                    )
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.success(f"Пользователь {row['ФИО']} удален")
                    st.rerun()
            row_cols[6].markdown("</div>", unsafe_allow_html=True)
            st.divider()
