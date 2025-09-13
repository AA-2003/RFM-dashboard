import streamlit as st
import pandas as pd
import os
import sys

# Add parent directory to sys.path for module imports
sys.path.append(os.path.abspath(".."))
from utils.custom_css import apply_custom_css
from utils.auth import login
from utils.load_data import exacute_query
from utils.funcs import convert_df, convert_df_to_excel

def main():
    """Main function for customer inquiry module"""
    st.set_page_config(page_title="سرچ مشتری", page_icon="📊", layout="wide")
    apply_custom_css()
    st.title("ماژول استعلام مشتری")

    # Check if user is authenticated
    if 'auth' in st.session_state and st.session_state.auth:
        tabs = st.tabs(["جست‌و‌جو", "آپلود"])

        # --- Single customer search tab ---
        with tabs[0]:
            with st.form(key='customer_inquiry_form'):
                st.write("برای جستجوی مشتری، حداقل یکی از فیلدهای زیر را وارد کنید: ")

                col1, col2, col3 = st.columns(3)
                with col1:
                    input_last_name = st.text_input("نام")
                with col2:
                    input_phone_number = st.text_input("شماره تلفن")
                with col3:
                    input_customer_id = st.text_input("کد دیدار مشتری")

                submit_inquiry = st.form_submit_button(label='جست‌وجو')

            if submit_inquiry:
                # If all fields are empty, show error
                if not input_last_name and not input_phone_number and not input_customer_id:
                    st.error("حداقل یکی از موارد را پر کنید.")
                else:
                    # Build SQL WHERE filters based on user input
                    filters = []
                    if input_last_name:
                        # Search by last name or first name (OR condition)
                        filters.append(f"(Last_name LIKE '%{input_last_name}%' OR First_name LIKE '%{input_last_name}%')")
                    if input_phone_number:
                        filters.append(f"phone_number LIKE '%{input_phone_number}%'")
                    if input_customer_id:
                        try:
                            customer_id_int = int(input_customer_id)
                            filters.append(f"customer_id = {customer_id_int}")
                        except ValueError:
                            st.error("کد مشتری باید عدد باشد.")
                            filters.append("1=0")  # Prevent query if invalid input

                    # Always require last_name is not null or empty
                    filters.insert(0, "Last_name IS NOT NULL AND Last_name != ''")
                    where_clause = " AND ".join(filters)

                    # Query RFM segments table with built filters
                    query = f"""
                        SELECT * FROM `customerhealth-crm-warehouse.didar_data.RFM_segments`
                        WHERE {where_clause}
                        ORDER BY recency
                    """
                    rfm_data = exacute_query(query)

                    if rfm_data is None or rfm_data.empty:
                        st.info('هیچ مشتری با این مشخصات وجود ندارد!!!')
                    elif rfm_data.shape[0] > 20:
                        # Too many results, ask for more specific input
                        st.info(f'{rfm_data.shape[0]} مشتری با این مشخصات پیدا شد!!! لطفا مشخصات دقیق‌تری ذکر کنید.')
                        st.write(rfm_data)
                        cols = st.columns(2)
                        with cols[0]:
                            st.download_button(
                                label="دانلود داده‌ها به صورت CSV",
                                data=convert_df(rfm_data),
                                file_name='rfm_segmentation_with_churn.csv',
                                mime='text/csv',
                                key="download_csv"
                            )
                        with cols[1]:
                            st.download_button(
                                label="دانلود داده‌ها به صورت اکسل",
                                data=convert_df_to_excel(rfm_data),
                                file_name='rfm_segmentation_with_churn.xlsx',
                                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                key="download_excel"
                            )
                    else:
                        st.info(f'{rfm_data.shape[0]} مشتری با این مشخصات پیدا شد.')
                        # Get unique customer IDs for further queries
                        ids = rfm_data['customer_id'].dropna().astype(int).unique().tolist()

                        # Query deals for found customers
                        deals = exacute_query(f"""
                            SELECT * FROM `customerhealth-crm-warehouse.didar_data.deals`
                            WHERE Customer_id IN ({', '.join(str(id) for id in ids)})
                        """)

                        # Query happy call scenarios for found customers
                        happy_call_1 = exacute_query(f"""
                            SELECT * FROM `customerhealth-crm-warehouse.Surveys.happy_call_scenario_one`
                            WHERE Custmer_ID IN ({', '.join(str(id) for id in ids)})
                        """)
                        happy_call_2 = exacute_query(f"""
                            SELECT * FROM `customerhealth-crm-warehouse.Surveys.happy_call_scenario_two`
                            WHERE Custmer_ID IN ({', '.join(str(id) for id in ids)})
                        """)
                        happy_call_3 = exacute_query(f"""
                            SELECT * FROM `customerhealth-crm-warehouse.Surveys.happy_call_scenario_three`
                            WHERE Custmer_ID IN ({', '.join(str(id) for id in ids)})
                        """)
                        # Query forms for found customers
                        forms = exacute_query(f"""
                            SELECT * FROM `customerhealth-crm-warehouse.didar_data.Forms`
                            WHERE person_code IN ({', '.join(str(id) for id in ids)})
                        """)

                        # Iterate over each found customer and display their info and history
                        for _, customer in rfm_data.iterrows():
                            st.markdown("---")
                            # Show customer info in three columns
                            info1, info2, info3 = st.columns([2, 2, 2])
                            with info1:
                                st.markdown(f"**کد دیدار مشتری:**<br>{customer['customer_id']}", unsafe_allow_html=True)
                                st.markdown(f"**نام:**<br>{customer['first_name'] if customer['first_name'] is not None else ''} {customer['last_name']}", unsafe_allow_html=True)
                                st.markdown(f"**شماره همراه:**<br>{customer['phone_number']}", unsafe_allow_html=True)
                            with info2:
                                st.markdown(f"**تازگی (Recency):**<br>{customer['recency']} روز", unsafe_allow_html=True)
                                st.markdown(f"**تعداد خرید (Frequency):**<br>{customer['frequency']}", unsafe_allow_html=True)
                                st.markdown(f"**ارزش خرید (Monetary):**<br>{round(customer['monetary'], 2)}", unsafe_allow_html=True)
                            with info3:
                                st.markdown(f"**سگمنت RFM:**<br><span style='color:#2b9348;font-weight:bold'>{customer['rfm_segment']}</span>", unsafe_allow_html=True)

                            # --- Deals history section ---
                            # Filter deals for this customer
                            customer_deals = deals[deals['Customer_id'] == customer['customer_id']]
                            with st.expander("مشاهده سوابق معامله", expanded=not customer_deals.empty):
                                if customer_deals.empty:
                                    st.info("سابقه معامله‌ای وجود ندارد.")
                                else:
                                    # Only show relevant columns if present
                                    show_cols = [
                                        col for col in [
                                            "DealID", "DealCreateDate", "DealValue", "Status", "DealChannel", "DealType", "Nights", "DealExpert"
                                        ] if col in customer_deals.columns
                                    ]
                                    deals_to_show = customer_deals[show_cols].copy()
                                    deals_to_show['DealValue'] = deals_to_show['DealValue'].round(2)
                                    deals_to_show = deals_to_show.sort_values(by="DealCreateDate", ascending=False)
                                    st.dataframe(
                                        deals_to_show,
                                        use_container_width=True,
                                        hide_index=True
                                    )

                            # --- Happy Call records section ---
                            with st.expander("مشاهده سوابق Happy Call", expanded=False):
                                has_any_happy = False
                                # Scenario 1
                                # Filter happy call 1 for this customer
                                customer_happy_call_1 = happy_call_1[happy_call_1['Custmer_ID'] == customer['customer_id']] if happy_call_1 is not None and not happy_call_1.empty else None
                                if customer_happy_call_1 is not None and not customer_happy_call_1.empty:
                                    has_any_happy = True
                                    st.markdown("**Happy Call Scenario 1**")
                                    show_happy_cols_1 = [col for col in customer_happy_call_1.columns if col != 'Customer_id']
                                    show_happy_1 = customer_happy_call_1[show_happy_cols_1].copy()
                                    if 'call_date' in show_happy_1.columns:
                                        show_happy_1 = show_happy_1.sort_values(by="call_date", ascending=False)
                                    st.dataframe(
                                        show_happy_1,
                                        use_container_width=True,
                                        hide_index=True
                                    )
                                # Scenario 2
                                customer_happy_call_2 = happy_call_2[happy_call_2['Custmer_ID'] == customer['customer_id']] if happy_call_2 is not None and not happy_call_2.empty else None
                                if customer_happy_call_2 is not None and not customer_happy_call_2.empty:
                                    has_any_happy = True
                                    st.markdown("**Happy Call Scenario 2**")
                                    show_happy_cols_2 = [col for col in customer_happy_call_2.columns if col != 'Customer_id']
                                    show_happy_2 = customer_happy_call_2[show_happy_cols_2].copy()
                                    if 'call_date' in show_happy_2.columns:
                                        show_happy_2 = show_happy_2.sort_values(by="call_date", ascending=False)
                                    st.dataframe(
                                        show_happy_2,
                                        use_container_width=True,
                                        hide_index=True
                                    )
                                # Scenario 3
                                customer_happy_call_3 = happy_call_3[happy_call_3['Custmer_ID'] == customer['customer_id']] if happy_call_3 is not None and not happy_call_3.empty else None
                                if customer_happy_call_3 is not None and not customer_happy_call_3.empty:
                                    has_any_happy = True
                                    st.markdown("**Happy Call Scenario 3**")
                                    show_happy_cols_3 = [col for col in customer_happy_call_3.columns if col != 'Customer_id']
                                    show_happy_3 = customer_happy_call_3[show_happy_cols_3].copy()
                                    if 'call_date' in show_happy_3.columns:
                                        show_happy_3 = show_happy_3.sort_values(by="call_date", ascending=False)
                                    st.dataframe(
                                        show_happy_3,
                                        use_container_width=True,
                                        hide_index=True
                                    )
                                if not has_any_happy:
                                    st.info("هیچ رکورد Happy Call برای این مشتری وجود ندارد.")

                            # --- Forms records section ---
                            # Filter forms for this customer
                            customer_forms = forms[forms['person_code'] == customer['customer_id']] if forms is not None and not forms.empty else None
                            with st.expander("مشاهده سوابق فرم‌ها", expanded=False):
                                if customer_forms is None or customer_forms.empty:
                                    st.info("هیچ فرم ثبت‌شده‌ای برای این مشتری وجود ندارد.")
                                else:
                                    show_form_cols = [col for col in customer_forms.columns if col != 'person_code']
                                    show_forms = customer_forms[show_form_cols].copy()
                                    if 'form_date' in show_forms.columns:
                                        show_forms = show_forms.sort_values(by="form_date", ascending=False)
                                    st.dataframe(
                                        show_forms,
                                        use_container_width=True,
                                        hide_index=True
                                    )

        # --- Batch customer search via file upload tab ---
        with tabs[1]:
            uploaded_file = st.file_uploader("آپلود فایل اکسل یا CSV", type=['xlsx', 'csv'])
            if uploaded_file is not None:
                try:
                    # Read uploaded file as DataFrame
                    if uploaded_file.name.endswith('.csv'):
                        file_data = pd.read_csv(uploaded_file)
                    else:
                        file_data = pd.read_excel(uploaded_file)

                    st.success("فایل با موفقیت آپلود شد!")
                    st.write("ستون‌های موجود در فایل:", list(file_data.columns))

                    selected_column = st.selectbox("ستون مورد نظر برای جستجو را انتخاب کنید", file_data.columns.values.tolist())
                    column_type = st.radio("محتوای ستون انتخابی چیست؟", ["شماره تلفن", "نام", "کد مشتری"])

                    # Load RFM data for comparison (separately for upload tab)
                    rfm_query = """
                        SELECT * FROM `customerhealth-crm-warehouse.didar_data.RFM_segments`
                        WHERE Last_name IS NOT NULL AND Last_name != ''
                    """
                    rfm_data_upload = exacute_query(rfm_query)

                    if st.button("جستجو"):
                        if rfm_data_upload is None or rfm_data_upload.empty:
                            st.error("داده‌های مشتری برای جستجو در دسترس نیست.")
                        else:
                            # Match uploaded file column with RFM data based on selected type
                            if column_type == "شماره تلفن":
                                matching_results = rfm_data_upload[rfm_data_upload['phone_number'].fillna(0).astype(int).isin(file_data[selected_column].fillna(0).astype(int))]
                                exists_mask = file_data[selected_column].fillna(0).astype(int).isin(rfm_data_upload['phone_number'].astype(int))
                            elif column_type == "نام":
                                matching_results = rfm_data_upload[rfm_data_upload['Last_name'].astype(str).isin(file_data[selected_column].astype(str))]
                                exists_mask = file_data[selected_column].astype(str).isin(rfm_data_upload['Last_name'].astype(str))
                            elif column_type == "کد مشتری":
                                matching_results = rfm_data_upload[rfm_data_upload['customer_id'].astype(int).isin(file_data[selected_column].fillna(0).astype(int))]
                                exists_mask = file_data[selected_column].fillna(0).astype(int).isin(rfm_data_upload['customer_id'].astype(int))
                            else:
                                matching_results = pd.DataFrame()
                                exists_mask = pd.Series([False]*len(file_data))

                            # Add a column to indicate if the record exists in the dataset
                            file_data['وضعیت_در_دیتاست'] = exists_mask

                            existing_users = file_data[file_data['وضعیت_در_دیتاست']]
                            new_users = file_data[~file_data['وضعیت_در_دیتاست']]

                            # Show found customers
                            if not existing_users.empty:
                                st.success(f"{len(existing_users)} مشتری موجود از فایل آپلود شده پیدا شد.")
                                st.dataframe(matching_results, use_container_width=True)

                            # Show new (acquisition) users
                            if not new_users.empty:
                                st.warning(f"{len(new_users)} کاربر جدید شناسایی شد که در دیتاست وجود ندارند.")
                                st.subheader("کاربران اکتسابی")
                                st.dataframe(new_users, use_container_width=True)

                except Exception as e:
                    st.error(f"خطا در پردازش فایل: {e}")
    else:
        # If not authenticated, show login
        login()

if __name__ == "__main__":
    main()