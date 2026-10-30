// Local-only production-build preview with explicit test data for visual inspection.
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { fixtureResponse } from "./admin-fixtures.mjs";

const PORT = Number(process.env.ADMIN_PREVIEW_PORT ?? 4180);
const ROOT = resolve(fileURLToPath(new URL("../../apps/web/dist", import.meta.url)));
const MIME = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css",
  ".woff2": "font/woff2", ".svg": "image/svg+xml" };

function api(req, res, path) {
  if (req.method !== "GET") {
    res.writeHead(405, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ detail: "Mutations must be explicitly intercepted by a browser test" }));
    return;
  }
  const identity = (req.headers.authorization ?? "").replace("Bearer preview-", "");
  const value = fixtureResponse(path, identity);
  res.writeHead(value === undefined ? 404 : 200, { "Content-Type": "application/json" });
  res.end(JSON.stringify(value ?? { detail: "No browser fixture for " + path }));
}

async function serve(req, res) {
  const path = new URL(req.url, "http://localhost").pathname;
  if (path.startsWith("/api/")) return api(req, res, path);
  const file = extname(path) ? resolve(ROOT, "." + path) : resolve(ROOT, "index.html");
  if (!file.startsWith(ROOT + sep)) { res.writeHead(403); res.end(); return; }
  try {
    let content = await readFile(file);
    if (file.endsWith(".html")) content = content.toString().replace("<head>",
      '<head><script>if (!localStorage.getItem("askflow_token")) localStorage.setItem("askflow_token","preview-admin")</script>');
    res.writeHead(200, { "Content-Type": MIME[extname(file)] ?? "application/octet-stream" });
    res.end(content);
  } catch { res.writeHead(404); res.end(); }
}

createServer((req, res) => void serve(req, res)).listen(PORT, "127.0.0.1", () => {
  console.log(`Admin fixture preview: http://127.0.0.1:${PORT}`);
});
