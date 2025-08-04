import streamlit as st
import pandas as pd
import os
import sys
from datetime import time, timedelta
from streamlit_nej_datepicker import datepicker_component, Config
import jdatetime

# Add path and imports
sys.path.append(os.path.abspath(".."))
from utils.custom_css import apply_custom_css
from utils.auth import login
from utils.load_data import exacute_query, exacute_queries


def filter_tips(selected_complexes, all_tips):
    if len(selected_complexes) == 0:
        return all_tips
    else:
        return [
            tip for tip in all_tips
            if any(complex_name in tip for complex_name in selected_complexes)
        ]

def main():
    """Main function to run the Streamlit app."""
    st.set_page_config(page_title="تحلیل چک‌این", page_icon="📊", layout="wide")
    apply_custom_css()
    st.title("تحلیل وضعیت چک‌این مجتمع‌ها")
    # Check data availability and login first
    if 'auth'in st.session_state and st.session_state.auth:  

        # Only deals where the difference between checking and checkout is equal to the number of nights 
        checkin_query = """
            SELECT 
                MIN(Checkin_date) AS min_date, 
                MAX(Checkin_date) AS max_date
            FROM `customerhealth-crm-warehouse.didar_data.deals`
            WHERE DATE_DIFF(CAST(Checkout AS DATE), CAST(Checkin_date AS DATE), DAY) = Nights
            AND Status = 'Won'
        """
        result_df = exacute_query(checkin_query)

        min_date = result_df.iloc[0]['min_date']
        max_date = result_df.iloc[0]['max_date']

        col1, _, col2, *_ = st.columns([5, 1, 5, 1, 1])

        ### date filter
        with col1:
            config = Config(
                always_open=True,
                dark_mode=True,
                locale="fa",
                minimum_date=min_date,
                maximum_date=max_date,
                color_primary="#ff4b4b",
                color_primary_light="#ff9494",
                selection_mode="range",
                placement="bottom",
                disabled=False
            )
            res = datepicker_component(config=config)

            if res and 'from' in res and res['from'] is not None:
                start_date = res['from'].togregorian()
            else:
                query = "select min(Checkin_date) as min_checkin_date from `customerhealth-crm-warehouse.didar_data.deals`"
                result = exacute_query(query)
                start_date = result['min_checkin_date'].iloc[0].date()

            if res and 'to' in res and res['to'] is not None:
                end_date = res['to'].togregorian()
            else:
                query = "select max(Checkin_date) as max_checkin_date from `customerhealth-crm-warehouse.didar_data.deals`"
                result = exacute_query(query)
                end_date = result['max_checkin_date'].iloc[0].date()

        ### complex filter     
        with col2:
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
        if st.button("محاسبه و نمایش", key='calculate_button'):

            products_query = """
                SELECT * FROM `customerhealth-crm-warehouse.didar_data.Products`
            """
            products = exacute_query(products_query)
            # Fix: set index to ProductCode, not ProductName
            products = products.set_index('ProductCode')
            tips_df = pd.DataFrame({"tip": tip_values})
            # Map tip to ProductCode using ProductName as key
            # So we need a mapping from ProductName to ProductCode
            # But for reverse mapping (ProductCode to ProductName), we need a dict
            name_to_code = products.reset_index().set_index('ProductName')['ProductCode'].to_dict()
            code_to_name = products.reset_index().set_index('ProductCode')['ProductName'].to_dict()
            tips_df['code'] = tips_df['tip'].map(name_to_code)

            # Remove tips with no code mapping
            tips_df = tips_df.dropna(subset=['code'])
            codes = tips_df['code'].astype(str).tolist()

            deals_query = f"""
                SELECT * FROM `customerhealth-crm-warehouse.didar_data.deals`
                WHERE Product_code IN ({','.join([f"'{code}'" for code in codes])})
                AND checkin_date BETWEEN '{start_date}' AND '{end_date}'
                AND Status = 'Won'
            """
            filtered_deals = exacute_query(deals_query)
            # st.write(filtered_deals)

            if filtered_deals.empty:
                st.warning("هیچ ورود (چک‌این) در بازه و فیلتر انتخابی یافت نشد.")
                st.stop()

            # KPIs
            total_arrivals = filtered_deals['Customer_id'].nunique()

    
            date_range_days = (end_date - start_date).days + 1
            weeks_in_range = date_range_days / 7.0 if date_range_days > 0 else 0
            avg_weekly = int(total_arrivals / weeks_in_range if weeks_in_range > 0 else 0)

            if 'Nights' in filtered_deals.columns:
                avg_stay = filtered_deals['Nights'].mean()
            else:
                avg_stay = 0

            filtered_deals['IsExtension'] = filtered_deals['DealType'].eq('Renewal')
            total_extensions = filtered_deals['IsExtension'].sum()

            total_new_arrivals = len(filtered_deals.loc[~filtered_deals['IsExtension'], 'Customer_id'].unique())

            colA1, colA2, colA3, colA4, colA5  = st.columns(5)
            with colA1:
                st.metric("تعداد کل ورودها", f"{total_arrivals}")
            with colA2:
                st.metric("میانگین ورود هفتگی", f"{avg_weekly}")
            with colA3:
                st.metric("میانگین مدت اقامت (شب)", f"{avg_stay:.2f}")
            with colA4:
                st.metric("تعداد تمدیدها", f"{int(total_extensions)}")
            with colA5:
                st.metric("تعداد ورود جدید", f"{total_new_arrivals}")
            
            st.write('---')
            st.subheader("تفکیک ورود بر اساس تیپ")
            # Add ProductName column to filtered_deals by mapping Product_code to ProductName
            filtered_deals['ProductName'] = filtered_deals['Product_code'].map(code_to_name)

            grouped = filtered_deals.groupby('ProductName', dropna=True)
            house_type_data = []
            for house_type, subdf in grouped:
                arrivals_count = len(subdf)
                avg_stay_ht = subdf['Nights'].mean() if 'Nights' in subdf.columns else 0
                ext_count = subdf['IsExtension'].sum()
                new_count = len(subdf[~subdf['IsExtension']])

                house_type_data.append({
                    'House Type': house_type,
                    'Arrivals': arrivals_count,
                    'Avg Stay': round(avg_stay_ht, 2),
                    'Extensions': ext_count,
                    'New Arrivals': new_count,
                })
            df_house_type = pd.DataFrame(house_type_data)
            st.dataframe(df_house_type)

    else:
        login()

if __name__ == "__main__":
    main()