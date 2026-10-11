import { createServer } from "node:http";
import { execFileSync } from "node:child_process";

// Exercise the real Python rendering/configuration path, not a copied template.
const html = execFileSync("python", [
  "-c", "from streamlit_app.dance_studio import studio_html; print(studio_html())",
], { encoding: "utf8" });

const host = `<!doctype html><html><body>
  <button id="hide">Leave studio tab</button>
  <button id="show">Return to studio tab</button>
  <iframe id="studio" src="/studio" title="Dance Studio" style="width:100%;height:720px"></iframe>
  <script>
    hide.onclick = () => studio.style.display = "none";
    show.onclick = () => studio.style.display = "block";
  </script>
</body></html>`;

createServer((request, response) => {
  response.writeHead(200, { "Content-Type": "text/html", "Cache-Control": "no-store" });
  response.end(request.url === "/studio" ? html : host);
}).listen(18765, "127.0.0.1");
