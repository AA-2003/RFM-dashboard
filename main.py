import streamlit as st
from utils.load_data import exacute_queries
from utils.custom_css import apply_custom_css
from utils.auth import login

def format_name(first_name, last_name):
    first = first_name if first_name is not None else ''
    last = last_name if last_name is not None else ''
    return f"{first.strip()} {last.strip()}".strip()

def format_currency(value):
    return f"{value:,.0f} تومان".replace(",", "،")

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
    st.image("static/logo.svg", width=300)
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
            SELECT customer_id, first_name, last_name, frequency, monetary, total_nights
            FROM `customerhealth-crm-warehouse.didar_data.RFM_segments`
            WHERE frequency = (
            SELECT MAX(frequency)
            FROM `customerhealth-crm-warehouse.didar_data.RFM_segments`
            )""",
            """
            SELECT customer_id, first_name, last_name, total_nights, monetary, frequency
            FROM `customerhealth-crm-warehouse.didar_data.RFM_segments`
            WHERE total_nights = (
            SELECT MAX(total_nights)
            FROM `customerhealth-crm-warehouse.didar_data.RFM_segments`
            )""",
            """
            SELECT customer_id, first_name, last_name, frequency, monetary, total_nights, (monetary / frequency) as avg_deal
            FROM `customerhealth-crm-warehouse.didar_data.RFM_segments`
            WHERE (monetary / frequency) = (
                SELECT MAX(monetary / frequency)
                FROM `customerhealth-crm-warehouse.didar_data.RFM_segments`
                WHERE frequency > 0
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
            """,
            """
            SELECT 
                d.Customer_id,
                c.FirstName as first_name,
                c.LastName as last_name,
                SUM(d.Discount) as distcount
            FROM `customerhealth-crm-warehouse.didar_data.deals` d
            LEFT JOIN `customerhealth-crm-warehouse.didar_data.Contacts` c
                ON d.Customer_id = c.Customer_ID
            WHERE d.Status = 'Won'
            AND d.Customer_id != 20700
            GROUP BY d.Customer_id, c.FirstName, c.LastName
            ORDER BY distcount DESC
            LIMIT 1
            """,
        ]

        results = exacute_queries(queries)
        if any(r is None or (hasattr(r, "empty") and r.empty) for r in results):
            st.info("خطایی در بارگزاری داده ها پیش امده است!")
        else:
            number_of_customers = results[0]
            mean_sales = results[1]['avg'].round(-5).values[0]
            most_selling_complex = results[2]
            most_selling_tip = results[3]   
            most_frequent_customer = results[4]
            most_nights_customer = results[5]
            most_ave_deal_customer = results[6]
            most_distcount_customer = results[8]

            # Segments count
            segments = results[7]

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
                mn_nights = int(most_nights_customer['total_nights'].values[0])
                md_first = most_distcount_customer['first_name'].values[0]
                md_last = most_distcount_customer['last_name'].values[0]
                md_dist = most_distcount_customer['distcount'].values[0]/10
                ma_first = most_ave_deal_customer['first_name'].values[0]
                ma_last = most_ave_deal_customer['last_name'].values[0]
                ma_avg = most_ave_deal_customer['avg_deal'].values[0]

                st.metric(
                    "پرخریدترین مشتری",
                    f"{format_name(mf_first, mf_last)}: {mf_freq}"
                )
                st.metric(
                    "مشتری با بیشترین تعداد شب اقامت",
                    f"{format_name(mn_first, mn_last)}: {mn_nights}"
                )
                st.metric(
                    "مشتری با بیشترین میانگین معامله",
                    f"{format_name(ma_first, ma_last)}: {format_currency(ma_avg)}"
                )
                st.metric(
                    "مشتری با بیشترین میزان تخفیف",
                    f"{format_name(md_first, md_last)}: {format_currency(md_dist)}"
                )


            segments['دسته بندی'] = segments['segment']
            segments['تعداد دسته'] = segments['count']
            segments['میانگین پرداختی'] = segments['Average_payment'].round(-3)
            segments['میانگین تعداد شب اقامت'] = segments['Average_number_of_nights'].round(1)
            segments['میانگین تعداد رزرو'] = segments['Average_number_of_reservations'].round(1)
            st.write(segments[['دسته بندی', 'تعداد دسته', 'میانگین پرداختی', 'میانگین تعداد شب اقامت', 'میانگین تعداد رزرو']].sort_values(by='تعداد دسته', ascending=False).reset_index(drop=True))
                

if __name__ == "__main__":
    main()