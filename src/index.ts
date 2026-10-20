import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { createLegacyMcpHandler } from "agents/mcp";
import { z } from "zod";

interface Env {
  MCP_ACCESS_TOKEN?: string;
  YOUTUBE_API_KEY?: string;
}

function createServer(youtubeApiKey?: string): McpServer {
  const server = new McpServer({ name: "youtube-ai-mcp", version: "0.1.3" });

  server.tool(
    "youtube_video_research",
    "Search public YouTube videos by keyword. Does not access private channel analytics.",
    {
      query: z.string().min(2).max(120).describe("Topic or keyword"),
      maxResults: z.number().int().min(1).max(10).optional().describe("Number of results, default 5"),
    },
    async ({ query, maxResults }) => {
      if (!youtubeApiKey) {
        return {
          content: [{ type: "text", text: "Not configured: add YOUTUBE_API_KEY as a Cloudflare Worker secret." }],
          isError: true,
        };
      }

      const url = new URL("https://www.googleapis.com/youtube/v3/search");
      url.searchParams.set("part", "snippet");
      url.searchParams.set("type", "video");
      url.searchParams.set("order", "viewCount");
      url.searchParams.set("q", query);
      url.searchParams.set("maxResults", String(maxResults ?? 5));
      url.searchParams.set("key", youtubeApiKey);

      const response = await fetch(url);
      if (!response.ok) {
        return {
          content: [{
            type: "text",
            text: `YouTube API returned HTTP ${response.status}. Check the API key, YouTube Data API v3 enablement, restrictions, and quota.`,
          }],
          isError: true,
        };
      }

      const data = await response.json() as {
        items?: Array<{
          id?: { videoId?: string };
          snippet?: { title?: string; channelTitle?: string; publishedAt?: string; description?: string };
        }>;
      };

      const videos = (data.items ?? []).map((item) => ({
        videoId: item.id?.videoId ?? "",
        title: item.snippet?.title ?? "",
        channel: item.snippet?.channelTitle ?? "",
        publishedAt: item.snippet?.publishedAt ?? "",
        description: (item.snippet?.description ?? "").slice(0, 300),
        url: item.id?.videoId ? `https://www.youtube.com/watch?v=${item.id.videoId}` : "",
      }));

      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            query,
            note: "Public results ordered by view count; this does not predict or guarantee future views.",
            videos,
          }, null, 2),
        }],
      };
    },
  );

  server.tool(
    "youtube_training_video_outline",
    "Create a training-video outline draft; does not create or publish a video.",
    {
      topic: z.string().min(3).max(180),
      audience: z.string().max(120).optional(),
      durationMinutes: z.number().int().min(1).max(60).optional(),
      language: z.string().max(40).optional(),
    },
    async ({ topic, audience, durationMinutes, language }) => {
      const outline = {
        topic,
        language: language ?? "Hindi",
        audience: audience ?? "beginners",
        durationMinutes: durationMinutes ?? 8,
        titleIdeas: [
          `${topic}: Step-by-Step Guide for Beginners`,
          `${topic} पूरी जानकारी | आसान तरीका`,
          `${topic} की 5 आम गलतियाँ`,
        ],
        sections: [
          "0:00 Hook and viewer problem",
          "Promise and prerequisites",
          "Step-by-step demo with a real example",
          "Common mistakes and recap",
          "Relevant question and related-video invitation",
        ],
        descriptionChecklist: [
          "State viewer benefit in first two lines",
          "Add accurate chapters after recording",
          "Use relevant hashtags only",
        ],
        thumbnailGuidance: "One clear subject, 2–4 readable words, high contrast, no misleading claim.",
        note: "Check current search suggestions and recent videos. Views are not guaranteed.",
      };
      return { content: [{ type: "text", text: JSON.stringify(outline, null, 2) }] };
    },
  );

  return server;
}

function jsonError(status: number, message: string): Response {
  return Response.json({ error: message }, { status });
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/health") {
      return Response.json({ ok: true, service: "youtube-ai-mcp", version: "0.1.3" });
    }

    // Keep MCP protected until OAuth is implemented for Claude's web connector.
    const suppliedAuthorization = request.headers.get("authorization") ?? "";
    const configuredToken = env.MCP_ACCESS_TOKEN;
    if (!configuredToken || suppliedAuthorization !== `Bearer ${configuredToken}`) {
      return jsonError(401, "Unauthorized. MCP_ACCESS_TOKEN is required.");
    }

    // Create a fresh SDK v1 server per request and close over this request's key.
    // This avoids shared mutable global state and uses the correct legacy handler.
    return createLegacyMcpHandler(createServer(env.YOUTUBE_API_KEY))(request);
  },
};