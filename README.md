# YouTube AI MCP (starter)

A Cloudflare Workers MCP starter for planning YouTube training videos.

## Current scope
- Search public YouTube videos by keyword using YouTube Data API v3.
- Generate training-video outlines and SEO checklists.
- Protect the MCP endpoint with a bearer token (MCP_ACCESS_TOKEN).

## Not yet enabled
Private channel analytics, uploading/publishing videos, and changing existing video titles/descriptions require Google OAuth 2.0 authorization for the channel owner. These features are not implemented yet. Views cannot be guaranteed.

## Deploy
1. Connect this repository to Cloudflare Workers using Workers & Pages → Create application → Import a repository.
2. Build command: `npm run build`; deploy command: `npx wrangler deploy`.
3. Add Worker secrets in Cloudflare Settings → Variables and Secrets: `MCP_ACCESS_TOKEN` (long random secret) and `YOUTUBE_API_KEY` (YouTube Data API v3 key).
4. Never commit API keys, OAuth client secrets, refresh tokens, or passwords to this public repository.

This is a starter, not a claim that YouTube publishing OAuth is already configured.
