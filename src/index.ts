import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { createMcpHandler } from "agents/mcp";
import { z } from "zod";

interface Env { MCP_ACCESS_TOKEN: string; YOUTUBE_API_KEY?: string; }
const server = new McpServer({ name: "youtube-ai-mcp", version: "0.1.0" });

server.tool("youtube_video_research", "Search public YouTube videos by keyword. Does not access private channel analytics.", {
  query: z.string().min(2).max(120).describe("Topic or keyword"),
  maxResults: z.number().int().min(1).max(10).optional().describe("Number of results, default 5")
}, async ({ query, maxResults }) => {
  const key = (globalThis as unknown as { __ytKey?: string }).__ytKey;
  if (!key) return { content: [{ type: "text", text: "Not configured: add YOUTUBE_API_KEY as a Cloudflare Worker secret." }], isError: true };
  const url = new URL("https://www.googleapis.com/youtube/v3/search");
  url.searchParams.set("part", "snippet"); url.searchParams.set("type", "video");
  url.searchParams.set("order", "viewCount"); url.searchParams.set("q", query);
  url.searchParams.set("maxResults", String(maxResults ?? 5)); url.searchParams.set("key", key);
  const response = await fetch(url);
  if (!response.ok) return { content: [{ type: "text", text: `YouTube API HTTP ${response.status}; check API key, API enablement and quota.` }], isError: true };
  const data = await response.json() as { items?: Array<{ id?: { videoId?: string }; snippet?: { title?: string; channelTitle?: string; publishedAt?: string; description?: string } }> };
  const videos = (data.items ?? []).map(item => ({ videoId: item.id?.videoId ?? "", title: item.snippet?.title ?? "", channel: item.snippet?.channelTitle ?? "", publishedAt: item.snippet?.publishedAt ?? "", description: (item.snippet?.description ?? "").slice(0, 300), url: item.id?.videoId ? `https://www.youtube.com/watch?v=${item.id.videoId}` : "" }));
  return { content: [{ type: "text", text: JSON.stringify({ query, note: "Public results ordered by view count; future views are not guaranteed.", videos }, null, 2) }] };
});

server.tool("youtube_training_video_outline", "Create a training video outline draft; does not create or publish a video.", {
  topic: z.string().min(3).max(180), audience: z.string().max(120).optional(),
  durationMinutes: z.number().int().min(1).max(60).optional(), language: z.string().max(40).optional()
}, async ({ topic, audience, durationMinutes, language }) => {
  const outline = { topic, language: language ?? "Hindi", audience: audience ?? "beginners", durationMinutes: durationMinutes ?? 8,
    titleIdeas: [`${topic}: Step-by-Step Guide for Beginners`, `${topic} पूरी जानकारी | आसान तरीका`, `${topic} की 5 आम गलतियाँ`],
    sections: ["0:00 Hook and viewer problem", "Promise and prerequisites", "Step-by-step demo with real example", "Common mistakes and recap", "Relevant question and related-video invitation"],
    descriptionChecklist: ["State viewer benefit in first two lines", "Add accurate chapters after recording", "Use relevant hashtags only"],
    thumbnailGuidance: "One clear subject, 2–4 readable words, high contrast, no misleading claim.",
    note: "Check current search suggestions and recent videos. Views are not guaranteed." };
  return { content: [{ type: "text", text: JSON.stringify(outline, null, 2) }] };
});

function error(status: number, message: string): Response { return Response.json({ error: message }, { status }); }
export default { async fetch(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);
  if (url.pathname === "/health") return Response.json({ ok: true, service: "youtube-ai-mcp", version: "0.1.0" });
  const authorization = request.headers.get("authorization") ?? "";
  if (!env.MCP_ACCESS_TOKEN || authorization !== `Bearer ${env.MCP_ACCESS_TOKEN}`) return error(401, "Unauthorized. Configure MCP_ACCESS_TOKEN as a Cloudflare Worker secret.");
  (globalThis as unknown as { __ytKey?: string }).__ytKey = env.YOUTUBE_API_KEY;
  return createMcpHandler(server)(request);
} };
