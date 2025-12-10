import streamlit as st
import pandas as pd
import numpy as np
import os
import sys
from streamlit_nej_datepicker import datepicker_component, Config
import jdatetime

# Add parent directory to sys.path for custom imports
sys.path.append(os.path.abspath(".."))
from utils.custom_css import apply_custom_css
from utils.auth import login
from utils.load_data import exacute_query
from utils.funcs import convert_df, convert_df_to_excel

def to_sql_list(values):
    # Convert a list of values to a SQL-friendly string for IN clause
    return ", ".join(f"'{v}'" for v in values)

def main():
    """Main function for the customer satisfaction dashboard"""
    st.set_page_config(page_title="هپی کال", page_icon="📊", layout="wide")
    apply_custom_css()
    st.title("رضایت مشتری ")
    # Check authentication before showing the dashboard
    if 'auth' in st.session_state and st.session_state.auth:  
        # Layout for filters
        col1, _, col2, *_ = st.columns([5,1,5,1,1])

        ### Date filter (complex: fetch min date from DB and use custom Persian datepicker)
        with col1:
            query = """
                SELECT 
                    MIN(Checkout) AS min_date
                FROM `customerhealth-crm-warehouse.didar_data.deals`
                WHERE DATE_DIFF(CAST(Checkout AS DATE), CAST(Checkin_date AS DATE), DAY) = Nights
                AND Status = 'Won'
            """
            result_df = exacute_query(query)
            min_date = result_df.iloc[0]['min_date']

            st.subheader("انتخاب بازه زمانی تاریخ خروج: ")
            config = Config(
                always_open=True,
                dark_mode=True,
                locale="fa",
                minimum_date=min_date,
                maximum_date=jdatetime.date.today(),
                color_primary="#ff4b4b",
                color_primary_light="#ff9494",
                selection_mode="range",
                placement="bottom",
                disabled=True
            )
            res = datepicker_component(config=config)

            # Convert selected Jalali dates to Gregorian, fallback to min/max if not selected
            if res and 'from' in res and res['from'] is not None:
                start_date = res['from'].togregorian()
            else:
                start_date = min_date

            if res and 'to' in res and res['to'] is not None:
                end_date = res['to'].togregorian()
            else:
                end_date = jdatetime.date.today().togregorian()
                
        with col2: 
            # VIP status filter
            vip_options = ['Non-VIP', 'Bronze VIP', 'Silver VIP', 'Gold VIP']
            vip_status = st.checkbox("انتخاب تمام وضعیت‌های VIP", value=True, key='vips_checkbox')
            if vip_status:
                vip_values = vip_options
            else:
                vip_values = st.multiselect(
                    "انتخاب وضعیت VIP:",
                    options=vip_options,
                    default=[],  
                    key='vips_multiselect_selectbox'
                )
            if vip_values == []:
                vip_values = vip_options

            # Segmentation filter (customer segments)
            semention_options = [
                'At Risk ✨ Potential', 'At Risk ❤️ Loyal Customers', 'At Risk 👑 Champions',
                'At Risk 💰 Big Spender', 'At Risk 🔒 Reliable Customers', 'At Risk �️️ Low Value',
                'At Risk 🧐 Curious Customers', 'Lost ✨ Potential', 'Lost ❤️ Loyal Customers',
                'Lost 👑 Champions', 'Lost 💰 Big Spender', 'Lost 🔒 Reliable Customers', 'Lost 🗑️ Low Value',
                'Lost 🧐 Curious Customers', 'New 🧐 Curious Customers',  '✨ Potential', '❤️ Loyal Customers',
                '👑 Champions', '💰 Big Spender', '🔒 Reliable Customers', '🗑️ Low Value', '🧐 Curious Customers'
            ]
            segment_status = st.checkbox("انتخاب تمام سگمنت ها", value=True, key='segments_checkbox')
            if segment_status:
                segment_values = semention_options
            else:
                segment_values = st.multiselect(
                    "انتخاب سگمنت:",
                    options=semention_options,
                    default=[semention_options[0]],  # Default to first option
                    key='segment_multiselect_selectbox'
                )
            if segment_values == []:
                segment_values = semention_options
        
            # Tip filter (complex: filter by building and then by tip/product)
            products = exacute_query("""
                SELECT * FROM `customerhealth-crm-warehouse.didar_data.Products`
            """)
            complex_options = [b for b in products['Building_name'].unique().tolist() if b != 'not_a_building']
            tip_options = products[products['Building_name'] != 'not_a_building']['ProductName'].unique().tolist() 
    
            complex_status = st.checkbox("انتخاب تمام مجتمع ها ", value=True, key='complex_checkbox')
            if complex_status:
                tip_values = tip_options
            else:
                complex_values = st.multiselect(
                    "انتخاب مجتمع :",
                    options=complex_options,
                    default=[],  # empty if user doesn’t pick
                    key='complex_multiselect_selectbox'
                )
                cols = st.columns([1, 4])

                with cols[1]:
                    # Filter tip options based on selected complexes
                    tip_options = products[
                        (products['Building_name'] != 'not_a_building') &
                        (products['Building_name'].isin(complex_values))
                    ]['ProductName'].unique().tolist()
                    tip_status = st.checkbox("انتخاب تمام تیپ ها ", value=True, key='tips_checkbox')
                    if tip_status:
                        tip_values = tip_options
                    else:
                        tip_values = st.multiselect(
                            "انتخاب تیپ :",
                            options=tip_options,
                            default=[],  # empty if user doesn’t pick
                            key='tip_multiselect_selectbox'
                        )
                    if tip_values == []:
                        tip_values = tip_options

            # Monthly/Non-monthly filter (complex: also set minimum nights for monthly)
            montly_status = st.checkbox("ماهانه و غیرماهانه", value=True, key='monthly_checkbox')
            if montly_status:
                montly_values = ["ماهانه", "غیر ماهانه"]
                monthly_limit = 15
            else:
                montly_values = st.selectbox(
                    "انتخاب وضعیت :",
                    options=["ماهانه", "غیر ماهانه"],
                    key='monthly_multiselect_selectbox'
                )
                monthly_limit = st.number_input(
                    "مینیمم میانگین اقامت برای اینکه مهمان ماهانه محسوب شود را وارد کنید:",
                    min_value=0, value=15, step=1, key='min_nights_filter'
                )

            if montly_values == []:
                montly_values = ["ماهانه", "غیر ماهانه"]
            elif len(montly_values) != 2:
                montly_values = list([montly_values])
            
            # Comment filter (complex: show sub-filters for comment types)
            comment_filter = st.checkbox(
                "فقط نظرسنجی‌هایی که کامنت دارند؟",
                key='comment_filter_checkbox'
            ) 
            columns = st.columns([1, 4])
            with columns[1]:
                if comment_filter:
                    nps_comment = st.checkbox('نظرسنجی‌هایی که کامنت nps دارند؟', key='nps_checkbox')
                    cleanness_comment = st.checkbox('نظرسنجی‌هایی که کامنت در مورد نظافت دارند؟', key='cleaness_checkbox')
                    staff_comment = st.checkbox('نظرسنجی‌هایی که کامنت در مورد پرسنل دارند؟', key='staff_checkbox')
                    amneties_comment = st.checkbox('نظرسنجی‌هایی که کامنت در مورد امکانات دارند؟', key='amneties_checkbox')

        # Main calculation and data retrieval
        if st.button("محاسبه و نمایش", key='calculate_button'):
            # 1. Get customer IDs matching all filters (complex: monthly, VIP, segment)
            customer_ids_query = f"""
                SELECT customer_id
                FROM (
                    SELECT *,
                        CASE
                            WHEN (total_nights / frequency) >= {monthly_limit} THEN "ماهانه"
                            ELSE "غیر ماهانه"
                        END AS monthly_status,
                        CASE
                            WHEN last_name LIKE '%💎%' THEN 'Gold VIP'
                            WHEN last_name LIKE '%⭐%' THEN 'Silver VIP'
                            WHEN last_name LIKE '%💠%' THEN 'Bronze VIP'
                            ELSE 'Non-VIP'
                        END AS vip_status
                    FROM `customerhealth-crm-warehouse.didar_data.RFM_segments`
                    WHERE rfm_segment IN ({to_sql_list(segment_values)})
                ) t
                WHERE vip_status IN ({to_sql_list(vip_values)})
                  AND monthly_status IN ({to_sql_list(montly_values)})
            """
            ids = exacute_query(customer_ids_query)
            customer_ids = ids['customer_id'].dropna().unique().tolist()
            ids_list_sql = ', '.join(str(int(i)) for i in customer_ids)

            # 2. Get deal IDs for those customers, filtered by tip, date, etc.
            deals_query = f"""
                SELECT 
                    d.DealId
                FROM `customerhealth-crm-warehouse.didar_data.deals` d
                JOIN `customerhealth-crm-warehouse.didar_data.Products` p
                    ON d.Product_code = p.ProductCode
                WHERE d.Customer_id IN ({ids_list_sql})
                  AND p.ProductName IN ({to_sql_list(tip_options)})
                  AND d.Checkout BETWEEN DATE('{start_date}') AND DATE('{end_date}')
                  AND p.Building_name IS NOT NULL
                  AND d.Status = 'Won'
            """
            deals_ids = exacute_query(deals_query)

            # 3. Prepare comment filters for different scenarios (complex: different logic for scenario 1/2 vs 3)
            one_two = ""
            three = ""
            if comment_filter:
                one_two = 'AND comment IS NOT NULL '
                three = 'AND (open_comment IS NOT NULL OR NPS_raw_comment IS NOT NULL OR staff_comment IS NOT NULL OR amneties_comment IS NOT NULL OR cleanliness_comment IS NOT NULL) '
                if nps_comment: 
                    one_two += "AND NPS_raw_score < 3 "
                    three += "AND NPS_raw_comment IS NOT NULL "
                if cleanness_comment:
                    one_two += "AND cleanliness_score < 3 "
                    three += "AND cleanliness_comment IS NOT NULL "
                if staff_comment:
                    one_two += "AND staff_score < 3 "
                    three += "AND staff_comment IS NOT NULL "
                if amneties_comment:
                    one_two += "AND amneties_score < 3 "
                    three += "AND amneties_comment IS NOT NULL "

            # 4. Query happy call survey data for all three scenarios (complex: different schemas)
            deal_ids_str = ','.join(str(id) for id in deals_ids['DealId'].unique().tolist())
            happy_call_1 = exacute_query(f"""
                SELECT * FROM `customerhealth-crm-warehouse.Surveys.happy_call_scenario_one`
                WHERE Deal_ID IN ({deal_ids_str})
                AND checkout_date IS NOT NULL 
                {one_two}
            """)
            happy_call_2 = exacute_query(f"""
                SELECT * FROM `customerhealth-crm-warehouse.Surveys.happy_call_scenario_two`
                WHERE Deal_ID IN ({deal_ids_str})
                AND checkout_date IS NOT NULL  
                {one_two}
            """)
            happy_call_3 = exacute_query(f"""
                SELECT * FROM `customerhealth-crm-warehouse.Surveys.happy_call_scenario_three`
                WHERE Deal_ID IN ({deal_ids_str})
                AND checkout_date IS NOT NULL  
                {three}
            """)

            # 5. Combine all scenarios into a single DataFrame (complex: schemas may differ)
            happy_calls = []
            for df in [happy_call_1, happy_call_2, happy_call_3]:
                if df is not None and not df.empty:
                    happy_calls.append(df)
            if happy_calls:
                all_calls = pd.concat(happy_calls, ignore_index=True)
            else:
                all_calls = pd.DataFrame()

            if not all_calls.empty:
                # 6. Standardize column names and fill missing columns (complex: mapping and harmonization)
                column_map = {
                    # Common columns
                    'Caller_name': 'Caller_name',
                    'Deal_ID': 'Deal_ID',
                    'Custmer_ID': 'Customer_ID',
                    'Customer_name': 'Customer_name',
                    'Phone_number': 'Phone_number',
                    'checkout_date': 'checkout_date',
                    'first_call_date': 'first_call_date',
                    'first_call_result': 'first_call_result',
                    'second_call_date': 'second_call_date',
                    'second_call_result': 'second_call_result',
                    'cleanliness_score': 'cleanliness_score',
                    'amneties_score': 'amneties_score',
                    'staff_score': 'staff_score',
                    'NPS_raw_score': 'NPS_raw_score',
                    # Comments (different names)
                    'comment': 'comment',  # scenario 1, 2
                    'cleanliness_comment': 'cleanliness_comment',  # scenario 3
                    'amneties_comment': 'amneties_comment',        # scenario 3
                    'staff_comment': 'staff_comment',              # scenario 3
                    'NPS_raw_comment': 'NPS_raw_comment',          # scenario 3
                    'open_comment': 'open_comment',                # scenario 3
                    'hamcall_comment': 'hamcall_comment',          # scenario 3
                    'hamcall_comments': 'hamcall_comment',         # scenario 2 (note plural)
                    # Other
                    'matching_score': 'matching_score',
                    'welcome_pack': 'welcome_pack',
                    'checkin_score': 'checkin_score',
                    'created_at': 'created_at',
                    'updated_at': 'updated_at',
                    'survey_id': 'survey_id'
                }

                # Ensure all expected columns exist (fill missing with NaN)
                for col in column_map.values():
                    if col not in all_calls.columns:
                        all_calls[col] = np.nan

                # Unify 'hamcall_comment' (from 'hamcall_comments' or 'hamcall_comment')
                if 'hamcall_comments' in all_calls.columns and 'hamcall_comment' not in all_calls.columns:
                    all_calls['hamcall_comment'] = all_calls['hamcall_comments']

                # 7. Create a unified customer comment column (complex: merge all possible comment fields)
                def combine_comments(row):
                    comments = []
                    # Scenario 1/2
                    if pd.notna(row.get('comment', None)):
                        comments.append(str(row['comment']))
                    # Scenario 3
                    for c in ['open_comment', 'NPS_raw_comment', 'staff_comment', 'amneties_comment', 'cleanliness_comment', 'hamcall_comment']:
                        if c in row and pd.notna(row[c]):
                            comments.append(str(row[c]))
                    return " | ".join([c for c in comments if c and c.strip()])

                all_calls['customer_comment'] = all_calls.apply(combine_comments, axis=1)

                # 8. Filter for valid rows (complex: require all key fields to be present)
                all_calls = all_calls[
                    (all_calls['first_call_date'].notna()) &
                    (all_calls['first_call_result'].notna()) &
                    (all_calls['Caller_name'].notna()) &
                    (all_calls['checkout_date'].notna()) &
                    (all_calls['Deal_ID'].notna())
                ].reset_index(drop=True).copy()

                # 9. Calculate metrics (number of calls, success rate, averages)
                num_calls = all_calls[all_calls['first_call_result'].notna()].shape[0]

                # Success rate: percent of calls with successful result (complex: check both first and second call)
                def is_success(row):
                    first = str(row.get('first_call_result', '')).strip()
                    second = str(row.get('second_call_result', '')).strip()
                    return (first.lower() == 'successful_call') or (second.lower() == 'successful_call')

                all_calls['success'] = all_calls.apply(is_success, axis=1)
                success_rate = all_calls['success'].mean() * 100 if len(all_calls) > 0 else np.nan

                # Average NPS
                avg_nps = all_calls['NPS_raw_score'].mean() if 'NPS_raw_score' in all_calls else np.nan

                # Average cleanliness
                avg_cleanliness = all_calls['cleanliness_score'].mean() if 'cleanliness_score' in all_calls else np.nan

                # Average staff score
                avg_staff = all_calls['staff_score'].mean() if 'staff_score' in all_calls else np.nan

                # 10. Show metrics in dashboard
                col1, col2, col3, col4, col5 = st.columns(5)
                col1.metric("تعداد تماس‌ها", f"{num_calls:,}")
                col2.metric("درصد موفقیت تماس", f"{success_rate:.1f}٪" if not np.isnan(success_rate) else "-")
                col3.metric("میانگین NPS", f"{avg_nps:.2f}" if avg_nps is not pd.NA and not np.isnan(avg_nps) else "-")
                col4.metric("میانگین نظافت", f"{avg_cleanliness:.2f}" if not np.isnan(avg_cleanliness) else "-")
                col5.metric("میانگین پرسنل", f"{avg_staff:.2f}" if not np.isnan(avg_staff) else "-")

                # Persian column names for display
                column_rename_dict = {
                    'survey_id': 'شناسه نظرسنجی',
                    'Caller_name': 'نام تماس‌گیرنده',
                    'Deal_ID': 'شناسه معامله',
                    # 'Customer_ID': 'شناسه مشتری',
                    'Customer_name': 'نام مشتری',
                    'Phone_number': 'شماره تماس',
                    'checkout_date': 'تاریخ خروج',
                    'first_call_date': 'تاریخ اولین تماس',
                    'first_call_result': 'نتیجه اولین تماس',
                    'second_call_date': 'تاریخ تماس دوم',
                    'second_call_result': 'نتیجه تماس دوم',
                    'matching_score': 'امتیاز تطابق',
                    'staff_score': 'امتیاز پرسنل',
                    'cleanliness_score': 'امتیاز نظافت',
                    'amneties_score': 'امتیاز امکانات',
                    'NPS_raw_score': 'امتیاز NPS',
                    'comment': 'نظر مشتری',
                    'cleanliness_comment': 'نظر نظافت',
                    'amneties_comment': 'نظر امکانات',
                    'staff_comment': 'نظر پرسنل',
                    'NPS_raw_comment': 'نظر NPS',
                    'open_comment': 'نظر باز',
                    'hamcall_comment': 'نظر هم‌کال',
                    'welcome_pack': 'پک خوشامدگویی',
                    'checkin_score': 'امتیاز ورود',
                    'created_at': 'زمان ایجاد',
                    'updated_at': 'زمان بروزرسانی',
                    'success': 'تماس موفق',
                    'customer_comment': 'نظر مشتری'
                }

                # Select columns to display (in a logical order)
                display_columns = [
                    'Caller_name', 'Deal_ID', 'Customer_name', 'Phone_number',
                    'checkout_date', 'staff_score', 'cleanliness_score', 'amneties_score',
                    'NPS_raw_score', 'customer_comment'
                ]

                # Only keep columns that exist in the DataFrame
                display_columns = [col for col in display_columns if col in all_calls.columns]

                all_calls_fa = all_calls[display_columns].rename(columns=column_rename_dict)

                st.write(all_calls_fa)
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        label="دانلود داده‌ها به صورت CSV",
                        data=convert_df(all_calls_fa.reset_index()),
                        file_name='happy_call_data.csv',
                        mime='text/csv',
                    )

                with col2:
                    st.download_button(
                        label="دانلود داده‌ها به صورت اکسل",
                        data=convert_df_to_excel(all_calls_fa.reset_index()),
                        file_name='happy_call_data.xlsx',
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    )
            else:
                st.info("داده‌ای برای نمایش وجود ندارد.")
    else:
        login()

if __name__ == "__main__":
    main()