import streamlit as st
import time
def login():
    st.title("صفحه ورود")
    st.write("لطفاً اطلاعات کاربری خود را وارد کنید.")
    passwords = st.secrets["passwords"]
    roles = st.secrets["roles"]

    username = st.text_input("نام کاربری")
    password = st.text_input("رمز عبور", type="password")
    
    if st.button('ورود'):
        if username and password:
            if username in passwords and passwords[username] == password:
                st.session_state.role = roles.get(username, "user")
                st.session_state.username = username
                st.session_state.auth = True

                st.success("ورود موفقیت آمیز! خوش آمدید")
                time.sleep(1) 
                st.rerun()
            else:
                st.error("رمز عبور اشتباه است.")
        else:
            st.warning("لطفاً رمز عبور را وارد کنید.")
        
