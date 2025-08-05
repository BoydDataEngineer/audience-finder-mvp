# app.py - Audience Finder v2.0 met Professionele UI

import streamlit as st
import pandas as pd
from io import BytesIO
import praw
from openpyxl.styles import Font, NamedStyle
from praw.exceptions import PRAWException
import numpy as np

# --- Configuratie & Secrets ---
# ... (geen wijzigingen hier) ...
CLIENT_ID = st.secrets.get("reddit_client_id")
CLIENT_SECRET = st.secrets.get("reddit_client_secret")
APP_PASSWORD = st.secrets.get("app_password")
REDIRECT_URI = st.secrets.get("redirect_uri")

# --- De Hybride Zoekfunctie ---
# ... (geen wijzigingen hier) ...
def calculate_relevance_score(found_via_string):
    """Berekent een logische score op basis van de gevonden methodes."""
    score = 0
    if "Direct Search" in found_via_string: score += 1
    if "Relevant Post" in found_via_string: score += 2
    if "Relevant Comment" in found_via_string: score += 3
    return score

def find_communities_hybrid(_reddit_instance, search_queries: tuple, direct_limit: int, post_limit: int, comment_limit: int):
    """
    Vindt communities met een HYBRIDE aanpak en ondersteunt een cancel-operatie.
    """
    reddit = praw.Reddit(
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET,
        user_agent=f"AudienceFinder by Boyd v2.0 (pro_ui)",
        refresh_token=st.session_state.get("refresh_token")
    )
    aggregated_results = {}
    
    # We gebruiken een placeholder voor de progress bar die we in de hoofd-app aansturen
    progress_bar = st.session_state.get('progress_bar_placeholder')

    for i, query in enumerate(search_queries):
        # NIEUW: Controleer de cancel-status aan het begin van elke lus
        if st.session_state.get('cancel_scan'):
            st.warning("Search cancelled by user.")
            break
        
        if progress_bar:
            progress_bar.progress(i / len(search_queries), text=f"Searching for: '{query}'...")
            
        # ... (De rest van de zoeklogica blijft exact hetzelfde) ...
        try:
            for subreddit in reddit.subreddits.search(query, limit=direct_limit):
                if st.session_state.get('cancel_scan'): break
                if subreddit.display_name.startswith('u_'): continue
                if subreddit.display_name not in aggregated_results: aggregated_results[subreddit.display_name] = {'Community': subreddit.display_name, 'Members': subreddit.subscribers, 'Found Via': set()}
                aggregated_results[subreddit.display_name]['Found Via'].add('Direct Search')
        except PRAWException: pass
        if st.session_state.get('cancel_scan'): break
        try:
            for post in reddit.subreddit("all").search(query, sort="relevance", time_filter="month", limit=post_limit):
                if st.session_state.get('cancel_scan'): break
                if post.subreddit.display_name.startswith('u_') or post.subreddit.over18: continue
                community_name = post.subreddit.display_name
                if community_name not in aggregated_results: aggregated_results[community_name] = {'Community': community_name, 'Members': post.subreddit.subscribers, 'Found Via': set()}
                aggregated_results[community_name]['Found Via'].add('Relevant Post')
                if comment_limit > 0:
                    try:
                        post.comments.replace_more(limit=0)
                        for comment in post.comments.list()[:comment_limit]:
                            if st.session_state.get('cancel_scan'): break
                            if hasattr(comment, 'body') and query.lower() in comment.body.lower():
                                aggregated_results[community_name]['Found Via'].add('Relevant Comment'); break
                    except Exception: continue
        except PRAWException: pass

    if progress_bar: progress_bar.progress(1.0, text="Finalizing results...")
    if not aggregated_results: return pd.DataFrame()

    final_list = [{'Community': f"r/{name}", **data} for name, data in aggregated_results.items()]
    df = pd.DataFrame(final_list)
    if df.empty: return df

    df['Found Via'] = df['Found Via'].apply(lambda s: ', '.join(sorted(list(s))))
    df['Relevance Score'] = df['Found Via'].apply(calculate_relevance_score)
    df['Community Link'] = df['Community'].apply(lambda name: f"https://www.reddit.com/{name}")
    df['Top Posts (Month)'] = df['Community'].apply(lambda name: f"https://www.reddit.com/{name}/top/?t=month")
    df = df.sort_values(by=['Relevance Score', 'Members'], ascending=[False, False])
    column_order = ['Community', 'Relevance Score', 'Found Via', 'Members', 'Community Link', 'Top Posts (Month)']
    return df[column_order].reset_index(drop=True)

