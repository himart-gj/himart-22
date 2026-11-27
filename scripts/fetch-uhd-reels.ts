import { execFileSync, execSync } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

const KEPCO26_FLOW_COVER_ID = "14D9_Wtbe_l4IDM8STM6ya9MP9lXbKCWl";
const KEPCO26_FLOW_COVER_BYTES = 1423276;
const KEPCO26_FLOW_COVER_SHA256 = "607be5f4974a532ab2701dd6c3e09a466ba262ed0f94b09eb11ee02e2f6ee860";

const KEPCO26_FLOW_BOARD_ID = "13CvBKevqoIDP1QuYQ_brDrR--9H-maId";
const KEPCO26_FLOW_BOARD_BYTES = 6320173;

const FLOW_MUSIC_WAV_URL = "https://storage.googleapis.com/producer-app-public/clips/0bdaf546-5de9-4121-9be2-a4dfc269fc4d.wav";

async function downloadDriveFile(id: string, expectedBytes?: number, expectedSha?: string): Promise<Buffer> {
  const urls = [
    `https://drive.usercontent.google.com/download?id=${id}&export=download&confirm=t`,
    `https://drive.google.com/uc?export=download&id=${id}&confirm=t`,
  ];
  for (const url of urls) {
    for (let attempt = 1; attempt <= 3; attempt++) {
      const resp = await fetch(url, { redirect: "follow" });
      if (!resp.ok) continue;
      const arr = await resp.arrayBuffer();
      const buf = Buffer.from(arr);
      if (expectedBytes && buf.length !== expectedBytes) continue;
      if (expectedSha) {
        const digest = crypto.createHash("sha256").update(buf).digest("hex");
        if (digest !== expectedSha) continue;
      }
      if (buf.length > 10000) return buf;
    }
  }
  throw new Error(`Failed to fetch Drive asset ${id}`);
}

async function downloadDirectUrl(url: string): Promise<Buffer> {
  for (let attempt = 1; attempt <= 3; attempt++) {
    const resp = await fetch(url, { redirect: "follow" });
    if (!resp.ok) continue;
    const buf = Buffer.from(await resp.arrayBuffer());
    if (buf.length > 500000) return buf;
  }
  throw new Error(`Failed to download URL: ${url}`);
}

function ensureFfmpegAndFonts(): void {
  if (!fs.existsSync("/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc") || !fs.existsSync("/usr/bin/ffmpeg")) {
    execSync(
      "sudo sed -i 's|azure.archive.ubuntu.com|archive.ubuntu.com|g' /etc/apt/sources.list /etc/apt/sources.list.d/*.sources /etc/apt/sources.list.d/*.list 2>/dev/null || true && sudo apt-get update -qq && sudo apt-get install -y -qq --no-install-recommends fonts-noto-cjk fonts-noto-cjk-extra fonts-inter ffmpeg python3-venv",
      { stdio: "inherit" }
    );
  }
}

function ensureReelVenv(): void {
  if (!fs.existsSync("/tmp/reel_venv/bin/python")) {
    execSync("python3 -m venv /tmp/reel_venv && /tmp/reel_venv/bin/pip install --quiet edge-tts pillow numpy opencv-python-headless", {
      stdio: "inherit",
    });
  }
}

function buildDishwasherCareReel(outDir: string): void {
  ensureFfmpegAndFonts();
  ensureReelVenv();
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

async function buildKepcoRebate2026FlowMaster(outDir: string): Promise<void> {
  ensureFfmpegAndFonts();
  ensureReelVenv();

  const coverBuf = await downloadDriveFile(KEPCO26_FLOW_COVER_ID, KEPCO26_FLOW_COVER_BYTES, KEPCO26_FLOW_COVER_SHA256);
  const coverOut = path.join(outDir, "kepco_rebate_2026_flow_cover_9x16.png");
  fs.writeFileSync(coverOut, coverBuf);
  console.log(`Published 9:16 custom cover (${coverBuf.length} bytes) to dist/reels/kepco_rebate_2026_flow_cover_9x16.png`);

  const boardBuf = await downloadDriveFile(KEPCO26_FLOW_BOARD_ID, KEPCO26_FLOW_BOARD_BYTES);
  const tmpBoard = "/tmp/kepco26_flow_board.png";
  fs.writeFileSync(tmpBoard, boardBuf);

  const wavBuf = await downloadDirectUrl(FLOW_MUSIC_WAV_URL);
  const tmpWav = "/tmp/kepco26_flow_music_0bdaf546.wav";
  fs.writeFileSync(tmpWav, wavBuf);

  const targetMp4 = path.join(outDir, "kepco_rebate_2026_flow_uhd_60fps.mp4");
  const scriptPath = path.join(process.cwd(), "scripts", "render_kepco26_flow_uhd.py");
  execFileSync(
    "/tmp/reel_venv/bin/python",
    [scriptPath, "--board-png", tmpBoard, "--bgm", tmpWav, "--out-mp4", targetMp4],
    { stdio: "inherit" }
  );

  const stat = fs.statSync(targetMp4);
  const sha = crypto.createHash("sha256").update(fs.readFileSync(targetMp4)).digest("hex");
  fs.writeFileSync(
    path.join(outDir, "kepco_rebate_2026_flow_status.json"),
    JSON.stringify(
      {
        ok: true,
        grade: "UHD_BROADCAST_MASTER",
        bytes: stat.size,
        sha256: sha,
        coverBytes: coverBuf.length,
        flowMusicSongId: "0bdaf546-5de9-4121-9be2-a4dfc269fc4d",
        updatedAt: new Date().toISOString(),
      },
      null,
      2
    ),
    "utf-8"
  );
  console.log(`Published KEPCO 2026 Flow UHD 60FPS Master (${stat.size} bytes, sha256=${sha}) to dist/reels/kepco_rebate_2026_flow_uhd_60fps.mp4`);
}

async function main(): Promise<void> {
  const outDir = path.join(process.cwd(), "dist", "reels");
  fs.mkdirSync(outDir, { recursive: true });

  buildDishwasherCareReel(outDir);
  await buildKepcoRebate2026FlowMaster(outDir);
}

main().catch((err: unknown) => {
  console.error(err);
  process.exit(1);
});
