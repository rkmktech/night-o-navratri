import { Storage } from "@google-cloud/storage";

// Replit's managed sidecar provides credentials; no keys are stored in code.
const endpoint = "http://127.0.0.1:1106";
export const storage = new Storage({
  credentials: {
    audience: "replit",
    subject_token_type: "access_token",
    token_url: `${endpoint}/token`,
    type: "external_account",
    credential_source: {
      url: `${endpoint}/credential`,
      format: { type: "json", subject_token_field_name: "access_token" },
    },
    universe_domain: "googleapis.com",
  },
  projectId: "",
});
