import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd
import os

ALLOWED_EMAIL = os.environ.get('ALLOWED_EMAIL')

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("Login")
    st.write("Please enter your email to access the app.")
    
    email = st.text_input("Email", key="email_input")
    
    if st.button("Login"):
        if email == ALLOWED_EMAIL:
            st.session_state.logged_in = True
            st.success("Login successful!")
            st.rerun()
        else:
            st.error(f"Access denied. Only {ALLOWED_EMAIL} is allowed.")
else:
    st.title("Hello World App")
    
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()
    
    conn = sqlite3.connect('names.db', check_same_thread=False)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS names
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  timestamp TEXT NOT NULL)''')
    conn.commit()
    
    name = st.text_input("What's your name?", key="name_input")
    
    if name:
        st.write(f"Hello {name}!")
        
        if st.button("Save Name"):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute("INSERT INTO names (name, timestamp) VALUES (?, ?)", (name, timestamp))
            conn.commit()
            st.success(f"Saved {name} at {timestamp}")
    
    st.subheader("Saved Names")
    c.execute("SELECT name, timestamp FROM names ORDER BY id ASC")
    rows = c.fetchall()
    
    if rows:
        df = pd.DataFrame(rows, columns=['Name', 'Timestamp'])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No names saved yet.")
