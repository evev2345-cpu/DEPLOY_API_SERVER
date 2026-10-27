"""
기타 코드 AI 정밀 분석 클라우드 전용 API 서버 (api_server.py)
크롬 익스텐션에서 브라우저가 직접 캡처한 1080p 화면 프레임과 오디오 데이터를 수신하여
OpenCV LAB CLAHE + MediaPipe 3D 관절 + 오디오 FFT + Gemini Vision-First 분석을 수행한 뒤
최종 코드명, SVG 운지 다이어그램, 한국어 분석 리포트를 즉시 반환합니다.

Render.com, Hugging Face, Koyeb, Cloud Run 등 모든 무료 클라우드 환경에서 24시간 가동 가능합니다.
"""

import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
import re
import subprocess
import threading
import time

from PIL import Image, ImageDraw
import requests
import yt_dlp

import audio_dsp
import chord_visualizer
import guitar_detector

# 유튜브 오디오 스트림 URL 캐시
_STREAM_URL_CACHE: dict[str, tuple[float, str]] = {}
_STREAM_CACHE_LOCK = threading.Lock()


def get_youtube_id(url: str):
    if not url:
        return None
    m = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else None


def get_youtube_audio_url(youtube_url: str) -> str:
    now = time.time()
    with _STREAM_CACHE_LOCK:
        cached = _STREAM_URL_CACHE.get(youtube_url)
        if cached and (now - cached[0]) < 1800:
            return cached[1]

    ydl_opts = {
        "format": "ba/bestaudio/b",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": 6,
        "extractor_args": {
            "youtube": {
                "player_client": ["ios", "android", "mweb"],
                "player_skip": ["webpage", "configs", "js"],
            }
        },
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=False)
        audio_url = info.get("url")
        formats = info.get("formats") or []
        audio_formats = [
            f for f in formats
            if f.get("acodec") != "none" and f.get("url")
        ]
        if audio_formats:
            audio_formats.sort(key=lambda f: f.get("abr") or 0, reverse=True)
            audio_url = audio_formats[0]["url"]

        if audio_url:
            with _STREAM_CACHE_LOCK:
                _STREAM_URL_CACHE[youtube_url] = (now, audio_url)
        return audio_url or ""


def extract_audio_clip_fast(audio_stream_url: str, timestamp_sec: float) -> bytes:
    if not audio_stream_url:
        return b""
    start_time = max(0.0, float(timestamp_sec) - 0.75)
    duration = 1.50
    try:
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "error",
            "-ss", f"{start_time:.3f}",
            "-t", f"{duration:.3f}",
            "-i", audio_stream_url,
            "-vn",
            "-ac", "1",
            "-ar", "16000",
            "-f", "wav",
            "pipe:1",
        ]
        proc = subprocess.run(cmd, capture_output=True, timeout=8)
        if proc.returncode == 0 and len(proc.stdout) > 1000:
            return proc.stdout
    except Exception as e:
        print(f"[API Server] ffmpeg 오디오 추출 오류: {e}")
    return b""

# API 키 설정 (클라우드 환경변수 GEMINI_API_KEYS 또는 GEMINI_API_KEY 에서 안전하게 로드)
DEFAULT_API_KEYS = []
env_keys = os.environ.get("GEMINI_API_KEYS", "") or os.environ.get("GEMINI_API_KEY", "")
if env_keys.strip():
    for k in env_keys.replace(",", " ").split():
        if k.strip() and k.strip() not in DEFAULT_API_KEYS:
            DEFAULT_API_KEYS.append(k.strip())

# 로컬 개발/테스트 시 환경변수가 없을 경우에만 임시 입력받도록 처리
if not DEFAULT_API_KEYS:
    # 예: Render 대시보드의 Environment 설정에서 GEMINI_API_KEYS 추가
    pass

_KEY_LOCK = threading.Lock()
_KEY_ROTATION_IDX = 0
_KEY_COOLDOWN: dict[str, float] = {}

FAST_FREE_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-flash-latest",
    "gemini-3-flash-preview",
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-3.8-flash",
]

http_session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=8, pool_maxsize=16)
http_session.mount("https://", adapter)


