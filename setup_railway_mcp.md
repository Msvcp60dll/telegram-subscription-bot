# Railway MCP Server Setup

## Installation Status
✅ Railway MCP server is installed at: `/Users/antongladkov/.nvm/versions/node/v24.5.0/lib/node_modules/@railway/mcp-server`

## Setup Instructions for Claude Desktop

1. **Open Claude Desktop Settings**
   - Click on Claude menu → Settings (or press `Cmd+,`)
   - Navigate to the "Developer" tab

2. **Add Railway MCP Server**
   Add this configuration to your MCP servers:

   ```json
   {
     "railway": {
       "command": "npx",
       "args": ["-y", "@railway/mcp-server"],
       "env": {
         "RAILWAY_API_TOKEN": "your-railway-token-here"
       }
     }
   }
   ```

3. **Get Your Railway API Token**
   - Go to: https://railway.app/account/tokens
   - Create a new token
   - Copy it and replace "your-railway-token-here" in the config above

4. **Restart Claude Desktop**
   - After adding the configuration, restart Claude Desktop
   - The Railway MCP tools should then be available

## Alternative: Manual API Token Setup

If you prefer not to restart Claude, you can set the token in your terminal:
```bash
export RAILWAY_API_TOKEN="your-token-here"
```

Then I can use the Railway CLI with full API access.

## Benefits of MCP Server
Once configured, I'll be able to:
- View detailed deployment logs
- See exact error messages
- Manage services directly
- Create/delete deployments
- Check build status in real-time
- Debug deployment issues effectively

## Current Issue
Your deployment is failing during the "network process" phase. With MCP access, I can:
1. See the actual build logs
2. Identify the exact error
3. Fix it programmatically

Please either:
1. Configure the MCP server in Claude Desktop settings (recommended)
2. OR provide your Railway API token so I can use the CLI with full access