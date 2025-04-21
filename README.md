# mcp-use tutorial
A simple barebones demo on creating and employing (mcp-use)[https://github.com/pietrozullo/mcp-use] clients to communicate with [MCP](https://modelcontextprotocol.io/introduction) servers

Samples are provided for Gemini and Anthropic based on the official mcp-use client examples - communicating with a local playwright server to query qoogle

## Setup

### Virtual Env
Create and activate Virtual env
```
python3 -m venv mcp-use-tutorial
cd mcp-use-tutorial
source ./bin/activate
```

### Dependancies
Install dependancies
* `pip install mcp-use`
* `pip install  langchain_google_genai` and/or
* `pip install  langchain-anthropic`


### Env Variables
Set keys in the `.env` file for desired agents

## Execute
* `python gemini-agent.py` and/or
* `python anthropic-agent.py`




