import streamlit as st

from teacher import (
    create_report,
    get_report,
    get_report_form_data,
    get_teacher_reports,
    save_report_items_bulk,
    submit_report,
)


def require_teacher():
    user = st.session_state.get("user")
    if not user:
        st.switch_page("app.py")
    if user["role"] not in {"teacher", "head"}:
        st.error("Страница доступна преподавателям")
        st.stop()
    return user


user = require_teacher()
user_id = user["id"]

st.title("Личный кабинет преподавателя")
st.caption("Выберите только нужные пункты, а баллы приложение посчитает автоматически.")

reports_df = get_teacher_reports(user_id)

with st.expander("Создать отчет за период", expanded=reports_df.empty):
    new_period = st.text_input("Период", placeholder="2025-2026")
    if st.button("Создать отчет"):
        if new_period.strip():
            report_id = create_report(user_id, new_period)
            st.session_state.selected_report_id = report_id
            st.success("Отчет создан")
            st.rerun()
        else:
            st.warning("Введите период")

if reports_df.empty:
    st.info("У вас пока нет отчетов. Создайте первый отчет за учебный период.")
    st.stop()

report_options = {
    f"{row.period} | {row.status} | позиций: {int(row.items_count)} | баллы: {row.claimed_points:.2f}": int(row.id)
    for row in reports_df.itertuples(index=False)
}

default_report_id = st.session_state.get("selected_report_id")
report_labels = list(report_options.keys())
default_index = 0
if default_report_id:
    for index, label in enumerate(report_labels):
        if report_options[label] == default_report_id:
            default_index = index
            break

selected_label = st.selectbox("Выберите отчет", options=report_labels, index=default_index)
report_id = report_options[selected_label]
st.session_state.selected_report_id = report_id

report = get_report(report_id)
if not report:
    st.error("Отчет не найден")
    st.stop()

meta1, meta2, meta3 = st.columns(3)
meta1.metric("Период", report["period"])
meta2.metric("Статус", report["status"])
meta3.metric("Кафедра", report.get("department_name") or "Без кафедры")

if report["status"] == "reviewed":
    st.success("Отчет уже проверен заведующим. Редактирование отключено.")

form_df = get_report_form_data(report_id)

selected_count = 0
selected_total = 0.0
payload = []

for group_name, group_df in form_df.groupby("group_name", dropna=False):
    with st.expander(group_name or "Без группы", expanded=False):
        for row in group_df.itertuples(index=False):
            selected = st.checkbox(
                f"{row.code} {row.criterion_name}",
                value=bool(row.item_id),
                key=f"selected_{report_id}_{row.criteria_id}",
                disabled=report["status"] == "reviewed",
            )
            st.caption(f"База: {row.base} | Автобалл: {row.score_text}")

            quantity = st.number_input(
                f"Количество для {row.code}",
                min_value=0.0,
                value=float(row.quantity or 1 if row.item_id else 1),
                step=1.0,
                key=f"qty_{report_id}_{row.criteria_id}",
                disabled=report["status"] == "reviewed" or not selected,
            )
            comment = st.text_area(
                f"Комментарий для {row.code}",
                value=row.teacher_comment or "",
                key=f"comment_{report_id}_{row.criteria_id}",
                disabled=report["status"] == "reviewed" or not selected,
                placeholder="Например: 2 статьи, Чита.ру, 12 постов, ОПОП и т.д.",
            )
            uploaded_file = st.file_uploader(
                f"Подтверждающий файл для {row.code}",
                key=f"file_{report_id}_{row.criteria_id}",
                disabled=report["status"] == "reviewed" or not selected,
            )

            auto_score = float(quantity) * float(row.score)
            info_col1, info_col2 = st.columns(2)
            info_col1.caption(f"Автоматически начислится: {auto_score:.2f} баллов")
            info_col2.caption(f"Статус пункта: {row.item_status}")

            if row.attachment_name:
                st.caption(f"Текущий файл: {row.attachment_name}")
            if row.review_comment:
                st.caption(f"Комментарий заведующего: {row.review_comment}")

            if selected:
                selected_count += 1
                selected_total += auto_score

            payload.append(
                {
                    "criteria_id": row.criteria_id,
                    "selected": selected,
                    "quantity": quantity,
                    "teacher_comment": comment,
                    "uploaded_file": uploaded_file,
                }
            )
            st.divider()

sum_col1, sum_col2 = st.columns(2)
sum_col1.metric("Выбрано пунктов", selected_count)
sum_col2.metric("Сумма баллов", f"{selected_total:.2f}")

selected_preview = []
for item in payload:
    if not item["selected"]:
        continue
    row = form_df[form_df["criteria_id"] == item["criteria_id"]].iloc[0]
    selected_preview.append(
        {
            "Код": row["code"],
            "Показатель": row["criterion_name"],
            "Количество": item["quantity"],
            "Баллы": float(item["quantity"]) * float(row["score"]),
            "Комментарий": item["teacher_comment"],
        }
    )

if selected_preview:
    st.subheader("Предпросмотр служебной записки")
    st.dataframe(selected_preview, use_container_width=True, hide_index=True)

if report["status"] != "reviewed":
    if st.button("Сохранить выбранные пункты"):
        save_report_items_bulk(report_id, payload)
        st.success("Выбранные пункты сохранены, баллы пересчитаны автоматически")
        st.rerun()

    if st.button("Отправить отчет заведующему", type="primary"):
        if submit_report(report_id):
            st.success("Отчет отправлен на проверку")
            st.rerun()
        else:
            st.warning("Сначала сохраните хотя бы один пункт отчета")
