import streamlit as st
import pandas as pd
import sqlite3
import uuid

# Page configuration
st.set_page_config(page_title="NicheAI Gig Hub | Vetted AI Training Jobs", page_icon="🎯", layout="wide")

# --- INITIALIZE DATABASE ---
def init_db():
    conn = sqlite3.connect("gigs.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gigs (
            id TEXT PRIMARY KEY,
            title TEXT,
            company TEXT,
            category TEXT,
            pay_rate TEXT,
            vetted_tier TEXT,
            apply_link TEXT,
            description TEXT
        )
    """)
    
    # Insert sample seed data if empty
    cursor.execute("SELECT COUNT(*) FROM gigs")
    if cursor.fetchone()[0] == 0:
        sample_data = [
            ("1", "Legal AI Prompt Engineer & Red Teamer", "ApexLLM Labs", "Law / Compliance", "$55/hr", "Elite ($50+/hr)", "https://example.com/apply1", "Review complex corporate contracts for AI model hallucination and safety alignment."),
            ("2", "Medical Dataset Annotator (Cardiology)", "HealthTrain AI", "Healthcare", "$45/hr", "Elite ($50+/hr)", "https://example.com/apply2", "Tag medical imaging data and clinical notes for diagnostic LLM training."),
            ("3", "Python Code Evaluator & Benchmark Builder", "CodeFlow AI", "Software Engineering", "$40/hr", "Mid-Tier ($30-$50/hr)", "https://example.com/apply3", "Write unit tests and evaluate complex Python code generation outputs."),
            ("4", "General Fact-Checker & RAG Curator", "ScaleTask", "General / Writing", "$22/hr", "Standard (<$30/hr)", "https://example.com/apply4", "Verify sources and ensure factual accuracy for search-augmented generation data.")
        ]
        cursor.executemany("INSERT INTO gigs VALUES (?, ?, ?, ?, ?, ?, ?, ?)", sample_data)
        conn.commit()
    return conn

db_conn = init_db()

# --- SESSION STATE FOR MEMBERSHIP ---
if "is_premium" not in st.session_state:
    st.session_state.is_premium = False

# --- SIDEBAR: MONETIZATION & FILTERS ---
with st.sidebar:
    st.title("🎯 NicheAI Hub")
    st.markdown("Skip the spam. Verified, high-paying AI training & contractor roles updated daily.")
    st.markdown("---")
    
    st.subheader("🔓 Membership Access")
    if st.session_state.is_premium:
        st.success("✨ VIP Access Active (All Gigs Unlocked)")
    else:
        st.info("🔒 Free Tier: Viewing basic listings. Upgrade to unlock $40+/hr direct apply links.")
        if st.button("Unlock All Gigs — $15 Lifetime Access", type="primary", use_container_width=True):
            # In production, replace this with your Stripe Payment Link URL
            st.session_state.is_premium = True
            st.rerun()
            
    st.markdown("---")
    st.subheader("🔍 Filter Gigs")
    category_filter = st.selectbox("Domain Expertise", ["All", "Law / Compliance", "Healthcare", "Software Engineering", "General / Writing"])
    tier_filter = st.selectbox("Pay Tier", ["All", "Elite ($50+/hr)", "Mid-Tier ($30-$50/hr)", "Standard (<$30/hr)"])

# --- MAIN CONTENT ---
st.title("Vetted AI Training & Niche Contractor Board")
st.markdown("High-intent micro-gigs collected from direct company boards. Filter by your expertise below.")
st.markdown("---")

# Fetch data from SQLite
cursor = db_conn.cursor()
query = "SELECT * FROM gigs WHERE 1=1"
params = []

if category_filter != "All":
    query += " AND category = ?"
    params.append(category_filter)
if tier_filter != "All":
    query += " AND vetted_tier = ?"
    params.append(tier_filter)

cursor.execute(query, params)
gigs = cursor.fetchall()

# Display Gigs
if not gigs:
    st.warning("No gigs match your current filter criteria.")
else:
    for gig in gigs:
        gig_id, title, company, category, pay_rate, vetted_tier, apply_link, description = gig
        
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.subheader(title)
                st.markdown(f"**Company:** {company} &nbsp;|&nbsp; **Domain:** `{category}`")
                st.write(description)
            with col2:
                st.markdown(f"### `{pay_rate}`")
                st.caption(f"Tier: {vetted_tier}")
                
                # Gate the apply link behind the $15 premium wall
                if vetted_tier == "Elite ($50+/hr)" and not st.session_state.is_premium:
                    st.warning("🔒 Locked (VIP Only)")
                else:
                    st.link_button("Apply Direct ↗", apply_link, use_container_width=True)

# Footer admin tool to add a gig (for you to test managing it)
with st.expander("🛠️ Admin: Add New Gig"):
    with st.form("add_gig_form"):
        new_title = st.text_input("Job Title")
        new_company = st.text_input("Company")
        new_cat = st.selectbox("Category", ["Law / Compliance", "Healthcare", "Software Engineering", "General / Writing"])
        new_pay = st.text_input("Pay Rate (e.g. $50/hr)")
        new_tier = st.selectbox("Tier", ["Elite ($50+/hr)", "Mid-Tier ($30-$50/hr)", "Standard (<$30/hr)"])
        new_link = st.text_input("Direct Apply URL")
        new_desc = st.text_area("Description")
        
        submitted = st.form_submit_button("Publish Gig")
        if submitted:
            c = db_conn.cursor()
            c.execute("INSERT INTO gigs VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                      (str(uuid.uuid4()), new_title, new_company, new_cat, new_pay, new_tier, new_link, new_desc))
            db_conn.commit()
            st.success("Gig published successfully!")
            st.rerun()
