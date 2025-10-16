import streamlit as st
import os
import asyncio
import sys

st.set_page_config(page_title="Claude Chatbot with MCP Tools", page_icon="🤖")

if 'api_key' not in st.session_state:
    st.session_state.api_key = os.environ.get('ANTHROPIC_API_KEY')

if 'client' not in st.session_state:
    st.session_state.client = None

if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'mcp_session' not in st.session_state:
    st.session_state.mcp_session = None

if 'mcp_tools' not in st.session_state:
    st.session_state.mcp_tools = []

if 'mcp_initialized' not in st.session_state:
    st.session_state.mcp_initialized = False


async def start_mcp_server():
    """Start MCP server and connect to it."""
    from mcp.client.stdio import StdioServerParameters, stdio_client
    from mcp.client.session import ClientSession
    
    server_script = os.path.join(os.path.dirname(__file__), "mcp_server.py")
    
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[server_script],
    )
    
    stdio_context = stdio_client(server_params)
    read_stream, write_stream = await stdio_context.__aenter__()
    
    session = ClientSession(read_stream, write_stream)
    
    await session.__aenter__()
    await session.initialize()
    
    tools_result = await session.list_tools()
    
    return session, tools_result.tools


def convert_mcp_tools_to_anthropic(mcp_tools):
    """Convert MCP tool format to Anthropic tool format."""
    anthropic_tools = []
    for tool in mcp_tools:
        anthropic_tools.append({
            "name": tool.name,
            "description": tool.description or "",
            "input_schema": tool.inputSchema
        })
    return anthropic_tools


st.title("🤖 Claude Chatbot with MCP Tools")
st.write("Chat with Anthropic's Claude AI model using MCP (Model Context Protocol)")

if st.session_state.api_key and not st.session_state.mcp_initialized:
    try:
        with st.spinner("Starting MCP server..."):
            session, mcp_tools = asyncio.run(start_mcp_server())
            st.session_state.mcp_session = session
            st.session_state.mcp_tools = convert_mcp_tools_to_anthropic(mcp_tools)
            st.session_state.mcp_initialized = True
            
            for tool in st.session_state.mcp_tools:
                st.success(f"🔧 MCP Tool available: {tool['name']} - {tool['description']}")
    except Exception as e:
        st.error(f"Failed to start MCP server: {str(e)}")
        st.error(f"Error details: {type(e).__name__}")
        import traceback
        st.error(traceback.format_exc())
        st.stop()

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
            tools=st.session_state.mcp_tools
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
                        st.info(f"🔧 Calling MCP tool: {block.name} with inputs: {block.input}")
            
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = asyncio.run(
                        st.session_state.mcp_session.call_tool(
                            block.name,
                            arguments=block.input
                        )
                    )
                    
                    result_content = ""
                    for content_item in result.content:
                        if hasattr(content_item, 'text'):
                            result_content += content_item.text
                    
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_content
                    })
            
            st.session_state.messages.append({
                "role": "user",
                "content": tool_results
            })
            
            response = st.session_state.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=8096,
                messages=st.session_state.messages,
                tools=st.session_state.mcp_tools
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
        import traceback
        st.error(traceback.format_exc())
        if st.button("Reset API Key"):
            st.session_state.api_key = None
            st.session_state.client = None
            st.session_state.mcp_initialized = False
            st.rerun()
