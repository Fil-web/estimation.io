import streamlit as st

from admin import (
    create_criteria_group,
    create_criterion,
    get_criteria_groups,
    get_criteria_table,
)


def require_admin():
    user = st.session_state.get("user")
    if not user:
        st.switch_page("app.py")
    if user["role"] != "admin":
        st.error("Доступ только для администратора")
        st.stop()


require_admin()

st.title("Управление критериями")

groups = get_criteria_groups()
group_options = {f"{group['code']} - {group['name']}": group["id"] for group in groups}

left_col, right_col = st.columns(2)

with left_col:
    st.subheader("Добавить группу")
    group_code = st.text_input("Код группы", placeholder="7")
    group_name = st.text_input("Название группы", placeholder="Новая группа критериев")
    if st.button("Сохранить группу"):
        if group_code.strip() and group_name.strip():
            create_criteria_group(group_code, group_name)
            st.success("Группа добавлена")
            st.rerun()
        else:
            st.warning("Заполните код и название группы")

with right_col:
    st.subheader("Добавить критерий")
    if group_options:
        selected_group = st.selectbox(
            "Группа",
            options=list(group_options.keys()),
            index=0,
        )
    else:
        selected_group = None
        st.caption("Сначала должна быть хотя бы одна группа")
    code = st.text_input("Код критерия", placeholder="3.20")
    name = st.text_area("Наименование критерия", height=100)
    base = st.text_input("База расчета", placeholder="Одна статья")
    score = st.number_input("Числовое значение баллов", min_value=0.0, value=10.0, step=1.0)
    score_text = st.text_input("Текст баллов", placeholder="10 на коллектив авторов")
    confirmation_type = st.selectbox(
        "Тип подтверждения",
        options=["file", "text"],
        format_func=lambda value: "Файл" if value == "file" else "Текст",
    )

    if st.button("Сохранить критерий", type="primary"):
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
            )
            st.success("Критерий добавлен")
            st.rerun()

st.divider()
st.subheader("Текущий справочник критериев")
st.dataframe(get_criteria_table(), use_container_width=True, hide_index=True)
