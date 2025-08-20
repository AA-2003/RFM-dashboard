import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime, timedelta
import plotly.express as px
from streamlit_nej_datepicker import datepicker_component, Config
import jdatetime

# Add parent directory to sys.path for utility imports
sys.path.append(os.path.abspath(".."))
from utils.custom_css import apply_custom_css
from utils.auth import login
from utils.load_data import exacute_query
from utils.funcs import convert_df, convert_df_to_excel

def get_first_successful_deal_date(selected_sellers):
    """
    Fetches the first successful deal date for each customer from BigQuery, filtered by date and sellers.
    Returns a DataFrame with columns: Customer_id, first_successful_deal_date, DealExpert
    """
    query = """
        WITH first_deals AS (
            SELECT
                Customer_id,
                DealExpert,
                DealDate,
                ROW_NUMBER() OVER (PARTITION BY Customer_id ORDER BY DealDate ASC) as rn
            FROM `customerhealth-crm-warehouse.didar_data.deals`
            WHERE
                Status = 'Won'
        )
        SELECT
            Customer_id,
            DealExpert,
            DealDate AS first_successful_deal_date
        FROM first_deals
        WHERE rn = 1
    """
    result = exacute_query(query)
    # Filter by selected sellers if provided
    if selected_sellers:
        result = result[result['DealExpert'].isin(selected_sellers)]
    return result

def pct_diff(new_val, old_val):
    # Calculate percent difference, return None if old_val is None or zero
    if old_val in [None, 0]:
        return None
    return f"{((new_val - old_val)/abs(old_val)*100):.2f}%"

