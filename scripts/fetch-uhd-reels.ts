import { execFileSync, execSync } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

interface ChunkSpec {
  id: string;
  bytes: number;
  sha256: string;
}

const CHUNKS: ChunkSpec[] = [
  { id: "1PIB0sB9-Z4aq5QMvCtpOdjT2MOYrHB1E", bytes: 6000000, sha256: "67a873ed2e768bcf449298124aa0544991bf5a7f39042bb2a485c6e475ad606a" },
  { id: "1b-0GABq_K9spvyDnhBbflNHFMchztYg8", bytes: 6000000, sha256: "1f005aae2971861cced524eb2808246de197b8aaa8f60c9761d6c4c146bf6460" },
  { id: "1NqkgHsT11gHVVwJH5DEVGgu_dW9lTVEU", bytes: 6000000, sha256: "640c384e54a7f96d19d2a39e860d8add45e5460c22e6dc89d5184578cadf28d6" },
  { id: "138kxMq9Zx61UjV9hY7HHY1Mb_WcDswWg", bytes: 6000000, sha256: "939121a7e78dcabb1d39b5640c9d991badbc48fdc3ac4c5b526f6b8f27b9be67" },
  { id: "1X2uivrK-SGrgH8GHpRfCsfMyJejCNWOT", bytes: 6000000, sha256: "9fdb13ac296f61ee904603cc6d209cf8294ff61abdd8ed8318de95cd453f5bb6" },
  { id: "1_pBGPpXdZVqQ8YfFx-K9xPLiiGYdAKf0", bytes: 6000000, sha256: "7458d2b0d900c3047017d7153158ec795682545d12c889b7bd9c37e3c28b39b8" },
  { id: "1aVthiwKbLjuhAV9_pTAKZQ2FGHmZ7tvp", bytes: 5715336, sha256: "7c62f5638f808b8919175791053d78587dcf5afdf2715492d88dd6d3da04ff45" },
];

const EXPECTED_TOTAL_BYTES = 41715336;
const EXPECTED_SHA256 = "245b72be7c359bfd7d60af5978eab62194352e468f5b1a27fff4c3cea21984bf";

async function downloadChunk(spec: ChunkSpec): Promise<Buffer> {
  const urls = [
    `https://drive.usercontent.google.com/download?id=${spec.id}&export=download&confirm=t`,
    `https://drive.google.com/uc?export=download&id=${spec.id}&confirm=t`,
  ];
  for (const url of urls) {
    for (let attempt = 1; attempt <= 3; attempt++) {
      const resp = await fetch(url, { redirect: "follow" });
      if (!resp.ok) continue;
      const arr = await resp.arrayBuffer();
      const buf = Buffer.from(arr);
      const digest = crypto.createHash("sha256").update(buf).digest("hex");
      if (buf.length === spec.bytes && digest === spec.sha256) {
        return buf;
      }
    }
  }
  throw new Error(`Failed to fetch verified chunk ${spec.id}`);
}

function buildDishwasherCareReel(outDir: string): void {
  if (!fs.existsSync("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")) {
    execSync(
      "sudo sed -i 's|azure.archive.ubuntu.com|archive.ubuntu.com|g' /etc/apt/sources.list /etc/apt/sources.list.d/*.sources /etc/apt/sources.list.d/*.list 2>/dev/null || true && sudo apt-get update -qq && sudo apt-get install -y -qq --no-install-recommends fonts-noto-cjk ffmpeg python3-venv",
      { stdio: "inherit" }
    );
  }
  execSync("python3 -m venv /tmp/reel_venv && /tmp/reel_venv/bin/pip install --quiet edge-tts pillow numpy", {
    stdio: "inherit",
  });
  const targetMp4 = path.join(outDir, "dishwasher_washer_care_uhd_60fps.mp4");
  const scriptPath = path.join(process.cwd(), "scripts", "render_dishwasher_care_reel.py");
  execFileSync("/tmp/reel_venv/bin/python", [scriptPath, targetMp4], { stdio: "inherit" });

  const stat = fs.statSync(targetMp4);
  const sha = crypto.createHash("sha256").update(fs.readFileSync(targetMp4)).digest("hex");
  fs.writeFileSync(
    path.join(outDir, "dishwasher_washer_care_status.json"),
    JSON.stringify({ ok: true, bytes: stat.size, sha256: sha, updatedAt: new Date().toISOString() }, null, 2),
    "utf-8"
  );
  console.log(`Published UHD 60FPS master (${stat.size} bytes) to dist/reels/dishwasher_washer_care_uhd_60fps.mp4`);
}

async function main(): Promise<void> {
  const outDir = path.join(process.cwd(), "dist", "reels");
  fs.mkdirSync(outDir, { recursive: true });

  try {
    const buffers: Buffer[] = [];
    for (const spec of CHUNKS) {
      const b = await downloadChunk(spec);
      buffers.push(b);
    }
    const merged = Buffer.concat(buffers);
    const fullSha = crypto.createHash("sha256").update(merged).digest("hex");
    if (merged.length === EXPECTED_TOTAL_BYTES && fullSha === EXPECTED_SHA256) {
      fs.writeFileSync(path.join(outDir, "humidifier_3room_uhd_60fps.mp4"), merged);
    }
  } catch (e: unknown) {
    console.warn("Note: humidifier_3room archive skipped:", e);
  }

  buildDishwasherCareReel(outDir);
}

main().catch((err: unknown) => {
  console.error(err);
  process.exit(1);
});
