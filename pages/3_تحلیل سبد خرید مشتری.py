import streamlit as st
import os
import sys
import plotly.express as px
import time

# Add path and imports
sys.path.append(os.path.abspath(".."))
from utils.custom_css import apply_custom_css
from utils.load_data import exacute_query
from utils.auth import login

def to_sql_list(values):
    return ', '.join(f"'{v}'" for v in values)

def filter_tips(selected_complexes, all_tips):
    return [
        tip for tip in all_tips
        if any(complex_name in tip for complex_name in selected_complexes)
    ]


def main():
    st.set_page_config(page_title="تحلیل کمپین", page_icon="📊", layout="wide")
    apply_custom_css()
    st.subheader("تحلیل سبد خرید مشتری بر اساس سگمنت‌ها و محصولات")    

    # Check data availability and login first
    if 'auth' in st.session_state and st.session_state.auth:  
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
            # tip filter  
            with open("data/tip_names.txt", "r", encoding="utf-8") as file:
                tip_options = [line.strip() for line in file if line.strip()]           
        
            complex_status = st.checkbox("انتخاب تمام مجتمع ها ", value=True, key='complex_checkbox')
            complex_options = [
                            "جمهوری",
                            "اقدسیه",
                            "جردن",
                            "شریعتی (پاسداران)",
                            "وزرا",
                            "کشاورز",
                            "مرزداران",
                            "میرداماد",
                            "ونک",
                            "ولنجک",
                            "پارک وی",
                            "بهشتی",
                            "ولیعصر",
                            "ویلا",
                            "کوروش",
                            "ترنج"
                        ]
            if complex_status:
                tip_values = tip_options
            else:
                complex_values = st.multiselect(
                        "Tip انتخاب وضعیت :",
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
                            "Tip انتخاب وضعیت :",
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
        ######################
        # add date filter
        ######################

        query = f"""
        SELECT customer_id
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
        ) t
        WHERE vip_status IN ({to_sql_list(vip_values)})
            AND blacklist_status IN ({to_sql_list(black_list_values)})
            AND monthly_status IN ({to_sql_list(montly_values)})
            AND is_staying IN ({to_sql_list(is_staying_values)})
        """
        
        if st.button("محاسبه و نمایش RFM", key='calculate_rfm_button'):
            ids = exacute_query(query)
            st.write(type(ids.loc[0, 'customer_id']))
            # ids['customer_id'] = ids['customer_id'].astype(str)
            deals_query =f"""SELECT * FROM `customerhealth-crm-warehouse.didar_data.deals`
                            WHERE Customer_id IN ({to_sql_list(ids['customer_id'].unique().tolist())})
                            LIMIT 100"""
            filtered_deals = exacute_query(deals_query)
            st.write(filtered_deals)
#                 # Get customers in selected clusters and VIP statuses
    #                 customers_in_clusters = rfm_data[(rfm_data['RFM_segment_label'].isin(selected_clusters)) &
    #                                                 (rfm_data['VIP Status'].isin(selected_vips_portfolio))]['Code'].unique()
    #                 # Filter deals data
    #                 deals_filtered = data_filtered_by_blacklist[data_filtered_by_blacklist[CUSTOMERID].isin(customers_in_clusters)]

    #                 if deals_filtered.empty:
    #                     st.warning("هیچ معامله‌ای با این شرایط پیدا نشد")
    #                 else:
    #                     # Frequency distribution
    #                     frequency_distribution = deals_filtered.groupby(PRODUCTTITLE).size().reset_index(name='Frequency')

    #                     # Monetary distribution
    #                     monetary_distribution = deals_filtered.groupby(PRODUCTTITLE)[DEALVALUE].sum().reset_index()

    #                     # Plot Frequency Distribution
    #                     st.subheader("توزیع فراوانی معاملات روی این محصولات")
    #                     fig_freq = px.bar(
    #                         frequency_distribution,
    #                         x=PRODUCTTITLE,
    #                         y='Frequency',
    #                         title='توزیع فراوانی',
    #                         labels={PRODUCTTITLE: 'Product', 'Frequency': 'Number of Purchases'},
    #                         text='Frequency'
    #                     )
    #                     fig_freq.update_traces(textposition='outside')
    #                     st.plotly_chart(fig_freq)

    #                     # Plot Monetary Distribution
    #                     st.subheader("توزیع ارزش مالی معاملات روی این محصولات")
    #                     fig_monetary = px.bar(
    #                         monetary_distribution,
    #                         x=PRODUCTTITLE,
    #                         y=DEALVALUE,
    #                         title='توزیع مالی',
    #                         labels={PRODUCTTITLE: 'Product', DEALVALUE: 'Total Monetary Value'},
    #                         text=DEALVALUE
    #                     )
    #                     fig_monetary.update_traces(textposition='outside')
    #                     st.plotly_chart(fig_monetary)

    #                     # Customer Details Table
    #                     st.subheader("Customer Details")
    #                     successful_deals = deals_filtered[deals_filtered[DEALSTATUS] == 'Won']

    #                     customer_nights = successful_deals.groupby([CUSTOMERID, PRODUCTTITLE])['nights'].sum().unstack(fill_value=0)

    #                     customer_details = rfm_data[rfm_data['Code'].isin(customers_in_clusters)][['Code', 'Name', 'VIP Status','average stay','Is staying', 'RFM_segment_label', 'Recency', 'Frequency', 'Monetary']]
    #                     customer_details = customer_details.merge(customer_nights, left_on='Code', right_index=True, how='inner').fillna(0)
                        
    #                     st.write(customer_details)
    #                     # Download buttons
    #                     col1, col2 = st.columns(2)
    #                     with col1:
    #                         st.download_button(
    #                             label="Download data as CSV",
    #                             data=convert_df(customer_details),
    #                             file_name='portfolio_analysis.csv',
    #                             mime='text/csv',
    #                         )
    #                     with col2:
    #                         st.download_button(
    #                             label="Download data as Excel",
    #                             data=convert_df_to_excel(customer_details),
    #                             file_name='portfolio_analysis.xlsx',
    #                             mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    #                         )
        
    else:
        login()

if __name__ == "__main__":
    main()