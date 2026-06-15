import streamlit as st
import pandas as pd

st.set_page_config(page_title="Compliance", layout="wide")
st.title("✅ App Working Test")

st.write("If you see this, app is working ✅")

file = st.file_uploader("Upload CSV")

if file:
    df = pd.read_csv(file)
    st.dataframe(df)
