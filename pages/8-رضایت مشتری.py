import streamlit as st
import pandas as pd
import numpy as np
import os
import sys

# Add path and imports
sys.path.append(os.path.abspath(".."))
from utils.custom_css import apply_custom_css
from utils.auth import login
from utils.load_data import exacute_query
from utils.funcs import convert_df, convert_df_to_excel

def main():
    """Main function """
    st.set_page_config(page_title="هپی کال", page_icon="📊", layout="wide")
    apply_custom_css()
    st.title("رضایت مشتری ")
    # Check data availability and login first
    if 'auth'in st.session_state and st.session_state.auth:  
        # happy call 
        happy_call_1 = exacute_query(f"""
            SELECT * FROM `customerhealth-crm-warehouse.Surveys.happy_call_scenario_one`
        """)
        happy_call_2 = exacute_query(f"""
            SELECT * FROM `customerhealth-crm-warehouse.Surveys.happy_call_scenario_two`
            WHERE checkout_date IS NOT NULL  
        """)
        happy_call_3 = exacute_query(f"""
            SELECT * FROM `customerhealth-crm-warehouse.Surveys.happy_call_scenario_three`
        """)


        # Combine all data for overall metrics
        happy_calls = []
        for df in [happy_call_1, happy_call_2, happy_call_3]:
            if df is not None and not df.empty:
                happy_calls.append(df)
        if happy_calls:
            all_calls = pd.concat(happy_calls, ignore_index=True)
        else:
            all_calls = pd.DataFrame()

        if not all_calls.empty:

            # fitler
            all_calls = all_calls[
                (all_calls['first_call_date'].notna())&
                (all_calls['first_call_result'].notna())&
                (all_calls['Caller_name'].notna())& 
                (all_calls['checkout_date'].notna())&
                (all_calls['Deal_ID'].notna())
            ].reset_index(drop=True).copy()

            # Number of calls (number of unique Deal_IDs)
            num_calls = all_calls[all_calls['first_call_result'].notna()].shape[0]
            # Success rate: percent of calls with successful result
            def is_success(row):
                first = str(row.get('first_call_result', '')).strip()
                second = str(row.get('second_call_result', '')).strip()
                return (first == 'Successful_call') or (second == 'Successful_call')

            all_calls['success'] = all_calls.apply(is_success, axis=1)
            success_rate = all_calls['success'].mean() * 100 if len(all_calls) > 0 else np.nan

            # Average NPS
            avg_nps = all_calls['NPS_raw_score'].mean() if 'NPS_raw_score' in all_calls else np.nan

            # Average cleanliness
            avg_cleanliness = all_calls['cleanliness_score'].mean() if 'cleanliness_score' in all_calls else np.nan

            # Average staff score
            avg_staff = all_calls['staff_score'].mean() if 'staff_score' in all_calls else np.nan

            # Show metrics
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("تعداد تماس‌ها", f"{num_calls:,}")
            col2.metric("درصد موفقیت تماس", f"{success_rate:.1f}٪" if not np.isnan(success_rate) else "-")
            col3.metric("میانگین NPS", f"{avg_nps:.2f}" if not np.isnan(avg_nps) else "-")
            col4.metric("میانگین نظافت", f"{avg_cleanliness:.2f}" if not np.isnan(avg_cleanliness) else "-")
            col5.metric("میانگین پرسنل", f"{avg_staff:.2f}" if not np.isnan(avg_staff) else "-")


            st.write(all_calls)

        else:
            st.info("داده‌ای برای نمایش وجود ندارد.")
                    
    else:
        login()

if __name__ == "__main__":
    main()