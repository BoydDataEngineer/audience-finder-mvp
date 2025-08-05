# app.py - Finale Versie met Comment Analyse en Geavanceerde Controles

import streamlit as st
import pandas as pd
from io import BytesIO
import praw
from openpyxl.styles import Font, NamedStyle
from praw.exceptions import PRAWException
import numpy as np

# --- Configuratie & Secrets ---
CLIENT_ID = st.secrets.get("reddit_client_id")
CLIENT_SECRET = st.secrets.get("reddit_client_secret")
APP_PASSWORD = st.secrets.get("app_password")
REDIRECT_URI = st.secrets.get("redirect_uri")

# --- De Enige Zoekfunctie die je Nodig Hebt ---

# Zorg ervoor dat je 'import numpy as np' bovenaan je script hebt staan

def calculate_relevance_score(found_via_string):
    """Berekent een logische score op basis van de gevonden methodes."""
    # Score 3: De 'heilige graal' - gevonden via alle methodes
    if "Direct Search" in found_via_string and "Relevant Post" in found_via_string and "Relevant Comment" in found_via_string:
        return 3
    # Score 2: Sterk signaal - relevante posts én comments
    if "Relevant Post" in found_via_string and "Relevant Comment" in found_via_string:
        return 2
    # Score 1: Goed signaal - ten minste één vorm van actieve discussie
    if "Relevant Post" in found_via_string or "Relevant Comment" in found_via_string:
        return 1
    # Score 0: Basis signaal - alleen een directe match op naam
    if "Direct Search" in found_via_string:
        return 0
    return -1 # Fallback voor onverwachte gevallen

@st.cache_data(ttl=3600, show_spinner=False)
def find_communities_hybrid(_reddit_instance, search_queries: tuple, direct_limit: int, post_limit: int, comment_limit: int):
    """
    Vindt communities met een HYBRIDE aanpak en sorteert ze op een CORRECT berekende RELEVANTIE SCORE.
    """
    # ... (de code voor het initialiseren van de Reddit instance en de zoek-lussen blijft hetzelfde) ...
    # ... (je hoeft alleen de functie als geheel te vervangen) ...
    reddit = praw.Reddit(
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET,
        user_agent=f"AudienceFinder by Boyd v1.1 (fixed_relevance)",
        refresh_token=st.session_state.get("refresh_token")
    )
    aggregated_results = {}
    progress_bar = st.progress(0.0, text="Starting search...")

    for i, query in enumerate(search_queries):
        progress_bar.progress(i / len(search_queries), text=f"Searching for: '{query}'...")
        # ... (De 3 zoekstrategieën blijven ongewijzigd) ...
        try:
            for subreddit in reddit.subreddits.search(query, limit=direct_limit):
                if subreddit.display_name.startswith('u_'): continue
                if subreddit.display_name not in aggregated_results: aggregated_results[subreddit.display_name] = {'Community': subreddit.display_name, 'Members': subreddit.subscribers, 'Found Via': set()}
                aggregated_results[subreddit.display_name]['Found Via'].add('Direct Search')
        except PRAWException: pass
        try:
            for post in reddit.subreddit("all").search(query, sort="relevance", time_filter="month", limit=post_limit):
                if post.subreddit.display_name.startswith('u_') or post.subreddit.over18: continue
                community_name = post.subreddit.display_name
                if community_name not in aggregated_results: aggregated_results[community_name] = {'Community': community_name, 'Members': post.subreddit.subscribers, 'Found Via': set()}
                aggregated_results[community_name]['Found Via'].add('Relevant Post')
                if comment_limit > 0:
                    try:
                        post.comments.replace_more(limit=0)
                        for comment in post.comments.list()[:comment_limit]:
                            if hasattr(comment, 'body') and query.lower() in comment.body.lower():
                                aggregated_results[community_name]['Found Via'].add('Relevant Comment'); break
                    except Exception: continue
        except PRAWException: pass
    
    progress_bar.progress(1.0, text="Search complete. Compiling results...")
    if not aggregated_results: return pd.DataFrame()

    final_list = [{'Community': name, **data} for name, data in aggregated_results.items()]
    df = pd.DataFrame(final_list)
    if df.empty: return df

    # --- DE CORRECTE LOGICA ---
    df['Found Via'] = df['Found Via'].apply(lambda s: ', '.join(sorted(list(s))))
    df['Relevance Score'] = df['Found Via'].apply(calculate_relevance_score)
    df['Community Link'] = df['Community'].apply(lambda name: f"https://www.reddit.com/r/{name}")
    df['Top Posts (Month)'] = df['Community'].apply(lambda name: f"https://www.reddit.com/r/{name}/top/?t=month")

    df = df.sort_values(by=['Relevance Score', 'Members'], ascending=[False, False])
    column_order = ['Community', 'Relevance Score', 'Found Via', 'Members', 'Community Link', 'Top Posts (Month)']
    return df[column_order].reset_index(drop=True)

