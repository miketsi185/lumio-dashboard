import streamlit as st

st.set_page_config(page_title="Lumio Dashboard", layout="wide")

st.title("✦ Lumio")
st.subheader("Business Intelligence Dashboard")

col1, col2, col3 = st.columns(3)

col1.metric("Revenue", "$19,840")
col2.metric("Appointments", "112")
col3.metric("Cancellation Rate", "15.6%")
