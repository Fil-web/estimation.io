import streamlit as st

from admin import (
    build_order_html,
    calculate_payments,
    get_admin_summary,
    get_audit_log,
    get_all_criteria,
    get_periods,
)
from export_utils import build_order_docx, build_order_excel, build_order_pdf


def render_page():
    st.title("Панель администратора")

    summary = get_admin_summary()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Пользователи", summary["users"])
    col2.metric("Отчеты", summary["reports"])
    col3.metric("На проверке", summary["submitted"])
    col4.metric("Проверено", summary["reviewed"])

    audit_items = get_audit_log()
    if audit_items:
        with st.expander("Журнал действий", expanded=False):
            audit_view = [
                {
                    "Когда": item["created_at"],
                    "Кто": item["actor_name"],
                    "Сущность": item["entity_type"],
                    "ID": item["entity_id"],
                    "Действие": item["action_type"],
                    "Описание": item["details"],
                }
                for item in audit_items
            ]
            st.dataframe(audit_view, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Итоговые баллы по проверенным отчетам")

    periods = get_periods()
    if periods:
        selected_period = st.selectbox("Период", options=periods, index=0)
    else:
        selected_period = None
        st.info("Пока нет отправленных отчетов")

    if selected_period:
        payments_df = calculate_payments(selected_period)
        if payments_df.empty:
            st.info("Для выбранного периода пока нет проверенных отчетов")
        else:
            payment_filter_col1, payment_filter_col2 = st.columns(2)
            payment_search = payment_filter_col1.text_input(
                "Поиск по преподавателю",
                key="admin_payment_search",
            )
            payment_departments = ["Все кафедры"] + sorted(
                payments_df["department"].fillna("Без кафедры").unique().tolist()
            )
            payment_department = payment_filter_col2.selectbox(
                "Кафедра",
                options=payment_departments,
                key="admin_payment_department",
            )

            filtered_payments_df = payments_df.copy()
            if payment_search.strip():
                filtered_payments_df = filtered_payments_df[
                    filtered_payments_df["full_name"].str.contains(payment_search, case=False, na=False)
                    | filtered_payments_df["position"].fillna("").str.contains(payment_search, case=False, na=False)
                ]
            if payment_department != "Все кафедры":
                filtered_payments_df = filtered_payments_df[
                    filtered_payments_df["department"].fillna("Без кафедры") == payment_department
                ]

            if filtered_payments_df.empty:
                st.info("По выбранным фильтрам преподаватели не найдены")
            else:
                payments_view = filtered_payments_df[["full_name", "position", "department", "total_points"]].rename(
                    columns={
                        "full_name": "ФИО",
                        "position": "Должность",
                        "department": "Кафедра",
                        "total_points": "Итоговые баллы",
                    }
                )
                st.dataframe(payments_view, use_container_width=True, hide_index=True)

                total_points = filtered_payments_df["total_points"].sum()
                st.metric("Всего баллов", f"{total_points:.2f}")

            order_html = build_order_html(selected_period, payments_df)
            order_docx = build_order_docx(selected_period, payments_df)
            order_pdf = build_order_pdf(selected_period, payments_df)
            order_excel = build_order_excel(selected_period, payments_df)
            dl1, dl2, dl3, dl4 = st.columns(4)
            dl1.download_button(
                "Скачать приказ в HTML",
                data=order_html,
                file_name=f"prikaz_{selected_period}.html",
                mime="text/html",
                use_container_width=True,
            )
            dl2.download_button(
                "Скачать приказ в Word",
                data=order_docx,
                file_name=f"prikaz_{selected_period}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
            dl3.download_button(
                "Скачать приказ в PDF",
                data=order_pdf,
                file_name=f"prikaz_{selected_period}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
            dl4.download_button(
                "Скачать приказ в Excel",
                data=order_excel,
                file_name=f"prikaz_{selected_period}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

    st.divider()
    st.subheader("Сводка по всем заявленным критериям")
    all_items_df = get_all_criteria()
    if all_items_df.empty:
        st.info("Данные появятся после заполнения отчетов преподавателями")
    else:
        filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
        item_search = filter_col1.text_input("Поиск по критерию", key="admin_item_search")
        item_departments = ["Все кафедры"] + sorted(all_items_df["department"].fillna("Без кафедры").unique().tolist())
        selected_department = filter_col2.selectbox(
            "Кафедра",
            options=item_departments,
            key="admin_item_department",
        )
        item_periods = ["Все периоды"] + sorted(all_items_df["period"].astype(str).unique().tolist(), reverse=True)
        selected_item_period = filter_col3.selectbox(
            "Период",
            options=item_periods,
            key="admin_item_period",
        )
        item_statuses = ["Все статусы"] + sorted(all_items_df["report_status"].dropna().unique().tolist())
        selected_report_status = filter_col4.selectbox(
            "Статус отчета",
            options=item_statuses,
            key="admin_item_report_status",
        )

        filter_col5, filter_col6 = st.columns(2)
        groups = ["Все группы"] + sorted(all_items_df["group_name"].dropna().unique().tolist())
        selected_group = filter_col5.selectbox("Группа критериев", options=groups, key="admin_item_group")
        item_statuses = ["Все статусы пунктов"] + sorted(all_items_df["item_status"].dropna().unique().tolist())
        selected_item_status = filter_col6.selectbox(
            "Статус пункта",
            options=item_statuses,
            key="admin_item_status",
        )

        filtered_items_df = all_items_df.copy()
        if item_search.strip():
            filtered_items_df = filtered_items_df[
                filtered_items_df["criterion_name"].str.contains(item_search, case=False, na=False)
                | filtered_items_df["code"].str.contains(item_search, case=False, na=False)
                | filtered_items_df["full_name"].str.contains(item_search, case=False, na=False)
            ]
        if selected_department != "Все кафедры":
            filtered_items_df = filtered_items_df[
                filtered_items_df["department"].fillna("Без кафедры") == selected_department
            ]
        if selected_item_period != "Все периоды":
            filtered_items_df = filtered_items_df[filtered_items_df["period"].astype(str) == selected_item_period]
        if selected_report_status != "Все статусы":
            filtered_items_df = filtered_items_df[filtered_items_df["report_status"] == selected_report_status]
        if selected_group != "Все группы":
            filtered_items_df = filtered_items_df[filtered_items_df["group_name"] == selected_group]
        if selected_item_status != "Все статусы пунктов":
            filtered_items_df = filtered_items_df[filtered_items_df["item_status"] == selected_item_status]

        if filtered_items_df.empty:
            st.info("По выбранным фильтрам критерии не найдены")
            return

        st.dataframe(
            filtered_items_df.rename(
                columns={
                    "period": "Период",
                    "report_status": "Статус отчета",
                    "full_name": "ФИО",
                    "username": "Логин",
                    "department": "Кафедра",
                    "group_name": "Группа критериев",
                    "code": "Код",
                    "criterion_name": "Показатель",
                    "quantity": "Количество",
                    "claimed_score": "Баллы",
                    "item_status": "Статус пункта",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )
