import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(__dirname, "..", "..");
const manifestPath = path.join(projectRoot, "dist", ".vite", "manifest.json");
const manifest = JSON.parse(await readFile(manifestPath, "utf8"));

const expectedDynamicModules = [
  "src/components/UploadPanel.tsx",
  "src/components/ChatPanel.tsx",
  "src/components/TerminalWindow.tsx",
  "src/components/DocumentPanel.tsx",
];

const missing = expectedDynamicModules.filter((modulePath) => {
  const entry = manifest[modulePath];
  return !entry || entry.isDynamicEntry !== true;
});

if (missing.length) {
  console.error("The following modules are not emitted as dynamic entries (lazy chunks):", missing);
  process.exit(1);
}

console.log("Verified dynamic imports for panels:", expectedDynamicModules.join(", "));
