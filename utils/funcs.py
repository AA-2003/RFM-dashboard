from io import BytesIO
import pandas as pd
import streamlit as st
from utils.constants import DEALSTATUS, CUSTOMERID, DEALDONEDATE
import re
import unicodedata

@st.cache_data(ttl=600, show_spinner=False)
def map_complex(name):
    name = str(name) if name is not None else ''
    if not name or name.lower() == 'nan':
        return ''

    if 'میرداماد' in name:
        return 'میرداماد'
    elif 'ویلا' in name or 'نجات‌اللهی' in name:
        return 'ویلا'
    elif 'جردن' in name:
        return 'جردن'
    elif 'ترنج' in name:
        return 'ترنج'
    elif 'گاندی' in name:
        return 'گاندی'
    elif 'نوفل' in name:
        return 'نوفل'
    elif 'پاسداران' in name or 'پاسدذاران' in name:
        return 'پاسداران'
    elif 'مصلی' in name or 'نیلوفر' in name:
        return 'مصلی'
    elif 'کشاورز' in name or 'کشاور ز' in name:
        return 'کشاورز'
    elif 'اشرفی' in name:
        return 'اشرفی'
    elif 'پارک وی' in name or 'پارک‌وی' in name:
        return 'پارک وی'
    elif 'ولیعصر' in name:
        return 'ولیعصر'
    elif 'اوین' in name:
        return 'اوین'
    elif 'ونک' in name:
        return 'ونک'
    elif 'جمهوری' in name or 'جموری' in name:
        return 'جمهوری'
    elif 'ولنجک' in name:
        return 'ولنجک'
    elif 'بهشتی' in name:
        return 'بهشتی'
    elif 'مرزداران' in name or 'مرزرداران' in name:
        return 'مرزداران'
    elif 'کوروش' in name:
        return 'کوروش'
    elif 'دلچه' in name:
        return 'دلچه'
    elif 'شریعتی' in name:
        return 'شریعتی'
    else:
        return 'نامشخص'
    

@st.cache_data(ttl=10, show_spinner=False)
def convert_df(df):
    # Cache the conversion to prevent computation on every rerun
    return df.to_csv(index=False).encode('utf-8')

@st.cache_data(ttl=600, show_spinner=False)
def convert_df_to_excel(df: pd.DataFrame):
    for col in df.select_dtypes(include=['datetimetz']).columns:
        df[col] = df[col].dt.tz_localize(None)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    output.seek(0)
    return output

@st.cache_data(ttl=600, show_spinner=False)
def get_first_successful_deal_date_for_customers(df):
    """Return a series mapping each customer to their first successful deal date."""
    successful_deals_only = df[df[DEALSTATUS] == 'Won'].copy()
    first_deal = successful_deals_only.groupby(CUSTOMERID)[DEALDONEDATE].min()
    return first_deal


@st.cache_data(ttl=600, show_spinner=False)
def extract_vip_status(name_series):
    """Extract VIP status from a series of names."""

    # 1) Fill NaNs with empty string so we can operate safely
    name_series = name_series.fillna("")

    # 2) Normalize Unicode to canonical form (NFC)
    name_series = name_series.apply(lambda x: unicodedata.normalize('NFC', x))

    # 3) Replace Excel’s special code for 💎
    name_series = name_series.str.replace(r"_xD83D__xDC8E", "💎", regex=True)

    # 4) Remove potential zero-width or variation selectors (like U+200D, U+FE0F, etc.)
    name_series = name_series.str.replace(r"[\u200B-\u200D\uFE0F]", "", regex=True)

    # 5) Final VIP status check
    def get_vip_status(name):
        if not name or pd.isna(name):
            return 'Non-VIP'
        if '💎' in name:
            return 'Gold VIP'
        elif '⭐' in name:
            return 'Silver VIP'
        elif '💠' in name:
            return 'Bronze VIP'
        else:
            return 'Non-VIP'

    return name_series.apply(get_vip_status)

@st.cache_data(ttl=600, show_spinner=False)
def extract_blacklist_status(name_series):
    """Extract Blacklist status from a series of names."""
    def get_blacklist_status(name):
        if pd.isna(name):
            return 'Non-BlackList'
        # بررسی وجود (*) در انتهای نام
        if re.search(r'\(\*\)\s*$', name):
            return 'BlackList'
        else:
            return 'Non-BlackList'
    return name_series.apply(get_blacklist_status)