import streamlit as st
import pandas as pd
import os
import sys
from streamlit_nej_datepicker import datepicker_component, Config
import jdatetime

# Add parent directory to sys.path for module imports
sys.path.append(os.path.abspath(".."))
from utils.custom_css import apply_custom_css
from utils.auth import login
from utils.load_data import exacute_query
from utils.funcs import convert_df, convert_df_to_excel

@st.cache_data(ttl=1200, show_spinner=False)
def get_min_max_dates(date_col):
    """
    Helper function to get min and max dates for a given date column (Checkin_date or Checkout).
    """
    # Query to get the minimum and maximum date for the selected column, only for valid deals
    query = f"""
        SELECT 
            MIN({date_col}) AS min_date, 
            MAX({date_col}) AS max_date
        FROM `customerhealth-crm-warehouse.didar_data.deals`
        WHERE DATE_DIFF(CAST(Checkout AS DATE), CAST(Checkin_date AS DATE), DAY) = Nights
        AND Status = 'Won'
    """
    result_df = exacute_query(query)
    return result_df.iloc[0]['min_date'], result_df.iloc[0]['max_date']

def get_date_range_picker(col, label, min_date, max_date, date_col):
    """
    Helper function to show a date range picker and return start and end dates.
    """
    with col:
        st.subheader(label)
        # Configure the Persian datepicker component
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

        # If user selects a range, use it; otherwise, use min/max
        if res and 'from' in res and res['from'] is not None:
            start_date = res['from'].togregorian()
        else:
            start_date = min_date

        if res and 'to' in res and res['to'] is not None:
            end_date = res['to'].togregorian()
        else:
            end_date = max_date
    return start_date, end_date

def get_complex_tip_filters(col):
    """
    Helper function to get selected complexes and tips.
    """
    with col:
        # Query all products to get complexes and tips
        products = exacute_query("""
                SELECT * FROM `customerhealth-crm-warehouse.didar_data.Products`
                """)
        # Filter out invalid building names
        complex_options = [b for b in products['Building_name'].unique().tolist() if b != 'not_a_building']
        tip_options =  products[products['Building_name']!='not_a_building']['ProductName'].unique().tolist() 

        # Checkbox for selecting all complexes
        complex_status = st.checkbox("انتخاب تمام مجتمع ها ", value=True, key=f'complex_checkbox_{col}')
        if complex_status:
            tip_values = tip_options
        else:
            # Multiselect for complexes
            complex_values = st.multiselect(
                    "انتخاب مجتمع:",
                    options=complex_options,
                    default=[],  # empty if user doesn’t pick
                    key=f'complex_multiselect_selectbox_{col}'
                )
            cols = st.columns([1, 4])
            with cols[1]:
                # Filter tips based on selected complexes
                tip_options = products[(products['Building_name']!='not_a_building')&
                                        (products['Building_name'].isin(complex_values))]['ProductName'].unique().tolist()
                # Checkbox for selecting all tips
                tip_status = st.checkbox("انتخاب تمام تیپ ها ", value=True, key=f'tips_checkbox_{col}')
                if tip_status:
                    tip_values = tip_options
                else:
                    # Multiselect for tips
                    tip_values = st.multiselect(
                        "انتخاب تیپ:",
                        options=tip_options,
                        default=[],  # empty if user doesn’t pick
                        key=f'tip_multiselect_selectbox_{col}'
                    )
                # If no tip selected, use all available tips
                if tip_values == []:
                    tip_values = tip_options
    return tip_values

