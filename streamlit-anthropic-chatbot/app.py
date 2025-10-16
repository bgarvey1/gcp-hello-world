import streamlit as st
import os

st.set_page_config(page_title="Claude Chatbot with Tools", page_icon="🤖")

if 'api_key' not in st.session_state:
    st.session_state.api_key = os.environ.get('ANTHROPIC_API_KEY')

if 'client' not in st.session_state:
    st.session_state.client = None

if 'messages' not in st.session_state:
    st.session_state.messages = []

def calculate_sum(a: float, b: float) -> float:
    return a + b

tools = [
    {
        "name": "calculate_sum",
        "description": "Calculate the sum of two numbers. Use this when the user asks you to add numbers together.",
        "input_schema": {
            "type": "object",
            "properties": {
                "a": {
                    "type": "number",
                    "description": "The first number to add"
                },
                "b": {
                    "type": "number",
                    "description": "The second number to add"
                }
            },
            "required": ["a", "b"]
        }
    }
]

st.title("🤖 Claude Chatbot with Tools")
st.write("Chat with Anthropic's Claude AI model")
st.info("🔧 Tool available: calculate_sum - Can add two numbers together")

if not st.session_state.api_key:
    st.warning("⚠️ No API key found in environment variables.")
    st.write("Please enter your Anthropic API key to get started.")
    st.write("Get your API key from: https://console.anthropic.com/settings/keys")
    
    api_key_input = st.text_input("Anthropic API Key", type="password", key="api_key_input")
    
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
        from anthropic import Anthropic
        st.session_state.client = Anthropic(api_key=st.session_state.api_key)
    except Exception as e:
        st.error(f"Failed to initialize Anthropic client: {str(e)}")
        st.error("Please check your API key and try again.")
        if st.button("Reset API Key"):
            st.session_state.api_key = None
            st.session_state.client = None
            st.rerun()
        st.stop()

for message in st.session_state.messages:
    with st.chat_message(message['role']):
        if isinstance(message['content'], str):
            st.write(message['content'])
        elif isinstance(message['content'], list):
            for item in message['content']:
                if isinstance(item, dict) and item.get('type') == 'tool_result':
                    continue
                st.write(str(item))

if prompt := st.chat_input("Type your message..."):
    st.session_state.messages.append({'role': 'user', 'content': prompt})
    with st.chat_message('user'):
        st.write(prompt)
    
    try:
        response = st.session_state.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=8096,
            messages=st.session_state.messages,
            tools=tools
        )
        
        while response.stop_reason == "tool_use":
            st.session_state.messages.append({
                "role": "assistant",
                "content": response.content
            })
            
            with st.chat_message('assistant'):
                for block in response.content:
                    if hasattr(block, 'text'):
                        st.write(block.text)
                    elif block.type == "tool_use":
                        st.info(f"🔧 Calling tool: {block.name} with inputs: {block.input}")
            
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    if block.name == "calculate_sum":
                        result = calculate_sum(
                            a=block.input["a"],
                            b=block.input["b"]
                        )
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(result)
                        })
            
            st.session_state.messages.append({
                "role": "user",
                "content": tool_results
            })
            
            response = st.session_state.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=8096,
                messages=st.session_state.messages,
                tools=tools
            )
        
        assistant_message = ""
        for block in response.content:
            if hasattr(block, "text"):
                assistant_message += block.text
        
        st.session_state.messages.append({'role': 'assistant', 'content': assistant_message})
        with st.chat_message('assistant'):
            st.write(assistant_message)
            
    except Exception as e:
        st.error(f"Error getting response from Claude: {str(e)}")
        if st.button("Reset API Key"):
            st.session_state.api_key = None
            st.session_state.client = None
            st.rerun()
