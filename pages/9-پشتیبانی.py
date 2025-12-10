import streamlit as st
from utils.custom_css import apply_custom_css
from utils.sheetConnect import append_to_sheet, authenticate_google_sheets
from datetime import datetime

from utils.auth import login


def support():
    """Support page content."""
    st.set_page_config(
        page_title="پشتیبانی", 
        layout="wide",
    )
    apply_custom_css()

    st.title("صفحه پشتیبانی")

    if 'auth' in st.session_state and st.session_state.auth:
        user_guide_link = st.secrets.get('UserGuide', {}).get('link')
        st.markdown(f"[راهنمای استفاده از داشبورد]({user_guide_link})", unsafe_allow_html=True)

        with st.expander("گزارش مشکل یا ارسال درخواست پشتیبانی", expanded=False):
            with st.form(key='support_form'):
                name = st.text_input('نام و نام خانوادگی:')
                email = st.text_input('ایمیل (اختیاری):')
                des = st.text_area('شرح مشکل یا درخواست خود را بنویسید:', height=200)

                submit_button = st.form_submit_button('ارسال درخواست')

                if submit_button:
                    if name and des:
                        row = [datetime.now().strftime('%Y-%m-%d %H:%M:%S'), name, email, des, 'RFM dashboard']
                        append_to_sheet(client=authenticate_google_sheets(), spreadsheet_key='REQ_SPREADSHEET_ID', sheet_name='Dashboard reports', row_data=row)
                        st.success("درخواست شما با موفقیت ثبت شد!")
                    else:
                        st.warning("لطفا نام و شرح مشکل/درخواست را وارد کنید")
    else: 
        login()

if __name__ == "__main__":
    support()