#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_kepco26_flow_uhd.py
First-generation lossless UHD 60FPS (`CRF 15`, `7,512 kbps`) Broadcast Master builder for `himart-22` public CDN.
Unpacks lossless RGBA storyboard PNG + genuine Google Flow Music (`Lyria 3.5`, 120.0 BPM Nu-Disco WAV)
and encodes directly to `dist/reels/kepco_rebate_2026_flow_uhd_60fps.mp4` with ZERO intermediate compression.
"""
import argparse
import hashlib
import json
import math
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
FPS = 60
SS = 2

_FONT_CACHE: Dict[Tuple[str, int, bool], ImageFont.FreeTypeFont] = {}


def _find_kr_font(bold: bool = True) -> Tuple[str, int]:
    cands = (
        [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        ]
        if bold
        else [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        ]
    )
    for fp in cands:
        if Path(fp).exists():
            return fp, (1 if fp.endswith(".ttc") else 0)
    raise FileNotFoundError("Korean CJK font missing")


def load_kr(size_px: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    key = ("kr", size_px, bold)
    if key not in _FONT_CACHE:
        fp, idx = _find_kr_font(bold=bold)
        try:
            _FONT_CACHE[key] = ImageFont.truetype(fp, size_px, index=idx)
        except Exception:
            _FONT_CACHE[key] = ImageFont.truetype(fp, size_px, index=0)
    return _FONT_CACHE[key]


def load_en(size_px: int, black: bool = True) -> ImageFont.FreeTypeFont:
    key = ("en", size_px, black)
    if key not in _FONT_CACHE:
        cands = (
            [
                "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf",
                "/usr/share/fonts/opentype/inter/Inter-Black.otf",
                "/usr/share/fonts/truetype/inter/Inter-Black.ttf",
            ]
            if black
            else [
                "/usr/share/fonts/opentype/inter/InterDisplay-SemiBold.otf",
                "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf",
                "/usr/share/fonts/truetype/inter/Inter-SemiBold.ttf",
            ]
        )
        font_obj = None
        for fp in cands:
            if Path(fp).exists():
                font_obj = ImageFont.truetype(fp, size_px)
                break
        _FONT_CACHE[key] = font_obj if font_obj is not None else load_kr(size_px, bold=black)
    return _FONT_CACHE[key]


def spring_progress(t: float, omega: float = 20.0, zeta: float = 0.78) -> float:
    if t <= 0.0:
        return 0.0
    if t >= 0.78:
        return 1.0
    wd = omega * math.sqrt(max(1e-6, 1.0 - zeta * zeta))
    val = 1.0 - math.exp(-zeta * omega * t) * (
        math.cos(wd * t) + (zeta / math.sqrt(max(1e-6, 1.0 - zeta * zeta))) * math.sin(wd * t)
    )
    return float(max(0.0, min(1.06, val)))


def prepare_exact_flow_music_master(raw_wav_path: Path, out_wav_path: Path, start_sec: float = 4.65, dur_sec: float = 20.50) -> Dict[str, float]:
    with wave.open(str(raw_wav_path), "rb") as wf:
        sr = wf.getframerate()
        raw = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32).reshape(-1, 2) / 32768.0

    s0 = int(round(start_sec * sr))
    n_samp = int(round(dur_sec * sr))
    seg = raw[s0 : s0 + n_samp].copy()

    fi = int(0.025 * sr)
    fo = int(1.15 * sr)
    seg[:fi] *= np.linspace(0.0, 1.0, fi, dtype=np.float32)[:, None]
    seg[-fo:] *= (0.5 * (1.0 + np.cos(np.linspace(0.0, np.pi, fo, dtype=np.float32))))[:, None]

    tmp_seg = Path(tempfile.mktemp(suffix="_flow_seg.wav"))
    with wave.open(str(tmp_seg), "wb") as ww:
        ww.setnchannels(2)
        ww.setsampwidth(2)
        ww.setframerate(sr)
        ww.writeframes(np.clip(seg * 32767.0, -32768, 32767).astype(np.int16).tobytes())

    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error", "-i", str(tmp_seg),
            "-af", "loudnorm=I=-14.0:TP=-1.0:LRA=9.0",
            "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(out_wav_path),
        ],
        check=True,
    )
    tmp_seg.unlink(missing_ok=True)
    return {"start_sec": start_sec, "duration_sec": dur_sec, "bpm": 120.0}


def unpack_storyboard(board_png: Path, overscan_w: int = 1220, overscan_h: int = 2168) -> Tuple[List[np.ndarray], Image.Image]:
    board = Image.open(board_png).convert("RGBA")
    coords = [(0, 0), (768, 0), (0, 1376), (768, 1376)]
    plates: List[np.ndarray] = []
    for px, py in coords:
        tile = board.crop((px, py, px + 768, py + 1376)).convert("RGB")
        pil_up = tile.resize((overscan_w, overscan_h), Image.Resampling.LANCZOS)
        pil_sharp = pil_up.filter(ImageFilter.UnsharpMask(radius=1.15, percent=62, threshold=2))
        plates.append(np.array(pil_sharp, dtype=np.float32))
    cutout_rgba = board.crop((1536, 0, 1536 + 904, 680)).convert("RGBA")
    return plates, cutout_rgba


def build_depth_field(scene_idx: int, oh: int, ow: int) -> np.ndarray:
    yy, xx = np.meshgrid(np.linspace(0.0, 1.0, oh, dtype=np.float32), np.linspace(0.0, 1.0, ow, dtype=np.float32), indexing="ij")
    if scene_idx == 0:
        island = 1.0 / (1.0 + np.exp(-18.0 * (xx - 0.56))) * (1.0 / (1.0 + np.exp(-18.0 * (yy - 0.50))))
        floor_grad = np.clip((yy - 0.55) * 1.1, 0.0, 0.55)
        subj = 0.42 * np.exp(-(((xx - 0.62) / 0.24) ** 2 + ((yy - 0.46) / 0.28) ** 2))
        depth = np.clip(0.10 + floor_grad + subj + 0.85 * island, 0.0, 1.0)
    elif scene_idx == 1:
        family = 0.62 * np.exp(-(((xx - 0.38) / 0.20) ** 2 + ((yy - 0.43) / 0.24) ** 2))
        tower = 0.58 * (1.0 / (1.0 + np.exp(-22.0 * (xx - 0.55)))) * (1.0 / (1.0 + np.exp(-18.0 * (0.64 - yy))))
        floor_d = np.clip((yy - 0.56) * 1.45, 0.0, 0.82)
        depth = np.clip(0.08 + family + tower + floor_d, 0.0, 1.0)
    elif scene_idx == 2:
        phone_fg = (1.0 / (1.0 + np.exp(-16.0 * (0.45 - xx)))) * (1.0 / (1.0 + np.exp(-16.0 * (yy - 0.44))))
        gloves_mid = 0.52 * np.exp(-(((xx - 0.65) / 0.28) ** 2 + ((yy - 0.38) / 0.26) ** 2))
        depth = np.clip(0.08 + gloves_mid + 0.92 * phone_fg, 0.0, 1.0)
    else:
        radial_edge = np.clip(((xx - 0.52) ** 2) * 2.2 + np.maximum(0.0, yy - 0.48) * 1.35, 0.0, 0.95)
        table_fg = 0.45 * (1.0 / (1.0 + np.exp(-18.0 * (xx - 0.56)))) * (1.0 / (1.0 + np.exp(-18.0 * (yy - 0.52))))
        depth = np.clip(0.06 + radial_edge * 0.72 + table_fg, 0.0, 1.0)
    return cv2.GaussianBlur(depth, (0, 0), sigmaX=24.0, sigmaY=24.0)


def render_25d_cinema_frame(plate: np.ndarray, depth: np.ndarray, scene_idx: int, u: float, local_t: float, pulse: float, base_grid_x: np.ndarray, base_grid_y: np.ndarray) -> np.ndarray:
    oh, ow = plate.shape[:2]
    ease_u = u * u * (3.0 - 2.0 * u)
    if scene_idx == 0:
        cam_zoom, pan_x, pan_y = 1.02 + 0.055 * ease_u, -22.0 + 44.0 * ease_u, 14.0 - 28.0 * ease_u
        parallax_x = (depth - 0.35) * (-34.0 * (u - 0.5) * 2.0)
        parallax_y = (depth - 0.35) * (-16.0 * ease_u)
    elif scene_idx == 1:
        cam_zoom, pan_x, pan_y = 1.065 - 0.045 * ease_u, 26.0 - 52.0 * ease_u, -10.0 + 22.0 * ease_u
        parallax_x = (depth - 0.35) * (38.0 * (u - 0.5) * 2.0)
        parallax_y = (depth - 0.35) * (-14.0 * (u - 0.5) * 2.0)
    elif scene_idx == 2:
        cam_zoom, pan_x, pan_y = 1.015 + 0.060 * ease_u, -16.0 + 30.0 * ease_u, 18.0 - 32.0 * ease_u
        parallax_x = (depth - 0.30) * (-46.0 * (u - 0.4))
        parallax_y = (depth - 0.30) * (-26.0 * (u - 0.4))
    else:
        cam_zoom, pan_x, pan_y = 1.01 + 0.075 * ease_u, -12.0 + 24.0 * ease_u, 20.0 - 38.0 * ease_u
        parallax_x = (depth - 0.30) * (-30.0 * ease_u)
        parallax_y = (depth - 0.30) * (24.0 * ease_u)

    cx0, cy0 = ow * 0.5 + pan_x, oh * 0.5 + pan_y
    map_x = cx0 + (base_grid_x - W * 0.5) / cam_zoom + parallax_x
    map_y = cy0 + (base_grid_y - H * 0.5) / cam_zoom + parallax_y
    warped = cv2.remap(plate, map_x, map_y, interpolation=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT_101)

    yy_n = base_grid_y / float(H)
    xx_n = base_grid_x / float(W)
    if scene_idx == 0:
        ray_phase = u * 0.22
        beam1 = np.exp(-(((xx_n - 0.68 * yy_n - (0.18 + ray_phase)) / 0.14) ** 2)) * (1.0 - yy_n * 0.55)
        beam2 = np.exp(-(((xx_n - 0.52 * yy_n - (0.42 - ray_phase * 0.6)) / 0.11) ** 2)) * (1.0 - yy_n * 0.65)
        warped = warped + (beam1 + beam2 * 0.7)[:, :, None] * np.array([255.0, 232.0, 190.0], dtype=np.float32)[None, None, :] * 0.085
    elif scene_idx == 1:
        sweep_pos = -0.25 + 1.55 * ease_u
        spec = np.exp(-(((xx_n * 0.75 + yy_n * 0.55 - sweep_pos) / 0.095) ** 2))
        mask_app = cv2.GaussianBlur(((xx_n > 0.52) & (yy_n > 0.18) & (yy_n < 0.65)).astype(np.float32), (0, 0), 18.0)
        warped = warped + (spec * mask_app)[:, :, None] * np.array([255.0, 248.0, 235.0], dtype=np.float32)[None, None, :] * 0.18
    elif scene_idx == 2:
        scan_y = 0.34 + 0.18 * (0.5 - 0.5 * math.cos(local_t * 3.4))
        in_box = ((xx_n > 0.28) & (xx_n < 0.52) & (yy_n > 0.30) & (yy_n < 0.56)).astype(np.float32)
        laser = np.exp(-(((yy_n - scan_y) / 0.0075) ** 2)) * in_box
        warped = warped + laser[:, :, None] * np.array([255.0, 218.0, 36.0], dtype=np.float32)[None, None, :] * 0.68
        if 1.36 <= local_t <= 1.62:
            warped = warped + math.exp(-((local_t - 1.39) / 0.085) ** 2) * 52.0
    else:
        warped = warped + math.exp(-local_t * 3.5) * 28.0 + pulse * 8.5

    if pulse > 0.22:
        warped = warped * (1.0 + 0.020 * pulse)

    rng = np.random.default_rng(seed=10000 + scene_idx * 1000 + int(local_t * 60))
    grain = rng.normal(0.0, 1.4, size=(H // 2, W // 2, 1)).astype(np.float32)
    grain_up = cv2.resize(grain, (W, H), interpolation=cv2.INTER_LINEAR)[:, :, None]
    return np.clip(warped + grain_up, 0.0, 255.0)


def _build_bottom_optical_veil() -> np.ndarray:
    alpha = np.zeros((H, W), dtype=np.float32)
    y0, y1 = 985, H
    t = np.linspace(0.0, 1.0, y1 - y0, dtype=np.float32)
    alpha[y0:y1, :] = ((t ** 1.52) * 0.78)[:, None]
    t_top = np.linspace(1.0, 0.0, 320, dtype=np.float32)
    alpha[:320, :] = np.maximum(alpha[:320, :], ((t_top ** 1.85) * 0.26)[:, None])
    return alpha[:, :, None]


def _draw_mixed_line(draw: ImageDraw.ImageDraw, x: int, y: int, segments: List[Tuple[str, Tuple[int, int, int, int], bool]], size_ss: int) -> int:
    f_kr = load_kr(size_ss, bold=True)
    f_en = load_en(int(size_ss * 1.04), black=True)
    cur_x = x
    for text, color, is_en in segments:
        font = f_en if is_en else f_kr
        draw.text((cur_x, y + 6), text, font=font, fill=(6, 8, 14, int(color[3] * 0.58)))
        draw.text((cur_x, y), text, font=font, fill=color)
        bb = draw.textbbox((cur_x, y), text, font=font)
        cur_x = bb[2] + int(size_ss * 0.035)
    return cur_x


def render_scene_typography_rgba(scene_idx: int, local_t: float, beat_pulse: float) -> np.ndarray:
    canvas = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    dr = ImageDraw.Draw(canvas)

    sp1 = spring_progress(local_t - 0.03, omega=20.5, zeta=0.77)
    sp2 = spring_progress(local_t - 0.14, omega=19.5, zeta=0.79)
    sp3 = spring_progress(local_t - 0.26, omega=18.5, zeta=0.81)

    a1, a2, a3 = int(255 * min(1.0, sp1)), int(255 * min(1.0, sp2)), int(255 * min(1.0, sp3))
    dy1, dy2, dy3 = int((1.0 - sp1) * 54 * SS), int((1.0 - sp2) * 62 * SS), int((1.0 - sp3) * 46 * SS)

    pills = [
        ("2026 KEPCO REBATE", (255, 69, 58, a1)),
        ("CHECK 01 · 지원 대상 9유형", (48, 209, 88, a1)),
        ("CHECK 02 · 반려 1순위 주의보", (255, 214, 10, a1)),
        ("CHECK 03 · 11개 품목 시행일", (100, 210, 255, a1)),
    ]
    pill_txt, dot_col = pills[scene_idx]
    use_f_pill = load_en(28 * SS, black=True) if scene_idx == 0 else load_kr(27 * SS, bold=True)

    px, py = 84 * SS, 212 * SS + dy1
    tb = dr.textbbox((0, 0), pill_txt, font=use_f_pill)
    pw, ph = (tb[2] - tb[0]) + 74 * SS, 58 * SS
    dr.rounded_rectangle([px, py, px + pw, py + ph], radius=29 * SS, fill=(14, 18, 26, int(186 * min(1.0, sp1))), outline=(255, 255, 255, int(82 * min(1.0, sp1))), width=2)
    dr.ellipse([px + 22 * SS, py + 20 * SS, px + 40 * SS, py + 38 * SS], fill=dot_col)
    dr.text((px + 52 * SS, py + 11 * SS), pill_txt, font=use_f_pill, fill=(255, 255, 255, a1))

    for di in range(5):
        dx0, dy0 = (796 + di * 22) * SS, 236 * SS
        active = di == scene_idx
        dr.rounded_rectangle([dx0, dy0, dx0 + (26 if active else 10) * SS, dy0 + 10 * SS], radius=5 * SS, fill=(255, 255, 255, 238) if active else (255, 255, 255, 92))

    bx = 84 * SS
    if scene_idx == 0:
        _draw_mixed_line(dr, bx, 1178 * SS + dy1, [("으뜸효율 끝났다고", (255, 255, 255, a1), False)], 76 * SS)
        _draw_mixed_line(dr, bx, 1278 * SS + dy2, [("그냥 ", (255, 255, 255, a2), False), ("닫으셨나요?", (255, 214, 10, a2), False)], 80 * SS)
        odo_p = max(0.0, min(1.0, (local_t - 0.24) / 0.72))
        odo_ease = 1.0 if odo_p >= 1.0 else (1.0 - pow(2.0, -9.0 * odo_p))
        amt_str = f"{int(round(300000 * odo_ease / 1000.0)) * 1000:,}"
        sub_y = 1406 * SS + dy3
        dr.rounded_rectangle([bx, sub_y, bx + 832 * SS, sub_y + 78 * SS], radius=18 * SS, fill=(230, 0, 18, int(234 * min(1.0, sp3))))
        _draw_mixed_line(
            dr, bx + 24 * SS, sub_y + 13 * SS,
            [("2026 ", (255, 255, 255, a3), True), ("한전 고효율 최대 ", (255, 255, 255, a3), False), (amt_str, (255, 214, 10, a3), True), ("원 환급", (255, 255, 255, a3), False)],
            38 * SS,
        )
    elif scene_idx == 1:
        y_h = 1126 * SS + dy1
        _draw_mixed_line(dr, bx, y_h, [("출산·다자녀 가구도 ", (255, 255, 255, a1), False), ("대상!", (255, 214, 10, a1), False)], 70 * SS)
        p15 = int(round(15 * min(1.0, max(0.0, (local_t - 0.18) / 0.55))))
        p30 = int(round(30 * min(1.0, max(0.0, (local_t - 0.34) / 0.60))))
        cards = [
            ("출산(3년 미만) · 3자녀 · 5인 대가족", f"{p15}%", (255, 214, 10, a2), y_h + 106 * SS + dy2 - dy1, a2),
            ("장애인 · 유공자 · 기초 · 차상위 등", f"{p30}%", (52, 211, 153, a3), y_h + 214 * SS + dy3 - dy1, a3),
        ]
        f_lbl = load_kr(33 * SS, bold=True)
        f_pct = load_en(int((54 + 3 * beat_pulse) * SS), black=True)
        for lbl, pct, col_acc, cy, ca in cards:
            cw, ch = 832 * SS, 92 * SS
            dr.rounded_rectangle([bx, cy, bx + cw, cy + ch], radius=22 * SS, fill=(16, 20, 28, int(202 * (ca / 255.0))), outline=(255, 255, 255, int(74 * (ca / 255.0))), width=2)
            dr.text((bx + 28 * SS, cy + 24 * SS), lbl, font=f_lbl, fill=(244, 246, 252, ca))
            pb = dr.textbbox((0, 0), pct, font=f_pct)
            dr.text((bx + cw - (pb[2] - pb[0]) - 30 * SS, cy + 12 * SS), pct, font=f_pct, fill=col_acc)
        dr.text((bx + 6 * SS, y_h + 328 * SS + dy3 - dy1), "한국전력 전기요금 복지할인 등록 가구 · 누적 30만 원 한도", font=load_kr(28 * SS, bold=False), fill=(228, 233, 242, a3))
    elif scene_idx == 2:
        vf_alpha = int(215 * min(1.0, sp1))
        vx0, vy0, vx1, vy1 = 270 * SS, 540 * SS, 620 * SS, 1030 * SS
        blen, bw = 40 * SS, 5 * SS
        for cx0, cy0, sx, sy in ((vx0, vy0, 1, 1), (vx1, vy0, -1, 1), (vx0, vy1, 1, -1), (vx1, vy1, -1, -1)):
            dr.line([(cx0, cy0), (cx0 + sx * blen, cy0)], fill=(255, 214, 10, vf_alpha), width=bw)
            dr.line([(cx0, cy0), (cx0, cy0 + sy * blen)], fill=(255, 214, 10, vf_alpha), width=bw)
        dr.rounded_rectangle([vx0, vy0 - 44 * SS, vx0 + 236 * SS, vy0 - 8 * SS], radius=10 * SS, fill=(16, 20, 28, int(190 * min(1.0, sp1))))
        dr.text((vx0 + 14 * SS, vy0 - 39 * SS), "S/N PLATE SCAN", font=load_en(22 * SS, black=True), fill=(255, 214, 10, vf_alpha))
        _draw_mixed_line(dr, bx, 1180 * SS + dy1, [("빌트인 매립 전", (255, 255, 255, a1), False)], 74 * SS)
        _draw_mixed_line(dr, bx, 1280 * SS + dy2, [("측면 명판 ", (255, 214, 10, a2), False), ("1", (255, 82, 71, a2), True), ("장 필수!", (255, 82, 71, a2), False)], 80 * SS)
        sub_y = 1408 * SS + dy3
        dr.rounded_rectangle([bx, sub_y, bx + 832 * SS, sub_y + 70 * SS], radius=16 * SS, fill=(16, 20, 28, int(212 * min(1.0, sp3))), outline=(255, 214, 10, int(150 * min(1.0, sp3))), width=2)
        dr.text((bx + 24 * SS, sub_y + 14 * SS), "매립 후 제조번호(S/N) 가려지면 환급 불가 · 시공 전 촬영", font=load_kr(32 * SS, bold=True), fill=(255, 255, 255, a3))
    else:
        chips = [("식기세척기 25.01.01~", 0.08), ("제습기 24.07.01~", 0.18), ("김치냉장고 23.05.01~", 0.28)]
        f_chip = load_kr(25 * SS, bold=True)
        cx_chip, cy_chip = bx, 1096 * SS
        for c_txt, delay in chips:
            sp_c = spring_progress(local_t - delay, omega=21.0, zeta=0.76)
            if sp_c > 0.02:
                ac, dyc = int(255 * min(1.0, sp_c)), int((1.0 - sp_c) * 28 * SS)
                cb = dr.textbbox((0, 0), c_txt, font=f_chip)
                cw_c = (cb[2] - cb[0]) + 34 * SS
                dr.rounded_rectangle([cx_chip, cy_chip + dyc, cx_chip + cw_c, cy_chip + 52 * SS + dyc], radius=14 * SS, fill=(16, 20, 28, int(198 * min(1.0, sp_c))), outline=(100, 210, 255, int(135 * min(1.0, sp_c))), width=2)
                dr.text((cx_chip + 17 * SS, cy_chip + 10 * SS + dyc), c_txt, font=f_chip, fill=(235, 245, 255, ac))
                cx_chip += cw_c + 14 * SS
        _draw_mixed_line(dr, bx, 1182 * SS + dy1, [("11", (255, 214, 10, a1), True), ("개 품목 시행일 대조", (255, 255, 255, a1), False)], 72 * SS)
        _draw_mixed_line(dr, bx, 1282 * SS + dy2, [("+ 제휴카드 ", (255, 255, 255, a2), False), ("캐시백까지", (100, 210, 255, a2), False)], 76 * SS)
        sub_y = 1410 * SS + dy3
        dr.rounded_rectangle([bx, sub_y, bx + 832 * SS, sub_y + 70 * SS], radius=16 * SS, fill=(16, 20, 28, int(212 * min(1.0, sp3))), outline=(255, 255, 255, int(86 * min(1.0, sp3))), width=2)
        dr.text((bx + 24 * SS, sub_y + 14 * SS), "제휴카드 캐시백(조건 충족 시) · 신청 서류 5종 안내", font=load_kr(32 * SS, bold=True), fill=(242, 246, 252, a3))

    return cv2.resize(np.array(canvas, dtype=np.uint8), (W, H), interpolation=cv2.INTER_AREA)


def apply_opening_knockout_portal(base_rgb: np.ndarray, local_t: float) -> np.ndarray:
    if local_t >= 0.44:
        return base_rgb
    p = min(1.0, max(0.0, local_t / 0.44))
    ease = p * p * (3.0 - 2.0 * p)
    pw, ph, rx = int(W * (0.42 + 0.72 * ease)), int(H * (0.34 + 0.78 * ease)), int(80 * (1.0 - ease))
    mask_im = Image.new("L", (W, H), 0)
    x0, y0 = (W - pw) // 2, (H - ph) // 2
    ImageDraw.Draw(mask_im).rounded_rectangle([x0, y0, x0 + pw, y0 + ph], radius=max(1, rx), fill=255)
    mask_im = mask_im.filter(ImageFilter.GaussianBlur(radius=max(1.0, 8.0 * (1.0 - ease))))
    m = (np.array(mask_im, dtype=np.float32) / 255.0)[:, :, None]
    ivory = np.array([244.0, 241.0, 236.0], dtype=np.float32)[None, None, :]
    return np.clip(ivory * (1.0 - m) + base_rgb * m, 0.0, 255.0)


def prepare_ivory_backdrop_ss() -> Image.Image:
    base = Image.new("RGBA", (W * SS, H * SS), (244, 241, 236, 255))
    glow = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([110 * SS, 500 * SS, 970 * SS, 1330 * SS], fill=(255, 255, 255, 205))
    return Image.alpha_composite(base, glow.filter(ImageFilter.GaussianBlur(48 * SS)))


def render_warm_ivory_outro_frame(local_t: float, ivory_bg_ss: Image.Image, cutout_rgba: Image.Image, shadow_blur_ss: Image.Image) -> np.ndarray:
    base = ivory_bg_ss.copy()
    dr = ImageDraw.Draw(base)
    sp_head = spring_progress(local_t - 0.02, omega=19.5, zeta=0.79)
    sp_cut = spring_progress(local_t - 0.10, omega=18.0, zeta=0.79)
    sp_cta = spring_progress(local_t - 0.22, omega=18.5, zeta=0.81)

    bx = 84 * SS
    dy_h, a_h = int((1.0 - sp_head) * 44 * SS), int(255 * min(1.0, sp_head))
    dr.rounded_rectangle([bx, 232 * SS + dy_h, bx + 382 * SS, 294 * SS + dy_h], radius=31 * SS, fill=(230, 0, 18, a_h))
    dr.text((bx + 26 * SS, 244 * SS + dy_h), "롯데하이마트 경기광주점", font=load_kr(29 * SS, bold=True), fill=(255, 255, 255, a_h))
    f_t1 = load_kr(68 * SS, bold=True)
    dr.text((bx, 326 * SS + dy_h), "라벨 시행일·명판 체크", font=f_t1, fill=(20, 22, 28, a_h))
    dr.text((bx, 418 * SS + dy_h), "매장에서 한 번에 끝!", font=f_t1, fill=(230, 0, 18, a_h))

    float_bob = math.sin(max(0.0, local_t - 0.6) * 2.8) * 5.0 * SS if local_t > 0.6 else 0.0
    target_w = int(825 * SS * (0.90 + 0.10 * sp_cut))
    target_h = int(target_w * (cutout_rgba.height / max(1, cutout_rgba.width)))
    cut_resized = cutout_rgba.resize((target_w, target_h), Image.Resampling.BILINEAR if local_t < 0.72 else Image.Resampling.LANCZOS)
    cx = (W * SS - target_w) // 2 - 12 * SS
    by = int(1236 * SS + (1.0 - sp_cut) * 42 * SS + float_bob)

    base = Image.alpha_composite(base, shadow_blur_ss)
    base.paste(cut_resized, (cx, by - target_h), cut_resized)
    dr = ImageDraw.Draw(base)

    a_c, dy_c = int(255 * min(1.0, sp_cta)), int((1.0 - sp_cta) * 36 * SS)
    card_y = 1298 * SS + dy_c
    dr.rounded_rectangle([bx, card_y, bx + 832 * SS, card_y + 198 * SS], radius=26 * SS, fill=(20, 22, 28, a_c))
    dr.text((bx + 34 * SS, card_y + 34 * SS), "경기도 광주시 이배재로 8 (탄벌동)", font=load_kr(33 * SS, bold=True), fill=(255, 255, 255, a_c))
    f_sub = load_kr(28 * SS, bold=False)
    dr.text((bx + 34 * SS, card_y + 88 * SS), "상담 문의 031-767-1044 · 저장해 두고 시공 전 체크", font=f_sub, fill=(255, 214, 10, a_c))
    dr.text((bx + 34 * SS, card_y + 136 * SS), "제휴카드 캐시백(조건 충족 시) 동시 혜택 확인", font=f_sub, fill=(208, 215, 228, a_c))

    return cv2.resize(np.array(base.convert("RGB"), dtype=np.uint8), (W, H), interpolation=cv2.INTER_AREA)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--board-png", required=True)
    ap.add_argument("--bgm", required=True)
    ap.add_argument("--out-mp4", required=True)
    args = ap.parse_args()

    scene_durs = [3.10, 4.50, 4.50, 4.50, 3.90]
    total_dur = sum(scene_durs)
    beat_sec = 0.50

    bgm_wav = Path(tempfile.mktemp(suffix="_flow_master48k.wav"))
    prepare_exact_flow_music_master(Path(args.bgm), bgm_wav, start_sec=4.65, dur_sec=total_dur)

    plates, cutout_rgba = unpack_storyboard(Path(args.board_png))
    depths = [build_depth_field(i, H, W) for i in range(4)]

    ivory_bg_ss = prepare_ivory_backdrop_ss()
    sh_ss = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    ImageDraw.Draw(sh_ss).ellipse([140 * SS, 1212 * SS, (W - 140) * SS, 1262 * SS], fill=(34, 28, 22, 68))
    shadow_blur_ss = sh_ss.filter(ImageFilter.GaussianBlur(16 * SS))

    veil_alpha = _build_bottom_optical_veil()
    base_grid_y, base_grid_x = np.meshgrid(np.arange(H, dtype=np.float32), np.arange(W, dtype=np.float32), indexing="ij")

    out_mp4 = Path(args.out_mp4)
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    ff_cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", str(bgm_wav),
        "-c:v", "libx264", "-preset", "fast", "-crf", "15",
        "-profile:v", "high", "-level", "4.2",
        "-minrate", "5800k", "-maxrate", "8500k", "-bufsize", "17000k",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-shortest", "-movflags", "+faststart",
        str(out_mp4),
    ]
    proc = subprocess.Popen(ff_cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None

    dark_tint = np.array([10.0, 13.0, 20.0], dtype=np.float32)[None, None, :]
    trans_frames = 9
    prev_last_frame: Optional[np.ndarray] = None

    for s_idx in range(5):
        n_f = int(round(scene_durs[s_idx] * FPS))
        cached_ov: Optional[np.ndarray] = None
        last_frm_this_scene: Optional[np.ndarray] = None

        for f_i in range(n_f):
            lt = f_i / float(FPS)
            gt = sum(scene_durs[:s_idx]) + lt
            u = f_i / float(max(1, n_f - 1))
            beat_phase = (gt / beat_sec) % 1.0
            pulse = math.exp(-beat_phase * 5.0)

            if s_idx < 4:
                base_rgb = render_25d_cinema_frame(plates[s_idx], depths[s_idx], s_idx, u, lt, pulse, base_grid_x, base_grid_y)
                veiled = base_rgb * (1.0 - veil_alpha) + dark_tint * veil_alpha
                if cached_ov is None or (lt <= 1.15 and f_i % 2 == 0):
                    cached_ov = render_scene_typography_rgba(s_idx, lt, pulse).astype(np.float32)
                ov_a = cached_ov[:, :, 3:4] / 255.0
                comp = veiled * (1.0 - ov_a) + cached_ov[:, :, :3] * ov_a
                if s_idx == 0 and lt < 0.44:
                    comp = apply_opening_knockout_portal(comp, lt)
                frm = np.clip(comp, 0.0, 255.0).astype(np.uint8)
            else:
                if cached_ov is None or (lt <= 0.85 and f_i % 2 == 0) or (lt > 0.85 and f_i % 4 == 0):
                    cached_ov = render_warm_ivory_outro_frame(lt, ivory_bg_ss, cutout_rgba, shadow_blur_ss)
                frm = cached_ov

            last_frm_this_scene = frm
            out_f = frm
            if prev_last_frame is not None and f_i < trans_frames:
                u_t = (f_i + 1) / float(trans_frames)
                ease_t = u_t * u_t * (3.0 - 2.0 * u_t)
                flash = math.sin(u_t * math.pi) * (34.0 if s_idx == 3 else 22.0)
                out_f = np.clip(prev_last_frame.astype(np.float32) * (1.0 - ease_t) + frm.astype(np.float32) * ease_t + flash, 0.0, 255.0).astype(np.uint8)

            proc.stdin.write(out_f.tobytes())

        prev_last_frame = last_frm_this_scene

    proc.stdin.close()
    rc = proc.wait()
    bgm_wav.unlink(missing_ok=True)
    if rc != 0:
        raise RuntimeError(f"FFmpeg exited with {rc}")


if __name__ == "__main__":
    main()
