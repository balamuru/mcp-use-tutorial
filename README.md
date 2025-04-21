# mcp-use tutorial
A demo on creating and employing [mcp-use](https://github.com/pietrozullo/mcp-use) clients to communicate with [MCP](https://modelcontextprotocol.io/introduction) servers

Samples are provided for Gemini and Anthropic based on the official mcp-use client examples - communicating with a local playwright server to query qoogle

## Setup
###
Ensure python version >= `3.13` (as of when this docuement was written)
`python --version`

### Clone repository
`git clone https://github.com/balamuru/mcp-use-tutorial.git`

### Setup Virtual Env
Create and activate Virtual environment
```
cd path-to-project-root-dir
python -m venv path-to-project-root-dir/venv
source venv/bin/activate
```

### Dependancies
Install dependancies
`pip install -r requirements.txt`

### Env Variables
Set API keys in the `.env` file for desired agent(s)

## Execute
* `python gemini-agent.py` and/or
* `python anthropic-agent.py`




