import streamlit as st
from scraping.model import MongoDBHandler
from scraping.service import run_scraping
from collections import Counter
import matplotlib.pyplot as plt
from wordcloud import WordCloud

# Initialize MongoDB
@st.cache_resource
def init_db(connection_uri):
    return MongoDBHandler(connection_uri)

# Get dashboard data
@st.cache_data(ttl=600)
def get_dashboard_data(sources, _db_handler):  # Tambahkan underscore
    articles = _db_handler.get_articles_by_sources(sources)
    
    # Process data
    keyword_counter = Counter()
    source_counter = Counter()
    
    for article in articles:
        keyword_counter.update(article.get("keywords", []))
        source_counter.update([article.get("source")])
    
    return {
        "articles": articles,
        "top_keywords": dict(keyword_counter.most_common(10)),
        "wordcloud_data": [[kw, count] for kw, count in keyword_counter.most_common(50)],
        "source_counts": dict(source_counter),
        "last_update": _db_handler.get_last_update()
    }

def main():
    st.set_page_config(
        page_title="Analisis Speech Delay",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Setup connection
    connection_uri = st.secrets["mongo"]["uri"]
    db_handler = init_db(connection_uri)
    
    # Sidebar controls
    with st.sidebar:
        st.title("Pengaturan")
        
        selected_sources = st.multiselect(
            "Pilih Sumber Data",
            options=["Haibunda", "Wikipedia", "Hellosehat"],
            default=["Haibunda", "Wikipedia", "Hellosehat"]
        )
        
        if st.button("🔄 Jalankan Scraping Sekarang"):
            with st.spinner("Sedang melakukan scraping..."):
                if run_scraping(connection_uri):
                    st.success("Scraping berhasil!")
                    st.experimental_rerun()
                else:
                    st.error("Terjadi error saat scraping")
    
    # Main content
    st.title("Analisis Artikel Speech Delay")
    
    # Get data
    data = get_dashboard_data(selected_sources, db_handler)
    
    # Last update and stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Artikel", len(data["articles"]))
    with col2:
        st.metric("Sumber Terpilih", ", ".join(selected_sources))
    with col3:
        st.metric("Terakhir Update", data["last_update"])
    
    # Visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Top 10 Keywords")
        st.bar_chart(data["top_keywords"])
        
    with col2:
        st.subheader("Distribusi Sumber")
        st.bar_chart(data["source_counts"])
    
    # Word cloud
    st.subheader("Word Cloud")
    if data["wordcloud_data"]:
        wordcloud = WordCloud(width=800, height=400, background_color='white').generate_from_frequencies(
            {kw[0]: kw[1] for kw in data["wordcloud_data"]}
        )
        plt.figure(figsize=(10, 5))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis("off")
        st.pyplot(plt)
    else:
        st.warning("Tidak ada data untuk ditampilkan")
    
    # Article list
    st.subheader("Daftar Artikel Terbaru")
    for article in data["articles"][:5]:
        with st.expander(f"{article['source']} - {article['title']}"):
            if "link" in article:
                st.markdown(f"[🔗 Buka Artikel]({article['link']})")
            st.write("**Keywords:**", ", ".join(article.get("keywords", [])))
            st.write(article.get("content", "")[:500] + "...")

if __name__ == "__main__":
    main()