# --- UI Functies (Login) blijven onveranderd ---
# ... (geen wijzigingen hier) ...
def show_password_form():
    # ... (deze functie blijft hetzelfde) ...
    st.title("🚀 The Audience Finder"); st.header("App Access Login")
    with st.form(key='password_login_form'):
        password = st.text_input("Enter the app password", type="password", label_visibility="collapsed")
        if st.form_submit_button("Login", use_container_width=True):
            if password == APP_PASSWORD: st.session_state["password_correct"] = True; st.rerun()
            else: st.error("🚨 Incorrect password.")

def show_reddit_login_page():
    # ... (deze functie blijft hetzelfde) ...
    st.title("🚀 The Audience Finder"); st.header("Step 2: Connect your Reddit Account")
    st.markdown("Your access is confirmed. Please log in with your Reddit account to proceed.")
    reddit_auth_instance = praw.Reddit(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, redirect_uri=REDIRECT_URI, user_agent="AudienceFinder/Boyd (OAuth Setup)")
    auth_url = reddit_auth_instance.auth.url(scopes=["identity", "read"], state="unique_state_123", duration="permanent")
    st.link_button("Login with Reddit", auth_url, type="primary", use_container_width=True)
    st.info("ℹ️ You will be redirected to Reddit to grant permission. This app never sees your password.")

