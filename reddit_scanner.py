import streamlit as st
import pandas as pd
import praw

# De @st.cache_data decorator zorgt ervoor dat als dezelfde gebruiker
# met dezelfde zoektermen zoekt, de data uit de cache komt.
# We moeten Streamlit vertellen de 'reddit' instance niet te hashen.
@st.cache_data(ttl="6h")
def find_communities(_reddit_user_info: str, search_queries: tuple):
    """
    Searches for relevant Reddit communities using a provided PRAW instance.
    
    _reddit_user_info is a dummy argument with the username to ensure
    the cache is per-user.
    search_queries must be a tuple to be hashable for the cache.
    """
    # De PRAW instance wordt nu doorgegeven vanuit de hoofapplicatie.
    # Hier maken we hem opnieuw aan binnen de gecachte functie.
    reddit = praw.Reddit(
        client_id=st.secrets["reddit_client_id"],
        client_secret=st.secrets["reddit_client_secret"],
        user_agent=f"AudienceFinder by Boyd v0.2 (user {_reddit_user_info})",
        refresh_token=st.session_state["refresh_token"]
    )
    
    aggregated_results = {}

    for query in search_queries:
        query = query.strip()
        if not query:
            continue
        
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
            # Print de error naar de terminal voor debugging
            print(f"Could not search with query '{query}'. Error: {e}")

    if not aggregated_results:
        return pd.DataFrame()

    final_list = list(aggregated_results.values())
    
    for item in final_list:
        item['Found By (Keywords)'] = ', '.join(sorted(list(item['Found By'])))
        del item['Found By']

    df = pd.DataFrame(final_list)

    if df.empty:
        return df

    df = df.sort_values(by='Members', ascending=False)
    
    column_order = [
        'Community', 'Members', 'Found By (Keywords)', 'Community Link', 'Top Posts (Month)'
    ]
    df = df[column_order].reset_index(drop=True)

    return df