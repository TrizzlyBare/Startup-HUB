import streamlit as st
import pandas as pd
from pathlib import Path
import json

# Set page config
st.set_page_config(
    page_title="Startup Group Search",
    page_icon="🔍",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .stTextInput > div > div > input {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 10px;
    }
    .stButton > button {
        background-color: #FF4B4B;
        color: white;
        border-radius: 10px;
        padding: 10px 20px;
        border: none;
    }
    .stButton > button:hover {
        background-color: #FF6B6B;
    }
    </style>
""", unsafe_allow_html=True)

def load_startup_groups():
    """Load startup groups data from JSON file"""
    try:
        with open(Path("Startup_HUB/Data/startup_groups.json"), 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("Startup groups data not found. Please ensure the data file exists.")
        return []

def search_groups(groups, query, filters):
    """Search groups based on query and filters"""
    if not query:
        return groups
    
    query = query.lower()
    results = []
    
    for group in groups:
        # Check if group matches search criteria
        name_match = query in group.get('name', '').lower()
        description_match = query in group.get('description', '').lower()
        industry_match = query in group.get('industry', '').lower()
        
        # Apply filters
        if filters['industry'] and group.get('industry') != filters['industry']:
            continue
            
        if filters['location'] and group.get('location') != filters['location']:
            continue
            
        if name_match or description_match or industry_match:
            results.append(group)
    
    return results

def main():
    st.title("🔍 Search Startup Groups")
    
    # Load data
    startup_groups = load_startup_groups()
    
    # Create two columns for search and filters
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Search input
        search_query = st.text_input("Search startup groups", placeholder="Enter keywords...")
    
    with col2:
        # Filters
        st.subheader("Filters")
        
        # Get unique industries and locations
        industries = sorted(list(set(group.get('industry', '') for group in startup_groups if group.get('industry'))))
        locations = sorted(list(set(group.get('location', '') for group in startup_groups if group.get('location'))))
        
        selected_industry = st.selectbox("Industry", ["All"] + industries)
        selected_location = st.selectbox("Location", ["All"] + locations)
        
        filters = {
            'industry': selected_industry if selected_industry != "All" else None,
            'location': selected_location if selected_location != "All" else None
        }
    
    # Search button
    if st.button("Search"):
        results = search_groups(startup_groups, search_query, filters)
        
        if not results:
            st.info("No startup groups found matching your criteria.")
        else:
            st.success(f"Found {len(results)} startup groups")
            
            # Display results in a grid
            for i in range(0, len(results), 2):
                cols = st.columns(2)
                for j in range(2):
                    if i + j < len(results):
                        group = results[i + j]
                        with cols[j]:
                            st.markdown(f"""
                                ### {group.get('name', 'Unnamed Group')}
                                **Industry:** {group.get('industry', 'N/A')}  
                                **Location:** {group.get('location', 'N/A')}  
                                **Members:** {len(group.get('members', []))}
                                
                                {group.get('description', 'No description available.')}
                                
                                ---
                            """)
                            
                            if st.button("View Details", key=f"view_{i+j}"):
                                st.session_state.selected_group = group
                                st.experimental_rerun()

if __name__ == "__main__":
    main()
