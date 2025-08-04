# app.py

import streamlit as st
import pandas as pd
from io import BytesIO
import praw
from openpyxl.styles import Font, NamedStyle
from praw.exceptions import PRAWException

# --- Configuratie & Secrets ---
# Deze haalt u uit de 'Secrets' van uw Streamlit app.
CLIENT_ID = st.secrets.get("reddit_client_id")
CLIENT_SECRET = st.secrets.get("reddit_client_secret")
APP_PASSWORD = st.secrets.get("app_password")  # Wachtwoord voor app-toegang
REDIRECT_URI = st.secrets.get("redirect_uri") # URL van je Streamlit app, bijv. "https://jouw-app.streamlit.app/"

# --- Helper Functie (onveranderd) ---
# Zorg ervoor dat deze functie in 'reddit_scanner.py' staat of hier gedefinieerd is.
@st.cache_data(ttl=3600) # Cache resultaten voor een uur
def find_communities(_reddit_instance, search_queries: tuple):
    # Let op: De PRAW instance (_reddit_instance) kan niet direct gecached worden, 
    # maar we kunnen de functie cachen zolang de queries hetzelfde zijn.
    # In een echte productie-app zou je de instance buiten de gecachete functie initialiseren.
    # Voor nu is dit een werkbare oplossing.
    
    # We moeten hier een nieuwe instance maken omdat de PRAW objecten zelf niet
    # 'hashable' zijn voor de Streamlit cache. Dit is een veelvoorkomende workaround.
    reddit = praw.Reddit(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        user_agent=f"AudienceFinder by Boyd v0.3 (cached_run)",
        refresh_token=st.session_state.get("refresh_token")
    )

    aggregated_results = {}
    for query in search_queries:
        try:
            for subreddit in reddit.subreddits.search(query, limit=7):
                community_name = subreddit.display_name
                if community_name in aggregated_results:
                    aggregated_results[community_name]['Found By'].add(query)
                else:
                    aggregated_results[community_name] = {
                        'Community': community_name,
                        'Members': subreddit.subscribers,
                        'Community Link': f"https://www.reddit.com/r/{community_name}",
                        'Top Posts (Month)': f"https://www.reddit.com/r/{community_name}/top/?t=month",
                        'Found By': {query}
                    }
        except Exception as e:
            st.warning(f"Could not search with query '{query}'. Error: {e}")

    if not aggregated_results:
        return pd.DataFrame()

    final_list = list(aggregated_results.values())
    for item in final_list:
        item['Found By (Keywords)'] = ', '.join(sorted(list(item['Found By'])))
        del item['Found By']

    df = pd.DataFrame(final_list)
    if df.empty:
        return df

    return df.sort_values(by='Members', ascending=False).reset_index(drop=True)

# --- UI Functies ---

def show_password_form():
    """Toont het wachtwoordformulier."""
    st.title("🚀 The Audience Finder")
    st.header("App Access Login")
    with st.form(key='password_login_form'):
        password = st.text_input("Enter the app password", type="password", label_visibility="collapsed")
        if st.form_submit_button("Login", use_container_width=True):
            if password == APP_PASSWORD:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("🚨 Incorrect password.")
                
def show_reddit_login_page():
    """Toont de 'Login with Reddit' knop, maar gebruikt een custom HTML-link."""
    st.title("🚀 The Audience Finder")
    st.header("Step 2: Connect your Reddit Account")
    st.markdown("Your access is confirmed. Please log in with your Reddit account to proceed. This allows the app to perform searches on your behalf, using your personal API access rate.")
    
    # Maak de PRAW instance en de autorisatie-URL (dit blijft hetzelfde)
    reddit_auth_instance = praw.Reddit(
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI, user_agent="AudienceFinder/Boyd (OAuth Setup)"
    )
    auth_url = reddit_auth_instance.auth.url(scopes=["identity", "read"], state="unique_state_123", duration="permanent")

    # --- START: DE VERBETERING ---
    # We vervangen de st.link_button met een custom-gestijlde HTML link
    
    # 1. Definieer de CSS stijl voor onze knop-link
    button_css = """
    <style>
    .custom-button {
        display: inline-block;
        padding: 0.5rem 1rem;
        background-color: #FF4500; /* Reddit Orangered */
        color: white !important;
        text-align: center;
        text-decoration: none;
        border-radius: 0.5rem;
        font-weight: bold;
        width: 100%;
        box-sizing: border-box;
    }
    .custom-button:hover {
        background-color: #E63E00;
        text-decoration: none;
    }
    </style>
    """
    
    # 2. Creëer de HTML-link met de CSS-klasse
    button_html = f'<a href="{auth_url}" class="custom-button" target="_self">Login with Reddit</a>'

    # 3. Render de CSS en de HTML met st.markdown
    st.markdown(button_css, unsafe_allow_html=True)
    st.markdown(button_html, unsafe_allow_html=True)
    
    # --- EINDE: DE VERBETERING ---
    
    st.info("ℹ️ You will be redirected to Reddit to grant permission. This app never sees your password.")

