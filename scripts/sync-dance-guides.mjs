import { createHash, randomUUID } from "node:crypto";
import { createReadStream } from "node:fs";
import { readFile, rename, rm } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { storage } from "./lib/app-storage.mjs";

const assets = new URL("../assets/", import.meta.url);
const guides = JSON.parse(await readFile(new URL("dance_guides.json", assets), "utf8"));

async function digest(path) {
  const hash = createHash("sha256");
  try {
    for await (const chunk of createReadStream(path)) hash.update(chunk);
    return hash.digest("hex");
  } catch (error) {
    if (error.code === "ENOENT") return null;
    throw error;
  }
}

for (const guide of guides) {
  const target = fileURLToPath(new URL(guide.filename, assets));
  if (await digest(target) === guide.sha256) continue;

  const bucket = process.env.DEFAULT_OBJECT_STORAGE_BUCKET_ID;
  if (!bucket) throw new Error("App Storage must be configured to restore the skeleton guides.");
  const temporary = `${target}.${randomUUID()}.tmp`;
  try {
    await storage.bucket(bucket).file(guide.object).download({ destination: temporary });
    if (await digest(temporary) !== guide.sha256) {
      throw new Error(`Integrity check failed for ${guide.filename}.`);
    }
    await rename(temporary, target);
    console.log(`Restored ${guide.filename} from App Storage.`);
  } finally {
    await rm(temporary, { force: true });
  }
}
