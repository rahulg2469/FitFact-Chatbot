import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import sys
import os
from datetime import datetime, timedelta

# Add database_files to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'database_files'))
from database_files.database import FitFactDB

# Page config
st.set_page_config(
    page_title="FitFact Analytics Dashboard",
    page_icon="💪",
    layout="wide"
)

# Initialize database
@st.cache_resource
def get_db():
    return FitFactDB()

db = get_db()

# Title
st.title("💪 FitFact Chatbot Analytics Dashboard")
st.markdown("### Real-time insights into fitness research and chatbot performance")

# Sidebar filters
st.sidebar.header("Filters")
time_range = st.sidebar.selectbox(
    "Time Range",
    ["Last 24 Hours", "Last 7 Days", "Last 30 Days", "All Time"]
)

# Convert time range to datetime
now = datetime.now()
if time_range == "Last 24 Hours":
    start_date = now - timedelta(days=1)
elif time_range == "Last 7 Days":
    start_date = now - timedelta(days=7)
elif time_range == "Last 30 Days":
    start_date = now - timedelta(days=30)
else:
    start_date = datetime(2020, 1, 1)

# ===== SECTION 1: KEY METRICS =====
st.header("📊 Key Metrics")

col1, col2, col3, col4 = st.columns(4)

# Total Papers
with col1:
    try:
        total_papers = db.conn.execute("SELECT COUNT(*) FROM research_papers").fetchone()[0]
        st.metric("Total Research Papers", f"{total_papers:,}")
    except Exception as e:
        st.metric("Total Research Papers", "0")
        st.caption(f"Error: {e}")

# Total Queries
with col2:
    try:
        total_queries = db.conn.execute("SELECT COUNT(*) FROM user_queries").fetchone()[0]
        st.metric("Total Queries Processed", f"{total_queries:,}")
    except Exception as e:
        st.metric("Total Queries Processed", "0")
        st.caption(f"Error: {e}")

# Cache Hit Rate
with col3:
    try:
        cache_hits = db.conn.execute("SELECT COUNT(*) FROM user_queries WHERE cache_hit = TRUE").fetchone()[0]
        total_q = db.conn.execute("SELECT COUNT(*) FROM user_queries").fetchone()[0]
        cache_rate = (cache_hits / total_q * 100) if total_q > 0 else 0
        st.metric("Cache Hit Rate", f"{cache_rate:.1f}%")
    except Exception as e:
        st.metric("Cache Hit Rate", "N/A")
        st.caption(f"Error: {e}")

# Avg Response Time
with col4:
    try:
        avg_time = db.conn.execute("SELECT AVG(response_time_ms) FROM user_queries WHERE response_time_ms IS NOT NULL").fetchone()[0]
        st.metric("Avg Response Time", f"{avg_time:.0f}ms" if avg_time else "N/A")
    except Exception as e:
        st.metric("Avg Response Time", "N/A")
        st.caption(f"Error: {e}")

st.divider()

# ===== SECTION 2: QUERY ANALYTICS =====
st.header("🔍 Query Analytics")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Top 10 Most Searched Topics")
    try:
        # Get top queries
        query_data = pd.read_sql_query(
            """
            SELECT query_text, COUNT(*) as count
            FROM user_queries
            GROUP BY query_text
            ORDER BY count DESC
            LIMIT 10
            """,
            db.conn
        )
        
        if not query_data.empty:
            # Truncate long queries for display
            query_data['short_query'] = query_data['query_text'].str[:60] + '...'
            
            fig = px.bar(
                query_data,
                x='count',
                y='short_query',
                orientation='h',
                title='',
                labels={'count': 'Number of Queries', 'short_query': ''},
                color='count',
                color_continuous_scale='Blues'
            )
            fig.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No query data available yet. Start using the chatbot to see analytics!")
    except Exception as e:
        st.error(f"Error loading query data: {e}")