# --- Hoofdapplicatie (Met alle upgrades) ---
# --- Hoofdapplicatie (Met alle upgrades) ---
def show_main_app(reddit):
    # Initialiseer de session state variabelen
    if 'community_scan_running' not in st.session_state: st.session_state.community_scan_running = False
    if 'cancel_scan' not in st.session_state: st.session_state.cancel_scan = False
    if 'scan_was_cancelled' not in st.session_state: st.session_state.scan_was_cancelled = False

    col1, col2 = st.columns([0.85, 0.15])
    with col1:
        st.title("🚀 The Audience Finder")
        st.markdown(f"Logged in as **u/{st.session_state.username}**.")
    with col2:
        if st.button("Logout", use_container_width=True, disabled=st.session_state.community_scan_running):
            st.session_state.clear(); st.rerun()

    # AANGEPAST: De instellingen zijn nu uitgeschakeld tijdens het zoeken
    with st.expander("⚙️ Advanced Search Settings"):
        st.markdown("Control the trade-off between search speed and thoroughness.")
        c1, c2, c3 = st.columns(3)
        direct_limit = c1.slider("Direct Search Depth", 0, 50, 10, help="How many communities to find based on name/description. Quick but less precise.", disabled=st.session_state.community_scan_running)
        post_limit = c2.slider("Post Search Depth", 0, 100, 25, help="How many posts to analyze. Finds communities where your topic is actively discussed.", disabled=st.session_state.community_scan_running)
        comment_limit = c3.slider("Comment Search Depth", 0, 50, 20, help="How many comments *per post* to analyze. Deepest (and slowest) search for finding hidden user pain points.", disabled=st.session_state.community_scan_running)

    # AANGEPAST: Header is nu niet meer genummerd
    st.header("Discover Communities")
    with st.form(key='search_form'):
        # AANGEPAST: Tekstveld is nu ook uitgeschakeld tijdens het zoeken
        search_queries_input = st.text_area("Keywords (one per line)", height=150, label_visibility="collapsed", placeholder="For example:\nSaaS for startups...", disabled=st.session_state.community_scan_running)
        submitted = st.form_submit_button("Find Communities", type="primary", use_container_width=True, disabled=st.session_state.community_scan_running)

        if submitted:
            queries_tuple = tuple(sorted([q.strip() for q in search_queries_input.split('\n') if q.strip()]))
            if not queries_tuple:
                st.warning("Please enter at least one search query.")
            else:
                st.session_state.community_scan_running = True
                st.session_state.cancel_scan = False
                st.session_state.scan_was_cancelled = False # Reset cancel status bij nieuwe zoekopdracht
                st.session_state.search_params = {"queries": queries_tuple, "direct": direct_limit, "post": post_limit, "comment": comment_limit}
                st.rerun()
    
    if st.session_state.community_scan_running:
        st.info("Community search in progress...")
        if st.button("Cancel Search"):
            st.session_state.cancel_scan = True
            st.session_state.scan_was_cancelled = True
        
        st.session_state['progress_bar_placeholder'] = st.progress(0.0)
        
        try:
            p = st.session_state.search_params
            st.session_state['results_df'] = find_communities_hybrid(reddit, p['queries'], p['direct'], p['post'], p['comment'])
        finally:
            st.session_state.community_scan_running = False
            st.session_state.cancel_scan = False
            if 'search_params' in st.session_state: del st.session_state.search_params
            if 'progress_bar_placeholder' in st.session_state: del st.session_state['progress_bar_placeholder']
            st.rerun()

    if st.session_state.get("scan_was_cancelled"):
        st.warning("️️Search was cancelled by the user.")
        st.session_state.scan_was_cancelled = False 
        if 'results_df' in st.session_state: del st.session_state['results_df']

    elif 'results_df' in st.session_state:
        results_df = st.session_state['results_df']
        # AANGEPAST: De headers voor resultaten zijn samengevoegd en niet meer genummerd
        st.header("Search Results") 
        if not results_df.empty:
            st.dataframe(results_df, use_container_width=True, hide_index=True)
            
            # De download knop hoort logisch bij de resultaten
            df_for_download = results_df.copy()
            df_for_download['Status'], df_for_download['Priority'], df_for_download['Notes'] = 'Not Started', '', ''
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_for_download.to_excel(writer, index=False, sheet_name='Communities')
                workbook, worksheet = writer.book, writer.sheets['Communities']
                hyperlink_style = NamedStyle(name="hyperlink_style", font=Font(color="0000FF", underline="single"))
                if "hyperlink_style" not in workbook.style_names: workbook.add_named_style(hyperlink_style)
                for col_name in ['Community Link', 'Top Posts (Month)']:
                    if col_name in df_for_download.columns:
                        col_letter = chr(65 + df_for_download.columns.get_loc(col_name))
                        for row in range(2, len(df_for_download) + 2): worksheet[f'{col_letter}{row}'].style = "hyperlink_style"
                for i, col in enumerate(df_for_download.columns):
                    width = 40 if "Link" in df_for_download.columns[i] or "Month" in df_for_download.columns[i] else max(df_for_download[col].astype(str).map(len).max(), len(col)) + 2
                    worksheet.column_dimensions[chr(65 + i)].width = width
            excel_data = output.getvalue()
            st.download_button(label="⬇️ Download as Formatted Excel File", data=excel_data, file_name='audience_finder_results.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', use_container_width=True)
        else:
            st.success("✅ Search complete. No communities found for these terms.")
            
# --- Hoofdlogica (onveranderd) ---
# ... (geen wijzigingen hier) ...
def main():
    st.set_page_config(page_title="The Audience Finder", layout="wide")
    # ... (De volledige, robuuste main() functie blijft hetzelfde) ...
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
            st.query_params.clear(); st.rerun()
        except PRAWException as e: st.error(f"Reddit authentication failed: {e}. Please try again."); st.session_state.clear(); st.rerun()
        return
    if st.session_state.get("password_correct"):
        show_reddit_login_page()
        return
    show_password_form()

if __name__ == "__main__":
    main()