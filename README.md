# YouTube AI MCP

Cloudflare Worker hosting an OAuth-protected MCP endpoint for Claude.

## Current tools
- `youtube_video_research`: searches public YouTube videos by keyword with YouTube Data API v3.
- `youtube_training_video_outline`: drafts video outlines and title ideas.

## Important limits
Private channel analytics, editing existing videos, uploading, and publishing are not implemented yet. They require Google OAuth and explicit YouTube channel permissions. This service does not guarantee views and does not automatically publish content.

## Cloudflare setup
The repository uses a Cloudflare KV namespace bound as `OAUTH_KV`.

Add these as **Worker secrets** in Cloudflare → Workers & Pages → youtube-ai-mcp → Settings → Variables and Secrets:
- `OAUTH_ADMIN_PASSWORD`: a long, unique password used only for the Claude connector authorization screen. Do not use your Google password.
- `YOUTUBE_API_KEY`: Google API key restricted to YouTube Data API v3.

The previous `MCP_ACCESS_TOKEN` is no longer used by the OAuth flow. Do not share any secret in chat or commit it to GitHub.

## Connect Claude
After the latest GitHub-triggered Cloudflare deployment succeeds:
1. Add a custom remote MCP connector in Claude.
2. URL: `https://youtube-ai-mcp.mkkhutar2.workers.dev/mcp`
3. Select OAuth / sign in when Claude detects authorization.
4. The browser should open the YouTube AI MCP authorization page. Enter the `OAUTH_ADMIN_PASSWORD` secret you created in Cloudflare and approve only if the client and redirect host match the Claude connection you just started.
5. After connection, test `youtube_video_research` with a topic.

If Claude does not open the authorization page or the Cloudflare deployment fails, do not disable OAuth or expose the endpoint publicly. Check the Cloudflare build/deployment logs.

## Health check
`https://youtube-ai-mcp.mkkhutar2.workers.dev/health`

## Security
- OAuth tokens are issued by Cloudflare Workers OAuth Provider and stored through the `OAUTH_KV` binding.
- Use a unique strong `OAUTH_ADMIN_PASSWORD`; never paste it into chat.
- Keep the Google API key restricted to YouTube Data API v3.
- OAuth to this MCP service is separate from Google OAuth for private channel access.
