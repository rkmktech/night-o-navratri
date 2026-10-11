import { createServer } from "node:http";
import { readFileSync } from "node:fs";

const fixture = readFileSync(new URL("./fixtures/tennis.jpg", import.meta.url));
createServer((request, response) => {
  response.setHeader("Cache-Control", "no-store");
  if (request.url === "/fixtures/tennis.jpg") {
    response.writeHead(200, { "Content-Type": "image/jpeg" });
    response.end(fixture);
  } else if (request.url === "/") {
    response.writeHead(200, { "Content-Type": "text/html" });
    response.end("<!doctype html><title>Real pose compatibility probe</title>");
  } else {
    response.writeHead(404);
    response.end("Not found");
  }
}).listen(18766, "127.0.0.1");
