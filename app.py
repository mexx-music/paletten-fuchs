import os, time, subprocess, streamlit as st
st.write("🔎 BUILD:", time.strftime("%Y-%m-%d %H:%M:%S"))
try:
    git_sha = subprocess.check_output(["git","rev-parse","--short","HEAD"], text=True).strip()
except Exception:
    git_sha = os.environ.get("GIT_SHA","?")
st.write("🔀 COMMIT:", git_sha)
st.write("📄 MAIN FILE:", __file__)
