import { execFileSync, execSync } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

const KEPCO26_FLOW_COVER_ID = "14D9_Wtbe_l4IDM8STM6ya9MP9lXbKCWl";
const KEPCO26_FLOW_COVER_BYTES = 1423276;
const KEPCO26_FLOW_COVER_SHA256 = "607be5f4974a532ab2701dd6c3e09a466ba262ed0f94b09eb11ee02e2f6ee860";

const KEPCO26_FLOW_BOARD_ID = "13CvBKevqoIDP1QuYQ_brDrR--9H-maId";
const KEPCO26_FLOW_BOARD_BYTES = 6320173;

const SUB3_COVER_ID = "1fZvjP-bNgbf-Mmu9NWPyCaVW1oIV4Dd_";
const SUB3_COVER_BYTES = 1012329;

const SUB3_BOARD_ID = "1k2UWnGVXDzlrMe9ybEaUsuXFph6ztFW2";
const SUB3_BOARD_BYTES = 1386599;
const SUB3_BOARD_SHA256 = "8e664de339296db5e5b7c93d236b463dc42be36abb20eebc03aca69f8198f7cd";

const SUB3_FLOW_MP4_ID = "16YPXy5S0xYwokXClT2861_OL_PNwHwUC";
const SUB3_FLOW_MP4_BYTES = 5486601;
const SUB3_FLOW_MP4_SHA256 = "31be25c66c3d71e77a81104379e85351d0b3c0fb7e6b83dbb9e726e121f069b5";

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

async function buildKepcoRebate2026FlowMaster(outDir: string, tmpWav: string): Promise<void> {
  ensureFfmpegAndFonts();
  ensureReelVenv();

  const coverBuf = await downloadDriveFile(KEPCO26_FLOW_COVER_ID, KEPCO26_FLOW_COVER_BYTES, KEPCO26_FLOW_COVER_SHA256);
  const coverOut = path.join(outDir, "kepco_rebate_2026_flow_cover_9x16.png");
  fs.writeFileSync(coverOut, coverBuf);

  const boardBuf = await downloadDriveFile(KEPCO26_FLOW_BOARD_ID, KEPCO26_FLOW_BOARD_BYTES);
  const tmpBoard = "/tmp/kepco26_flow_board.png";
  fs.writeFileSync(tmpBoard, boardBuf);

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
      { ok: true, grade: "UHD_BROADCAST_MASTER", bytes: stat.size, sha256: sha, coverBytes: coverBuf.length, updatedAt: new Date().toISOString() },
      null,
      2
    ),
    "utf-8"
  );
  console.log(`Published KEPCO 2026 Flow UHD 60FPS Master (${stat.size} bytes) to dist/reels/kepco_rebate_2026_flow_uhd_60fps.mp4`);
}

async function buildSubVsLump3BundleMaster(outDir: string, tmpWav: string): Promise<void> {
  ensureFfmpegAndFonts();
  ensureReelVenv();

  const coverBuf = await downloadDriveFile(SUB3_COVER_ID, SUB3_COVER_BYTES);
  const coverOut = path.join(outDir, "sub_vs_lump_3bundle_cover_9x16.png");
  fs.writeFileSync(coverOut, coverBuf);
  console.log(`Published Topic 3 9:16 custom cover (${coverBuf.length} bytes) to dist/reels/sub_vs_lump_3bundle_cover_9x16.png`);

  const boardBuf = await downloadDriveFile(SUB3_BOARD_ID, SUB3_BOARD_BYTES, SUB3_BOARD_SHA256);
  const tmpBoard = "/tmp/sub3_storyboard.png";
  fs.writeFileSync(tmpBoard, boardBuf);

  const flowBuf = await downloadDriveFile(SUB3_FLOW_MP4_ID, SUB3_FLOW_MP4_BYTES, SUB3_FLOW_MP4_SHA256);
  const tmpFlow = "/tmp/sub3_flow_690f.mp4";
  fs.writeFileSync(tmpFlow, flowBuf);

  const targetMp4 = path.join(outDir, "sub_vs_lump_3bundle_uhd_60fps.mp4");
  const scriptPath = path.join(process.cwd(), "scripts", "render_sub_vs_lump_uhd.py");
  execFileSync(
    "/tmp/reel_venv/bin/python",
    [scriptPath, "--flow-mp4", tmpFlow, "--board-png", tmpBoard, "--bgm", tmpWav, "--out-mp4", targetMp4],
    { stdio: "inherit" }
  );

  const stat = fs.statSync(targetMp4);
  const sha = crypto.createHash("sha256").update(fs.readFileSync(targetMp4)).digest("hex");
  fs.writeFileSync(
    path.join(outDir, "sub_vs_lump_3bundle_status.json"),
    JSON.stringify(
      { ok: true, grade: "UHD_BROADCAST_MASTER", bytes: stat.size, sha256: sha, coverBytes: coverBuf.length, updatedAt: new Date().toISOString() },
      null,
      2
    ),
    "utf-8"
  );
  console.log(`Published Topic 3 Sub-vs-Lump UHD 60FPS Master (${stat.size} bytes, sha256=${sha}) to dist/reels/sub_vs_lump_3bundle_uhd_60fps.mp4`);
}

async function main(): Promise<void> {
  const outDir = path.join(process.cwd(), "dist", "reels");
  fs.mkdirSync(outDir, { recursive: true });

  const wavBuf = await downloadDirectUrl(FLOW_MUSIC_WAV_URL);
  const tmpWav = "/tmp/flow_music_0bdaf546.wav";
  fs.writeFileSync(tmpWav, wavBuf);

  buildDishwasherCareReel(outDir);
  await buildKepcoRebate2026FlowMaster(outDir, tmpWav);
  await buildSubVsLump3BundleMaster(outDir, tmpWav);
}

main().catch((err: unknown) => {
  console.error(err);
  process.exit(1);
});
