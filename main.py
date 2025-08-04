import streamlit as st
# import pandas as pd
from utils.load_data import exacute_queries, exacute_query
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
            """SELECT COUNT(customer_id) as count FROM `customerhealth-crm-warehouse.didar_data.RFM_segments`
            WHERE favorite_product IS NOT NULL
            AND favorite_product NOT LIKE '%صبحانه%' 
            AND favorite_product NOT LIKE '%خودرو%'
            """,
            "SELECT AVG(monetary) as avg FROM `customerhealth-crm-warehouse.didar_data.RFM_segments`",
            """
            SELECT 
                c.complex,
                COUNT(*) AS sales_count
            FROM `customerhealth-crm-warehouse.didar_data.deals` d
            LEFT JOIN `customerhealth-crm-warehouse.didar_data.Products` p
                ON d.Product_code = p.ProductCode
            LEFT JOIN (
                SELECT 
                    ProductCode,
                    CASE
                        WHEN ProductName LIKE '%جمهوری%' THEN 'جمهوری'
                        WHEN ProductName LIKE '%اقدسیه%' THEN 'اقدسیه'
                        WHEN ProductName LIKE '%جردن%' THEN 'جردن'
                        WHEN ProductName LIKE '%شریعتی%' THEN 'شریعتی (پاسداران)'
                        WHEN ProductName LIKE '%پاسداران%' THEN 'شریعتی (پاسداران)'
                        WHEN ProductName LIKE '%وزرا%' THEN 'وزرا'
                        WHEN ProductName LIKE '%کشاورز%' THEN 'کشاورز'
                        WHEN ProductName LIKE '%مرزداران%' THEN 'مرزداران'
                        WHEN ProductName LIKE '%میرداماد%' THEN 'میرداماد'
                        WHEN ProductName LIKE '%ونک%' THEN 'ونک'
                        WHEN ProductName LIKE '%ولنجک%' THEN 'ولنجک'
                        WHEN ProductName LIKE '%پارک وی%' THEN 'پارک وی'
                        WHEN ProductName LIKE '%بهشتی%' THEN 'بهشتی'
                        WHEN ProductName LIKE '%ولیعصر%' THEN 'ولیعصر'
                        WHEN ProductName LIKE '%ویلا%' THEN 'ویلا'
                        WHEN ProductName LIKE '%کوروش%' THEN 'کوروش'
                        WHEN ProductName LIKE '%ترنج%' THEN 'ترنج'
                        ELSE NULL
                    END AS complex
                FROM `customerhealth-crm-warehouse.didar_data.Products`
            ) c
            ON d.Product_code = c.ProductCode
            WHERE c.complex IS NOT NULL
            GROUP BY c.complex
            ORDER BY sales_count DESC
            """,
            """
            SELECT 
                p.ProductName AS tip,
                COUNT(*) AS sales_count
            FROM `customerhealth-crm-warehouse.didar_data.deals` d
            LEFT JOIN `customerhealth-crm-warehouse.didar_data.Products` p
                ON d.Product_code = p.ProductCode
            WHERE p.ProductName IS NOT NULL
            GROUP BY p.ProductName
            ORDER BY sales_count DESC
            """,
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
            SELECT customer_id, first_name, last_name, monetary
            FROM `customerhealth-crm-warehouse.didar_data.RFM_segments`
            WHERE monetary = (
            SELECT MAX(monetary)
            FROM `customerhealth-crm-warehouse.didar_data.RFM_segments`
            )
            """,
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
            most_selling_complex = results[2]
            most_selling_tip = results[3]
            most_frequent_customer = results[4]
            most_nights_customer = results[5]
            most_monetary_customer = results[6]
            # Segments count
            segments = results[7]

            if number_of_customers is None or mean_sales is None or most_frequent_customer is None or most_nights_customer is None is None or segments is None:
                st.warning('خطایی در بارگذاری داده پیش امده است!')
            
            else: 
                def format_name(first_name, last_name):
                    first = first_name if first_name is not None else ''
                    last = last_name if last_name is not None else ''
                    return f"{first.strip()} {last.strip()}".strip()

                def format_currency(value):
                    return f"{value:,.0f} تومان".replace(",", "،")

                with tabs[0]:
                    st.metric("تعداد مشتریان", number_of_customers['count'].values[0])
                    st.metric("میانگین فروش به ازای هر مشتری", format_currency(mean_sales))
                    st.metric("پرفروش ترین مجتمع", most_selling_complex['complex'].values[0])
                    st.metric("پرفروش ترین تیپ", most_selling_tip['tip'].values[0])

                with tabs[1]:
                    mf_first = most_frequent_customer['first_name'].values[0]
                    mf_last = most_frequent_customer['last_name'].values[0]
                    mf_id = most_frequent_customer['customer_id'].values[0]
                    mf_freq = most_frequent_customer['frequency'].values[0]
                    mn_first = most_nights_customer['first_name'].values[0]
                    mn_last = most_nights_customer['last_name'].values[0]
                    mn_nights = most_nights_customer['total_nights'].values[0]
                    mm_first = most_monetary_customer['first_name'].values[0]
                    mm_last = most_monetary_customer['last_name'].values[0]
                    mm_monetary = most_monetary_customer['monetary'].values[0]

                    st.metric(
                        "پرخریدترین مشتری",
                        f"{mf_id} - {format_name(mf_first, mf_last)}: {mf_freq}"
                    )
                    st.metric(
                        "مشتری با بیشترین تعداد شب اقامت",
                        f"{format_name(mn_first, mn_last)}: {mn_nights}"
                    )
                    st.metric(
                        "ولخرج ترین مشتری",
                        f"{format_name(mm_first, mm_last)}: {format_currency(mm_monetary)}"
                    )

                segments['دسته بندی'] = segments['segment']
                segments['تعداد دسته'] = segments['count']
                segments['میانگین پرداختی'] = segments['Average_payment'].round(-3)
                segments['میانگین تعداد شب اقامت'] = segments['Average_number_of_nights'].round(1)
                segments['میانگین تعداد رزرو'] = segments['Average_number_of_reservations'].round(1)
                st.write(segments[['دسته بندی', 'تعداد دسته', 'میانگین پرداختی', 'میانگین تعداد شب اقامت', 'میانگین تعداد رزرو']].sort_values(by='تعداد دسته', ascending=False).reset_index(drop=True))
                

if __name__ == "__main__":
    main()