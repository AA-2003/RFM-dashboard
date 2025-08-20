import streamlit as st
import time

def login():
    st.title("صفحه ورود")
    st.write("لطفاً اطلاعات کاربری خود را وارد کنید.")

    # Get passwords and roles from Streamlit secrets
    passwords = st.secrets["passwords"]
    roles = st.secrets["roles"]

    # User input fields
    username = st.text_input("نام کاربری")
    password = st.text_input("رمز عبور", type="password")

    if st.button("ورود"):
        if username and password:
            # Check if username exists and password matches
            if username in passwords and passwords[username] == password:
                # Set session state for role, username, and authentication
                st.session_state.role = roles.get(username, "user")  # Default role is 'user' if not found
                st.session_state.username = username
                st.session_state.auth = True
                st.success("ورود موفقیت‌آمیز! خوش آمدید")
                time.sleep(1)  # Wait for 1 second to show success message
                st.rerun()     # Rerun the app to update session state
            else:
                st.error("رمز عبور اشتباه است.")
        else:
            st.warning("لطفاً اطلاعات را کامل وارد کنید.")

