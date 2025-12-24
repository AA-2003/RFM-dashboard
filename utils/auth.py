import time
import streamlit as st
from utils.sheetConnect import load_sheet
from utils.logger import log_event

@st.cache_data(ttl=600, show_spinner=False)
def load_users():
    users = load_sheet(key='MAIN_SPREADSHEET_ID', sheet_name='Users')
    return users

def login():
    st.title("صفحه ورود")
    st.write("لطفاً اطلاعات کاربری خود را وارد کنید.")
    
    users = load_users()
    users = users[users['status'] == 'active']

    # User input fields
    username = st.text_input("نام کاربری")
    password = st.text_input("رمز عبور", type="password")

    if st.button("ورود"):
        if username and password:
            # Check if username exists and password matches
            if username in users['username'].values:
                stored_password = users.loc[users['username'] == username, 'password'].values[0]
                if password == stored_password:
                    log_event(user=username, event_type='login', message='User logged in successfully.')
                    st.success("ورود موفقیت‌آمیز بود!")
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = username
                    st.session_state['role'] = users.loc[users['username'] == username, 'role'].values[0]
                    st.session_state['auth'] = True
                    st.rerun()
                else:
                    st.error("رمز عبور اشتباه است.")
            else:
                st.error("رمز عبور اشتباه است.")
        else:
            st.warning("لطفاً اطلاعات را کامل وارد کنید.")
