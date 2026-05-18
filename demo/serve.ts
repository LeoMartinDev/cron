/**
 * Simple Deno HTTP server to serve:
 *  - The demo HTML page
 *  - The GGUF model file (for loading via URL instead of file picker)
 *
 * Usage:
 *   deno run -A demo/serve.ts
 *
 * Then open http://localhost:8080 in your browser.
 *
 * The model is served from:
 *   ~/.unsloth/studio/exports/SmolLM2-360M-Instruct-gguf/SmolLM2-360M-Instruct.Q4_K_M.gguf
 *
 * Override with MODEL_PATH env var:
 *   MODEL_PATH=/path/to/model.gguf deno run -A demo/serve.ts
 */

const MODEL_PATH = Deno.env.get("MODEL_PATH") ??
  Deno.env.get("HOME") +
    "/.unsloth/studio/exports/SmolLM2-360M-Instruct-gguf/SmolLM2-360M-Instruct.Q4_K_M.gguf";

const PORT = parseInt(Deno.env.get("PORT") ?? "8000");

const HTML_PATH = new URL("./index.html", import.meta.url).pathname;

function getContentType(path: string): string {
  if (path.endsWith(".html")) return "text/html; charset=utf-8";
  if (path.endsWith(".gguf")) return "application/octet-stream";
  if (path.endsWith(".js")) return "application/javascript; charset=utf-8";
  if (path.endsWith(".css")) return "text/css; charset=utf-8";
  if (path.endsWith(".wasm")) return "application/wasm";
  return "application/octet-stream";
}

async function handleRequest(req: Request): Promise<Response> {
  const url = new URL(req.url);
  const path = url.pathname;

  // CORS headers for CDN-loaded wllama to work
  const corsHeaders = {
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Embedder-Policy": "require-corp",
    "Access-Control-Allow-Origin": "*",
  };

  try {
    // Serve the HTML page
    if (path === "/" || path === "/index.html") {
      const html = await Deno.readTextFile(HTML_PATH);
      return new Response(html, {
        headers: {
          "Content-Type": "text/html; charset=utf-8",
          ...corsHeaders,
        },
      });
    }

    // Serve the model file
    if (path === "/model.gguf") {
      const stat = await Deno.stat(MODEL_PATH);
      const file = await Deno.open(MODEL_PATH, { read: true });

      return new Response(file.readable, {
        headers: {
          "Content-Type": "application/octet-stream",
          "Content-Length": String(stat.size),
          "Content-Disposition": `attachment; filename="model.gguf"`,
          ...corsHeaders,
        },
      });
    }

    return new Response("Not Found", { status: 404 });
  } catch (err) {
    if (err instanceof Deno.errors.NotFound) {
      return new Response("Not Found", { status: 404 });
    }
    console.error(err);
    return new Response("Internal Server Error", { status: 500 });
  }
}

// Check model exists
try {
  const stat = await Deno.stat(MODEL_PATH);
  console.log(`✅ Model found: ${MODEL_PATH}`);
  console.log(`   Size: ${(stat.size / 1024 / 1024).toFixed(1)} MB`);
} catch {
  console.error(`❌ Model not found at: ${MODEL_PATH}`);
  console.error("   Set MODEL_PATH env var to point to your GGUF file.");
  Deno.exit(1);
}

console.log(`\n🚀 Serving at http://localhost:${PORT}`);
console.log("   Open this URL in your browser.");
console.log("   (set PORT env var to change)\n");

Deno.serve({ port: PORT }, handleRequest);
