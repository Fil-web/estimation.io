import json

import streamlit as st

from teacher import (
    create_report,
    get_report,
    get_report_form_data,
    get_report_history,
    get_teacher_reports,
    save_report_items_bulk,
    submit_report,
)
from ui import item_status_label, report_status_label


def render_page(user):
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
                st.rerun()
            else:
                st.warning("Введите период")

    if reports_df.empty:
        st.info("У вас пока нет отчетов. Создайте первый отчет за учебный период.")
        return

    report_options = {
        f"{row.period} | {report_status_label(row.status)} | позиций: {int(row.items_count)} | баллы: {row.claimed_points:.2f}": int(row.id)
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
        return

    signature_key = f"autosave_signature_{report_id}"

    meta1, meta2, meta3 = st.columns(3)
    meta1.metric("Период", report["period"])
    meta2.metric("Статус", report_status_label(report["status"]))
    meta3.metric("Кафедра", report.get("department_name") or "Без кафедры")

    if report["status"] == "reviewed":
        st.success("Отчет уже проверен заведующим. Редактирование отключено.")
    elif report["status"] == "returned":
        st.warning(
            "Отчет возвращен на доработку. Внесите правки и отправьте его повторно."
            + (f" Комментарий заведующего: {report['reviewer_comment']}" if report.get("reviewer_comment") else "")
        )

    form_df = get_report_form_data(report_id)

    filter_col1, filter_col2, filter_col3 = st.columns(3)
    criterion_search = filter_col1.text_input("Поиск по критерию", key=f"criterion_search_{report_id}")
    group_options = ["Все группы"] + sorted(form_df["group_name"].dropna().unique().tolist())
    selected_group = filter_col2.selectbox("Группа", options=group_options, key=f"group_filter_{report_id}")
    status_options = ["Все статусы", "Ожидает решения", "Подтвержден", "Отклонен"]
    selected_status = filter_col3.selectbox("Статус пункта", options=status_options, key=f"status_filter_{report_id}")

    filtered_df = form_df.copy()
    if criterion_search.strip():
        mask = (
            filtered_df["criterion_name"].str.contains(criterion_search, case=False, na=False)
            | filtered_df["code"].str.contains(criterion_search, case=False, na=False)
        )
        filtered_df = filtered_df[mask]
    if selected_group != "Все группы":
        filtered_df = filtered_df[filtered_df["group_name"] == selected_group]
    if selected_status != "Все статусы":
        status_map = {
            "Ожидает решения": "pending",
            "Подтвержден": "approved",
            "Отклонен": "rejected",
        }
        filtered_df = filtered_df[filtered_df["item_status"] == status_map[selected_status]]

    selected_count = 0
    selected_total = 0.0
    payload = []

    for group_name, group_df in filtered_df.groupby("group_name", dropna=False):
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
                info_col2.caption(f"Статус пункта: {item_status_label(row.item_status)}")

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
        current_signature = json.dumps(
            [
                {
                    "criteria_id": item["criteria_id"],
                    "selected": item["selected"],
                    "quantity": item["quantity"],
                    "teacher_comment": item["teacher_comment"],
                    "uploaded_name": item["uploaded_file"].name if item["uploaded_file"] is not None else "",
                }
                for item in payload
            ],
            ensure_ascii=False,
            sort_keys=True,
        )
        if signature_key not in st.session_state:
            st.session_state[signature_key] = current_signature
        elif st.session_state[signature_key] != current_signature:
            try:
                save_report_items_bulk(report_id, payload, actor_id=user_id)
                st.session_state[signature_key] = current_signature
                st.info("Черновик сохранен автоматически")
            except ValueError as exc:
                st.warning(str(exc))
                st.session_state[signature_key] = current_signature

        if st.button("Отправить отчет заведующему", type="primary"):
            try:
                if submit_report(report_id):
                    st.session_state[signature_key] = current_signature
                    st.success("Отчет отправлен на проверку")
                    st.rerun()
                else:
                    st.warning("Сначала сохраните хотя бы один пункт отчета")
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