def show_kpis(filtered_deals, start_date, end_date, is_checkin=True):
    """
    Show KPIs for arrivals (checkin) or departures (checkout).
    """
    # Main count
    total_count = filtered_deals['Customer_id'].nunique()
    date_range_days = (end_date - start_date).days + 1
    weeks_in_range = date_range_days / 7.0 if date_range_days > 0 else 0
    avg_weekly = int(total_count / weeks_in_range if weeks_in_range > 0 else 0)

    # Average stay
    if 'Nights' in filtered_deals.columns:
        avg_stay = filtered_deals.groupby('Customer_id')['Nights'].sum().mean()
    else:
        avg_stay = 0

    # Mark deals as extension or new
    filtered_deals['IsExtension'] = filtered_deals['DealType'].eq('Renewal')
    total_extensions = filtered_deals[(filtered_deals['IsExtension'])]['Customer_id'].nunique()
    total_new = filtered_deals.loc[(~filtered_deals['IsExtension']), 'Customer_id'].nunique()

    colA1, colA2, colA3, colA4, colA5  = st.columns(5)
    with colA1:
        st.metric("تعداد کل افراد " + ("ورودی" if is_checkin else "خروجی"), f"{total_count}")
    with colA2:
        st.metric("میانگین " + ("ورود" if is_checkin else "خروج") + " هفتگی", f"{avg_weekly}")
    with colA3:
        st.metric("میانگین مدت اقامت (شب)", f"{avg_stay:.2f}")
    with colA4:
        st.metric("تعداد تمدیدی‌ها", f"{int(total_extensions)}")
    with colA5:
        st.metric("تعداد " + ("ورود" if is_checkin else "خروج") + " جدید", f"{total_new}")

def show_grouped_tables(filtered_deals, group_col, is_checkin=True):
    """
    Show grouped tables by complex or tip for arrivals/departures.
    """
    # Group by the selected column (complex or tip)
    grouped = filtered_deals.groupby(group_col, dropna=True)
    house_type_data = []
    for house_type, subdf in grouped:
        count = subdf['Customer_id'].nunique()
        avg_stay_ht = subdf['Nights'].mean() if 'Nights' in subdf.columns else 0
        ext_count = subdf[subdf['IsExtension']]['Customer_id'].nunique()
        new_count = subdf[~subdf['IsExtension']]['Customer_id'].nunique()
        house_type_data.append({
            ('مجتمع' if group_col == 'Building_name' else 'تیپ'): house_type,
            ('ورودی‌ها' if is_checkin else 'خروجی‌ها'): count,
            'میانگین شب اقامت': round(avg_stay_ht, 2),
            'تمدیدها': ext_count,
            ('ورودی های جدید' if is_checkin else 'خروجی های جدید'): new_count,
        })
    df_house_type = pd.DataFrame(house_type_data)
    st.dataframe(df_house_type)
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="دانلود داده‌ها به صورت CSV",
            data=convert_df(df_house_type),
            file_name='rfm_segmentation_with_churn.csv',
            mime='text/csv',
            key=f"{group_col}_csv_{'in' if is_checkin else 'out'}"
        )
    with col2:
        st.download_button(
            label="دانلود داده‌ها به صورت اکسل",
            data=convert_df_to_excel(df_house_type),
            file_name='rfm_segmentation_with_churn.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            key=f"{group_col}_excel_{'in' if is_checkin else 'out'}"
        )

def show_daily_table(filtered_deals, date_col, is_checkin=True):
    """
    Show daily arrivals/departures table.
    """
    # Convert date column to datetime and extract only the date part
    filtered_deals[date_col] = pd.to_datetime(filtered_deals[date_col])
    filtered_deals[f'{date_col}_only'] = filtered_deals[date_col].dt.date
    # Only count "New Sale" deals per day
    grouped = filtered_deals[filtered_deals['DealType']=='New Sale'].groupby(f'{date_col}_only', dropna=True)[date_col].count().reset_index()
    grouped.columns = ['تاریخ میلادی', f'تعداد {"ورود" if is_checkin else "خروج"}']

    # Add Jalali (Persian) date column for user-friendly display
    grouped['تاریخ شمسی'] = grouped['تاریخ میلادی'].apply(lambda d: jdatetime.date.fromgregorian(date=d).strftime('%Y/%m/%d'))
    grouped = grouped[['تاریخ شمسی', 'تاریخ میلادی', f'تعداد {"ورود" if is_checkin else "خروج"}']]
    st.dataframe(grouped)

