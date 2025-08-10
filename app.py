import streamlit as st
from streamlit_drawable_canvas import st_canvas

st.set_page_config(page_title="Mini Canvas Test", layout="centered")
st.title("Mini Canvas Test")

canvas = st_canvas(
    fill_color="rgba(0, 0, 0, 0)",
    stroke_width=1,
    stroke_color="#666666",
    background_color=None,
    width=600,
    height=200,
    drawing_mode="transform",
    key="mini",
    update_streamlit=True,
    display_toolbar=False,
)
st.write("OK:", canvas is not None)
