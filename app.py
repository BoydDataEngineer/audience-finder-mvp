import streamlit as st
import pandas as pd
from io import BytesIO
from reddit_scanner import find_communities

def show_login_form():
    st.title("🚀 The Audience Finder")
    st.header("Login")
    
    with st.form(key='login_form'):
        password = st.text_input("Please enter the password", type="password", label_visibility="collapsed")
        submitted = st.form_submit_button("Login")

        if submitted:
            if password == st.secrets["app_password"]:
                st.session_state["logged_in"] = True
                st.rerun()
            else:
                st.error("🚨 The password you entered is incorrect.")

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
                    results_df = find_communities(search_queries_list)
                    
                    st.header("2. Discovered Communities")
                    
                    if not results_df.empty:
                        # Voeg de extra kolommen toe
                        results_df['Status'] = 'Not Started'
                        results_df['Priority'] = ''
                        results_df['Notes'] = ''
                        results_df['Last Contact'] = ''
                        
                        st.dataframe(results_df, use_container_width=True)

                        # Excel Download Logic
                        output = BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            results_df.to_excel(writer, index=False, sheet_name='Communities')
                            worksheet = writer.sheets['Communities']
                            for i, col in enumerate(results_df.columns):
                                column_len = max(results_df[col].astype(str).map(len).max(), len(col))
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