// Tiny local server so you can try the site without the Vercel CLI:
//   npm install   &&   npm run dev      -> open http://localhost:3000
// It serves the static files and routes POST /api/score to the same handler
// Vercel would run.

import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { scoreLead } from "./api/score.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = 3000;
const TYPES = { ".html": "text/html", ".css": "text/css", ".js": "text/javascript",
                ".json": "application/json" };

const server = http.createServer(async (req, res) => {
  if (req.method === "POST" && req.url === "/api/score") {
    let body = "";
    req.on("data", (c) => (body += c));
    req.on("end", async () => {
      try {
        const out = await scoreLead(JSON.parse(body));
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify(out));
      } catch (e) {
        res.writeHead(400, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: String(e.message || e) }));
      }
    });
    return;
  }
  // static files
  const file = req.url === "/" ? "/index.html" : req.url.split("?")[0];
  const fp = path.join(__dirname, file);
  if (fs.existsSync(fp) && fs.statSync(fp).isFile()) {
    res.writeHead(200, { "Content-Type": TYPES[path.extname(fp)] || "text/plain" });
    fs.createReadStream(fp).pipe(res);
  } else {
    res.writeHead(404).end("Not found");
  }
});

server.listen(PORT, () => console.log(`dev server on http://localhost:${PORT}`));
