import streamlit as st
import os

st.set_page_config(page_title="Gemini Chatbot", page_icon="🤖")

if 'api_key' not in st.session_state:
    st.session_state.api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_CLOUD_API_KEY')

if 'client' not in st.session_state:
    st.session_state.client = None

if 'messages' not in st.session_state:
    st.session_state.messages = []

st.title("🤖 Gemini Chatbot")
st.write("Chat with Google's Gemini AI model")

if not st.session_state.api_key:
    st.warning("⚠️ No API key found in environment variables.")
    st.write("Please enter your Gemini API key to get started.")
    st.write("Get your API key from: https://aistudio.google.com/apikey")
    
    api_key_input = st.text_input("Gemini API Key", type="password", key="api_key_input")
    
    if st.button("Set API Key"):
        if api_key_input:
            st.session_state.api_key = api_key_input
            st.success("API key set successfully!")
            st.rerun()
        else:
            st.error("Please enter an API key.")
    st.stop()

if st.session_state.client is None:
    try:
        from google import genai
        st.session_state.client = genai.Client(api_key=st.session_state.api_key)
        st.session_state.chat = st.session_state.client.chats.create(model='gemini-2.5-flash')
    except Exception as e:
        st.error(f"Failed to initialize Gemini client: {str(e)}")
        st.error("Please check your API key and try again.")
        if st.button("Reset API Key"):
            st.session_state.api_key = None
            st.session_state.client = None
            st.rerun()
        st.stop()

for message in st.session_state.messages:
    with st.chat_message(message['role']):
        st.write(message['content'])

if prompt := st.chat_input("Type your message..."):
    st.session_state.messages.append({'role': 'user', 'content': prompt})
    with st.chat_message('user'):
        st.write(prompt)
    
    try:
        response = st.session_state.chat.send_message(prompt)
        assistant_message = response.text
        
        st.session_state.messages.append({'role': 'assistant', 'content': assistant_message})
        with st.chat_message('assistant'):
            st.write(assistant_message)
    except Exception as e:
        st.error(f"Error getting response from Gemini: {str(e)}")
        if st.button("Reset API Key"):
            st.session_state.api_key = None
            st.session_state.client = None
            st.rerun()
