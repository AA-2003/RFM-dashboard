import streamlit as st
import os
import sys
import plotly.express as px
import pandas as pd
from streamlit_nej_datepicker import datepicker_component, Config
import jdatetime

# Add path and imports
sys.path.append(os.path.abspath(".."))
from utils.custom_css import apply_custom_css
from utils.load_data import BigQueryExecutor, exacute_query
from utils.constants import COLOR_MAP
from utils.funcs import convert_df, convert_df_to_excel
from utils.auth import login

def to_sql_list(values):
    return ', '.join(f"'{v}'" for v in values)


def customer_analyze():
    col1, col2 = st.columns(2)
    with col1: 
        vip_options = ['Non-VIP', 'Bronze VIP', 'Silver VIP', 'Gold VIP']
        vip_status = st.checkbox("انتخاب تمام وضعیت‌هایVIP", value=True, key='vips_checkbox')
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

        # blacklist filter
        blacklist_options = ['non-blacklist', 'blacklist']
        black_list_status = st.checkbox("انتخاب تمام وضعیت‌های بلک لیست", value=True, key='blacklists_checkbox')
        if black_list_status:
            black_list_values = blacklist_options
        else:
            black_list_values = st.multiselect(
                "انتخاب وضعیت بلک لیست:",
                options=blacklist_options,
                key='blacklist_multiselect_selectbox'
            )
        if black_list_values == []:
            black_list_values = blacklist_options

        # segmentation filter
        semention_options = ['At Risk ✨ Potential', 'At Risk ❤️ Loyal Customers', 'At Risk 👑 Champions',
                            'At Risk 💰 Big Spender', 'At Risk 🔒 Reliable Customers', 'At Risk �️️ Low Value',
                            'At Risk 🧐 Curious Customers', 'Lost ✨ Potential', 'Lost ❤️ Loyal Customers',
                            'Lost 👑 Champions', 'Lost 💰 Big Spender', 'Lost 🔒 Reliable Customers', 'Lost 🗑️ Low Value',
                            'Lost 🧐 Curious Customers', 'New 🧐 Curious Customers',  '✨ Potential', '❤️ Loyal Customers',
                            '👑 Champions', '💰 Big Spender', '🔒 Reliable Customers', '🗑️ Low Value', '🧐 Curious Customers']
        segment_status = st.checkbox("انتخاب تمام سگمنت‌ها", value=True, key='segments_checkbox')
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

        # last check_in filter
        with BigQueryExecutor() as bq:
            max_min_last_check_in = bq.exacute_query("Select max(last_checkin) as max, min(last_checkin) as min from `customerhealth-crm-warehouse.didar_data.RFM_segments`")
            max_min_check_in = bq.exacute_query("Select max(Checkin_date) as max, min(Checkin_date) as min from `customerhealth-crm-warehouse.didar_data.deals`")
        
        st.subheader("انتخاب بازه زمانی آخرین ورود: ")
        last_checkin_config = Config(
            always_open = False,
            dark_mode=True,
            locale="fa",
            minimum_date=jdatetime.date.fromgregorian(date=pd.to_datetime(max_min_last_check_in['min'].iloc[0]).date()),
            maximum_date=jdatetime.date.fromgregorian(date=pd.to_datetime(max_min_last_check_in['max'].iloc[0]).date()),
            color_primary="#ff4b4b",
            color_primary_light="#ff9494",
            selection_mode="range",
            placement="bottom",
            disabled=True
        )
        last_check_in_values = datepicker_component(config=last_checkin_config) 

        # Check if last_check_in_values is not None and has 'from' and 'to'
        if last_check_in_values and 'from' in last_check_in_values and last_check_in_values['from'] is not None:
            last_checkin_start_date = last_check_in_values['from'].togregorian()
        else:
            last_checkin_start_date = pd.to_datetime(max_min_last_check_in['min'].iloc[0]).date()

        if last_check_in_values and 'to' in last_check_in_values and last_check_in_values['to'] is not None:
            last_checkin_end_date = last_check_in_values['to'].togregorian()
        else:
            last_checkin_end_date = pd.to_datetime(max_min_last_check_in['max'].iloc[0]).date()
        
    
        st.subheader("انتخاب بازه زمانی ورود: ")
        checkin_config = Config(
            always_open = False,
            dark_mode=True,
            locale="fa",
            minimum_date=jdatetime.date.fromgregorian(date=pd.to_datetime(max_min_check_in['min'].iloc[0]).date()),
            maximum_date=jdatetime.date.fromgregorian(date=pd.to_datetime(max_min_check_in['max'].iloc[0]).date()),
            color_primary="#ff4b4b",
            color_primary_light="#ff9494",
            selection_mode="range",
            placement="bottom",
            disabled=True
        )
        check_in_values = datepicker_component(config=checkin_config) 

        # Check if check_in_values is not None and has 'from' and 'to'
        if check_in_values and 'from' in check_in_values and check_in_values['from'] is not None:
            checkin_start_date = check_in_values['from'].togregorian()
        else:
            checkin_start_date = pd.to_datetime(max_min_check_in['min'].iloc[0]).date()

        if check_in_values and 'to' in check_in_values and check_in_values['to'] is not None:
            checkin_end_date = check_in_values['to'].togregorian()
        else:
            checkin_end_date = pd.to_datetime(max_min_check_in['max'].iloc[0]).date()
        

    with col2:
        # favorite tip filter 
        products = exacute_query("""
                        SELECT * fROM `customerhealth-crm-warehouse.didar_data.Products`
                        """)
        complex_options = [b for b in products['Building_name'].unique().tolist() if b != 'not_a_building']
        tip_options =  products[products['Building_name']!='not_a_building']['ProductName'].unique().tolist() 
       
        favorite_complex_status = st.checkbox("انتخاب تمام مجتمع ها(مورد علاقه) ", value=True, key='favorite_complex_checkbox')
        if favorite_complex_status:
            favorite_tip_values = tip_options
        else:
            favorite_complex_values = st.multiselect(
                    " انتخاب مجتمع مورد علاقه :",
                    options=complex_options,
                    default=[],  # empty if user doesn’t pick
                    key='favorite_complex_multiselect_selectbox'
                )
            cols = st.columns([1, 4])

            with cols[1]:
                favorite_tip_options = products[(products['Building_name']!='not_a_building')&
                                        (products['Building_name'].isin(favorite_complex_values))]['ProductName'].unique().tolist()
                favorite_tip_status = st.checkbox("انتخاب تمام تیپ ها ", value=True, key='favorite_tips_checkbox')
                if favorite_tip_status:
                    favorite_tip_values = favorite_tip_options
                else:
                    favorite_tip_values = st.multiselect(
                        "انتخاب تیپ مورد علاقه :",
                        options=favorite_tip_options,
                        default=[],  # empty if user doesn’t pick
                        key='favorite_tip_multiselect_selectbox'
                    )
                if favorite_tip_values == []:
                    favorite_tip_values = favorite_tip_options

        # Resident complex        
        resident_complex_status = st.checkbox("انتخاب تمام مجتمع ها(مقیم) ", value=True, key='resident_complex_checkbox')
        if resident_complex_status:
            resident_tip_values = tip_options
        else:
            resident_complex_values = st.multiselect(
                    "انتخاب مجتمع مقیم:",
                    options=complex_options,
                    default=[],  # empty if user doesn’t pick
                    key='resident_complex_multiselect_selectbox'
                )
            cols = st.columns([1, 4])

            with cols[1]:
                resident_tip_options = products[(products['Building_name']!='not_a_building')&
                                        (products['Building_name'].isin(resident_complex_values))]['ProductName'].unique().tolist()
                resident_tip_status = st.checkbox("انتخاب تمام تیپ ها ", value=True, key='resident_tips_checkbox')
                if resident_tip_status:
                    resident_tip_values = resident_tip_options
                else:
                    resident_tip_values = st.multiselect(
                        "انتخاب تیپ مقمم :",
                        options=resident_tip_options,
                        default=[],  # empty if user doesn’t pick
                        key='residen_tip_multiselect_selectbox'
                    )
                if resident_tip_values == []:
                    resident_tip_values = resident_tip_options


        # monthly filter
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
            monthly_limit  = st.number_input(
                    "مینیمم میانگین اقامت برای اینکه مهمان ماهانه محسوب شود را وارد کنید:",
                    min_value=0, value=15, step=1, key='min_nights_filter'
                )

        if montly_values == []:
            montly_values = ["ماهانه", "غیر ماهانه"]
        elif len(montly_values) != 2:
            montly_values = list([montly_values])
        
        # Is staying
        is_staying = st.checkbox('هم مقیم و هم غیرمقیم', value=True, key='is_staying_checkbox')
        if is_staying:
            is_staying_values = ["مقیم","غیر مقیم"]
        else:
            is_staying_values = st.selectbox(
                "انتخاب وضعیت اقامت:",
                options=["مقیم","غیر مقیم"],
                key='is_staying_selectbox'
            )
        if is_staying_values == []:
            is_staying_values = ["مقیم","غیر مقیم"]
        elif len(is_staying_values) != 2:
            is_staying_values = list([is_staying_values])


        # happy call filter
        happycall_status = st.checkbox("فقط مشتریانی که تماس هپی‌کال موفق داشته‌اند؟", value=False, key='happycall_status')
        if happycall_status:
            happycall_value = "(c.customer_nps IS NOT NULL OR  c.customer_amneties_score IS NOT NULL OR c.customer_staff_score IS NOT NULL)"
            cols = st.columns(2)
            with cols[0]:
                nps_min = st.number_input("حداقل میانگین NPS", min_value=-100, max_value=100, value=-100, key='nps_min')
                cleanness_min = st.number_input("حداقل میانگین امتیاز نظافت", min_value=0, max_value=5, value=0, key='cleanness_min')
                personnel_min = st.number_input("حداقل میانگین امتیاز پرسنل", min_value=0, max_value=5, value=0, key='personnel_min')
            with cols[1]:
                nps_max = st.number_input("حداکثر میانگین NPS", min_value=-100, max_value=100, value=100, key='nps_max')
                cleanness_max = st.number_input("حداکثر میانگین امتیاز نظافت", min_value=0, max_value=5, value=5, key='cleanness_max')
                personnel_max = st.number_input("حداکثر میانگین امتیاز پرسنل", min_value=0, max_value=5, value=5, key='personnel_max')
        else:
            happycall_value = ''
            nps_min = None
            nps_max = None
            cleanness_min = None
            cleanness_max = None
            personnel_min = None
            personnel_max = None

        # Build the happy call filter for the query
        if happycall_status:
            happycall_filter = f"""
                AND {happycall_value}
                AND c.customer_nps >= {nps_min} AND c.customer_nps <= {nps_max}
                AND c.customer_amneties_score >= {cleanness_min} AND c.customer_amneties_score <= {cleanness_max}
                AND c.customer_staff_score >= {personnel_min} AND c.customer_staff_score <= {personnel_max}
            """
        else:
            # Only filter on happy_call_count  (i.e., do not require happy call or scores)
            happycall_filter = ""

        query = f"""
        SELECT *
        FROM (
            SELECT *,
                (total_nights / frequency) AS average_stay,
                CASE
                    WHEN (total_nights / frequency) >= {monthly_limit} THEN "ماهانه"
                    ELSE "غیر ماهانه"
                END AS monthly_status,
                CASE
                    WHEN last_checkin < CURRENT_DATE() AND last_checkout > CURRENT_DATE() THEN 'مقیم'
                    ELSE 'غیر مقیم'
                END AS is_staying,
                CASE 
                    WHEN last_name LIKE '%*%' THEN 'blacklist'
                    ELSE 'non-blacklist'
                END AS blacklist_status,
                CASE
                    WHEN last_name LIKE '%💎%' THEN 'Gold VIP'
                    WHEN last_name LIKE '%⭐%' THEN 'Silver VIP'
                    WHEN last_name LIKE '%💠%' THEN 'Bronze VIP'
                    ELSE 'Non-VIP'
                END AS vip_status
            FROM `customerhealth-crm-warehouse.didar_data.RFM_segments`
            WHERE rfm_segment IN ({to_sql_list(segment_values)})
            AND (favorite_product IN ({to_sql_list(favorite_tip_values)}))
        ) t
        WHERE vip_status IN ({to_sql_list(vip_values)})
            AND blacklist_status IN ({to_sql_list(black_list_values)})
            AND monthly_status IN ({to_sql_list(montly_values)})
            AND is_staying IN ({to_sql_list(is_staying_values)})
            AND customer_id IN (
                SELECT DISTINCT d.Customer_id
                FROM `customerhealth-crm-warehouse.didar_data.deals` d
                INNER JOIN `customerhealth-crm-warehouse.didar_data.Products` p
                    ON d.Product_code = p.ProductCode
                INNER JOIN `customerhealth-crm-warehouse.didar_data.RFM_segments` r
                    ON d.Customer_id = r.customer_id
                INNER JOIN `customerhealth-crm-warehouse.CHS.CHS_components` c
                    ON c.Customer_ID = d.Customer_id
                WHERE
                    p.ProductName IN ({to_sql_list(resident_tip_values)})
                    AND d.Checkin_date >= DATE('{checkin_start_date}') AND d.Checkin_date <= DATE('{checkin_end_date}')
                    AND d.Status = 'Won'
                    AND r.last_checkin >= DATE('{last_checkin_start_date}') AND r.last_checkin <= DATE('{last_checkin_end_date}')
                    {happycall_filter}
            )
        """

    if st.button("محاسبه و نمایش RFM", key='calculate_rfm_button'):
        with BigQueryExecutor() as bq_executor:
            data = bq_executor.exacute_query(query)
            CHS_data = bq_executor.exacute_query(f"""
                            select * from `customerhealth-crm-warehouse.CHS.CHS_components`
                            where Customer_ID in ({', '.join(str(i) for i in data['customer_id'].unique())})
                            """)
        
        if data is None or data.empty:
            st.info('هیچ داده ای با فیلترهای اعمال شده وجود ندارد!!!')
        else:
            final_data = pd.merge(data, CHS_data[['Customer_ID', 'customer_nps', 'customer_amneties_score', 'customer_staff_score']], left_on='customer_id', right_on='Customer_ID', how='left').drop(columns='Customer_ID')
            # تبدیل نام ستون‌ها به فارسی برای نمایش
            column_map = {
                'customer_id': 'شناسه مشتری',
                'first_name': 'نام',
                'last_name': 'نام خانوادگی',
                'phone_number': 'شماره تماس',
                'recency': 'تازگی خرید',
                'frequency': 'تعداد خرید',
                'monetary': 'مبلغ کل خرید',
                'total_nights': 'تعداد شب اقامت',
                'last_reserve_date': 'تاریخ آخرین رزرو',
                'last_checkin': 'تاریخ آخرین ورود',
                'last_checkout': 'تاریخ آخرین خروج',
                'favorite_product': 'محصول مورد علاقه',
                'last_product': 'آخرین محصول',
                'rfm_segment': 'سگمنت RFM',
                'average_stay': 'میانگین مدت اقامت',
                'monthly_status': 'وضعیت ماهانه',
                'is_staying': 'وضعیت اقامت',
                'blacklist_status': 'وضعیت بلک‌لیست',
                'vip_status': 'وضعیت VIP',
                'customer_nps': 'امتیاز NPS مشتری',
                'customer_amneties_score': 'امتیاز امکانات مشتری',
                'customer_staff_score': 'امتیاز پرسنل مشتری'
            }
            persian_final_data = final_data.rename(columns=column_map)
            st.write(persian_final_data)
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="دانلود داده‌ها به صورت CSV",
                    data=convert_df(final_data),
                    file_name='rfm_segmentation_with_churn.csv',
                    mime='text/csv',
                )

            with col2:
                st.download_button(
                    label="دانلود داده‌ها به صورت اکسل",
                    data=convert_df_to_excel(final_data),
                    file_name='rfm_segmentation_with_churn.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                )

def main():
    """Main function to run the Streamlit app."""
    st.set_page_config(page_title="تحلیل مشتری", page_icon="📊", layout="wide")
    apply_custom_css()
    st.title("تحلیل مشتری")
    
    # Check data availability and login first
    if 'auth'in st.session_state and st.session_state.auth:    
        role = st.session_state.get('role', 'user')

        if role == 'admin':
            tabs = st.tabs(["دیتای بخش‌بندی مشتریان", "نمودار پراکندگی سه بعدی", "سایر"])
            with tabs[0]:
                customer_analyze()

            with tabs[1]:
                st.subheader("نمودار پراکندگی سه بعدی متریک‌های بخش‌بندی")
                
                with BigQueryExecutor() as bq_exacutor:
                    rfm = bq_exacutor.exacute_query("""
                        select customer_id, first_name, last_name, total_nights, frequency, monetary, rfm_segment
                        from `customerhealth-crm-warehouse.didar_data.RFM_segments`
                        WHERE last_name IS NOT NULL
                    """)
                if rfm is None or rfm.empty:
                    st.info("مشکلی در بارگذاری داده های پیش امده است!!!")
                else:
                    fig3d = px.scatter_3d(
                        rfm,
                        x='total_nights', y='frequency', z='monetary',
                        color='rfm_segment', color_discrete_map=COLOR_MAP,
                        hover_data=['customer_id','first_name','last_name']
                    )
                    fig3d.update_layout(
                        scene=dict(
                            xaxis_title='total_nights',
                            yaxis_title='Frequency',
                            zaxis_title='Monetary'
                        ),
                        legend_title='RFM Segments'
                    )
                    st.plotly_chart(fig3d)
            
            with tabs[2]:
                st.text('در حال اماده سازی ...')
            
        else:
            customer_analyze()
    else:
        login()

if __name__ == "__main__":
    main()