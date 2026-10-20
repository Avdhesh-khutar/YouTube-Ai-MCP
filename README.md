# YouTube AI MCP (starter)

A Cloudflare Workers MCP starter for researching public YouTube videos and planning training-video content.

## Implemented tools
- `youtube_video_research`: searches public YouTube videos by keyword using YouTube Data API v3.
- `youtube_training_video_outline`: drafts a training-video outline, title ideas, and a description checklist.

## Current security
- `/health` is public and reports service health only.
- The MCP endpoint requires `Authorization: Bearer <MCP_ACCESS_TOKEN>`.
- Keep `MCP_ACCESS_TOKEN` and `YOUTUBE_API_KEY` in Cloudflare Worker secrets. Never commit secrets to this repository.
- Restrict the Google API key to YouTube Data API v3.

## Connect Claude securely
This Worker currently protects the MCP endpoint with a static bearer token. In Claude's custom connector settings, select **No sign-in**, then configure a fixed request header if the UI offers it:
- Header name: `Authorization`
- Header value: `Bearer <your MCP_ACCESS_TOKEN>`

Use the value of the `MCP_ACCESS_TOKEN` secret already stored in Cloudflare. Do not paste it into a chat, GitHub, or a public issue. Claude supports fixed request headers for servers that use a bearer token. If the Request headers option is unavailable in your connector UI, do not remove server-side authentication; implement a supported OAuth flow instead.

This bearer token only authenticates access to this MCP server. It is not Google OAuth and does not grant access to private YouTube channel data.

## Not yet implemented
- Private channel analytics.
- Changing existing video titles/descriptions.
- Uploading or publishing videos.
These require Google OAuth authorization from the channel owner and additional implementation. Views cannot be guaranteed.

## Deploy
1. Connect this repository to Cloudflare Workers using Workers & Pages → Create application → Import a repository.
2. Build command: `npm run build`; deploy command: `npx wrangler deploy`.
3. Add Worker secrets in Cloudflare Settings → Variables and Secrets: `MCP_ACCESS_TOKEN` (long random secret) and `YOUTUBE_API_KEY` (YouTube Data API v3 key).

## Build note
The build script intentionally avoids running a separate TypeScript compiler because the Cloudflare build environment previously hit a JavaScript heap out-of-memory error. Wrangler bundles the Worker during deployment. Verify the newest deployment logs after each code change.