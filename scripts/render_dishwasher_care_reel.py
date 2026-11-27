#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Self-contained UHD 60FPS Broadcast Master Renderer for himart-gj/himart-22 GitHub Pages CDN.
Synthesizes 5-cut ko-KR-SunHiNeural showhost narration, mixes 116 BPM editorial BGM with 32% ducking,
and encodes 1080x1920 @ 60FPS H.264 High@L4.2 CRF 17 MP4 (`dishwasher_washer_care_uhd_60fps.mp4`).
"""
import asyncio
import io
import math
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

STORYBOARD_DRIVE_ID = "1m03hXynmcUz0yGE6t3vtR1mGw1-VN5DI"

NARRATION = [
    ("식기세척기에 에이이 에러 떴다고 바로 출장비 쓰지 마세요! 열풍건조구 물기부터 확인하면 해결됩니다.", "+10%", "+6Hz"),
    ("세제 거품이 넘쳐 비이 에러가 떴다면, 빈 통 상단 바구니에 우유 이백 밀리리터만 넣고 표준코스를 돌려보세요.", "+10%", "+6Hz"),
    ("물이 안 빠지는 오이나 오씨 에러는 삼십 분 식힌 뒤 바닥 거름망만 씻어주시고, 급수 에러는 싱크대 밸브를 열어주세요.", "+10%", "+5Hz"),
    ("세탁기 통살균할 때 과탄산소다와 구연산을 섞어 부으면 거품 팽창으로 고장 나니, 산소계 클리너만 단독으로 넣으세요!", "+10%", "+6Hz"),
    ("브랜드별 에러코드 일곱 가지 해결법, 롯데하이마트 경기광주점 프로필과 블로그에서 바로 확인해 보세요!", "+9%", "+5Hz"),
]


def find_font(bold: bool = True, size: int = 36) -> ImageFont.FreeTypeFont:
    cands = (
        [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJKkr-Bold.otf",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        ]
        if bold
        else [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJKkr-Regular.otf",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        ]
    )
    for p in cands:
        if Path(p).exists():
            return ImageFont.truetype(p, size=size)
    return ImageFont.load_default()


def download_storyboard() -> Image.Image:
    urls = [
        f"https://drive.usercontent.google.com/download?id={STORYBOARD_DRIVE_ID}&export=download&confirm=t",
        f"https://drive.google.com/uc?export=download&id={STORYBOARD_DRIVE_ID}&confirm=t",
    ]
    for url in urls:
        for _ in range(3):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=45) as resp:
                    raw = resp.read()
                im = Image.open(io.BytesIO(raw)).convert("RGB")
                if im.size[0] >= 2000:
                    return im
            except Exception:
                continue
    raise RuntimeError(f"Failed to download storyboard {STORYBOARD_DRIVE_ID}")


def synth_and_mix_audio(work: Path) -> tuple[list[float], Path]:
    import edge_tts  # type: ignore

    sr = 48000
    af_chain = (
        "silenceremove=start_periods=1:start_silence=0.02:start_threshold=-48dB,"
        "aresample=48000,highpass=f=80,"
        "equalizer=f=3200:width_type=h:width=900:g=1.8,"
        "equalizer=f=7200:width_type=h:width=1800:g=-2.2,"
        "acompressor=threshold=-16dB:ratio=2.4:attack=6:release=75,volume=1.85"
    )

    async def _run_tts() -> None:
        for idx, (txt, rate, pitch) in enumerate(NARRATION):
            mp3_p = work / f"tts_{idx}.mp3"
            for _ in range(4):
                try:
                    comm = edge_tts.Communicate(txt, "ko-KR-SunHiNeural", rate=rate, pitch=pitch)
                    await asyncio.wait_for(comm.save(str(mp3_p)), timeout=25.0)
                    if mp3_p.exists() and mp3_p.stat().st_size > 800:
                        break
                except Exception:
                    await asyncio.sleep(1.0)

    asyncio.run(_run_tts())
    pcms: list[np.ndarray] = []
    for idx in range(len(NARRATION)):
        mp3_p = work / f"tts_{idx}.mp3"
        if mp3_p.exists() and mp3_p.stat().st_size > 800:
            raw_f = work / f"v{idx}.f32"
            subprocess.run(
                ["ffmpeg", "-y", "-v", "error", "-i", str(mp3_p), "-af", af_chain, "-f", "f32le", "-ar", str(sr), "-ac", "1", str(raw_f)],
                check=True,
            )
            pcms.append(np.fromfile(raw_f, dtype=np.float32))
        else:
            pcms.append(np.zeros(int(7.5 * sr), dtype=np.float32))

    cut_durs = [round(len(p) / sr + 0.48, 2) for p in pcms]
    total_dur = sum(cut_durs)
    n_tot = int(math.ceil(total_dur * sr))

    beat_p = 60.0 / 116.0
    chords = [
        [174.61, 220.00, 261.63, 329.63],
        [164.81, 196.00, 246.94, 293.66],
        [146.83, 174.61, 220.00, 261.63],
        [130.81, 164.81, 196.00, 246.94],
    ]
    bgm = np.zeros(n_tot, dtype=np.float32)
    bar_len = beat_p * 4.0
    for i in range(int(math.ceil(total_dur / bar_len))):
        st, ed = int(i * bar_len * sr), min(n_tot, int((i + 1) * bar_len * sr))
        if ed <= st:
            break
        seg_t = np.arange(ed - st, dtype=np.float32) / sr
        env = np.minimum(1.0, seg_t / 0.15) * np.exp(-seg_t * 0.55)
        pad = sum(0.18 * np.sin(2.0 * math.pi * f * seg_t) for f in chords[i % 4])
        bgm[st:ed] += (pad * env).astype(np.float32)
    for b in range(int(total_dur / beat_p)):
        bst, bed = int(b * beat_p * sr), min(n_tot, int(b * beat_p * sr) + int(0.18 * sr))
        if bed <= bst:
            break
        bt = np.arange(bed - bst, dtype=np.float32) / sr
        kick = 0.24 * np.sin(2.0 * math.pi * (110.0 * np.exp(-bt * 24.0) + 48.0) * bt) * np.exp(-bt * 16.0)
        bgm[bst:bed] += kick.astype(np.float32)
    bgm = bgm / (float(np.max(np.abs(bgm))) or 1.0) * 0.36

    voice_mix = np.zeros(n_tot, dtype=np.float32)
    duck_env = np.ones(n_tot, dtype=np.float32)
    cursor = 0.0
    for pcm, cd in zip(pcms, cut_durs):
        vst = int((cursor + 0.14) * sr)
        ved = min(n_tot, vst + len(pcm))
        pk = float(np.max(np.abs(pcm)))
        if ved > vst and pk > 1e-4:
            voice_mix[vst:ved] += (pcm[: ved - vst] / pk * 0.88).astype(np.float32)
            duck_env[max(0, vst - int(0.08 * sr)) : min(n_tot, ved + int(0.16 * sr))] = 0.32
        cursor += cd

    win = max(1, int(0.045 * sr))
    duck_smooth = np.convolve(duck_env, np.ones(win, dtype=np.float32) / win, mode="same")
    master = np.clip(bgm * duck_smooth + voice_mix, -0.98, 0.98).astype(np.float32)

    raw_master = work / "master.f32"
    out_wav = work / "master.wav"
    master.tofile(raw_master)
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", str(raw_master), "-ac", "2", "-c:a", "pcm_s16le", str(out_wav)],
        check=True,
    )
    return cut_durs, out_wav


def make_shadow_text(canvas: Image.Image, pos: tuple[int, int], text: str, font: ImageFont.FreeTypeFont, color: tuple[int, int, int]) -> None:
    tmp = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    td = ImageDraw.Draw(tmp)
    td.text((pos[0], pos[1] + 6), text, font=font, fill=(0, 0, 0, 170), anchor="mm")
    tmp = tmp.filter(ImageFilter.GaussianBlur(radius=6))
    td2 = ImageDraw.Draw(tmp)
    td2.text(pos, text, font=font, fill=(*color, 255), anchor="mm")
    canvas.alpha_composite(tmp)


def crop_nonzero_rows(arr: np.ndarray) -> tuple[int, np.ndarray]:
    nz = np.where(np.any(arr[..., 3] > 0, axis=1))[0]
    if len(nz) == 0:
        return 0, arr[:1]
    y0, y1 = int(nz[0]), int(nz[-1]) + 1
    return y0, arr[y0:y1].copy()


def build_cut_overlays() -> list[tuple[tuple[int, np.ndarray], tuple[int, np.ndarray]]]:
    w, h, cx = 1080, 1920, 500
    f_badge = find_font(True, 30)
    f_h1 = find_font(True, 74)
    f_h2 = find_font(True, 80)
    f_sub = find_font(True, 35)
    f_card_t = find_font(True, 36)
    f_card_s = find_font(False, 28)
    f_store = find_font(True, 66)

    raw_pairs: list[tuple[Image.Image, Image.Image]] = []

    hd0 = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(hd0)
    d.rounded_rectangle((cx - 210, 250, cx + 210, 316), radius=33, fill=(225, 29, 72, 255))
    d.text((cx, 283), "출장비 아끼는 3초 점검", font=f_badge, fill=(255, 255, 255, 255), anchor="mm")
    make_shadow_text(hd0, (cx, 425), "식세기 AE 떴다고", f_h1, (255, 212, 59))
    make_shadow_text(hd0, (cx, 525), "출장비 쓰지 마세요!", f_h2, (255, 255, 255))
    bd0 = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(bd0)
    d.rounded_rectangle((84, 1335, 916, 1495), radius=26, fill=(15, 23, 42, 228), outline=(255, 212, 59, 255), width=3)
    d.text((cx, 1390), "열풍건조 에어필터 물기 유입 · 퐁퐁 거품", font=f_sub, fill=(255, 255, 255, 255), anchor="mm")
    d.text((cx, 1446), "큰 냄비만 뒤집어 넣어도 바로 예방!", font=f_card_s, fill=(255, 212, 59, 255), anchor="mm")
    raw_pairs.append((hd0, bd0))

    hd1 = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(hd1)
    d.rounded_rectangle((cx - 220, 250, cx + 220, 316), radius=33, fill=(15, 90, 229, 255))
    d.text((cx, 283), "LG bE · 거품 역류 응급처치", font=f_badge, fill=(255, 255, 255, 255), anchor="mm")
    make_shadow_text(hd1, (cx, 425), "거품 넘쳐 멈췄을 땐", f_h1, (255, 255, 255))
    make_shadow_text(hd1, (cx, 525), "우유 200ml 한 컵!", f_h2, (255, 212, 59))
    bd1 = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(bd1)
    d.rounded_rectangle((84, 1335, 916, 1495), radius=26, fill=(15, 23, 42, 228), outline=(96, 165, 250, 255), width=3)
    d.text((cx, 1390), "빈 통 린스 L0 설정 + 상단 바구니 우유 그릇", font=f_sub, fill=(255, 255, 255, 255), anchor="mm")
    d.text((cx, 1446), "무세제 표준코스 1회면 거품 즉시 제거!", font=f_card_s, fill=(147, 197, 253, 255), anchor="mm")
    raw_pairs.append((hd1, bd1))

    hd2 = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(hd2)
    d.rounded_rectangle((cx - 220, 245, cx + 220, 311), radius=33, fill=(16, 185, 129, 255))
    d.text((cx, 278), "배수 · 급수 멈춤 3분 자가해결", font=f_badge, fill=(255, 255, 255, 255), anchor="mm")
    make_shadow_text(hd2, (cx, 415), "OE · 5C / IE · 4C", f_h1, (255, 212, 59))
    make_shadow_text(hd2, (cx, 512), "거름망 · 밸브만 확인!", f_h1, (255, 255, 255))
    bd2 = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(bd2)
    d.rounded_rectangle((84, 1080, 916, 1265), radius=26, fill=(15, 23, 42, 232), outline=(255, 212, 59, 255), width=3)
    d.text((cx, 1138), "OE · 5C 배수 에러 (30분 냉각 필수)", font=f_card_t, fill=(255, 212, 59, 255), anchor="mm")
    d.text((cx, 1202), "바닥 거름망 반시계 분리 세척 · 전원+시작 3초 강제배수", font=f_card_s, fill=(255, 255, 255, 255), anchor="mm")
    d.rounded_rectangle((84, 1295, 916, 1480), radius=26, fill=(15, 23, 42, 232), outline=(96, 165, 250, 255), width=3)
    d.text((cx, 1353), "IE · 4C 급수 에러 (수돗물 미유입)", font=f_card_t, fill=(147, 197, 253, 255), anchor="mm")
    d.text((cx, 1417), "싱크대 아래 급수밸브 일자 개방 · 겨울철 호스 결빙 점검", font=f_card_s, fill=(255, 255, 255, 255), anchor="mm")
    raw_pairs.append((hd2, bd2))

    hd3 = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(hd3)
    d.rounded_rectangle((cx - 225, 250, cx + 225, 316), radius=33, fill=(225, 29, 72, 255))
    d.text((cx, 283), "제조사 공식 통살균 금기 주의보", font=f_badge, fill=(255, 255, 255, 255), anchor="mm")
    make_shadow_text(hd3, (cx, 425), "과탄산 + 구연산", f_h1, (255, 212, 59))
    make_shadow_text(hd3, (cx, 525), "절대 섞지 마세요!", f_h2, (255, 255, 255))
    bd3 = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(bd3)
    d.rounded_rectangle((84, 1295, 916, 1495), radius=26, fill=(15, 23, 42, 232), outline=(244, 63, 94, 255), width=3)
    d.text((cx, 1352), "식세기 물때 ➔ 구연산 단독 (20~22회 주기)", font=f_sub, fill=(255, 212, 59, 255), anchor="mm")
    d.text((cx, 1410), "LG 세탁조 ➔ 산소계 단독 · 삼성 ➔ 60℃ 무세제", font=f_sub, fill=(255, 255, 255, 255), anchor="mm")
    d.text((cx, 1460), "혼합 시 기체 급팽창 · 수위센서 오류 위험!", font=f_card_s, fill=(253, 164, 175, 255), anchor="mm")
    raw_pairs.append((hd3, bd3))

    hd4 = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(hd4)
    d.rounded_rectangle((cx - 210, 380, cx + 210, 448), radius=34, fill=(217, 56, 30, 255))
    d.text((cx, 414), "가전 관리 · 케어 공식 상담센터", font=f_badge, fill=(255, 255, 255, 255), anchor="mm")
    d.text((cx, 560), "롯데하이마트", font=f_store, fill=(15, 23, 42, 255), anchor="mm")
    d.text((cx, 650), "경기광주점", font=f_h2, fill=(217, 56, 30, 255), anchor="mm")
    bd4 = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(bd4)
    d.rounded_rectangle((84, 830, 916, 1185), radius=30, fill=(255, 255, 255, 255), outline=(203, 213, 225, 255), width=3)
    d.text((cx, 915), "에러코드 7종 표 · 통살균 정량 가이드", font=f_card_t, fill=(15, 90, 229, 255), anchor="mm")
    d.text((cx, 990), "@himart.ggukji 프로필 · 네이버 블로그 확인", font=f_sub, fill=(15, 23, 42, 255), anchor="mm")
    d.text((cx, 1070), "경기도 광주시 이배재로 8 (탄벌동)", font=f_card_s, fill=(71, 85, 105, 255), anchor="mm")
    d.text((cx, 1125), "대형 전용 무료주차 완비 · 031-767-1044", font=f_card_s, fill=(71, 85, 105, 255), anchor="mm")
    raw_pairs.append((hd4, bd4))

    return [(crop_nonzero_rows(np.array(a)), crop_nonzero_rows(np.array(b))) for a, b in raw_pairs]


def blend_strip(rgb: np.ndarray, strip_info: tuple[int, np.ndarray], dy: int = 0, opacity: float = 1.0) -> None:
    if opacity <= 0.01:
        return
    base_y, strip = strip_info
    sh = strip.shape[0]
    y0 = base_y + dy
    y1 = y0 + sh
    h = rgb.shape[0]
    s0 = max(0, -y0)
    s1 = sh - max(0, y1 - h)
    d0 = max(0, y0)
    d1 = min(h, y1)
    if s1 <= s0 or d1 <= d0:
        return
    sub = strip[s0:s1]
    alpha = sub[..., 3:4].astype(np.float32) * (opacity / 255.0)
    dst = rgb[d0:d1]
    rgb[d0:d1] = (dst * (1.0 - alpha) + sub[..., :3] * alpha).astype(np.uint8)


def main() -> None:
    out_mp4 = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("dist/reels/dishwasher_washer_care_uhd_60fps.mp4")
    out_mp4.parent.mkdir(parents=True, exist_ok=True)

    work = Path(tempfile.mkdtemp(prefix="uhd_care_reel_"))
    try:
        sb = download_storyboard()
        bgs = [
            np.array(sb.crop((0, 0, 1260, 2240)), dtype=np.uint8),
            np.array(sb.crop((1260, 0, 2520, 2240)), dtype=np.uint8),
            np.array(sb.crop((0, 2240, 1260, 4480)), dtype=np.uint8),
            np.array(sb.crop((1260, 2240, 2520, 4480)), dtype=np.uint8),
        ]
        ivory_bg = np.full((1920, 1080, 3), (244, 241, 236), dtype=np.uint8)

        w, h, fps = 1080, 1920, 60
        scrim_a = np.zeros((h, 1, 1), dtype=np.float32)
        for y in range(h):
            if y < 560:
                a = min(235, int(198 * (1.0 - y / 560.0) ** 1.2 + 48))
            elif y > 1040:
                a = min(238, int(222 * ((y - 1040) / (h - 1040)) ** 1.15 + 48))
            else:
                a = 48
            scrim_a[y, 0, 0] = a / 255.0
        scrim_keep = 1.0 - scrim_a
        scrim_add = np.array([[[8.0, 11.0, 18.0]]], dtype=np.float32) * scrim_a

        cut_durs, wav_path = synth_and_mix_audio(work)
        total_dur = sum(cut_durs)
        total_frames = int(round(total_dur * fps))
        overlays = build_cut_overlays()

        bounds = []
        acc = 0.0
        for idx, cd in enumerate(cut_durs):
            bounds.append((idx, acc, acc + cd))
            acc += cd

        cmd = [
            "ffmpeg", "-y", "-v", "error",
            "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{w}x{h}", "-r", str(fps), "-i", "pipe:0",
            "-i", str(wav_path),
            "-c:v", "libx264", "-preset", "fast", "-crf", "17",
            "-profile:v", "high", "-level", "4.2",
            "-minrate", "4800k", "-b:v", "6200k", "-maxrate", "8500k", "-bufsize", "16000k",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-shortest", "-movflags", "+faststart",
            str(out_mp4),
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        assert proc.stdin is not None

        rng = np.random.default_rng(20261127)
        grains = [rng.integers(-5, 6, size=(h, w, 1), dtype=np.int16) for _ in range(8)]

        for f_i in range(total_frames):
            t_g = f_i / fps
            c_idx, st_t, ed_t = bounds[-1]
            for idx, s0, s1 in bounds:
                if s0 <= t_g < s1:
                    c_idx, st_t, ed_t = idx, s0, s1
                    break
            tl = t_g - st_t
            prog = min(1.0, max(0.0, tl / max(0.2, ed_t - st_t)))
            sp = 1.0 - math.exp(-11.0 * tl) * math.cos(14.0 * tl) if tl < 0.65 else 1.0
            op_hd = min(1.0, tl * 6.0)
            op_bd = min(1.0, max(0.0, (tl - 0.18) * 5.0))
            dy_hd = int(round(-44.0 * (1.0 - sp)))
            dy_bd = int(round(36.0 * (1.0 - min(1.0, max(0.0, (tl - 0.15) * 4.5)))))

            if c_idx < 4:
                bg = bgs[c_idx]
                mh, mw, _ = bg.shape
                if c_idx == 0:
                    x0, y0 = int((mw - w) * 0.5), int((mh - h) * (0.82 - 0.65 * prog))
                elif c_idx == 1:
                    x0, y0 = int((mw - w) * (0.15 + 0.70 * prog)), int((mh - h) * 0.5)
                elif c_idx == 2:
                    x0, y0 = int((mw - w) * 0.5), int((mh - h) * (0.20 + 0.65 * prog))
                else:
                    x0, y0 = int((mw - w) * (0.80 - 0.60 * prog)), int((mh - h) * (0.65 - 0.35 * prog))
                crop = bg[y0 : y0 + h, x0 : x0 + w]
                frame = (crop.astype(np.float32) * scrim_keep + scrim_add).astype(np.uint8)
            else:
                frame = ivory_bg.copy()

            hd_s, bd_s = overlays[c_idx]
            blend_strip(frame, hd_s, dy=dy_hd, opacity=op_hd)
            blend_strip(frame, bd_s, dy=dy_bd, opacity=op_bd)
            frame = np.clip(frame.astype(np.int16) + grains[f_i & 7], 0, 255).astype(np.uint8)
            proc.stdin.write(frame.tobytes())

        proc.stdin.close()
        rc = proc.wait()
        if rc != 0:
            raise RuntimeError(f"ffmpeg exited with {rc}")
        print(f"Rendered UHD 60FPS master: {out_mp4} ({out_mp4.stat().st_size:,} bytes, {total_dur:.2f}s)")
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
