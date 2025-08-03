import streamlit as st
import praw
import pandas as pd
from collections import defaultdict

# --- Haal de keys op uit Streamlit Secrets ---
CLIENT_ID = st.secrets["reddit_client_id"]
CLIENT_SECRET = st.secrets["reddit_client_secret"]
USER_AGENT = "AudienceFinder by Boyd v0.1"

def find_communities(search_queries: list):
    """
    Searches for relevant Reddit communities, aggregates duplicate finds,
    and lists all keywords that found the community.
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

    # --- NIEUWE LOGICA: Gebruik een dictionary om resultaten te aggregeren ---
    # De sleutel is de naam van de community, de waarde is de data.
    aggregated_results = {}

    for query in search_queries:
        query = query.strip()
        if not query:
            continue
        
        try:
            for subreddit in reddit.subreddits.search(query, limit=7):
                community_name = subreddit.display_name

                # Als we deze community al eerder hebben gevonden...
                if community_name in aggregated_results:
                    # ...voeg dan alleen de nieuwe zoekterm toe aan de lijst.
                    aggregated_results[community_name]['Found By'].add(query)
                # Als dit de eerste keer is dat we de community zien...
                else:
                    # ...maak dan een nieuwe entry aan.
                    aggregated_results[community_name] = {
                        'Community': community_name,
                        'Members': subreddit.subscribers,
                        'Community Link': f"https://www.reddit.com/r/{community_name}",
                        'Top Posts (Month)': f"https://www.reddit.com/r/{community_name}/top/?t=month",
                        # Gebruik een 'set' om automatische duplicaten van keywords te voorkomen
                        'Found By': {query} 
                    }
        except Exception as e:
            print(f"Could not search with query '{query}'. Error: {e}")

    if not aggregated_results:
        return pd.DataFrame()

    # --- Converteer de geaggregeerde data naar een lijst voor het DataFrame ---
    final_list = list(aggregated_results.values())
    
    # Maak de 'Found By' set leesbaar door het om te zetten naar een string
    for item in final_list:
        item['Found By (Keywords)'] = ', '.join(sorted(list(item['Found By'])))
        del item['Found By'] # Verwijder de tijdelijke 'set'

    # Maak het definitieve DataFrame
    df = pd.DataFrame(final_list)

    # Sorteer op ledenaantal en zorg voor een schone volgorde van kolommen
    df = df.sort_values(by='Members', ascending=False)
    # Definieer de gewenste kolomvolgorde
    column_order = [
        'Community', 
        'Members', 
        'Found By (Keywords)', 
        'Community Link', 
        'Top Posts (Month)'
    ]
    df = df[column_order].reset_index(drop=True)

    return df