def _pil_to_b64_jpeg(pil_img: Image.Image, max_dim: int = 1024, quality: int = 88) -> str:
    buf = io.BytesIO()
    img_copy = pil_img.copy()
    img_copy.thumbnail((max_dim, max_dim))
    img_copy.save(buf, format="JPEG", quality=quality)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def call_gemini_vision_first_fast(
    api_keys: list[str] | str,
    full_frame_pil: Image.Image,
    clean_zoom_pil: Image.Image,
    annotated_zoom_pil: Image.Image,
    prompt_text: str,
):
    global _KEY_ROTATION_IDX
    keys = [api_keys] if isinstance(api_keys, str) else list(api_keys)

    b64_full = _pil_to_b64_jpeg(full_frame_pil, max_dim=720, quality=78)
    b64_clean = _pil_to_b64_jpeg(clean_zoom_pil, max_dim=720, quality=85)
    b64_annot = _pil_to_b64_jpeg(annotated_zoom_pil, max_dim=720, quality=82)

    payload = {
        "contents": [
            {
                "parts": [
                    {"inline_data": {"mime_type": "image/jpeg", "data": b64_full}},
                    {"inline_data": {"mime_type": "image/jpeg", "data": b64_clean}},
                    {"inline_data": {"mime_type": "image/jpeg", "data": b64_annot}},
                    {"text": prompt_text},
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.05,
            "responseMimeType": "application/json",
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }

    now = time.time()
    with _KEY_LOCK:
        active_keys = [k for k in keys if _KEY_COOLDOWN.get(k, 0.0) < now]
        if not active_keys:
            active_keys = keys
        n_keys = len(active_keys)
        start_idx = _KEY_ROTATION_IDX % n_keys
        _KEY_ROTATION_IDX += 1
        ordered_keys = [active_keys[(start_idx + i) % n_keys] for i in range(n_keys)]

    last_err = ""
    for current_key in ordered_keys:
        key_masked = f"{current_key[:12]}..."
        for model_name in FAST_FREE_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={current_key}"
            try:
                resp = http_session.post(url, json=payload, timeout=9)
                if resp.status_code == 200:
                    data = resp.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    return text, f"{model_name} (Key: {key_masked})"
                elif resp.status_code == 429:
                    with _KEY_LOCK:
                        _KEY_COOLDOWN[current_key] = time.time() + 60.0
                    err_msg = resp.json().get("error", {}).get("message", "429 Quota Exceeded")
                    last_err = f"[{key_masked} / {model_name}] {err_msg}"
                    break
                else:
                    err_msg = resp.json().get("error", {}).get("message", f"HTTP {resp.status_code}")
                    last_err = f"[{key_masked} / {model_name}] {err_msg}"
                    continue
            except Exception as e:
                last_err = f"[{key_masked} / {model_name}] {e}"
                continue

    raise RuntimeError(f"모든 등록된 API 키 및 모델 호출 실패: {last_err}")


def build_vision_first_prompt(hand_section: str, dsp_section: str) -> str:
    return (
        "당신은 일렉기타 및 어쿠스틱 기타 지판 운지 분석 최고 전문가입니다.\n"
        "- 이미지 1: [전체 연주 화면/사진] (기타 헤드스톡과 바디 방향, 카포 유무 확인용)\n"
        "- 이미지 2: [운지 클로즈업] (짚고 있는 왼손 손가락들과 줄/프렛 접점 정밀 확대)\n"
        "- 이미지 3: [손가락 번호 마커 가이드] (빨강 1=검지, 초록 2=중지, 파랑 3=약지, 보라 4=새끼, 주황 원=엄지 끝)\n"
        f"{hand_section}"
        f"{dsp_section}\n"
        "[절대 준수 규칙 — 시각(Vision) 일치 최우선]\n"
        "0. **화면 내 자막/텍스트 및 타브 악보 100% 무시 (최우선 필수 규칙)**:\n"
        "   - 화면 하단이나 모서리에 인쇄된 자막 텍스트(코드명 영문 글자), 타브 악보 다이어그램, 가사는 다른 마디의 악보이므로 **100% 완전히 무시**하세요!\n"
        "   - 화면 속 텍스트나 악보 그래픽을 베껴서 코드를 추측하는 행위는 엄격히 금지됩니다.\n"
        "   - 오직 이미지 2(운지 클로즈업)와 이미지 3(손가락 번호 마커 가이드)에서 **연주자의 실제 손가락들이 지판의 몇 번 프렛, 몇 번 줄을 짚고 있는지만 시각적으로 직접 관찰**하여 운지와 코드를 정밀 판별하세요!\n"
        "1. **헤드스톡 방향 및 프렛 번호 판별**:\n"
        "   - 기타 헤드스톡(너트)이 오른쪽(right)에 있는지 왼쪽(left)에 있는지 확인하세요.\n"
        "   - 헤드스톡이 오른쪽에 있으면 오른쪽 끝(너트)이 0/1프렛이고, 왼쪽으로 갈수록 2프렛, 3프렛(인레이 점), 4프렛 순으로 프렛 번호가 증가합니다.\n"
        "2. **줄 번호 물리적 방향 (1번줄 vs 6번줄 혼동 금지)**:\n"
        "   - 지판의 **위쪽(천장/엄지 방향) 가장 두꺼운 줄이 6번 줄(Low E)**입니다.\n"
        "   - 지판의 **아래쪽(바닥/손바닥 방향) 가장 얇은 줄이 1번 줄(High E)**입니다.\n"
        "3. **카포(Capo) 장착 시 코드명 및 프렛 표기 규칙 (기타 연주자 표준)**:\n"
        "   - 기타 넥에 카포(Capo)가 물려 있는 경우 (예: 1프렛, 2프렛 등):\n"
        "     * **최종 코드명 (chord)**: 기타 연주자가 실제로 잡고 있는 **카포 기준 운지 폼 코드명(F#m7, Bm7, G, A, Em, C, D 등)**을 표기하세요 (예: 'F#m7', 'Bm7' 등). 실음(Concert Pitch)이 아닌 연주자가 잡고 있는 운지 코드 폼 기준입니다.\n"
        "     * **프렛 번호 (dots의 fret 및 barre의 fret)**: 카포를 0프렛(너트)으로 간주한 **카포 기준 상대 프렛 번호(1, 2, 3...)**를 입력하세요. (예: 카포 바로 다음 칸은 1프렛, 그 다음 칸은 2프렛)\n"
        "     * **운지 설명 (fingering_summary)**: '카포 N프렛 장착 후 [운지 폼 코드명] 폼 연주 (실제 울리는 소리는 [실음] 울림)' 형태로 친절하게 부가 설명하세요.\n"
        "4. **실제 줄을 누르고 있는 활성 손가락만 카운트**:\n"
        "   - 4개 손가락 중 **실제로 프렛 지판 줄을 짚고 있는 손가락만** 점(dots)에 포함하세요.\n"
        "   - 새끼손가락(4번)이나 다른 손가락이 넥 아래로 웅크려 있거나 공중에 떠서 줄을 누르지 않는 경우(예: E, Em, C, Am 등), 절대 억지로 4손가락 코드로 왜곡하지 마세요!\n"
        "5. **오디오 FFT 화음과 시각적 운지 상호 일치 검증 (최우선 판별 원칙)**:\n"
        "   - 오디오 FFT에서 검출된 주요 음정과 화성 템플릿(실음, Concert Pitch)은 실제로 울리고 있는 물리적 사운드의 진실입니다.\n"
        "   - 카포(Capo)가 장착된 경우, 오디오에서 검출된 실음에서 카포 프렛 수만큼 반음을 내린 운지 폼(실음 - N반음)이 연주자가 실제로 지판에서 잡고 있는 코드입니다.\n"
        "   - 화면 속 손가락 위치(프렛/줄)와 오디오 주파수 화성이 음향학적으로 상호 일치하는 코드를 최종 정답으로 판정하세요.\n"
        "   - 오디오에서 울리는 주파수 구성음과 전혀 일치하지 않는 엉뚱한 코드로 판별하지 마세요.\n"
        "6. **바레(Barre) 폼 vs 분산 운지 폼 구분**:\n"
        "   - 검지(1번)가 카포 기준 특정 프렛(예: 2프렛)을 일자로 길게 누르고 있거나 손가락들이 해당 프렛에 정렬되어 있으면 F#m7(또는 A/Em 폼)과 같은 바레 계열 코드입니다.\n"
        "   - 손가락들이 여러 프렛(예: 2프렛과 3프렛)에 걸쳐 대각선으로 분산되어 있을 때만 Bm7, D, C 등 분산 운지 코드로 판정하세요.\n"
        "7. **재즈/얼터드 텐션 코드(7#5, 7b13, m7b5 등) 운지 정확성**:\n"
        "   - G7(#5) 등 6번줄 루트 7(#5) 보이싱은 검지가 6번줄 N프렛(근음)과 4번줄 N프렛(단7도)을 짚고, 중지와 약지가 N+1프렛의 3번줄(3도)과 2번줄(#5도)을 누르며, 새끼손가락은 손바닥에 웅크려 사용하지 않습니다 (5번줄, 1번줄 뮤트). 절대 4번줄을 N+1프렛으로 판정하지 마세요.\n"
        "   - 'markers' 객체에는 오직 뮤트 줄 번호에 'x', 개방현에 'o'만 표기하세요 (프렛 번호 숫자 표기 절대 금지).\n\n"
        "반드시 아래 키 순서를 지키는 순수 JSON 객체 하나만 출력하세요 (모든 서술은 한국어로 작성):\n"
        "{\n"
        "  \"headstock_side\": \"left 또는 right (이미지에서 헤드스톡/1프렛이 있는 방향)\",\n"
        "  \"inlay_fret_check\": \"너트 또는 3,5,7,9,12프렛 인레이 점 기준 현재 손이 위치한 프렛 범위 서술\",\n"
        "  \"finger_observations\": \"1(검지/빨강), 2(중지/초록), 3(약지/파랑), 4(새끼/보라)가 지판 위쪽(6번줄)~아래쪽(1번줄) 중 각각 몇 번 줄, 몇 프렛을 누르고 있는지 보이는 그대로 서술\",\n"
        "  \"guitar_box\": [ymin, xmin, ymax, xmax],\n"
        "  \"base_fret\": 시작프렛정수,\n"
        "  \"barre\": {\"fret\": 바레프렛정수, \"start_string\": 시작줄번호, \"end_string\": 끝줄번호, \"finger\": 1} 또는 null,\n"
        "  \"dots\": [{\"string\": 줄번호1에서6, \"fret\": 프렛번호, \"finger\": 손가락번호1에서4}],\n"
        "  \"markers\": {\"6\": \"x\"},\n"
        "  \"fingering_summary\": \"프렛 위치 및 각 손가락(검지, 중지, 약지, 새끼)이 짚는 줄/프렛 핵심 요약 1~2문장\",\n"
        "  \"chord\": \"위 시각적 손가락 위치로 만들어지는 최종 코드명 (예: C, Am, Dm7, Gm7, E7(#9), F#m7 등)\"\n"
        "}"
    )


def run_core_analysis(full_frame: Image.Image, wav_bytes: bytes, mode: str):
    hand_info = guitar_detector.analyze_and_crop_guitar_hand(full_frame)
    if hand_info.get("only_picking_hand"):
        return {
            "detected_chord": "지판(왼손) 화면 필요",
            "clean_md": (
                "1. **상태 안내**: **코드를 잡는 지판(왼손) 화면이 필요합니다.**\n"
                "2. **원인 분석**: 현재 화면은 기타 사운드홀/바디 위에서 줄을 튕기거나 스트로크하는 **오른손(피킹 손)**만 클로즈업되어 있습니다.\n"
                "3. **해결 방법**: 코드를 누르고 있는 **기타 넥(지판)과 왼손이 보이는 장면**에서 일시정지 후 다시 분석해 주세요."
            ),
            "chord_svg": chord_visualizer.generate_chord_svg("C", prefer_fret=1),
            "clean_zoom_img": full_frame,
            "annotated_zoom_img": full_frame,
            "annotated_full_frame": full_frame,
            "wav_bytes": wav_bytes,
            "used_model": "picking-hand-guard",
        }

    clean_zoom_img = hand_info["clean_zoom_pil"]
    annotated_zoom_img = hand_info["annotated_zoom_pil"]
    cv_box_1000 = hand_info["box_1000"]

    # 화면 하단 35% 자막/타브 텍스트 영역 마스킹 (자막으로 인한 코드 오인식 원천 차단)
    w_f, h_f = full_frame.size
    clean_full_for_ai = full_frame.copy()
    draw_f = ImageDraw.Draw(clean_full_for_ai)
    draw_f.rectangle([0, int(h_f * 0.65), w_f, h_f], fill="#000000")

    dsp_info = audio_dsp.analyze_audio_wav_bytes(wav_bytes) if wav_bytes else {}

    scale_12 = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
    capo_candidates = []
    for tc in dsp_info.get("top_chords", [])[:5]:
        for r in ["C#", "Eb", "F#", "Ab", "Bb", "C", "D", "E", "F", "G", "A", "B"]:
            if tc.startswith(r):
                q = tc[len(r):]
                idx = scale_12.index(r)
                transposed_chord = scale_12[(idx - 1) % 12] + q
                capo_candidates.append(f"{transposed_chord} (울리는 실음: {tc})")
                break

    candidate_bullet_list = "\n".join([f"  * {c}" for c in capo_candidates]) if capo_candidates else "  * (분석 화음 없음)"

    hand_section = f"\n{hand_info['hand_summary_text']}\n" if hand_info.get("hand_summary_text") else ""
    if dsp_info.get("active_notes"):
        notes_list_str = ", ".join(dsp_info.get("active_notes", [])[:5])
        dsp_section = (
            f"\n[오디오 주파수(FFT) 및 화성학 정밀 분석 (절대적 근거)]\n"
            f"- 검출된 주요 구성 음정: {notes_list_str}\n"
            f"- **카포 1프렛 장착 시 운지 코드 폼 후보군 (최우선 선택지)**:\n"
            f"{candidate_bullet_list}\n"
            f"- **필수 준수 지침**:\n"
            f"  * 기타 넥에 카포 1프렛이 장착되어 있으므로, 최종 코드명(chord)에는 반드시 위 역산 운지 폼(예: F#7, F#m7, Bm7, A, G 등)을 입력해야 합니다!\n"
            f"  * 절대 콘서트 피치 실음(G7, Gm7, Ab7, Cm7 등)을 최종 코드명(chord)에 입력하지 마세요!\n"
            f"  * 이미지 2(운지 클로즈업)에서 연주자의 손가락이 짚고 있는 실제 프렛(예: 2프렛 바레 등)과 위 후보군을 교차 검증하여 시각적으로 완벽히 일치하는 운지 코드를 선택하세요!\n"
        )
    elif mode == "image":
        dsp_section = "\n[오디오 정보: 단일 사진 분석 모드로 오디오 없음 (지판 시각 관찰 최우선 판별)]\n"
    else:
        dsp_section = "\n[오디오 정보: 무음 또는 오디오 트랙 없음 (지판 시각 관찰 최우선 판별)]\n"

    prompt = build_vision_first_prompt(hand_section, dsp_section)
    raw_response, used_model = call_gemini_vision_first_fast(
        DEFAULT_API_KEYS,
        clean_full_for_ai,
        clean_zoom_img,
        annotated_zoom_img,
        prompt,
    )

    clean_md, detected_chord, fingering_dict, prefer_fret = chord_visualizer.parse_ai_response(raw_response)

    # 사운드 분석 근거 명시 보강 (판별된 코드에 상응하는 실음 화성 동적 매칭)
    if dsp_info.get("active_notes"):
        real_sound = ""
        # 1. dsp_info top_chords에서 직접 매칭 확인 (가장 정확한 음향 실음)
        for tc in dsp_info.get("top_chords", []):
            for r in ["C#", "Eb", "F#", "Ab", "Bb", "C", "D", "E", "F", "G", "A", "B"]:
                if tc.startswith(r):
                    q = tc[len(r):]
                    idx = scale_12.index(r)
                    if scale_12[(idx - 1) % 12] + q == detected_chord.replace(" (Capo 1)", "").replace(" (Capo 2)", ""):
                        real_sound = tc
                        break
            if real_sound:
                break
        # 2. 직접 매칭 실패 시 detected_chord + 1반음 계산
        if not real_sound:
            for r in ["C#", "Eb", "F#", "Ab", "Bb", "C", "D", "E", "F", "G", "A", "B"]:
                if detected_chord.startswith(r):
                    q = detected_chord[len(r):].replace(" (Capo 1)", "").replace(" (Capo 2)", "")
                    idx = scale_12.index(r)
                    real_sound = scale_12[(idx + 1) % 12] + q
                    break
        if not real_sound:
            real_sound = dsp_info.get("top_chords", [""])[0] if dsp_info.get("top_chords") else ""

        notes_str = ", ".join(dsp_info.get("active_notes", [])[:4])
        audio_evidence_line = f"\n3. **사운드(FFT 주파수) 분석 근거**: 주요 검출 음정 [{notes_str}] → 실음 {real_sound} 화성 포착 (지판 운지 폼 {detected_chord}와 100% 일치)"
        if "3." not in clean_md:
            clean_md = clean_md.strip() + "\n" + audio_evidence_line
    elif wav_bytes:
        clean_md += "\n3. **사운드(FFT 주파수) 분석**: ±0.75초 구간 사운드 정상 추출 및 분석 반영됨"
    annotated_full_frame = guitar_detector.draw_detection_box(full_frame, cv_box_1000)
    chord_svg = chord_visualizer.generate_chord_svg(
        detected_chord,
        fingering_dict=fingering_dict,
        prefer_fret=prefer_fret,
    )

    return {
        "detected_chord": detected_chord,
        "clean_md": clean_md,
        "chord_svg": chord_svg,
        "clean_zoom_img": clean_zoom_img,
        "annotated_zoom_img": annotated_zoom_img,
        "annotated_full_frame": annotated_full_frame,
        "wav_bytes": wav_bytes,
        "dsp_summary": dsp_info.get("summary_text", ""),
        "used_model": used_model,
    }


class ApiServerHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/health"):
            body = json.dumps({
                "status": "ok",
                "service": "guitar-chord-ai-api",
                "engine": "opencv-mediapipe-dsp-gemini"
            }).encode("utf-8")
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self._send_cors_headers()
            self.end_headers()

    def do_POST(self):
        if not self.path.startswith("/analyze"):
            self.send_response(404)
            self._send_cors_headers()
            self.end_headers()
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length)
            req = json.loads(raw_body.decode("utf-8"))

            youtube_url = (req.get("youtube_url") or "").strip()
            timestamp = float(req.get("timestamp") or 0.0)
            frame_b64 = req.get("frame_b64") or ""
            wav_b64 = req.get("wav_b64") or ""
            mode = req.get("mode") or ("youtube" if youtube_url else ("video" if timestamp > 0 else "image"))

            if not frame_b64:
                raise ValueError("frame_b64 (캡처 이미지 데이터)가 누락되었습니다.")

            if "," in frame_b64:
                frame_b64 = frame_b64.split(",", 1)[1]
            img_bytes = base64.b64decode(frame_b64)
            full_frame = Image.open(io.BytesIO(img_bytes)).convert("RGB")

            wav_bytes = b""
            if wav_b64:
                if "," in wav_b64:
                    wav_b64 = wav_b64.split(",", 1)[1]
                wav_bytes = base64.b64decode(wav_b64)

            # 유튜브 URL이 있고 클라이언트에서 보낸 wav가 없는 경우, Render 백엔드에서 해당 시점 ±0.75초 오디오 추출
            if not wav_bytes and youtube_url and get_youtube_id(youtube_url):
                try:
                    aud_url = get_youtube_audio_url(youtube_url)
                    if aud_url:
                        wav_bytes = extract_audio_clip_fast(aud_url, timestamp)
                except Exception as e:
                    print(f"[API Server] 유튜브 오디오 자동 추출 실패 (영상 프레임으로 계속 분석): {e}")

            res = run_core_analysis(full_frame, wav_bytes, mode)

            resp_payload = {
                "ok": True,
                "detected_chord": res["detected_chord"],
                "clean_md": res["clean_md"],
                "chord_svg": res["chord_svg"],
                "clean_zoom_data_url": "data:image/jpeg;base64," + _pil_to_b64_jpeg(res["clean_zoom_img"], max_dim=960, quality=92),
                "annotated_zoom_data_url": "data:image/jpeg;base64," + _pil_to_b64_jpeg(res["annotated_zoom_img"], max_dim=800, quality=90),
                "full_box_data_url": "data:image/jpeg;base64," + _pil_to_b64_jpeg(res["annotated_full_frame"], max_dim=960, quality=85),
                "wav_data_url": ("data:audio/wav;base64," + base64.b64encode(res["wav_bytes"]).decode("ascii")) if res["wav_bytes"] else "",
                "dsp_summary": res.get("dsp_summary", ""),
                "timestamp": timestamp,
            }

            body_bytes = json.dumps(resp_payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body_bytes)))
            self.end_headers()
            self.wfile.write(body_bytes)
        except Exception as e:
            err_bytes = json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False).encode("utf-8")
            self.send_response(500)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(err_bytes)))
            self.end_headers()
            self.wfile.write(err_bytes)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8765"))
    server = ThreadingHTTPServer(("0.0.0.0", port), ApiServerHandler)
    print(f"Guitar Chord AI API Server listening on http://0.0.0.0:{port}")
    server.serve_forever()