with col2:
    st.subheader("Query Volume Over Time")
    try:
        # Get queries by date
        time_data = pd.read_sql_query(
            """
            SELECT DATE(timestamp) as date, COUNT(*) as count
            FROM user_queries
            GROUP BY DATE(timestamp)
            ORDER BY date DESC
            LIMIT 30
            """,
            db.conn
        )
        
        if not time_data.empty:
            fig = px.line(
                time_data,
                x='date',
                y='count',
                title='',
                labels={'count': 'Queries', 'date': 'Date'},
                markers=True
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No time-series data available yet. Query history will appear here over time.")
    except Exception as e:
        st.error(f"Error loading time data: {e}")

st.divider()

# ===== SECTION 3: RESEARCH DATABASE =====
st.header("📚 Research Database Insights")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Papers by Publication Year")
    try:
        year_data = pd.read_sql_query(
            """
            SELECT EXTRACT(YEAR FROM publication_date) as year, COUNT(*) as count
            FROM research_papers
            WHERE publication_date IS NOT NULL
            GROUP BY year
            ORDER BY year DESC
            LIMIT 10
            """,
            db.conn
        )
        
        if not year_data.empty:
            fig = px.bar(
                year_data,
                x='year',
                y='count',
                title='',
                labels={'count': 'Number of Papers', 'year': 'Year'},
                color='count',
                color_continuous_scale='Greens'
            )
            fig.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No publication data available. Papers will appear here once indexed.")
    except Exception as e:
        st.error(f"Error loading publication data: {e}")

with col2:
    st.subheader("Most Cited Papers")
    try:
        citation_data = pd.read_sql_query(
            """
            SELECT p.title, COUNT(c.response_id) as citations
            FROM research_papers p
            LEFT JOIN response_citations c ON p.paper_id = c.paper_id
            GROUP BY p.paper_id, p.title
            ORDER BY citations DESC
            LIMIT 10
            """,
            db.conn
        )
        
        if not citation_data.empty and citation_data['citations'].sum() > 0:
            # Truncate long titles
            citation_data['short_title'] = citation_data['title'].str[:50] + '...'
            
            fig = px.bar(
                citation_data,
                x='citations',
                y='short_title',
                orientation='h',
                title='',
                labels={'citations': 'Times Cited', 'short_title': ''},
                color='citations',
                color_continuous_scale='Purples'
            )
            fig.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No citation data available yet. Papers cited in responses will appear here.")
    except Exception as e:
        st.error(f"Error loading citation data: {e}")

st.divider()

# ===== SECTION 4: PERFORMANCE METRICS =====
st.header("⚡ System Performance")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Response Time Distribution")
    try:
        perf_data = pd.read_sql_query(
            """
            SELECT response_time_ms
            FROM user_queries
            WHERE response_time_ms IS NOT NULL
            """,
            db.conn
        )
        
        if not perf_data.empty:
            fig = px.histogram(
                perf_data,
                x='response_time_ms',
                nbins=30,
                title='',
                labels={'response_time_ms': 'Response Time (ms)', 'count': 'Frequency'},
                color_discrete_sequence=['#636EFA']
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No performance data available yet. Response times will be tracked here.")
    except Exception as e:
        st.error(f"Error loading performance data: {e}")

with col2:
    st.subheader("Cache Performance")
    try:
        cache_data = pd.read_sql_query(
            """
            SELECT cache_hit, COUNT(*) as count
            FROM user_queries
            GROUP BY cache_hit
            """,
            db.conn
        )
        
        if not cache_data.empty:
            cache_data['status'] = cache_data['cache_hit'].map({True: 'Cache Hit', False: 'Cache Miss'})
            
            fig = px.pie(
                cache_data,
                values='count',
                names='status',
                title='',
                color_discrete_sequence=['#00CC96', '#EF553B']
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No cache data available yet. Cache performance will be tracked here.")
    except Exception as e:
        st.error(f"Error loading cache data: {e}")

# ===== SECTION 5: ADDITIONAL INSIGHTS =====
st.divider()
st.header("📈 Additional Insights")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Most Active Topics")
    try:
        topic_data = pd.read_sql_query(
            """
            SELECT t.topic_name, COUNT(uq.query_id) as query_count
            FROM topics t
            LEFT JOIN user_queries uq ON uq.detected_topic = t.topic_name
            GROUP BY t.topic_name
            ORDER BY query_count DESC
            LIMIT 10
            """,
            db.conn
        )
        
        if not topic_data.empty and topic_data['query_count'].sum() > 0:
            fig = px.pie(
                topic_data,
                values='query_count',
                names='topic_name',
                title=''
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No topic data available yet.")
    except Exception as e:
        st.error(f"Error: {e}")

with col2:
    st.subheader("Database Health")
    try:
        # Get various stats with error handling for each
        health_metrics = []
        
        try:
            db.cursor.execute("SELECT COUNT(*) FROM research_papers")
            total_papers = db.cursor.fetchone()[0]
            health_metrics.append({'Metric': 'Research Papers', 'Count': total_papers})
        except:
            health_metrics.append({'Metric': 'Research Papers', 'Count': 0})
        
        try:
            db.cursor.execute("SELECT COUNT(*) FROM cached_responses")
            total_cached = db.cursor.fetchone()[0]
            health_metrics.append({'Metric': 'Cached Responses', 'Count': total_cached})
        except:
            health_metrics.append({'Metric': 'Cached Responses', 'Count': 0})
        
        try:
            db.cursor.execute("SELECT COUNT(*) FROM user_queries")
            total_queries = db.cursor.fetchone()[0]
            health_metrics.append({'Metric': 'Total Queries', 'Count': total_queries})
        except:
            health_metrics.append({'Metric': 'Total Queries', 'Count': 0})
        
        try:
            db.cursor.execute("SELECT COUNT(*) FROM topics")
            total_topics = db.cursor.fetchone()[0]
            health_metrics.append({'Metric': 'Topics Tracked', 'Count': total_topics})
        except:
            health_metrics.append({'Metric': 'Topics Tracked', 'Count': 0})
        
        health_data = pd.DataFrame(health_metrics)
        
        fig = px.bar(
            health_data,
            x='Metric',
            y='Count',
            title='',
            color='Count',
            color_continuous_scale='Viridis'
        )
        fig.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error loading database health: {str(e)}")

# Footer
st.divider()
st.markdown("""  
**Last updated:** """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """  
**FitFact Chatbot** - Evidence-based fitness Q&A powered by PubMed research
""")