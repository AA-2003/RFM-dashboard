import streamlit as st
import os
import sys
import plotly.express as px
import pandas as pd

# Add path and imports
sys.path.append(os.path.abspath(".."))
from utils.custom_css import apply_custom_css
from utils.load_data import exacute_query
from utils.constants import COLOR_MAP
from utils.funcs import convert_df, convert_df_to_excel
from utils.auth import login

def to_sql_list(values):
    return ', '.join(f"'{v}'" for v in values)


def filter_tips(selected_complexes, all_tips):
    if len(selected_complexes) == 0:
        return all_tips
    else:
        return [
            tip for tip in all_tips
            if any(complex_name in tip for complex_name in selected_complexes)
        ]


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
        segment_status = st.checkbox("انتخاب تمام بخش‌ها", value=True, key='segments_checkbox')
        if segment_status:
            segment_values = semention_options
        else:
            segment_values = st.multiselect(
                "انتخاب بخش:",
                options=semention_options,
                default=[semention_options[0]],  # Default to first option
                key='segment_multiselect_selectbox'
            )
        if segment_values == []:
            segment_values = semention_options
    
    with col2:
        # tip filter favorite
        with open("data/tip_names.txt", "r", encoding="utf-8") as file:
            tip_options = [line.strip() for line in file if line.strip()]           
    
        complex_status = st.checkbox("(مورد علاقه)انتخاب تمام مجتمع ها ", value=True, key='complex_checkbox')
        complex_options = [
                            "جمهوری", "اقدسیه", "جردن", "کوروش", "ترنج", 
                            "شریعتی (پاسداران)", "وزرا", "کشاورز", "مرزداران", "میرداماد",
                            "ونک", "ولنجک", "پارک وی", "بهشتی", "ولیعصر", "ویلا",
                        ]
        if complex_status:
            tip_values = tip_options
        else:
            complex_values = st.multiselect(
                    " انتخاب مجتمع مورد علاقه :",
                    options=complex_options,
                    default=[],  # empty if user doesn’t pick
                    key='complex_multiselect_selectbox'
                )
            cols = st.columns([1, 4])

            with cols[1]:
                tip_options = filter_tips(complex_values, tip_options)
                tip_status = st.checkbox("انتخاب تمام تیپ ها ", value=True, key='tips_checkbox')
                if tip_status:
                    tip_values = tip_options
                else:
                    tip_values = st.multiselect(
                        "انتخاب تیپ مورد علاقه :",
                        options=tip_options,
                        default=[],  # empty if user doesn’t pick
                        key='tip_multiselect_selectbox'
                    )
                if tip_values == []:
                    tip_values = tip_options

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


        # add happy call filter

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
        AND (favorite_product IN ({to_sql_list(tip_values)}) OR favorite_product IS NULL )
    ) t
    WHERE vip_status IN ({to_sql_list(vip_values)})
        AND blacklist_status IN ({to_sql_list(black_list_values)})
        AND monthly_status IN ({to_sql_list(montly_values)})
        AND is_staying IN ({to_sql_list(is_staying_values)})
        AND favorite_product IS NOT NULL
    """

    if st.button("محاسبه و نمایش RFM", key='calculate_rfm_button'):
        data = exacute_query(query)
        CHS_data = exacute_query(f"""
                        select * from `customerhealth-crm-warehouse.CHS.CHS_components`
                        where Customer_ID in ({', '.join(str(i) for i in data['customer_id'].unique())})
                        """)
        if data is None or data.empty:
            st.info('هیچ داده ای با فیلترهای اعمال شده وجود ندارد!!!')
        else:
            st.write(pd.merge(data, CHS_data[['Customer_ID', 'customer_nps']], left_on='customer_id', right_on='Customer_ID', how='left').drop(columns='Customer_ID'))
            # st.write(data)
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="Download data as CSV",
                    data=convert_df(data),
                    file_name='rfm_segmentation_with_churn.csv',
                    mime='text/csv',
                )

            with col2:
                st.download_button(
                    label="Download data as Excel",
                    data=convert_df_to_excel(data),
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
                rfm = exacute_query("""
                    select customer_id, first_name, last_name, total_nights, frequency, monetary, rfm_segment
                    from `customerhealth-crm-warehouse.didar_data.RFM_segments`
                    WHERE last_name IS NOT NULL
                """)
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