@st.cache_data(ttl=600, show_spinner=False)
def seller_analys(deals, prev_deals, df_first_deals, start_date_str, end_date_str, horizontal=True) -> pd.DataFrame:
    # Calculate main KPIs for the seller(s)
    total_deals = len(deals)
    successful_deals = deals[deals['Status'] == 'Won']
    successful_deals_count = len(successful_deals)
    success_rate = (successful_deals_count / total_deals * 100) if total_deals > 0 else 0
    avg_deal_value = (deals['DealValue']/10).mean() if not deals.empty else 0

    # Calculate new and returning customers
    if not deals.empty:
        new_customers = df_first_deals[
            (df_first_deals['first_successful_deal_date'] >= start_date_str) &
            (df_first_deals['first_successful_deal_date'] <= end_date_str)
        ]['Customer_id'].nunique()
        returning_customers = deals['Customer_id'].nunique() - new_customers
    else:
        new_customers = 0
        returning_customers = 0

    # Calculate average nights and extension rate
    avg_nights = deals['Nights'].mean() if 'Nights' in deals.columns and not deals.empty else 0
    if 'DealType' in deals.columns and not deals.empty:
        extention_rate = deals[deals['DealType'] == 'Renewal'].shape[0] / deals.shape[0] * 100
    else:
        extention_rate = 0

    # Calculate previous period KPIs
    prev_total_deals = len(prev_deals)
    prev_successful_deals = prev_deals[prev_deals['Status'] == 'Won'] if not prev_deals.empty else []
    prev_successful_deals_count = len(prev_successful_deals)
    prev_success_rate = (prev_successful_deals_count / prev_total_deals * 100) if prev_total_deals > 0 else 0
    prev_avg_deal_value = (prev_deals['DealValue']/10).mean() if not prev_deals.empty else 0
    prev_avg_nights = prev_deals['Nights'].mean() if 'Nights' in prev_deals.columns and not prev_deals.empty else 0
    if 'DealType' in prev_deals.columns and not prev_deals.empty:
        prev_extention_rate = prev_deals[prev_deals['DealType'] == 'Renewal'].shape[0] / prev_deals.shape[0] * 100
    else:
        prev_extention_rate = 0

    # Display KPIs in horizontal or vertical layout
    if horizontal:
        st.subheader("شاخص‌های کلیدی عملکرد (KPI)")
        colKPI1, colKPI2, colKPI3, colKPI4 = st.columns(4)
        colKPI1.metric(
            "تعداد کل معاملات",
            f"{total_deals}",
            pct_diff(total_deals, prev_total_deals)
        )
        colKPI2.metric(
            "تعداد معاملات موفق",
            f"{successful_deals_count}",
            pct_diff(successful_deals_count, prev_successful_deals_count)
        )
        colKPI3.metric(
            "نرخ موفقیت (%)",
            f"{success_rate:.2f}%",
            pct_diff(success_rate, prev_success_rate)
        )
        colKPI4.metric(
            "میانگین ارزش معامله",
            f"{avg_deal_value:,.0f}",
            pct_diff(avg_deal_value, prev_avg_deal_value)
        )
        colKPI5, colKPI6, colKPI7, colKPI8 = st.columns(4)
        colKPI5.metric("مشتریان جدید", f"{new_customers}")
        colKPI6.metric("مشتریان بازگشتی", f"{returning_customers}")
        colKPI7.metric(
            "میانگین شب اقامت",
            f"{avg_nights:.2f}",
            pct_diff(avg_nights, prev_avg_nights)
        )
        colKPI8.metric(
            "نرخ تمدید",
            f"{extention_rate:.2f}%",
            pct_diff(extention_rate, prev_extention_rate)
        )
    else:
        # Vertical layout for KPIs
        st.metric("تعداد کل معاملات", f"{total_deals}", pct_diff(total_deals, prev_total_deals))
        st.metric("تعداد معاملات موفق", f"{successful_deals_count}", pct_diff(successful_deals_count, prev_successful_deals_count))
        st.metric("نرخ موفقیت (%)", f"{success_rate:.2f}%", pct_diff(success_rate, prev_success_rate))
        st.metric("میانگین ارزش معامله", f"{avg_deal_value:,.0f}", pct_diff(avg_deal_value, prev_avg_deal_value))
        st.metric("مشتریان جدید", f"{new_customers}")
        st.metric("مشتریان بازگشتی", f"{returning_customers}")
        st.metric("میانگین شب اقامت", f"{avg_nights:.2f}", pct_diff(avg_nights, prev_avg_nights))
        st.metric("نرخ تمدید", f"{extention_rate:.2f}%", pct_diff(extention_rate, prev_extention_rate))
    st.write('---')

    # Customer cluster analysis
    customer_ids = deals['Customer_id'].values.tolist()
    if customer_ids:
        # Prepare customer IDs for SQL query
        customer_ids_list = ', '.join(str(int(id)) for id in customer_ids)
        # Query for RFM segments and customer scores
        cluster_query = f"""
            SELECT *
            FROM `customerhealth-crm-warehouse.didar_data.RFM_segments` r
            INNER JOIN (
                SELECT Customer_ID, customer_nps, customer_amneties_score, customer_staff_score
                FROM `customerhealth-crm-warehouse.CHS.CHS_components`
            ) c
            ON c.Customer_ID = r.customer_id
            WHERE r.customer_id IN ({customer_ids_list})
        """
        cluster_df = exacute_query(cluster_query)
        # If cluster data exists and has rfm_segment column, show segment distribution
        if cluster_df is not None and not cluster_df.empty and 'rfm_segment' in cluster_df.columns:
            segment_counts = cluster_df['rfm_segment'].value_counts().reset_index()
            segment_counts.columns = ['rfm_segment', 'count']
            # Bar chart for customer segment distribution
            cluster_chart = px.bar(
                segment_counts,
                x='rfm_segment',
                y='count',
                title='توزیع سگمنت مشتریان',
                labels={'rfm_segment': 'سگمنت', 'count': 'تعداد'},
                text='count',
                color='rfm_segment',
            )
            cluster_chart.update_layout(xaxis_title='سگمنت', yaxis_title='تعداد')
            st.plotly_chart(cluster_chart)
        else:
            st.info("داده‌ای برای نمایش سگمنت مشتریان وجود ندارد.")
        # Show customer details table
        st.subheader("جزئیات مشتریان")
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
            'customer_nps': 'امتیاز NPS مشتری',
            'customer_amneties_score': 'امتیاز امکانات مشتری',
            'customer_staff_score': 'امتیاز پرسنل مشتری'
        }
        persian_cluster_df = cluster_df.rename(columns=column_map) if cluster_df is not None else pd.DataFrame()
        st.write(persian_cluster_df.drop(columns='Customer_ID_1'))
    else:
        st.info("هیچ مشتری‌ای برای این فروشنده وجود ندارد.")
        persian_cluster_df = pd.DataFrame()
    return persian_cluster_df