def show_main_app(reddit):
    """Toont de daadwerkelijke zoek-app met correct gestijlde, klikbare links."""
    # ... (de titel en logout knop code blijft hetzelfde) ...
    col1, col2 = st.columns([0.85, 0.15])
    with col1:
        st.title("🚀 The Audience Finder")
        st.markdown(f"Logged in as **u/{st.session_state.username}**. Discover relevant Reddit communities.")
    with col2:
        if st.button("Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    st.header("1. Enter Your Search Queries")
    st.markdown("Enter one search query per line. Combine words on a single line for more specific results.")
    with st.form(key='search_form'):
        search_queries_input = st.text_area("Queries", height=150, label_visibility="collapsed", placeholder="For example:\nSaaS for startups...")
        if st.form_submit_button("Find Communities", type="primary", use_container_width=True):
            queries_tuple = tuple(sorted([q.strip() for q in search_queries_input.split('\n') if q.strip()]))
            if not queries_tuple:
                st.warning("Please enter at least one search query.")
            else:
                with st.spinner('Searching the depths of Reddit... This might take a moment.'):
                    results_df = find_communities(reddit, queries_tuple)
                    st.session_state['results_df'] = results_df

    if 'results_df' in st.session_state:
        results_df = st.session_state['results_df']
        st.header("2. Discovered Communities")
        if not results_df.empty:
            st.dataframe(results_df, use_container_width=True)

            st.header("3. Download Your Results")
            df_for_download = results_df.copy()
            df_for_download['Community Link'] = df_for_download['Community Link'].apply(lambda url: f'=HYPERLINK("{url}", "{url}")')
            df_for_download['Top Posts (Month)'] = df_for_download['Top Posts (Month)'].apply(lambda url: f'=HYPERLINK("{url}", "{url}")')
            df_for_download['Status'] = 'Not Started'; df_for_download['Priority'] = ''; df_for_download['Notes'] = ''; df_for_download['Last Contact'] = ''

            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_for_download.to_excel(writer, index=False, sheet_name='Communities')
                workbook = writer.book
                worksheet = writer.sheets['Communities']
                
                # --- START: DEFINITIEVE HYPERLINK STYLING ---
                # Maak een 'NamedStyle' object voor hyperlinks
                hyperlink_style = NamedStyle(name="hyperlink_style")
                hyperlink_style.font = Font(color="0000FF", underline="single")
                # Voeg de stijl toe aan de workbook
                if "hyperlink_style" not in workbook.style_names:
                    workbook.add_named_style(hyperlink_style)

                # Vind de kolomletters voor de links
                link_col_letter = chr(65 + df_for_download.columns.get_loc('Community Link'))
                top_posts_col_letter = chr(65 + df_for_download.columns.get_loc('Top Posts (Month)'))

                # Pas de stijl toe op elke cel in die kolommen (behalve de header)
                for row in range(2, len(df_for_download) + 2):
                    worksheet[f'{link_col_letter}{row}'].style = "hyperlink_style"
                    worksheet[f'{top_posts_col_letter}{row}'].style = "hyperlink_style"
                # --- EINDE STYLING ---

                # Pas kolombreedtes aan
                for i, col in enumerate(df_for_download.columns):
                    column = chr(65 + i)
                    if "Link" in col or "Month" in col:
                         worksheet.column_dimensions[column].width = 40
                    else:
                        max_len = max(df_for_download[col].astype(str).map(len).max(), len(col))
                        worksheet.column_dimensions[column].width = max_len + 2
            
            excel_data = output.getvalue()
            st.download_button(label="⬇️ Download results as formatted Excel file", data=excel_data, file_name='audience_finder_results.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', use_container_width=True)
        else:
            st.success("✅ Search complete, but no communities were found for these terms.")
            
# --- HOOFDLOGICA (NIEUWE, ROBUUSTE VERSIE) ---
def main():
    st.set_page_config(page_title="The Audience Finder", layout="wide")

    # Haal de 'code' uit de URL, als die er is
    query_params = st.query_params
    auth_code = query_params.get("code")

    # ---- START VAN DE NIEUWE LOGICA-VOLGORDE ----

    # 1. Is de gebruiker al volledig ingelogd? (De meest complete staat)
    if "refresh_token" in st.session_state:
        # Initialiseer de PRAW instance en toon de hoofd-app
        reddit_instance = praw.Reddit(
            client_id=CLIENT_ID, client_secret=CLIENT_SECRET,
            user_agent=f"AudienceFinder/Boyd (user: {st.session_state.get('username', '...')})",
            refresh_token=st.session_state["refresh_token"]
        )
        show_main_app(reddit_instance)
        return # Stop de uitvoering hier

    # 2. Is de gebruiker net terug van Reddit? (Heeft een 'code' om in te wisselen)
    if auth_code:
        try:
            # Wissel de code in voor een refresh token
            temp_reddit = praw.Reddit(
                client_id=CLIENT_ID, client_secret=CLIENT_SECRET,
                redirect_uri=REDIRECT_URI, user_agent="AudienceFinder/Boyd (Token Exchange)"
            )
            refresh_token = temp_reddit.auth.authorize(auth_code)
            st.session_state["refresh_token"] = refresh_token

            # Haal gebruikersnaam op en sla op
            user_reddit = praw.Reddit(
                client_id=CLIENT_ID, client_secret=CLIENT_SECRET,
                user_agent="AudienceFinder/Boyd (Get Username)", refresh_token=refresh_token
            )
            st.session_state["username"] = user_reddit.user.me().name
            
            # Belangrijk: zet password_correct OOK hier op True
            st.session_state["password_correct"] = True

            # Maak de URL schoon en herlaad de app
            st.query_params.clear()
            st.rerun()

        except PRAWException as e:
            st.error(f"Reddit authentication failed: {e}. Please try again.")
            st.session_state.clear()
            st.rerun()
        return # Stop de uitvoering hier

    # 3. Heeft de gebruiker net het wachtwoord ingevuld?
    if st.session_state.get("password_correct"):
        show_reddit_login_page()
        return # Stop de uitvoering hier

    # 4. Als geen van bovenstaande waar is, toon het wachtwoordformulier
    show_password_form()


if __name__ == "__main__":
    main()