# --- UI Functies (onveranderd) ---
def show_password_form():
    # ... (code is hetzelfde als voorheen)
    st.title("🚀 The Audience Finder")
    st.header("App Access Login")
    with st.form(key='password_login_form'):
        password = st.text_input("Enter the app password", type="password", label_visibility="collapsed")
        if st.form_submit_button("Login", use_container_width=True):
            if password == APP_PASSWORD: st.session_state["password_correct"] = True; st.rerun()
            else: st.error("🚨 Incorrect password.")

def show_reddit_login_page():
    # ... (code is hetzelfde als voorheen)
    st.title("🚀 The Audience Finder")
    st.header("Step 2: Connect your Reddit Account")
    st.markdown("Your access is confirmed. Please log in with your Reddit account to proceed.")
    reddit_auth_instance = praw.Reddit(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, redirect_uri=REDIRECT_URI, user_agent="AudienceFinder/Boyd (OAuth Setup)")
    auth_url = reddit_auth_instance.auth.url(scopes=["identity", "read"], state="unique_state_123", duration="permanent")
    st.link_button("Login with Reddit", auth_url, type="primary", use_container_width=True)
    st.info("ℹ️ You will be redirected to Reddit to grant permission. This app never sees your password.")

def show_main_app(reddit):
    # --- NIEUW: GEAVANCEERDE CONTROLES VOOR DE GEBRUIKER ---
    col1, col2 = st.columns([0.85, 0.15])
    with col1:
        st.title("🚀 The Audience Finder")
        st.markdown(f"Logged in as **u/{st.session_state.username}**. Discover relevant Reddit communities.")
    with col2:
        if st.button("Logout", use_container_width=True): st.session_state.clear(); st.rerun()

    with st.expander("⚙️ Advanced Search Settings"):
        st.markdown("Control the trade-off between search speed and thoroughness.")
        c1, c2, c3 = st.columns(3)
        with c1:
            direct_limit = st.slider("Direct Search Depth", 0, 50, 10, 1, help="How many communities to find based on their name or description. A quick way to find the most obvious communities.")
        with c2:
            post_limit = st.slider("Post Search Depth", 0, 50, 10, 1, help="How many posts to analyze across all of Reddit. This is great for finding communities where your topic is actively being discussed, even if it's not in their name.")
        with c3:
            comment_limit = st.slider("Comment Search Depth", 0, 50, 10, 1, help="How many comments *per post* to analyze. This is the deepest (and slowest) search, perfect for finding hidden conversations and real user pain points. Set to 0 to disable.")

    st.header("1. Enter Your Search Queries")
    with st.form(key='search_form'):
        search_queries_input = st.text_area("Queries (one per line)", height=150, label_visibility="collapsed", placeholder="For example:\nSaaS for startups...")
        submitted = st.form_submit_button("Find Communities", type="primary", use_container_width=True)

        if submitted:
            # --- NIEUW: ROBUUSTE ERROR HANDLING VOOR LIMIETEN ---
            queries_tuple = tuple(sorted([q.strip() for q in search_queries_input.split('\n') if q.strip()]))
            # Een simpele 'workload' berekening om overbelasting te voorkomen
            workload = len(queries_tuple) * (post_limit * (1 + comment_limit / 10))
            if not queries_tuple:
                st.warning("Please enter at least one search query.")
            elif workload > 5000: # Stel een veilige drempel in
                st.error(f"⚠️ Search is too demanding! Your current settings create a very high workload ({workload:.0f} units). Please reduce the number of queries or lower the search depth sliders.")
            else:
                st.session_state.search_params = {
                    "queries": queries_tuple, "direct": direct_limit,
                    "post": post_limit, "comment": comment_limit
                }
                
    if 'search_params' in st.session_state:
        p = st.session_state.search_params
        st.session_state['results_df'] = find_communities_hybrid(reddit, p['queries'], p['direct'], p['post'], p['comment'])
        del st.session_state.search_params # Verwijder om opnieuw zoeken te voorkomen bij refresh

    # Zoek in je show_main_app functie het deel waar je de dataframe toont.
    # Vervang de simpele st.download_button door dit volledige blok.

    if 'results_df' in st.session_state:
        results_df = st.session_state['results_df']
        st.header("2. Discovered Communities")
        if not results_df.empty:
            # Toon de dataframe in de app
            st.dataframe(results_df, use_container_width=True, hide_index=True)

            # --- START: GECORRIGEERDE EXCEL DOWNLOAD LOGICA ---
            st.header("3. Download Your Results")
            df_for_download = results_df.copy()
            
            # Voeg extra kolommen toe voor de gebruiker
            df_for_download['Status'] = 'Not Started'
            df_for_download['Priority'] = ''
            df_for_download['Notes'] = ''

            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Schrijf de data naar een 'Communities' tabblad
                df_for_download.to_excel(writer, index=False, sheet_name='Communities')
                workbook = writer.book
                worksheet = writer.sheets['Communities']
                
                # Definieer een stijl voor hyperlinks
                hyperlink_style = NamedStyle(name="hyperlink_style")
                hyperlink_style.font = Font(color="0000FF", underline="single")
                if "hyperlink_style" not in workbook.style_names:
                    workbook.add_named_style(hyperlink_style)

                # Vind de kolomletters voor de links
                link_cols = ['Community Link', 'Top Posts (Month)']
                for col_name in link_cols:
                    if col_name in df_for_download.columns:
                        col_letter = chr(65 + df_for_download.columns.get_loc(col_name))
                        # Pas de stijl toe op elke cel in die kolom (behalve de header)
                        for row in range(2, len(df_for_download) + 2):
                            worksheet[f'{col_letter}{row}'].style = "hyperlink_style"

                # Pas kolombreedtes dynamisch aan
                for i, col in enumerate(df_for_download.columns):
                    column = chr(65 + i)
                    max_len = max(df_for_download[col].astype(str).map(len).max(), len(col))
                    # Geef link-kolommen extra ruimte
                    width = 40 if "Link" in col or "Month" in col else max_len + 2
                    worksheet.column_dimensions[column].width = width
            
            excel_data = output.getvalue()
            st.download_button(
                label="⬇️ Download as Formatted Excel File", 
                data=excel_data, 
                file_name='audience_finder_results.xlsx', 
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
                use_container_width=True
            )
            # --- EINDE GECORRIGEERDE LOGICA ---
        else:
            st.success("✅ Search complete. No communities found for these terms with the current settings.")


