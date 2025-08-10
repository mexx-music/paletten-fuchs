import os, time, streamlit as st
st.write("🔎 BUILD:", time.strftime("%Y-%m-%d %H:%M:%S"))
st.write("📄 Datei:", __file__)
st.write("📂 CWD:", os.getcwd())
st.write("🧱 Streamlit:", st.__version__)