def main():
    """Main function to run the Streamlit app for both check-in and check-out analysis."""
    st.set_page_config(page_title="تحلیل ورود/خروج", page_icon="📊", layout="wide")
    apply_custom_css()
    st.title("تحلیل وضعیت ورود و خروج مجتمع‌ها")
    if 'auth' in st.session_state and st.session_state.auth:
        # Tabs for ورود (check-in) and خروج (check-out)
        tabs = st.tabs(['ورود', 'خروج'])

        # --- ورود (Check-in) Tab ---
        with tabs[0]:
            # Get min/max check-in dates
            min_date, max_date = get_min_max_dates('Checkin_date')
            col1, _, col2, *_ = st.columns([5, 1, 5, 1, 1])
            # Date picker for check-in
            start_date, end_date = get_date_range_picker(col1, "انتخاب بازه زمانی تاریخ ورود:", min_date, max_date, 'Checkin_date')
            # Complex/tip filter
            tip_values = get_complex_tip_filters(col2)
            if st.button("محاسبه و نمایش", key='calculate_checkin'):
                # Build SQL IN clause for selected tips
                tip_values_sql = ','.join([f"'{tip}'" for tip in tip_values])
                # Query deals for selected tips and date range
                deals_query = f"""
                    SELECT d.*, p.ProductName, p.Building_name
                    FROM `customerhealth-crm-warehouse.didar_data.deals` d
                    INNER JOIN `customerhealth-crm-warehouse.didar_data.Products` p
                        ON d.Product_code = p.ProductCode
                    WHERE p.ProductName IN ({tip_values_sql})
                      AND d.Checkin_date BETWEEN DATE('{start_date}') AND DATE('{end_date}')
                      AND d.Status = 'Won'
                """
                filtered_deals = exacute_query(deals_query)
                if filtered_deals.empty:
                    st.warning("هیچ ورودی (چک‌این) در بازه و فیلتر انتخابی یافت نشد.")
                    st.stop()
                # KPIs for check-in
                show_kpis(filtered_deals, start_date, end_date, is_checkin=True)
                st.write('---')
                with st.expander("تفکیک ورود بر اساس مجتمع", expanded=False):
                    # Show grouped table by complex
                    show_grouped_tables(filtered_deals, 'Building_name', is_checkin=True)
                with st.expander("تفکیک ورود بر اساس تیپ", expanded=False):
                    # Show grouped table by tip
                    show_grouped_tables(filtered_deals, 'ProductName', is_checkin=True)
                with st.expander('تفکیک ورود براساس روز', expanded=False):
                    # Show daily arrivals
                    show_daily_table(filtered_deals, 'Checkin_date', is_checkin=True)

        # --- خروج (Check-out) Tab ---
        with tabs[1]:
            # Get min/max check-out dates
            min_date, max_date = get_min_max_dates('Checkout')
            col1, _, col2, *_ = st.columns([5, 1, 5, 1, 1])
            # Date picker for check-out
            start_date, end_date = get_date_range_picker(col1, "انتخاب بازه زمانی تاریخ خروج:", min_date, max_date, 'Checkout')
            # Complex/tip filter
            tip_values = get_complex_tip_filters(col2)
            if st.button("محاسبه و نمایش", key='calculate_checkout'):
                # Build SQL IN clause for selected tips
                tip_values_sql = ','.join([f"'{tip}'" for tip in tip_values])
                # Query deals for selected tips and date range
                deals_query = f"""
                    SELECT d.*, p.ProductName, p.Building_name
                    FROM `customerhealth-crm-warehouse.didar_data.deals` d
                    INNER JOIN `customerhealth-crm-warehouse.didar_data.Products` p
                        ON d.Product_code = p.ProductCode
                    WHERE p.ProductName IN ({tip_values_sql})
                      AND d.Checkout BETWEEN DATE('{start_date}') AND DATE('{end_date}')
                      AND d.Status = 'Won'
                """
                filtered_deals = exacute_query(deals_query)
                if filtered_deals.empty:
                    st.warning("هیچ خروجی (چک‌اوت) در بازه و فیلتر انتخابی یافت نشد.")
                    st.stop()
                # KPIs for check-out
                show_kpis(filtered_deals, start_date, end_date, is_checkin=False)
                st.write('---')
                with st.expander("تفکیک خروج بر اساس مجتمع", expanded=False):
                    # Show grouped table by complex
                    show_grouped_tables(filtered_deals, 'Building_name', is_checkin=False)
                with st.expander("تفکیک خروج بر اساس تیپ", expanded=False):
                    # Show grouped table by tip
                    show_grouped_tables(filtered_deals, 'ProductName', is_checkin=False)
                with st.expander('تفکیک خروج براساس روز', expanded=False):
                    # Show daily departures
                    show_daily_table(filtered_deals, 'Checkout', is_checkin=False)
    else:
        login()

if __name__ == "__main__":
    main()