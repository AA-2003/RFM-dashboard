from io import BytesIO
import pandas as pd
import streamlit as st
from utils.constants import DEALSTATUS, CUSTOMERID, DEALDONEDATE

@st.cache_data(ttl=10, show_spinner=False)
def convert_df(df):
    # Cache the conversion to prevent computation on every rerun
    return df.to_csv(index=False).encode('utf-8')

@st.cache_data(ttl=10, show_spinner=False)
def convert_df_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    processed_data = output.getvalue()
    return processed_data

def get_first_successful_deal_date_for_customers(df):
    """Return a series mapping each customer to their first successful deal date."""
    successful_deals_only = df[df[DEALSTATUS] == 'Won'].copy()
    first_deal = successful_deals_only.groupby(CUSTOMERID)[DEALDONEDATE].min()
    return first_deal