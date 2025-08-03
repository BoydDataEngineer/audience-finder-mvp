import praw
import pandas as pd
import streamlit as st

CLIENT_ID = st.secrets["reddit_client_id"]
CLIENT_SECRET = st.secrets["reddit_client_secret"]
USER_AGENT = "AudienceFinder by Boyd v0.1"

def find_communities(search_queries: list):
    """
    Searches for relevant Reddit communities based on a list of search queries.
    Each item in the list can contain multiple words.
    """
    try:
        reddit = praw.Reddit(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            user_agent=USER_AGENT,
        )
    except Exception as e:
        print(f"Error initializing Reddit client: {e}")
        raise e

    all_results = []

    for query in search_queries:
        query = query.strip()
        if not query:
            continue
        
        try:
            for subreddit in reddit.subreddits.search(query, limit=7): 
                community_data = {
                    'Search Query': query, # Changed to English
                    'Community': subreddit.display_name,
                    'Members': subreddit.subscribers, # Changed to English
                    'Community Link': f"https://www.reddit.com/r/{subreddit.display_name}",
                    'Top Posts (Month)': f"https://www.reddit.com/r/{subreddit.display_name}/top/?t=month"
                }
                all_results.append(community_data)
        except Exception as e:
            print(f"Could not search with query '{query}'. Error: {e}")

    if all_results:
        df = pd.DataFrame(all_results)
        df = df.sort_values(by='Members', ascending=False).reset_index(drop=True)
        return df
    else:
        return pd.DataFrame()