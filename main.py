import streamlit as st
# import pandas as pd
from utils.load_data import exacute_queries
from utils.custom_css import apply_custom_css
from utils.auth import login



def main() -> None:
    """
    Main function that creates a Streamlit dashboard for Tehran Mobel sales analysis.
    """
    st.set_page_config(
        page_title="داشبورد تحلیل فروش و مشتری تهران مبله", 
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    apply_custom_css()
    st.title("داشبورد تحلیل فروش و مشتری تهران مبله")

    if 'auth' not in st.session_state or not st.session_state.auth:
        login()
    else:
        tabs = st.columns([1,1])
        
        queries = [
            "SELECT COUNT(customer_id) as count FROM `customerhealth-crm-warehouse.didar_data.RFM_segments`",
            "SELECT AVG(monetary) as avg FROM `customerhealth-crm-warehouse.didar_data.RFM_segments`",
            """
            SELECT customer_id, first_name, last_name, frequency
            FROM `customerhealth-crm-warehouse.didar_data.RFM_segments`
            WHERE frequency = (
            SELECT MAX(frequency)
            FROM `customerhealth-crm-warehouse.didar_data.RFM_segments`
            )""",
            """
            SELECT customer_id, first_name, last_name, total_nights
            FROM `customerhealth-crm-warehouse.didar_data.RFM_segments`
            WHERE total_nights = (
            SELECT MAX(total_nights)
            FROM `customerhealth-crm-warehouse.didar_data.RFM_segments`
            )""",
            """
            SELECT  rfm_segment as segment,
                    COUNT(customer_id) as count,
                    AVG(monetary) as Average_payment,
                    SUM(total_nights)/SUM(frequency)  as Average_number_of_nights,
                    AVG(frequency)  as Average_number_of_reservations
                                 
            FROM `customerhealth-crm-warehouse.didar_data.RFM_segments`
            WHERE favorite_product IS NOT NULL
            GROUP BY rfm_segment;     
            """
        ]

        if None in queries:
            st.info("خطایی در بارگزاری داده ها پیش امده است!")
        else:
            results = exacute_queries(queries)
            
            number_of_customers = results[0]
            mean_sales = results[1]['avg'].round(-5).values[0]
            most_frequent_customer = results[2]
            most_nights_customer = results[3]
            # Segments count
            segments = results[4]

            if number_of_customers is None or mean_sales is None or most_frequent_customer is None or most_nights_customer is None is None or segments is None:
                st.warning('خطایی در بارگذاری داده پیش امده است!')
            
            else: 
                with tabs[0]:
                    st.metric("تعداد مشتریان", number_of_customers['count'].values[0])
                    st.metric("میانگین فروش به ازای هر مشتری", f"{mean_sales:,.0f} ریال".replace(",", "،"))
                with tabs[1]:
                    st.metric("پرخریدترین مشتری", f"{most_frequent_customer['first_name'].values[0] if most_frequent_customer['first_name'].values[0] is not None else '  '} {most_frequent_customer['last_name'].values[0]}: {most_frequent_customer['frequency'].values[0]}")
                    st.metric("مشتری بابیشترین شب اقامت", f"{most_nights_customer['first_name'].values[0] if most_nights_customer['first_name'].values[0] is not None else '  '} {most_nights_customer['last_name'].values[0]}: {most_nights_customer['total_nights'].values[0]}")
                
                
                segments['دسته بندی'] = segments['segment']
                segments['تعداد دسته'] = segments['count']
                segments['میانگین پرداختی'] = segments['Average_payment'].round(-3)
                segments['میانگین تعداد شب اقامت'] = segments['Average_number_of_nights'].round(1)
                segments['میانگین تعداد رزرو'] = segments['Average_number_of_reservations'].round(1)
                st.write(segments[['دسته بندی', 'تعداد دسته', 'میانگین پرداختی', 'میانگین تعداد شب اقامت', 'میانگین تعداد رزرو']])       
    return

if __name__ == "__main__":
    main()