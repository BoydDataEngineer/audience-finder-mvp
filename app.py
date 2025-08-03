import streamlit as st
import pandas as pd
from io import BytesIO
from reddit_scanner import find_communities

# --- Functie om het inlogformulier te tonen ---
def show_login_form():
    st.title("🚀 The Audience Finder")
    st.header("Login")
    
    with st.form(key='login_form'):
        password = st.text_input("Please enter the password", type="password", label_visibility="collapsed")
        submitted = st.form_submit_button("Login")

        if submitted:
            if password == st.secrets.get("app_password", "test"): # Gebruikt secret, met 'test' als fallback voor lokaal
                st.session_state["logged_in"] = True
                st.rerun()
            else:
                st.error("🚨 The password you entered is incorrect.")

# --- Functie om de hoofdapplicatie te tonen (AANGEPAST) ---
def show_main_app():
    st.title("🚀 The Audience Finder")
    st.markdown("Discover relevant Reddit communities and their top posts based on your search queries.")

    st.header("1. Enter Your Search Queries")
    st.markdown("Enter one search query per line. Combine words on a single line for more specific results.")
    
    with st.form(key='search_form'):
        search_queries_input = st.text_area(
            "Label for screen readers, not displayed",
            label_visibility="collapsed",
            height=150, 
            placeholder="For example:\nSaaS for startups\ndigital nomad\nproductivity tools"
        )
        find_button_submitted = st.form_submit_button("Find Communities", type="primary")

    if find_button_submitted:
        search_queries_list = [query.strip() for query in search_queries_input.split('\n') if query.strip()]
        
        if not search_queries_list:
            st.warning("Please enter at least one search query.")
        else:
            with st.spinner('Searching the depths of Reddit... This might take a moment.'):
                try:
                    # De find_communities functie geeft nu geaggregeerde data terug
                    results_df = find_communities(search_queries_list)
                    
                    st.header("2. Discovered Communities")
                    
                    if not results_df.empty:
                        # --- BELANGRIJKE WIJZIGING ---
                        # We maken een kopie om de tracking kolommen toe te voegen voor de download
                        # De weergave op het scherm toont alleen de pure data.
                        df_for_display = results_df.copy()

                        # Maak het DataFrame voor de download
                        df_for_download = results_df.copy()
                        df_for_download['Status'] = 'Not Started'
                        df_for_download['Priority'] = ''
                        df_for_download['Notes'] = ''
                        df_for_download['Last Contact'] = ''
                        
                        # Toon het DataFrame ZONDER de extra kolommen op het scherm
                        st.dataframe(df_for_display, use_container_width=True)

                        # Excel Download Logic
                        output = BytesIO()
                        # We gebruiken het DataFrame MET de extra kolommen voor de Excel-export
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            df_for_download.to_excel(writer, index=False, sheet_name='Communities')
                            worksheet = writer.sheets['Communities']
                            for i, col in enumerate(df_for_download.columns):
                                column_len = max(df_for_download[col].astype(str).map(len).max(), len(col))
                                worksheet.column_dimensions[chr(65 + i)].width = column_len + 2
                        
                        excel_data = output.getvalue()
                        
                        st.header("3. Download Your Results")
                        st.download_button(
                            label="Download results as formatted Excel file",
                            data=excel_data,
                            file_name='audience_finder_results.xlsx',
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        )
                    else:
                        st.success("✅ Search complete, but no communities were found for these terms.")

                except Exception as e:
                    st.error(f"An error occurred during the search: {e}")

# --- Hoofdlogica van de App ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if st.session_state["logged_in"]:
    show_main_app()
else:
    show_login_form()