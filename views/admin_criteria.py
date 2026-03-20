import streamlit as st

from admin import (
    create_criteria_group,
    create_criterion,
    delete_criteria_group,
    delete_criterion,
    get_criteria_groups,
    get_criteria_table,
    update_criteria_group,
    update_criterion,
)


def render_page(current_user=None):
    st.title("Управление критериями")
    st.markdown(
        """
        <style>
            .delete-button-host {
                width: 100%;
            }
            .compact-table-header {
                font-size: 0.76rem;
                font-weight: 700;
                line-height: 1.08;
            }
            .compact-table-cell {
                font-size: 0.72rem;
                line-height: 1.12;
                padding-top: 0.15rem;
            }
            .delete-button-host div[data-testid="stButton"] > button {
                font-size: 0.72rem;
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
                font-size: 0.72rem !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    groups = get_criteria_groups()
    group_options = {f"{group['code']} - {group['name']}": group["id"] for group in groups}
    criteria_df = get_criteria_table()

    @st.dialog("Группы", width="large")
    def groups_dialog():
        st.subheader("Добавить группу")
        group_code = st.text_input("Код группы", placeholder="7", key="dialog_group_code")
        group_name = st.text_input(
            "Название группы",
            placeholder="Новая группа критериев",
            key="dialog_group_name",
        )
        if st.button("Сохранить группу", key="dialog_save_group", type="primary"):
            if group_code.strip() and group_name.strip():
                create_criteria_group(group_code, group_name, actor_id=(current_user or {}).get("id"))
                st.success("Группа добавлена")
                st.rerun()
            else:
                st.warning("Заполните код и название группы")

        st.divider()
        st.subheader("Изменить или удалить группу")
        if not groups:
            st.info("Группы пока не созданы")
            return

        editable_groups = {
            f"{group['code']} - {group['name']}": group
            for group in groups
        }
        selected_group_label = st.selectbox(
            "Группа для изменения",
            options=list(editable_groups.keys()),
            key="dialog_edit_group_select",
        )
        selected_group_data = editable_groups[selected_group_label]
        edit_group_code = st.text_input(
            "Код группы",
            value=selected_group_data["code"],
            key="dialog_edit_group_code",
        )
        edit_group_name = st.text_input(
            "Название группы",
            value=selected_group_data["name"],
            key="dialog_edit_group_name",
        )
        group_btn1, group_btn2 = st.columns(2)
        if group_btn1.button("Сохранить", key="dialog_update_group", type="primary"):
            if edit_group_code.strip() and edit_group_name.strip():
                update_criteria_group(
                    selected_group_data["id"],
                    edit_group_code,
                    edit_group_name,
                    selected_group_data.get("group_type", "effectiveness"),
                    actor_id=(current_user or {}).get("id"),
                )
                st.success("Группа обновлена")
                st.rerun()
            else:
                st.warning("Заполните код и название группы")
        if group_btn2.button("Удалить группу", key="dialog_delete_group"):
            try:
                delete_criteria_group(selected_group_data["id"], actor_id=(current_user or {}).get("id"))
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.success("Группа удалена")
                st.rerun()

    @st.dialog("Критерии", width="large")
    def criteria_dialog():
        st.subheader("Добавить критерий")
        if group_options:
            selected_group = st.selectbox(
                "Группа",
                options=list(group_options.keys()),
                index=0,
                key="dialog_add_criterion_group",
            )
        else:
            selected_group = None
            st.caption("Сначала должна быть хотя бы одна группа")
        code = st.text_input("Код критерия", placeholder="3.20", key="dialog_add_criterion_code")
        name = st.text_area(
            "Наименование критерия",
            height=100,
            key="dialog_add_criterion_name",
        )
        base = st.text_input("База расчета", placeholder="Одна статья", key="dialog_add_criterion_base")
        score = st.number_input(
            "Числовое значение баллов",
            min_value=0.0,
            value=10.0,
            step=1.0,
            key="dialog_add_criterion_score",
        )
        score_text = st.text_input(
            "Текст баллов",
            placeholder="10 на коллектив авторов",
            key="dialog_add_criterion_score_text",
        )
        confirmation_type = st.selectbox(
            "Тип подтверждения",
            options=["file", "text"],
            format_func=lambda value: "Файл" if value == "file" else "Текст",
            key="dialog_add_criterion_confirmation_type",
        )

        if st.button("Сохранить критерий", key="dialog_save_criterion", type="primary"):
            if not group_options:
                st.warning("Сначала добавьте группу")
            elif not all([code.strip(), name.strip(), base.strip(), score_text.strip()]):
                st.warning("Заполните код, название, базу и текст баллов")
            else:
                create_criterion(
                    group_id=group_options[selected_group],
                    code=code,
                    name=name,
                    base=base,
                    score=score,
                    score_text=score_text,
                    confirmation_type=confirmation_type,
                    actor_id=(current_user or {}).get("id"),
                )
                st.success("Критерий добавлен")
                st.rerun()

        st.divider()
        st.subheader("Изменить или удалить критерий")
        if criteria_df.empty or not group_options:
            st.info("Критерии пока не созданы")
            return

        criteria_options = {
            f"{row.code} - {row.criterion_name}": row._asdict()
            for row in criteria_df.itertuples(index=False)
        }
        selected_criterion_label = st.selectbox(
            "Критерий для изменения",
            options=list(criteria_options.keys()),
            key="dialog_edit_criterion_select",
        )
        selected_criterion = criteria_options[selected_criterion_label]

        group_id_to_label = {group["id"]: f"{group['code']} - {group['name']}" for group in groups}
        current_group_label = group_id_to_label.get(selected_criterion["group_id"])
        group_labels = list(group_id_to_label.values())
        default_group_index = group_labels.index(current_group_label) if current_group_label in group_labels else 0

        edit_group_label = st.selectbox(
            "Группа",
            options=group_labels,
            index=default_group_index,
            key="dialog_edit_criterion_group",
        )
        edit_code = st.text_input(
            "Код критерия",
            value=selected_criterion["code"],
            key="dialog_edit_criterion_code",
        )
        edit_name = st.text_area(
            "Наименование критерия",
            value=selected_criterion["criterion_name"],
            height=100,
            key="dialog_edit_criterion_name",
        )
        edit_base = st.text_input(
            "База расчета",
            value=selected_criterion["base"],
            key="dialog_edit_criterion_base",
        )
        edit_score = st.number_input(
            "Числовое значение баллов",
            min_value=0.0,
            value=float(selected_criterion["score"]),
            step=1.0,
            key="dialog_edit_criterion_score",
        )
        edit_score_text = st.text_input(
            "Текст баллов",
            value=selected_criterion["score_text"],
            key="dialog_edit_criterion_score_text",
        )
        confirmation_options = {"Файл": "file", "Текст": "text"}
        current_confirmation_label = "Файл" if selected_criterion["confirmation_type"] == "Файл" else "Текст"
        edit_confirmation_label = st.selectbox(
            "Тип подтверждения",
            options=list(confirmation_options.keys()),
            index=list(confirmation_options.keys()).index(current_confirmation_label),
            key="dialog_edit_criterion_confirmation",
        )
        edit_active = st.checkbox(
            "Критерий активен",
            value=selected_criterion["is_active"] == "Да",
            key="dialog_edit_criterion_active",
        )

        criterion_btn1, criterion_btn2 = st.columns(2)
        if criterion_btn1.button("Сохранить", key="dialog_update_criterion", type="primary"):
            if not all([edit_code.strip(), edit_name.strip(), edit_base.strip(), edit_score_text.strip()]):
                st.warning("Заполните код, название, базу и текст баллов")
            else:
                selected_group_id = next(
                    group["id"] for group in groups if group_id_to_label[group["id"]] == edit_group_label
                )
                update_criterion(
                    selected_criterion["id"],
                    selected_group_id,
                    edit_code,
                    edit_name,
                    edit_base,
                    edit_score,
                    edit_score_text,
                    confirmation_options[edit_confirmation_label],
                    edit_active,
                    actor_id=(current_user or {}).get("id"),
                )
                st.success("Критерий обновлен")
                st.rerun()
        if criterion_btn2.button("Удалить критерий", key="dialog_delete_criterion"):
            try:
                delete_criterion(selected_criterion["id"], actor_id=(current_user or {}).get("id"))
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.success("Критерий удален")
                st.rerun()

    action_col1, action_col2 = st.columns(2)
    if action_col1.button("Группы", use_container_width=True):
        groups_dialog()
    if action_col2.button("Критерии", use_container_width=True):
        criteria_dialog()

    st.divider()
    st.subheader("Текущий справочник критериев")
    criteria_table = get_criteria_table().rename(
        columns={
            "group_id": "ID группы",
            "code": "Код",
            "criterion_name": "Наименование",
            "base": "База расчета",
            "score": "Балл за единицу",
            "confirmation_type": "Тип подтверждения",
            "is_active": "Активен",
            "group_name": "Группа",
        }
    )
    if criteria_table.empty:
        st.info("Критерии пока не созданы")
    else:
        header_cols = st.columns([0.75, 2.55, 1.25, 0.75, 0.95, 0.75, 1.0, 1.5])
        headers = [
            "Код",
            "Наименование",
            "База расчета",
            "Балл",
            "Файл",
            "Активен",
            "Группа",
            "Действие",
        ]
        for col, title in zip(header_cols, headers):
            col.markdown(f"<div class='compact-table-header'>{title}</div>", unsafe_allow_html=True)

        for row in criteria_table.to_dict("records"):
            row_cols = st.columns([0.75, 2.55, 1.25, 0.75, 0.95, 0.75, 1.0, 1.5])
            row_cols[0].markdown(f"<div class='compact-table-cell'>{row['Код']}</div>", unsafe_allow_html=True)
            row_cols[1].markdown(
                f"<div class='compact-table-cell'>{row['Наименование']}</div>",
                unsafe_allow_html=True,
            )
            row_cols[2].markdown(f"<div class='compact-table-cell'>{row['База расчета']}</div>", unsafe_allow_html=True)
            row_cols[3].markdown(f"<div class='compact-table-cell'>{row['Балл за единицу']}</div>", unsafe_allow_html=True)
            row_cols[4].markdown(
                f"<div class='compact-table-cell'>{row['Тип подтверждения']}</div>",
                unsafe_allow_html=True,
            )
            row_cols[5].markdown(f"<div class='compact-table-cell'>{row['Активен']}</div>", unsafe_allow_html=True)
            row_cols[6].markdown(f"<div class='compact-table-cell'>{row['Группа']}</div>", unsafe_allow_html=True)
            row_cols[7].markdown("<div class='delete-button-host'>", unsafe_allow_html=True)
            if row_cols[7].button(
                "Удалить",
                key=f"delete_criterion_row_{row['id']}",
                use_container_width=False,
            ):
                try:
                    delete_criterion(row["id"], actor_id=(current_user or {}).get("id"))
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.success(f"Критерий {row['Код']} удален")
                    st.rerun()
            row_cols[7].markdown("</div>", unsafe_allow_html=True)
            st.divider()
