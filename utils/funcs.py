from io import BytesIO
import pandas as pd
import streamlit as st

@st.cache_data(ttl=10, show_spinner=False)
def convert_df(df):
    """
    Convert a DataFrame to CSV bytes for download.
    Cached to avoid recomputation.
    """
    return df.to_csv(index=False).encode('utf-8')

@st.cache_data(ttl=600, show_spinner=False)
def convert_df_to_excel(df: pd.DataFrame):
    """
    Convert a DataFrame to an Excel file in memory (BytesIO).
    Handles timezone-aware datetime columns by localizing to naive.
    """
    # Remove timezone info from datetime columns (Excel does not support tz-aware datetimes)
    for col in df.select_dtypes(include=['datetimetz']).columns:
        df[col] = df[col].dt.tz_localize(None)

    output = BytesIO()
    # Write DataFrame to Excel in memory
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    output.seek(0)
    return output

@st.cache_data(ttl=600, show_spinner=False)
def get_first_successful_deal_date_for_customers(df):
    """
    Return a Series mapping each customer to their first successful deal date.
    Only considers deals with Status == 'Won'.
    """
    # Filter only successful deals
    successful_deals_only = df[df['Status'] == 'Won'].copy()
    # Group by customer and get the earliest deal date
    first_deal = successful_deals_only.groupby('Customer_id')['DealDate'].min()
    return first_deal