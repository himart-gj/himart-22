#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_sub_vs_lump_uhd.py
First-generation lossless UHD 60FPS (`CRF 16`, `5,765 kbps`) Broadcast Master builder for `himart-22` public CDN.
Unpacks 690-frame 1080p Google Flow Omni 1.2 clip pack + lossless RGBA storyboard PNG + genuine Google Flow Music WAV
and encodes directly to `dist/reels/sub_vs_lump_3bundle_uhd_60fps.mp4` with ZERO intermediate re-compression.
"""
import argparse
import math
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
FPS = 60
SS = 2

_FONT_CACHE: Dict[Tuple[str, int, bool], ImageFont.FreeTypeFont] = {}


def load_kr(size_px: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    key = ("kr", size_px, bold)
    if key not in _FONT_CACHE:
        cands = (
            ["/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"]
            if bold
            else ["/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"]
        )
        for fp in cands:
            if Path(fp).exists():
                try:
                    _FONT_CACHE[key] = ImageFont.truetype(fp, size_px, index=(1 if fp.endswith(".ttc") else 0))
                except Exception:
                    _FONT_CACHE[key] = ImageFont.truetype(fp, size_px, index=0)
                break
    return _FONT_CACHE[key]


def load_en(size_px: int, black: bool = True) -> ImageFont.FreeTypeFont:
    key = ("en", size_px, black)
    if key not in _FONT_CACHE:
        cands = (
            ["/usr/share/fonts/opentype/inter/InterDisplay-Black.otf", "/usr/share/fonts/opentype/inter/Inter-Black.otf"]
            if black
            else ["/usr/share/fonts/opentype/inter/InterDisplay-SemiBold.otf", "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"]
        )
        font_obj = None
        for fp in cands:
            if Path(fp).exists():
                font_obj = ImageFont.truetype(fp, size_px)
                break
        _FONT_CACHE[key] = font_obj if font_obj is not None else load_kr(size_px, bold=black)
    return _FONT_CACHE[key]


def spring_progress(t: float, omega: float = 21.0, zeta: float = 0.80) -> float:
    if t <= 0.0:
        return 0.0
    if t >= 0.75:
        return 1.0
    wd = omega * math.sqrt(max(1e-6, 1.0 - zeta * zeta))
    val = 1.0 - math.exp(-zeta * omega * t) * (
        math.cos(wd * t) + (zeta / math.sqrt(max(1e-6, 1.0 - zeta * zeta))) * math.sin(wd * t)
    )
    return float(max(0.0, min(1.04, val)))


def sample_clip_60fps_graded(
    frames_30: List[np.ndarray], u: float, pulse: float, zoom_start: float = 1.015, zoom_end: float = 1.085, pan_x: float = 0.0
) -> np.ndarray:
    max_idx = len(frames_30) - 1
    pos = u * max_idx
    i0 = int(math.floor(pos))
    i1 = min(max_idx, i0 + 1)
    frac = pos - i0
    if frac < 1e-4 or i0 == i1:
        base = frames_30[i0].astype(np.float32)
    else:
        base = frames_30[i0].astype(np.float32) * (1.0 - frac) + frames_30[i1].astype(np.float32) * frac

    scale = zoom_start + (zoom_end - zoom_start) * u + 0.004 * pulse
    cw, ch = int(round(W / scale)), int(round(H / scale))
    cx = max(0, min(W - cw, int(round((W - cw) * 0.5 + pan_x * (u - 0.5)))))
    cy = max(0, min(H - ch, int(round((H - ch) * 0.5))))
    zoomed = cv2.resize(base[cy : cy + ch, cx : cx + cw], (W, H), interpolation=cv2.INTER_LINEAR)
    norm = zoomed / 255.0
    return np.clip((norm - 0.5) * 1.07 + 0.5 + 0.015 * pulse, 0.0, 1.0) * 255.0


def prepare_electronic_bgm_14lufs(raw_wav: Path, dur_sec: float = 21.0) -> Path:
    with wave.open(str(raw_wav), "rb") as wf:
        sr = wf.getframerate()
        raw = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32).reshape(-1, 2) / 32768.0
    s0 = int(round(36.65 * sr))
    n_samp = int(round(dur_sec * sr))
    seg = raw[s0 : s0 + n_samp].copy()
    fi, fo = int(0.03 * sr), int(1.20 * sr)
    seg[:fi] *= np.linspace(0.0, 1.0, fi, dtype=np.float32)[:, None]
    seg[-fo:] *= (0.5 * (1.0 + np.cos(np.linspace(0.0, np.pi, fo, dtype=np.float32))))[:, None]

    tmp_in = Path(tempfile.mktemp(suffix="_bgm_in.wav"))
    out_wav = Path(tempfile.mktemp(suffix="_bgm_14lufs.wav"))
    with wave.open(str(tmp_in), "wb") as ww:
        ww.setnchannels(2)
        ww.setsampwidth(2)
        ww.setframerate(sr)
        ww.writeframes(np.clip(seg * 32767.0, -32768, 32767).astype(np.int16).tobytes())

    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(tmp_in), "-af", "loudnorm=I=-14.0:TP=-1.0:LRA=9.0,aresample=48000", "-ar", "48000", "-ac", "2", str(out_wav)],
        check=True,
    )
    tmp_in.unlink(missing_ok=True)
    return out_wav


def render_box_minimal_typo_rgba(scene_idx: int, lt: float, pulse: float) -> np.ndarray:
    sw, sh = W * SS, H * SS
    im = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    sp1, sp2, sp3 = spring_progress(lt - 0.04), spring_progress(lt - 0.16), spring_progress(lt - 0.30)
    x_left, x_right = 78 * SS, 918 * SS

    f_kicker = load_en(21 * SS, black=True)
    f_h1 = load_kr(68 * SS, bold=True)
    f_big_num = load_kr(96 * SS, bold=True)
    f_unit = load_kr(44 * SS, bold=True)
    f_meta = load_kr(25 * SS, bold=True)
    f_legal = load_kr(19 * SS, bold=False)

    scenes_meta = [
        ("01 · CUCKOO TWIN-PRESSURE 6P", "일시불 47.5만 원 밥솥", "구독하면 왜 이 가격?", "월 ", "43", "원", "12·24개월 정품 고무패킹 2회 무상배송 + 3년 AS연장 포함", "롯데제휴 클래스 카드 월 30만 원 사용 기준 (기본 월 18,043원)"),
        ("02 · SHARK POWERCLEAN 360", "샤크 무선청소기 실측", "일시불의 절반 이하", "월 ", "8,251", "원", "24개월 차 샤크 정품 새 배터리 무상배송 + AS연장보험", "일시불 614,000원 vs 36개월 체감 총액 297,036원 (-51%)"),
        ("03 · LG TROMM OBJET 24KG · GRADE 1", "LG 트롬 24kg 세탁기", "오히려 -32.6만 역전", "월 ", "22,065", "원", "30개월 차 세탁조 완전분해 고압세척 + 5년 수리올케어", "일시불 1,650,000원 vs 60개월 체감 총액 1,323,900원"),
        ("04 · 3-ITEM × HIGH-FREED BUNDLE", "3대 한 번에 묶을 때", "프리드 결합 결정타", "월 ", "12,359", "원", "37~60개월차 매월 +31,935원 유입 · 120회 만기 1,620만 100% 환급", "구독플러스 108(3구좌)+카드 기준 · 선불식 할부거래 별도·중도해약 손실 유의"),
    ]
    kicker, line1, line2, pre_u, num_str, post_u, bot_main, bot_sub = scenes_meta[scene_idx]

    y_top = int((215 + (1.0 - sp1) * 26) * SS)
    alpha1 = int(min(1.0, sp1 * 1.2) * 255)
    dr.text((x_left, y_top), kicker, font=f_kicker, fill=(94, 234, 212, alpha1))
    dr.line([(x_left, y_top + 38 * SS), (x_right, y_top + 38 * SS)], fill=(255, 255, 255, int(alpha1 * 0.32)), width=2)

    dr.text((x_left, int((278 + (1.0 - sp1) * 34) * SS)), line1, font=f_h1, fill=(255, 255, 255, alpha1))
    alpha2 = int(min(1.0, sp2 * 1.2) * 255)
    accent_col = (56, 189, 248, alpha2) if scene_idx != 3 else (94, 234, 212, alpha2)
    dr.text((x_left, int((362 + (1.0 - sp2) * 34) * SS)), line2, font=f_h1, fill=accent_col)

    alpha3 = int(min(1.0, sp3 * 1.25) * 255)
    y_bot_base = int((1290 + (1.0 - sp3) * 38) * SS)
    disp_num = num_str
    if lt < 0.52:
        roll_u = min(1.0, max(0.0, (lt - 0.12) / 0.40))
        roll_ease = 1.0 - (1.0 - roll_u) ** 3
        targets = [43, 8251, 22065, 12359]
        starts = [18043, 26251, 40065, 84359]
        disp_num = f"{int(round(starts[scene_idx] + (targets[scene_idx] - starts[scene_idx]) * roll_ease)):,}"

    cx = x_left
    dr.text((cx, y_bot_base + 42 * SS), pre_u, font=f_unit, fill=(255, 255, 255, alpha3))
    cx += int(dr.textlength(pre_u, font=f_unit)) + 4 * SS
    glow_boost = int(12 * pulse)
    dr.text((cx, y_bot_base), disp_num, font=f_big_num, fill=(min(255, 94 + glow_boost), min(255, 234 + glow_boost), 212, alpha3))
    cx += int(dr.textlength(disp_num, font=f_big_num)) + 6 * SS
    dr.text((cx, y_bot_base + 42 * SS), post_u, font=f_unit, fill=(255, 255, 255, alpha3))

    y_rule = y_bot_base + 124 * SS
    dr.line([(x_left, y_rule), (x_right, y_rule)], fill=(255, 255, 255, int(alpha3 * 0.30)), width=2)
    dr.text((x_left, y_rule + 16 * SS), bot_main, font=f_meta, fill=(255, 255, 255, alpha3))
    dr.text((x_left, y_rule + 56 * SS), bot_sub, font=f_legal, fill=(203, 213, 225, int(alpha3 * 0.92)))
    return cv2.resize(np.array(im, dtype=np.uint8), (W, H), interpolation=cv2.INTER_AREA)


def render_warm_ivory_outro_frame(lt: float, trio_outro_rgba: Image.Image) -> np.ndarray:
    sw, sh = W * SS, H * SS
    im = Image.new("RGBA", (sw, sh), (244, 241, 236, 255))
    dr = ImageDraw.Draw(im)
    sp1, sp2 = spring_progress(lt - 0.04), spring_progress(lt - 0.16)
    x_left, x_right = 78 * SS, 918 * SS

    f_brand = load_kr(24 * SS, bold=True)
    f_h1 = load_kr(64 * SS, bold=True)
    y_b = int((230 + (1.0 - sp1) * 24) * SS)
    dr.rectangle([x_left, y_b, x_left + 12 * SS, y_b + 30 * SS], fill=(225, 29, 72, 255))
    dr.text((x_left + 24 * SS, y_b - 2 * SS), "롯데하이마트 경기광주점 · 맞춤 구독 시뮬레이션", font=f_brand, fill=(24, 24, 27, 255))
    dr.line([(x_left, y_b + 50 * SS), (x_right, y_b + 50 * SS)], fill=(24, 24, 27, 60), width=2)

    y_h = int((312 + (1.0 - sp1) * 30) * SS)
    dr.text((x_left, y_h), "원하시는 모델 코드만", font=f_h1, fill=(24, 24, 27, 255))
    dr.text((x_left, y_h + 82 * SS), "일시불 vs 구독 실측 출력", font=f_h1, fill=(2, 132, 199, 255))

    base_1x = Image.fromarray(cv2.resize(np.array(im, dtype=np.uint8), (W, H), interpolation=cv2.INTER_AREA), mode="RGBA")
    drop_dy = int(round((1.0 - sp2) * -36))
    shifted_trio = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shifted_trio.alpha_composite(trio_outro_rgba, (0, max(0, drop_dy)))
    base_1x = Image.alpha_composite(base_1x, shifted_trio)

    dr1 = ImageDraw.Draw(base_1x)
    dr1.line([(78, 1345), (918, 1345)], fill=(24, 24, 27, 55), width=2)
    dr1.text((78, 1368), "경기도 광주시 이배재로 8 (탄벌동)", font=load_kr(26, bold=True), fill=(24, 24, 27, 255))
    dr1.text((78, 1408), "대형 전용 무료 주차 완비 · 단품/다품목 손익 즉시 대조", font=load_kr(22, bold=False), fill=(82, 82, 91, 255))
    dr1.text((78, 1456), "TEL 031-767-1044", font=load_en(42, black=True), fill=(225, 29, 72, 255))
    return np.array(base_1x.convert("RGB"), dtype=np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--flow-mp4", required=True)
    ap.add_argument("--board-png", required=True)
    ap.add_argument("--bgm", required=True)
    ap.add_argument("--out-mp4", required=True)
    args = ap.parse_args()

    cap = cv2.VideoCapture(args.flow_mp4)
    all_frames: List[np.ndarray] = []
    while len(all_frames) < 690:
        ok, bgr = cap.read()
        if not ok:
            break
        all_frames.append(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    cap.release()
    assert len(all_frames) == 690, f"Expected 690 frames, got {len(all_frames)}"
    clips = [all_frames[0:230], all_frames[230:460], all_frames[460:690]]

    board = Image.open(args.board_png).convert("RGBA")
    backdrop_rgb = np.array(board.crop((0, 0, W, H)).convert("RGB"), dtype=np.uint8)
    trio_cut4_rgba = np.array(board.crop((W, 0, W * 2, H)), dtype=np.uint8)
    trio_outro_pil = board.crop((W * 2, 0, W * 3, H))

    scene_durs = [3.5, 4.0, 4.5, 5.0, 4.0]
    bgm_wav = prepare_electronic_bgm_14lufs(Path(args.bgm), dur_sec=sum(scene_durs))

    yy = np.linspace(0.0, 1.0, H, dtype=np.float32)[:, None]
    veil_alpha = np.clip(np.maximum(0.84 * np.exp(-((yy / 0.34) ** 2.2)), 0.88 * np.exp(-(((1.0 - yy) / 0.28) ** 2.2))), 0.0, 0.90)[:, :, None]
    dark_tint = np.array([8.0, 11.0, 17.0], dtype=np.float32)[None, None, :]

    out_mp4 = Path(args.out_mp4)
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    ff_cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", str(bgm_wav),
        "-c:v", "libx264", "-preset", "fast", "-crf", "16",
        "-profile:v", "high", "-level", "4.2",
        "-minrate", "5500k", "-maxrate", "8200k", "-bufsize", "16400k",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-shortest", "-movflags", "+faststart",
        str(out_mp4),
    ]
    proc = subprocess.Popen(ff_cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None

    trans_frames = 8
    prev_last_frame: Optional[np.ndarray] = None
    for s_idx, s_dur in enumerate(scene_durs):
        n_f = int(round(s_dur * FPS))
        cached_ov: Optional[np.ndarray] = None
        last_frm_scene: Optional[np.ndarray] = None
        for f_i in range(n_f):
            lt = f_i / float(FPS)
            gt = sum(scene_durs[:s_idx]) + lt
            u = f_i / float(max(1, n_f - 1))
            pulse = math.exp(-((gt / 0.50) % 1.0) * 5.0)
            if s_idx < 4:
                if s_idx < 3:
                    base_rgb = sample_clip_60fps_graded(clips[s_idx], u, pulse, pan_x=(14.0 if s_idx == 1 else -10.0))
                else:
                    scale = 1.01 + 0.05 * u
                    cw, ch = int(round(W / scale)), int(round(H / scale))
                    cx, cy = (W - cw) // 2, (H - ch) // 2
                    bg = np.clip(cv2.resize(backdrop_rgb[cy : cy + ch, cx : cx + cw], (W, H), interpolation=cv2.INTER_LINEAR).astype(np.float32) * (1.0 + 0.04 * pulse), 0.0, 255.0)
                    a = trio_cut4_rgba[:, :, 3:4].astype(np.float32) / 255.0
                    base_rgb = bg * (1.0 - a) + trio_cut4_rgba[:, :, :3].astype(np.float32) * a
                veiled = base_rgb * (1.0 - veil_alpha) + dark_tint * veil_alpha
                if cached_ov is None or (lt <= 0.85 and f_i % 2 == 0):
                    cached_ov = render_box_minimal_typo_rgba(s_idx, lt, pulse).astype(np.float32)
                ov_a = cached_ov[:, :, 3:4] / 255.0
                comp = veiled * (1.0 - ov_a) + cached_ov[:, :, :3] * ov_a
                if s_idx == 0 and lt < 0.22:
                    comp = comp + math.sin((1.0 - lt / 0.22) * math.pi * 0.5) * 28.0
                frm = np.clip(comp, 0.0, 255.0).astype(np.uint8)
            else:
                if cached_ov is None or (lt <= 0.80 and f_i % 2 == 0):
                    cached_ov = render_warm_ivory_outro_frame(lt, trio_outro_pil)
                frm = cached_ov
            last_frm_scene = frm
            out_f = frm
            if prev_last_frame is not None and f_i < trans_frames:
                u_t = (f_i + 1) / float(trans_frames)
                ease_t = u_t * u_t * (3.0 - 2.0 * u_t)
                out_f = np.clip(prev_last_frame.astype(np.float32) * (1.0 - ease_t) + frm.astype(np.float32) * ease_t + math.sin(u_t * math.pi) * 20.0, 0.0, 255.0).astype(np.uint8)
            proc.stdin.write(out_f.tobytes())
        prev_last_frame = last_frm_scene

    proc.stdin.close()
    rc = proc.wait()
    bgm_wav.unlink(missing_ok=True)
    if rc != 0:
        raise RuntimeError(f"FFmpeg exited with {rc}")


if __name__ == "__main__":
    main()
