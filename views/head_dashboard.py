import streamlit as st

from export_utils import build_service_note_docx, build_service_note_excel, build_service_note_pdf
from head import (
    bulk_review_report_items,
    build_service_note_html,
    finalize_report_review,
    get_head_reports,
    get_head_reviewed_periods,
    get_report_history,
    get_report_review_data,
    get_service_note_context,
    review_report_item,
    return_report_for_revision,
)
from teacher import get_attachment_bytes, get_report
from ui import item_status_label, report_status_label


def render_page(user):
    st.title("Проверка отчетов кафедры")

    reviewed_periods = get_head_reviewed_periods(user["id"])
    if reviewed_periods:
        st.subheader("Служебная записка")
        memo_col1, memo_col2 = st.columns(2)
        memo_period = memo_col1.selectbox(
            "Период для служебной записки",
            options=reviewed_periods,
            key="memo_period",
        )
        selection_mode = memo_col2.radio(
            "Состав записки",
            options=["Вся кафедра", "Выбранные преподаватели"],
            horizontal=True,
            key="memo_selection_mode",
        )
        base_memo_context = get_service_note_context(user["id"], memo_period, register_number=False)
        selected_teacher_ids = None
        if base_memo_context and selection_mode == "Выбранные преподаватели":
            teacher_options = {
                f"{teacher['full_name']} ({teacher['position'] or 'должность не указана'})": teacher["user_id"]
                for teacher in base_memo_context["teachers"]
            }
            chosen_labels = st.multiselect(
                "Преподаватели для включения в записку",
                options=list(teacher_options.keys()),
                default=list(teacher_options.keys()),
                key="memo_teacher_selection",
            )
            selected_teacher_ids = [teacher_options[label] for label in chosen_labels]

        if selection_mode == "Выбранные преподаватели" and not selected_teacher_ids:
            st.info("Выберите хотя бы одного преподавателя для формирования записки")
        else:
            memo_context = get_service_note_context(
                user["id"],
                memo_period,
                selected_teacher_ids=selected_teacher_ids,
                register_number=True,
            )
            memo_html = build_service_note_html(memo_context)
            if memo_html:
                memo_docx = build_service_note_docx(memo_context)
                memo_pdf = build_service_note_pdf(memo_context)
                memo_excel = build_service_note_excel(memo_context)
                st.caption(f"Номер служебной записки: № {memo_context['note_number']} от {memo_context['note_date']}")
                dl1, dl2, dl3, dl4 = st.columns(4)
                dl1.download_button(
                    "Скачать записку в HTML",
                    data=memo_html,
                    file_name=f"sluzhebnaya_zapiska_{memo_period}.html",
                    mime="text/html",
                    use_container_width=True,
                )
                dl2.download_button(
                    "Скачать записку в Word",
                    data=memo_docx,
                    file_name=f"sluzhebnaya_zapiska_{memo_period}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )
                dl3.download_button(
                    "Скачать записку в PDF",
                    data=memo_pdf,
                    file_name=f"sluzhebnaya_zapiska_{memo_period}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
                dl4.download_button(
                    "Скачать записку в Excel",
                    data=memo_excel,
                    file_name=f"sluzhebnaya_zapiska_{memo_period}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
                with st.expander("Предпросмотр служебной записки"):
                    st.components.v1.html(memo_html, height=700, scrolling=True)

    st.divider()

    reports_df = get_head_reports(user["id"])
    if reports_df.empty:
        st.info("У кафедры пока нет отчетов на проверку")
        return

    reports_filter_col1, reports_filter_col2, reports_filter_col3 = st.columns(3)
    report_search = reports_filter_col1.text_input("Поиск по преподавателю", key="head_report_search")
    period_filter = reports_filter_col2.selectbox(
        "Фильтр по периоду",
        options=["Все периоды"] + sorted(reports_df["period"].astype(str).unique().tolist()),
        key="head_period_filter",
    )
    status_filter = reports_filter_col3.selectbox(
        "Фильтр по статусу",
        options=["Все статусы", "На проверке", "На доработке", "Проверен"],
        key="head_status_filter",
    )

    filtered_reports_df = reports_df.copy()
    if report_search.strip():
        filtered_reports_df = filtered_reports_df[
            filtered_reports_df["full_name"].str.contains(report_search, case=False, na=False)
        ]
    if period_filter != "Все периоды":
        filtered_reports_df = filtered_reports_df[filtered_reports_df["period"] == period_filter]
    if status_filter != "Все статусы":
        status_map = {
            "На проверке": "submitted",
            "На доработке": "returned",
            "Проверен": "reviewed",
        }
        filtered_reports_df = filtered_reports_df[filtered_reports_df["status"] == status_map[status_filter]]

    if filtered_reports_df.empty:
        st.info("По выбранным фильтрам отчеты не найдены")
        return

    report_options = {
        f"{row.period} | {row.full_name} | {report_status_label(row.status)} | {row.claimed_points:.2f} баллов": int(row.id)
        for row in filtered_reports_df.itertuples(index=False)
    }

    selected_label = st.selectbox("Отчет преподавателя", options=list(report_options.keys()))
    report_id = report_options[selected_label]
    report = get_report(report_id)

    meta1, meta2, meta3 = st.columns(3)
    meta1.metric("Преподаватель", report["full_name"])
    meta2.metric("Период", report["period"])
    meta3.metric("Статус", report_status_label(report["status"]))
    if report["status"] == "returned" and report.get("reviewer_comment"):
        st.info(f"Последний комментарий к доработке: {report['reviewer_comment']}")

    review_df = get_report_review_data(report_id)
    item_filter_col1, item_filter_col2 = st.columns(2)
    item_search = item_filter_col1.text_input("Поиск по пунктам отчета", key=f"item_search_{report_id}")
    item_status_filter = item_filter_col2.selectbox(
        "Фильтр по статусу пунктов",
        options=["Все статусы", "Ожидает решения", "Подтвержден", "Отклонен"],
        key=f"item_status_filter_{report_id}",
    )

    filtered_review_df = review_df.copy()
    if item_search.strip():
        filtered_review_df = filtered_review_df[
            filtered_review_df["criterion_name"].str.contains(item_search, case=False, na=False)
            | filtered_review_df["code"].str.contains(item_search, case=False, na=False)
            | filtered_review_df["teacher_comment"].fillna("").str.contains(item_search, case=False, na=False)
        ]
    if item_status_filter != "Все статусы":
        status_map = {
            "Ожидает решения": "pending",
            "Подтвержден": "approved",
            "Отклонен": "rejected",
        }
        filtered_review_df = filtered_review_df[filtered_review_df["status"] == status_map[item_status_filter]]

    expand_all_groups = st.checkbox("Раскрыть все группы критериев", key=f"expand_groups_{report_id}")

    selected_item_ids = []
    for group_name, group_df in filtered_review_df.groupby("group_name", dropna=False):
        pending_count = int((group_df["status"] == "pending").sum())
        group_title = f"{group_name} ({len(group_df)} пункт.)"
        if pending_count:
            group_title += f" | ожидает решения: {pending_count}"

        with st.expander(group_title, expanded=expand_all_groups):
            for row in group_df.itertuples(index=False):
                with st.container(border=True):
                    checked = st.checkbox(
                        f"Отметить пункт {row.code} для массового действия",
                        key=f"mass_select_{row.id}",
                        disabled=report["status"] == "reviewed",
                    )
                    if checked:
                        selected_item_ids.append(int(row.id))
                    st.markdown(f"**{row.code}**. {row.criterion_name}")
                    st.caption(f"Количество: {row.quantity} | Баллы: {row.claimed_score:.2f} | База: {row.base}")
                    st.caption(f"Статус пункта: {item_status_label(row.status)}")
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
                        try:
                            review_report_item(row.id, action, review_comment, user["id"])
                            st.success(f"Решение по {row.code} сохранено")
                            st.rerun()
                        except ValueError as exc:
                            st.warning(str(exc))

    if report["status"] != "reviewed" and selected_item_ids:
        st.divider()
        st.subheader("Массовое действие по отмеченным пунктам")
        bulk_col1, bulk_col2 = st.columns(2)
        bulk_action = bulk_col1.radio(
            "Действие",
            options=["Подтвердить", "Отклонить"],
            horizontal=True,
            key=f"bulk_action_{report_id}",
        )
        bulk_comment = bulk_col2.text_input("Общий комментарий", key=f"bulk_comment_{report_id}")
        if st.button("Применить к отмеченным пунктам", type="primary"):
            try:
                affected = bulk_review_report_items(report_id, selected_item_ids, bulk_action, bulk_comment, user["id"])
                st.success(f"Массовое действие выполнено. Изменено пунктов: {affected}")
                st.rerun()
            except ValueError as exc:
                st.warning(str(exc))

    if report["status"] != "reviewed":
        final_comment = st.text_area("Итоговый комментарий к отчету", key=f"final_comment_{report_id}")
        action_col1, action_col2 = st.columns(2)
        if action_col1.button("Вернуть на доработку"):
            try:
                if return_report_for_revision(report_id, user["id"], final_comment):
                    st.success("Отчет возвращен преподавателю на доработку")
                    st.rerun()
            except ValueError as exc:
                st.warning(str(exc))
        if action_col2.button("Завершить проверку", type="primary"):
            try:
                if finalize_report_review(report_id, user["id"], final_comment):
                    st.success("Проверка отчета завершена")
                    st.rerun()
                else:
                    st.warning("Сначала примите решение по всем пунктам отчета")
            except ValueError as exc:
                st.warning(str(exc))

    history_items = get_report_history(report_id)
    if history_items:
        action_labels = {
            "create_report": "Создание отчета",
            "autosave_draft": "Автосохранение черновика",
            "submit_report": "Отправка отчета",
            "return_for_revision": "Возврат на доработку",
            "review_item": "Проверка пункта",
            "bulk_review": "Массовая проверка",
            "finalize_review": "Завершение проверки",
        }
        history_df = [
            {
                "Когда": item["created_at"],
                "Кто": item["actor_name"],
                "Действие": action_labels.get(item["action_type"], item["action_type"]),
                "Описание": item["details"],
            }
            for item in history_items
        ]
        with st.expander("История изменений по отчету"):
            st.dataframe(history_df, use_container_width=True, hide_index=True)
