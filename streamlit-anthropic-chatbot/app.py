import streamlit as st
import os
import asyncio
import sys
from datetime import datetime

st.set_page_config(page_title="Claude Chatbot with MCP Tools", page_icon="🤖")

if 'api_key' not in st.session_state:
    st.session_state.api_key = os.environ.get('ANTHROPIC_API_KEY')

if 'client' not in st.session_state:
    st.session_state.client = None

if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'mcp_sessions' not in st.session_state:
    st.session_state.mcp_sessions = {}

if 'mcp_tools' not in st.session_state:
    st.session_state.mcp_tools = []

if 'mcp_initialized' not in st.session_state:
    st.session_state.mcp_initialized = False

if 'event_loop' not in st.session_state:
    st.session_state.event_loop = None

if 'stdio_contexts' not in st.session_state:
    st.session_state.stdio_contexts = []


async def start_mcp_servers():
    """Start all MCP servers and connect to them."""
    from mcp.client.stdio import StdioServerParameters, stdio_client
    from mcp.client.session import ClientSession
    
    sessions = {}
    all_tools = []
    contexts = []
    
    server_script = os.path.join(os.path.dirname(__file__), "mcp_server.py")
    
    calc_params = StdioServerParameters(
        command=sys.executable,
        args=[server_script],
    )
    
    calc_context = stdio_client(calc_params)
    calc_read, calc_write = await calc_context.__aenter__()
    calc_session = ClientSession(calc_read, calc_write)
    await calc_session.__aenter__()
    await calc_session.initialize()
    calc_tools = await calc_session.list_tools()
    
    for tool in calc_tools.tools:
        sessions[tool.name] = calc_session
    all_tools.extend(calc_tools.tools)
    contexts.append(calc_context)
    
    brave_api_key = os.environ.get('BRAVE_API_KEY')
    if brave_api_key:
        brave_params = StdioServerParameters(
            command="npx",
            args=["-y", "@brave/brave-search-mcp-server"],
            env={"BRAVE_API_KEY": brave_api_key}
        )
        
        brave_context = stdio_client(brave_params)
        brave_read, brave_write = await brave_context.__aenter__()
        brave_session = ClientSession(brave_read, brave_write)
        await brave_session.__aenter__()
        await brave_session.initialize()
        brave_tools = await brave_session.list_tools()
        
        for tool in brave_tools.tools:
            sessions[tool.name] = brave_session
        all_tools.extend(brave_tools.tools)
        contexts.append(brave_context)
    
    return sessions, all_tools, contexts


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


def get_system_prompt():
    """Generate system prompt with current date."""
    current_date = datetime.utcnow().strftime("%B %d, %Y")
    return f"You are a helpful AI assistant with access to supplemental tools. The current date is {current_date}. Use your baseline knowledge and capabilities to answer questions. Only call tools when they would provide specific additional value beyond your built-in knowledge."


st.title("🤖 Claude Chatbot with MCP Tools")
st.write("Chat with Anthropic's Claude AI model using MCP (Model Context Protocol)")

if st.session_state.api_key and not st.session_state.mcp_initialized:
    try:
        with st.spinner("Starting MCP servers..."):
            if st.session_state.event_loop is None:
                st.session_state.event_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(st.session_state.event_loop)
            
            loop = st.session_state.event_loop
            sessions, mcp_tools, stdio_contexts = loop.run_until_complete(start_mcp_servers())
            st.session_state.mcp_sessions = sessions
            st.session_state.stdio_contexts = stdio_contexts
            st.session_state.mcp_tools = convert_mcp_tools_to_anthropic(mcp_tools)
            st.session_state.mcp_initialized = True
            
            for tool in st.session_state.mcp_tools:
                st.success(f"🔧 MCP Tool available: {tool['name']} - {tool['description']}")
    except Exception as e:
        st.error(f"Failed to start MCP servers: {str(e)}")
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
            system=get_system_prompt(),
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
                    session = st.session_state.mcp_sessions.get(block.name)
                    if session:
                        result = st.session_state.event_loop.run_until_complete(
                            session.call_tool(
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
                    else:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Error: Tool {block.name} not found",
                            "is_error": True
                        })
            
            st.session_state.messages.append({
                "role": "user",
                "content": tool_results
            })
            
            response = st.session_state.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=8096,
                system=get_system_prompt(),
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
