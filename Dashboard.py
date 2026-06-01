import streamlit as st

st.set_page_config(page_title="Audit Dashboard", layout="wide")

pages = [
    st.Page("pages/2_City_Clusters.py", title="🏙️ City Clusters"),
    st.Page("pages/3_Data_Upload.py", title="📤 Data Upload"),
    st.Page("pages/5_Planning_Config.py", title="⚙️ Planning Config"),
    st.Page("pages/6_Planning_Analysis.py", title="📈 Planning Analysis"),
    st.Page("pages/7_Department_Overlaps.py", title="🔗 Department Overlaps"),
]

pg = st.navigation(pages, position="sidebar")
pg.run()
