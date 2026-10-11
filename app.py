import streamlit as st

st.set_page_config(page_title="ABS & NC Formate", page_icon="📐", layout="wide")
page = st.navigation([
    st.Page("ui/abs_page.py", title="ABS · Bewehrung", icon="📐", default=True),
    st.Page("ui/nc_page.py", title="Stahlbau · DSTV / NC / NC1", icon="🏗️"),
])
page.run()