# --- Hoofdlogica (onveranderd, maar zorg dat deze de finale versie is) ---
def main():
    st.set_page_config(page_title="The Audience Finder", layout="wide")
    # ... (De volledige, robuuste main() functie van de vorige versie) ...
    query_params = st.query_params
    auth_code = query_params.get("code")
    if "refresh_token" in st.session_state:
        reddit_instance = praw.Reddit(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, user_agent=f"AudienceFinder/Boyd (user: {st.session_state.get('username', '...')})", refresh_token=st.session_state["refresh_token"])
        show_main_app(reddit_instance)
        return
    if auth_code:
        try:
            temp_reddit = praw.Reddit(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, redirect_uri=REDIRECT_URI, user_agent="AudienceFinder/Boyd (Token Exchange)")
            refresh_token = temp_reddit.auth.authorize(auth_code)
            st.session_state["refresh_token"] = refresh_token
            user_reddit = praw.Reddit(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, user_agent="AudienceFinder/Boyd (Get Username)", refresh_token=refresh_token)
            st.session_state["username"] = user_reddit.user.me().name
            st.session_state["password_correct"] = True
            st.query_params.clear()
            st.rerun()
        except PRAWException as e:
            st.error(f"Reddit authentication failed: {e}. Please try again."); st.session_state.clear(); st.rerun()
        return
    if st.session_state.get("password_correct"):
        show_reddit_login_page()
        return
    show_password_form()


if __name__ == "__main__":
    main()