def main():
    st.set_page_config(page_title="تحلیل فروشنده", page_icon="📊", layout="wide")
    apply_custom_css()
    st.header("تحلیل فروشنده")
    
    # Check authentication before proceeding
    if 'auth' in st.session_state and st.session_state.auth:
        col1, _, col2, *_ = st.columns([5, 1, 5, 1, 1])

        # --- Date filter section ---
        with col1:
            st.subheader("انتخاب بازه زمانی تاریخ انجام معامله: ")
            config = Config(
                always_open=True,
                dark_mode=True,
                locale="fa",
                maximum_date=jdatetime.date.today() - jdatetime.timedelta(days=3),
                color_primary="#ff4b4b",
                color_primary_light="#ff9494",
                selection_mode="range",
                placement="bottom",
                disabled=False
            )
            res = datepicker_component(config=config)

            # If user selected a start date, use it; otherwise, get min date from DB
            if res and 'from' in res and res['from'] is not None:
                start_date = res['from'].togregorian()
            else:
                query = "select min(DealCreateDate) as min_deal_date from `customerhealth-crm-warehouse.didar_data.deals`"
                result = exacute_query(query)
                start_date = result['min_deal_date'].iloc[0].date()

            # If user selected an end date, use it; otherwise, get max date from DB
            if res and 'to' in res and res['to'] is not None:
                end_date = res['to'].togregorian()
            else:
                query = "select max(DealCreateDate) as max_deal_date from `customerhealth-crm-warehouse.didar_data.deals`"
                result = exacute_query(query)
                end_date = result['max_deal_date'].iloc[0].date()

        # --- Sellers filter section ---
        with col2:
            sellers_query = """
                select DealExpert from `customerhealth-crm-warehouse.didar_data.deals`
                group by DealExpert
            """
            sellers_options = exacute_query(sellers_query)['DealExpert'].values.tolist()
            select_all = st.checkbox("انتخاب همه فروشنده‌ها", value=True, key='sellers_select_all_checkbox')
            if select_all:
                selected_sellers = sellers_options
            else:
                selected_sellers = st.multiselect(
                    "انتخاب  فروشنده:",
                    options=sellers_options,
                    default=[],
                    key='sellers_multiselect_box'
                )

        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")

        if st.button("محاسبه و نمایش", key='calculate_rfm_button'):
            # Get first successful deal date for each customer for selected sellers
            df_first_deals = get_first_successful_deal_date(selected_sellers)
            sellers_list = ','.join([f"'{seller}'" for seller in selected_sellers])
            # Query deals for selected sellers and date range
            deals_query = f"""
                SELECT * FROM `customerhealth-crm-warehouse.didar_data.deals`
                WHERE DealExpert IN ({sellers_list})  
                AND DealCreateDate BETWEEN DATE('{start_date_str}') AND DATE('{end_date_str}')
            """
            deals = exacute_query(deals_query)
            if deals is None or deals.empty:
                st.info('هیچ داده‌ای برای بازه زمانی ثبت شده وجود ندارد!!!')
                return

            # Calculate previous period (same length, immediately before current period)
            start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
            period_days = (end_dt - start_dt).days + 1

            prev_end_dt = start_dt - timedelta(days=1)
            prev_start_dt = prev_end_dt - timedelta(days=period_days - 1)
            prev_start_date_str = prev_start_dt.strftime("%Y-%m-%d")
            prev_end_date_str = prev_end_dt.strftime("%Y-%m-%d")

            # Query deals for previous period
            prev_deals_query = f"""
                SELECT * FROM `customerhealth-crm-warehouse.didar_data.deals`
                WHERE DealExpert IN ({sellers_list})  
                AND DealCreateDate BETWEEN DATE('{prev_start_date_str}') AND DATE('{prev_end_date_str}')
            """
            prev_deals = exacute_query(prev_deals_query)

            if not selected_sellers:
                st.warning('حداقل یک فروشنده را انتخاب کنید!')
            match len(selected_sellers):
                case 1:
                    # Single seller analysis
                    cluster_df = seller_analys(
                        deals, prev_deals, df_first_deals, start_date_str, end_date_str
                    )
                    if not cluster_df.empty:
                        cols = st.columns(2)
                        with cols[0]:
                            st.download_button(
                                label="دانلود داده‌ها به صورت CSV",
                                data=convert_df(cluster_df),
                                file_name='rfm_segmentation_with_churn.csv',
                                mime='text/csv',
                            )
                        with cols[1]:
                            st.download_button(
                                label="دانلود داده‌ها به صورت اکسل",
                                data=convert_df_to_excel(cluster_df),
                                file_name='rfm_segmentation_with_churn.xlsx',
                                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                            )
                case 2:
                    # Compare two sellers side by side
                    col1, col2 = st.columns(2)
                    seller1, seller2 = selected_sellers
                    with col1:
                        st.write(seller1)
                        cluster_df = seller_analys(
                            deals[deals['DealExpert'] == seller1],
                            prev_deals[prev_deals['DealExpert'] == seller1],
                            df_first_deals, start_date_str, end_date_str, horizontal=False
                        )
                        if not cluster_df.empty:
                            cols = st.columns(2)
                            with cols[0]:
                                st.download_button(
                                    label="دانلود داده‌ها به صورت CSV",
                                    data=convert_df(cluster_df),
                                    file_name='rfm_segmentation_with_churn.csv',
                                    mime='text/csv',
                                    key=f"download_csv_{seller1}"
                                )
                            with cols[1]:
                                st.download_button(
                                    label="دانلود داده‌ها به صورت اکسل",
                                    data=convert_df_to_excel(cluster_df),
                                    file_name='rfm_segmentation_with_churn.xlsx',
                                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                    key=f"download_excel_{seller1}"
                                )
                    with col2:
                        st.write(seller2)
                        persian_cluster_df = seller_analys(
                            deals[deals['DealExpert'] == seller2],
                            prev_deals[prev_deals['DealExpert'] == seller2],
                            df_first_deals, start_date_str, end_date_str, horizontal=False
                        )
                        if not persian_cluster_df.empty:
                            cols = st.columns(2)
                            with cols[0]:
                                st.download_button(
                                    label="دانلود داده‌ها به صورت CSV",
                                    data=convert_df(persian_cluster_df),
                                    file_name='rfm_segmentation_with_churn.csv',
                                    mime='text/csv',
                                    key=f"download_csv_{seller2}"
                                )
                            with cols[1]:
                                st.download_button(
                                    label="دانلود داده‌ها به صورت اکسل",
                                    data=convert_df_to_excel(persian_cluster_df),
                                    file_name='rfm_segmentation_with_churn.xlsx',
                                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                    key=f"download_excel_{seller2}"
                                )
                case _:
                    # Compare more than two sellers (summary table and charts)
                    metrics = []
                    # Collect all unique customer_ids for all selected sellers
                    all_customer_ids = deals[deals['DealExpert'].isin(selected_sellers)]['Customer_id'].unique().tolist()
                    if all_customer_ids:
                        all_customer_ids_list = ', '.join(str(int(id)) for id in all_customer_ids)
                        cluster_query = f"""
                            select * from `customerhealth-crm-warehouse.didar_data.RFM_segments`
                            where customer_id in ({all_customer_ids_list})
                        """
                        all_cluster_df = exacute_query(cluster_query)
                    else:
                        all_cluster_df = pd.DataFrame()
                    for seller in selected_sellers:
                        seller_deals = deals[deals['DealExpert'] == seller]
                        seller_successful = seller_deals[seller_deals['Status'] == 'Won']
                        total_deals = len(seller_deals)
                        successful_deals = len(seller_successful)
                        # Calculate renewal rate, avoid division by zero
                        renewal_rate = len(seller_deals[seller_deals['DealType'] == "Renewal"]) / successful_deals * 100 if successful_deals != 0 else 0
                        total_value = seller_deals[seller_deals['Status'] == 'Won']['DealValue'].sum() / 10 if not seller_deals.empty else 0
                        avg_value = seller_deals[seller_deals['Status'] == 'Won']['DealValue'].mean() / 10 if not seller_deals.empty else 0
                        success_rate = (successful_deals / total_deals * 100) if total_deals > 0 else 0
                        total_nights = seller_deals['Nights'].sum() if 'Nights' in seller_deals.columns and not seller_deals.empty else 0
                        # Calculate new customers for this seller
                        if (
                            df_first_deals is not None
                            and not seller_deals.empty
                            and 'first_successful_deal_date' in df_first_deals.columns
                        ):
                            customer_ids = seller_deals['Customer_id'].unique().tolist()
                            seller_first_deals = df_first_deals[
                                (df_first_deals['DealExpert'] == seller) &
                                (df_first_deals['first_successful_deal_date'] >= start_date_str) &
                                (df_first_deals['first_successful_deal_date'] <= end_date_str)
                            ]
                            new_customers = seller_first_deals['Customer_id'].nunique()
                        else:
                            new_customers = 0
                        # Find top segment for this seller
                        customer_ids = seller_deals['Customer_id'].unique().tolist()
                        if customer_ids and not all_cluster_df.empty and 'rfm_segment' in all_cluster_df.columns:
                            seller_cluster_df = all_cluster_df[all_cluster_df['customer_id'].isin(customer_ids)]
                            if not seller_cluster_df.empty:
                                seg_counts = seller_cluster_df['rfm_segment'].value_counts()
                                top_segment = seg_counts.idxmax()
                            else:
                                top_segment = "-"
                        else:
                            top_segment = "-"
                        metrics.append({
                            "فروشنده": seller,
                            "تعداد کل معاملات": total_deals,
                            "تعداد معاملات موفق": successful_deals,
                            "نرخ موفقیت": f"{success_rate:.2f}",
                            "جمع تعداد شب": int(total_nights),
                            "ارزش کل معاملات": total_value,
                            "میانگین ارزش معاملات": avg_value,
                            "نرخ تمدید": renewal_rate,
                            "تعداد مشتریان جدید": new_customers,
                            "سگمنت غالب": top_segment
                        })
                    metrics_df = pd.DataFrame(metrics)
                    st.subheader("مقایسه فروشندگان (جدول شاخص‌ها)")
                    st.dataframe(metrics_df.sort_values(by='تعداد معاملات موفق', ascending=False
                                        ).reset_index(drop=True), use_container_width=True)
                    # Prepare chart titles based on number of sellers
                    if len(metrics_df) > 10:
                        titles = [
                            "تعداد معاملات موفق هر فروشنده(10 نفر برتر)",
                            "میزان فروش هر فروشنده(10 نفر برتر)"
                        ]
                    else:
                        titles = [
                            "تعداد معاملات موفق هر فروشنده",
                            "میزان فروش هر فروشنده"
                        ]
                    top10_metrics_df = metrics_df.sort_values("تعداد معاملات موفق", ascending=False).head(10)
                    # Bar chart: تعداد معاملات موفق per seller
                    st.subheader(titles[0])
                    fig1 = px.bar(
                        top10_metrics_df,
                        x="فروشنده",
                        y="تعداد معاملات موفق",
                        title='',
                        text="تعداد معاملات موفق",
                        color="فروشنده"
                    )
                    fig1.update_layout(xaxis_title="فروشنده", yaxis_title="تعداد معاملات موفق")
                    st.plotly_chart(fig1, use_container_width=True)
                    # Add total value in million toman for chart
                    top10_metrics_df = top10_metrics_df.copy()
                    top10_metrics_df["ارزش کل معاملات (میلیون تومان)"] = (top10_metrics_df["ارزش کل معاملات"] / 1000).round(2)
                    # Bar chart: ارزش کل معاملات per seller (میلیون تومان)
                    st.subheader(titles[1])
                    fig2 = px.bar(
                        top10_metrics_df.sort_values(by="ارزش کل معاملات", ascending=False),
                        x="فروشنده",
                        y="ارزش کل معاملات (میلیون تومان)",
                        title='',
                        text="ارزش کل معاملات (میلیون تومان)",
                        color="فروشنده"
                    )
                    fig2.update_layout(xaxis_title="فروشنده", yaxis_title="ارزش کل معاملات (میلیون تومان)")
                    st.plotly_chart(fig2, use_container_width=True)
    else:
        login()

if __name__ == "__main__":
    main()