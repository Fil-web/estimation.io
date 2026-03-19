import streamlit as st

from head import (
    build_service_note_html,
    finalize_report_review,
    get_head_reports,
    get_head_reviewed_periods,
    get_report_review_data,
    get_service_note_context,
    review_report_item,
)
from teacher import get_attachment_bytes, get_report


def require_head():
    user = st.session_state.get("user")
    if not user:
        st.switch_page("app.py")
    if user["role"] != "head":
        st.error("Доступ только для заведующего кафедрой")
        st.stop()
    return user


user = require_head()

st.title("Проверка отчетов кафедры")

reviewed_periods = get_head_reviewed_periods(user["id"])
if reviewed_periods:
    st.subheader("Служебная записка")
    memo_period = st.selectbox(
        "Период для служебной записки",
        options=reviewed_periods,
        key="memo_period",
    )
    memo_context = get_service_note_context(user["id"], memo_period)
    memo_html = build_service_note_html(memo_context)
    if memo_html:
        st.download_button(
            "Скачать служебную записку (HTML)",
            data=memo_html,
            file_name=f"sluzhebnaya_zapiska_{memo_period}.html",
            mime="text/html",
        )
        with st.expander("Предпросмотр служебной записки"):
            st.components.v1.html(memo_html, height=700, scrolling=True)

st.divider()

reports_df = get_head_reports(user["id"])
if reports_df.empty:
    st.info("У кафедры пока нет отчетов на проверку")
    st.stop()

report_options = {
    f"{row.period} | {row.full_name} | {row.status} | {row.claimed_points:.2f} баллов": int(row.id)
    for row in reports_df.itertuples(index=False)
}

selected_label = st.selectbox("Отчет преподавателя", options=list(report_options.keys()))
report_id = report_options[selected_label]
report = get_report(report_id)

meta1, meta2, meta3 = st.columns(3)
meta1.metric("Преподаватель", report["full_name"])
meta2.metric("Период", report["period"])
meta3.metric("Статус", report["status"])

review_df = get_report_review_data(report_id)

for row in review_df.itertuples(index=False):
    with st.container(border=True):
        st.markdown(f"**{row.code}**. {row.criterion_name}")
        st.caption(f"Количество: {row.quantity} | Баллы: {row.claimed_score:.2f} | База: {row.base}")
        if row.teacher_comment:
            st.write(f"Комментарий преподавателя: {row.teacher_comment}")

        if row.attachment_name and row.attachment_path:
            attachment_bytes = get_attachment_bytes(row.attachment_path)
            if attachment_bytes:
                st.download_button(
                    f"Скачать {row.attachment_name}",
                    data=attachment_bytes,
                    file_name=row.attachment_name,
                    key=f"download_{row.id}",
                )

        action = st.radio(
            f"Решение по {row.code}",
            options=["Подтвердить", "Отклонить"],
            index=0 if row.status == "approved" else 1 if row.status == "rejected" else 0,
            horizontal=True,
            key=f"action_{row.id}",
            disabled=report["status"] == "reviewed",
        )
        review_comment = st.text_area(
            f"Комментарий заведующего по {row.code}",
            value=row.review_comment,
            key=f"review_comment_{row.id}",
            disabled=report["status"] == "reviewed",
        )

        if st.button(
            f"Сохранить решение по {row.code}",
            key=f"save_review_{row.id}",
            disabled=report["status"] == "reviewed",
        ):
            review_report_item(row.id, action, review_comment, user["id"])
            st.success(f"Решение по {row.code} сохранено")
            st.rerun()

if report["status"] != "reviewed":
    final_comment = st.text_area("Итоговый комментарий к отчету", key=f"final_comment_{report_id}")
    if st.button("Завершить проверку", type="primary"):
        if finalize_report_review(report_id, user["id"], final_comment):
            st.success("Проверка отчета завершена")
            st.rerun()
        else:
            st.warning("Сначала примите решение по всем пунктам отчета")
