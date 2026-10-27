"""
기타 코드 지판 다이어그램 SVG 생성기 (Vision-First 구조화 데이터 & 전 코드 보이싱 지원)
사용자가 제공한 참고 이미지(가로 6줄, 세로 프렛, 손가락 번호 원 ①~④, 바레 캡슐 박스, 프렛 번호) 스타일을 재현합니다.
"""

import json
import re

NOTE_TO_SEMITONE = {
    'C': 0, 'B#': 0,
    'C#': 1, 'DB': 1,
    'D': 2,
    'D#': 3, 'EB': 3,
    'E': 4, 'FB': 4,
    'F': 5, 'E#': 5,
    'F#': 6, 'GB': 6,
    'G': 7,
    'G#': 8, 'AB': 8,
    'A': 9,
    'A#': 10, 'BB': 10,
    'B': 11, 'CB': 11,
}

SEMITONE_TO_NOTE = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'Bb', 'B']

TUNING = {6: 4, 5: 9, 4: 2, 3: 7, 2: 11, 1: 4}

CHORD_INTERVALS = {
    '': [0, 4, 7], 'maj': [0, 4, 7], 'major': [0, 4, 7],
    'm': [0, 3, 7], 'min': [0, 3, 7], 'minor': [0, 3, 7], '-': [0, 3, 7],
    '7': [0, 4, 7, 10], 'dom7': [0, 4, 7, 10],
    'maj7': [0, 4, 7, 11], 'm7': [0, 3, 7, 10], 'min7': [0, 3, 7, 10], '-7': [0, 3, 7, 10],
    'mmaj7': [0, 3, 7, 11],
    'dim': [0, 3, 6], 'dim7': [0, 3, 6, 9], 'm7b5': [0, 3, 6, 10], 'm7(b5)': [0, 3, 6, 10],
    'aug': [0, 4, 8], 'aug7': [0, 4, 8, 10], '7aug': [0, 4, 8, 10], '7#5': [0, 4, 8, 10], '7(#5)': [0, 4, 8, 10], '+7': [0, 4, 8, 10],
    'sus4': [0, 5, 7], 'sus2': [0, 2, 7], '7sus4': [0, 5, 7, 10],
    '6': [0, 4, 7, 9], 'm6': [0, 3, 7, 9], 'add9': [0, 2, 4, 7], '9': [0, 2, 4, 7, 10],
    'maj9': [0, 2, 4, 7, 11], 'm9': [0, 2, 3, 7, 10], '7b9': [0, 1, 4, 7, 10], '7#9': [0, 3, 4, 7, 10],
    '11': [0, 2, 4, 5, 7, 10], '13': [0, 2, 4, 7, 9, 10]
}

OPEN_CHORD_DB = {
    'MUTE': {
        'base_fret': 1,
        'dots': [],
        'markers': {1: 'x', 2: 'x', 3: 'x', 4: 'x', 5: 'x', 6: 'x'}
    },
    'C': {
        'base_fret': 1,
        'dots': [
            {'string': 2, 'fret': 1, 'finger': 1},
            {'string': 4, 'fret': 2, 'finger': 2},
            {'string': 5, 'fret': 3, 'finger': 3},
        ],
        'markers': {6: 'x'}
    },
    'C7': {
        'base_fret': 1,
        'dots': [
            {'string': 2, 'fret': 1, 'finger': 1},
            {'string': 4, 'fret': 2, 'finger': 2},
            {'string': 5, 'fret': 3, 'finger': 3},
            {'string': 3, 'fret': 3, 'finger': 4},
        ],
        'markers': {6: 'x'}
    },
    'CMAJ7': {
        'base_fret': 1,
        'dots': [
            {'string': 4, 'fret': 2, 'finger': 2},
            {'string': 5, 'fret': 3, 'finger': 3},
        ],
        'markers': {6: 'x'}
    },
    'D': {
        'base_fret': 1,
        'dots': [
            {'string': 3, 'fret': 2, 'finger': 1},
            {'string': 1, 'fret': 2, 'finger': 2},
            {'string': 2, 'fret': 3, 'finger': 3},
        ],
        'markers': {6: 'x', 5: 'x'}
    },
    'DM': {
        'base_fret': 1,
        'dots': [
            {'string': 1, 'fret': 1, 'finger': 1},
            {'string': 3, 'fret': 2, 'finger': 2},
            {'string': 2, 'fret': 3, 'finger': 4},
        ],
        'markers': {6: 'x', 5: 'x'}
    },
    'D7': {
        'base_fret': 1,
        'dots': [
            {'string': 2, 'fret': 1, 'finger': 1},
            {'string': 3, 'fret': 2, 'finger': 2},
            {'string': 1, 'fret': 2, 'finger': 3},
        ],
        'markers': {6: 'x', 5: 'x'}
    },
    'DM7': {
        'base_fret': 1,
        'barre': {'fret': 1, 'start_string': 1, 'end_string': 2, 'finger': 1},
        'dots': [
            {'string': 3, 'fret': 2, 'finger': 2},
        ],
        'markers': {6: 'x', 5: 'x'}
    },
    'E': {
        'base_fret': 1,
        'dots': [
            {'string': 3, 'fret': 1, 'finger': 1},
            {'string': 5, 'fret': 2, 'finger': 2},
            {'string': 4, 'fret': 2, 'finger': 3},
        ],
        'markers': {}
    },
    'EM': {
        'base_fret': 1,
        'dots': [
            {'string': 5, 'fret': 2, 'finger': 2},
            {'string': 4, 'fret': 2, 'finger': 3},
        ],
        'markers': {}
    },
    'E7': {
        'base_fret': 1,
        'dots': [
            {'string': 3, 'fret': 1, 'finger': 1},
            {'string': 5, 'fret': 2, 'finger': 2},
        ],
        'markers': {}
    },
    'EM7': {
        'base_fret': 1,
        'dots': [
            {'string': 5, 'fret': 2, 'finger': 2},
        ],
        'markers': {}
    },
    'G': {
        'base_fret': 1,
        'dots': [
            {'string': 5, 'fret': 2, 'finger': 2},
            {'string': 6, 'fret': 3, 'finger': 3},
            {'string': 1, 'fret': 3, 'finger': 4},
        ],
        'markers': {}
    },
    'G7': {
        'base_fret': 1,
        'dots': [
            {'string': 1, 'fret': 1, 'finger': 1},
            {'string': 5, 'fret': 2, 'finger': 2},
            {'string': 6, 'fret': 3, 'finger': 3},
        ],
        'markers': {}
    },
    'A': {
        'base_fret': 1,
        'dots': [
            {'string': 4, 'fret': 2, 'finger': 2},
            {'string': 3, 'fret': 2, 'finger': 3},
            {'string': 2, 'fret': 2, 'finger': 4},
        ],
        'markers': {6: 'x'}
    },
    'AM': {
        'base_fret': 1,
        'dots': [
            {'string': 2, 'fret': 1, 'finger': 1},
            {'string': 4, 'fret': 2, 'finger': 2},
            {'string': 3, 'fret': 2, 'finger': 3},
        ],
        'markers': {6: 'x'}
    },
    'A7': {
        'base_fret': 1,
        'dots': [
            {'string': 4, 'fret': 2, 'finger': 2},
            {'string': 2, 'fret': 2, 'finger': 3},
        ],
        'markers': {6: 'x'}
    },
    'AM7': {
        'base_fret': 1,
        'dots': [
            {'string': 2, 'fret': 1, 'finger': 1},
            {'string': 4, 'fret': 2, 'finger': 2},
        ],
        'markers': {6: 'x'}
    },
    'B7': {
        'base_fret': 1,
        'dots': [
            {'string': 4, 'fret': 1, 'finger': 1},
            {'string': 5, 'fret': 2, 'finger': 2},
            {'string': 3, 'fret': 2, 'finger': 3},
            {'string': 1, 'fret': 2, 'finger': 4},
        ],
        'markers': {6: 'x'}
    },
}


def build_movable_voicing(root_semi, quality, prefer_high_fret=None):
    fret_6 = (root_semi - 4) % 12
    if fret_6 == 0:
        fret_6 = 12
    fret_5 = (root_semi - 9) % 12
    if fret_5 == 0:
        fret_5 = 12

    q = quality.lower().strip()

    if q in ['9', 'm9', 'maj9', '7b9', '7(b9)', '7#9', '7(#9)']:
        r_fret = fret_5
        if prefer_high_fret and abs(fret_5 + 12 - prefer_high_fret) < abs(fret_5 - prefer_high_fret):
            r_fret = fret_5 + 12
        base = max(1, r_fret - 1)
        if q == 'm9':
            return {
                'base_fret': base,
                'dots': [
                    {'string': 4, 'fret': r_fret - 1, 'finger': 1},
                    {'string': 5, 'fret': r_fret, 'finger': 2},
                    {'string': 3, 'fret': r_fret, 'finger': 3},
                    {'string': 2, 'fret': r_fret, 'finger': 4},
                ],
                'markers': {6: 'x', 1: 'x'}
            }
        elif q in ['7b9', '7(b9)']:
            return {
                'base_fret': base,
                'dots': [
                    {'string': 4, 'fret': r_fret - 1, 'finger': 1},
                    {'string': 2, 'fret': r_fret - 1, 'finger': 1},
                    {'string': 5, 'fret': r_fret, 'finger': 2},
                    {'string': 3, 'fret': r_fret, 'finger': 3},
                ],
                'markers': {6: 'x', 1: 'x'}
            }
        elif q in ['7#9', '7(#9)']:
            return {
                'base_fret': base,
                'dots': [
                    {'string': 4, 'fret': r_fret - 1, 'finger': 1},
                    {'string': 5, 'fret': r_fret, 'finger': 2},
                    {'string': 3, 'fret': r_fret, 'finger': 3},
                    {'string': 2, 'fret': r_fret + 1, 'finger': 4},
                ],
                'markers': {6: 'x', 1: 'x'}
            }
        else:
            return {
                'base_fret': base,
                'barre': {'fret': r_fret, 'start_string': 1, 'end_string': 3, 'finger': 3},
                'dots': [
                    {'string': 4, 'fret': r_fret - 1, 'finger': 1},
                    {'string': 5, 'fret': r_fret, 'finger': 2},
                ],
                'markers': {6: 'x'}
            }

    use_5th_string = False
    if prefer_high_fret is not None:
        dist_6 = min(abs(fret_6 - prefer_high_fret), abs((fret_6 % 12) - prefer_high_fret))
        dist_5 = min(abs(fret_5 - prefer_high_fret), abs((fret_5 % 12) - prefer_high_fret))
        use_5th_string = dist_5 < dist_6
    else:
        if fret_5 <= 7 and fret_6 > 7:
            use_5th_string = True

    if q in ['7#5', '7(#5)', '7aug', 'aug7', '+7', '7b13', '7(b13)', 'aug']:
        if use_5th_string:
            bf = fret_5
            return {
                'base_fret': max(1, bf - 1),
                'dots': [
                    {'string': 5, 'fret': bf, 'finger': 1},
                    {'string': 4, 'fret': bf + 2, 'finger': 3},
                    {'string': 3, 'fret': bf + 1, 'finger': 2},
                    {'string': 2, 'fret': bf + 2, 'finger': 4},
                ],
                'markers': {6: 'x', 1: 'x'}
            }
        else:
            bf = fret_6
            return {
                'base_fret': bf,
                'dots': [
                    {'string': 6, 'fret': bf, 'finger': 1},
                    {'string': 4, 'fret': bf, 'finger': 1},
                    {'string': 3, 'fret': bf + 1, 'finger': 2},
                    {'string': 2, 'fret': bf + 1, 'finger': 3},
                ],
                'markers': {5: 'x', 1: 'x'}
            }

    if q in ['m7b5', 'm7(b5)', 'half-dim', 'ø', 'ø7', 'm7-5', 'm7(-5)']:
        if use_5th_string:
            bf = fret_5
            return {
                'base_fret': max(1, bf - 1),
                'dots': [
                    {'string': 5, 'fret': bf, 'finger': 1},
                    {'string': 4, 'fret': bf + 1, 'finger': 3},
                    {'string': 3, 'fret': bf, 'finger': 2},
                    {'string': 2, 'fret': bf + 1, 'finger': 4},
                ],
                'markers': {6: 'x', 1: 'x'}
            }
        else:
            bf = fret_6
            return {
                'base_fret': max(1, bf - 1),
                'dots': [
                    {'string': 6, 'fret': bf, 'finger': 1},
                    {'string': 4, 'fret': bf, 'finger': 2},
                    {'string': 3, 'fret': bf, 'finger': 3},
                    {'string': 2, 'fret': bf - 1, 'finger': 1},
                ],
                'markers': {5: 'x', 1: 'x'}
            }

    if q in ['dim7', 'dim', '°7', '°']:
        bf = fret_5
        return {
            'base_fret': max(1, bf - 1),
            'dots': [
                {'string': 5, 'fret': bf, 'finger': 1},
                {'string': 4, 'fret': bf + 1, 'finger': 3},
                {'string': 3, 'fret': bf - 1, 'finger': 2},
                {'string': 2, 'fret': bf + 1, 'finger': 4},
            ],
            'markers': {6: 'x', 1: 'x'}
        }

    if use_5th_string:
        bf = fret_5
        if q in ['m', 'min', 'minor', '-']:
            return {
                'base_fret': bf,
                'barre': {'fret': bf, 'start_string': 1, 'end_string': 5, 'finger': 1},
                'dots': [
                    {'string': 2, 'fret': bf + 1, 'finger': 2},
                    {'string': 4, 'fret': bf + 2, 'finger': 3},
                    {'string': 3, 'fret': bf + 2, 'finger': 4},
                ],
                'markers': {6: 'x'}
            }
        elif q in ['m7', 'min7', '-7']:
            return {
                'base_fret': bf,
                'barre': {'fret': bf, 'start_string': 1, 'end_string': 5, 'finger': 1},
                'dots': [
                    {'string': 2, 'fret': bf + 1, 'finger': 2},
                    {'string': 4, 'fret': bf + 2, 'finger': 3},
                ],
                'markers': {6: 'x'}
            }
        elif q in ['7', 'dom7']:
            return {
                'base_fret': bf,
                'barre': {'fret': bf, 'start_string': 1, 'end_string': 5, 'finger': 1},
                'dots': [
                    {'string': 4, 'fret': bf + 2, 'finger': 3},
                    {'string': 2, 'fret': bf + 2, 'finger': 4},
                ],
                'markers': {6: 'x'}
            }
        elif q in ['maj7', 'm7+', 'Δ7']:
            return {
                'base_fret': bf,
                'barre': {'fret': bf, 'start_string': 1, 'end_string': 5, 'finger': 1},
                'dots': [
                    {'string': 3, 'fret': bf + 1, 'finger': 2},
                    {'string': 4, 'fret': bf + 2, 'finger': 3},
                    {'string': 2, 'fret': bf + 2, 'finger': 4},
                ],
                'markers': {6: 'x'}
            }
        else:
            return {
                'base_fret': bf,
                'barre': {'fret': bf, 'start_string': 1, 'end_string': 5, 'finger': 1},
                'dots': [
                    {'string': 4, 'fret': bf + 2, 'finger': 2},
                    {'string': 3, 'fret': bf + 2, 'finger': 3},
                    {'string': 2, 'fret': bf + 2, 'finger': 4},
                ],
                'markers': {6: 'x'}
            }
    else:
        bf = fret_6
        if q in ['m', 'min', 'minor', '-']:
            return {
                'base_fret': bf,
                'barre': {'fret': bf, 'start_string': 1, 'end_string': 6, 'finger': 1},
                'dots': [
                    {'string': 5, 'fret': bf + 2, 'finger': 3},
                    {'string': 4, 'fret': bf + 2, 'finger': 4},
                ],
                'markers': {}
            }
        elif q in ['m7', 'min7', '-7']:
            return {
                'base_fret': bf,
                'barre': {'fret': bf, 'start_string': 1, 'end_string': 6, 'finger': 1},
                'dots': [
                    {'string': 5, 'fret': bf + 2, 'finger': 3},
                ],
                'markers': {}
            }
        elif q in ['7', 'dom7']:
            return {
                'base_fret': bf,
                'barre': {'fret': bf, 'start_string': 1, 'end_string': 6, 'finger': 1},
                'dots': [
                    {'string': 3, 'fret': bf + 1, 'finger': 2},
                    {'string': 5, 'fret': bf + 2, 'finger': 3},
                ],
                'markers': {}
            }
        elif q in ['maj7', 'Δ7']:
            return {
                'base_fret': bf,
                'dots': [
                    {'string': 6, 'fret': bf, 'finger': 1},
                    {'string': 4, 'fret': bf + 1, 'finger': 3},
                    {'string': 3, 'fret': bf + 1, 'finger': 4},
                    {'string': 2, 'fret': bf, 'finger': 2},
                ],
                'markers': {5: 'x', 1: 'x'}
            }
        else:
            return {
                'base_fret': bf,
                'barre': {'fret': bf, 'start_string': 1, 'end_string': 6, 'finger': 1},
                'dots': [
                    {'string': 3, 'fret': bf + 1, 'finger': 2},
                    {'string': 5, 'fret': bf + 2, 'finger': 3},
                    {'string': 4, 'fret': bf + 2, 'finger': 4},
                ],
                'markers': {}
            }


def resolve_chord_data(chord_name, prefer_fret=None):
    clean = str(chord_name or "C").strip()
    for p in ["**", "정확한 코드명:", "추정 코드명:", "코드명:", "코드:"]:
        clean = clean.replace(p, "").strip()
    if clean in ['-', 'NONE', '', '미상', '알 수 없음']:
        return {'base_fret': 1, 'barre': None, 'dots': [], 'markers': {}, 'chord': '-'}
    clean_main = clean.split("/")[0].split()[0].strip() if clean else "C"
    upper_key = clean.upper().replace(" MAJOR", "").strip()

    if (prefer_fret is None or prefer_fret <= 3) and upper_key in OPEN_CHORD_DB:
        return OPEN_CHORD_DB[upper_key]

    if 'MUTE' in upper_key or '뮤트' in clean:
        base_match = re.match(r'^([A-G][#b♯♭]?[^\s\(]*)', clean, re.IGNORECASE)
        if base_match:
            base_chord = base_match.group(1).strip()
            return resolve_chord_data(base_chord, prefer_fret=prefer_fret)
        return OPEN_CHORD_DB['MUTE']

    m = re.match(r'^([A-G][#b♯♭]?)(.*)$', clean_main, re.IGNORECASE)
    if not m:
        return OPEN_CHORD_DB.get('C')

    root_str = m.group(1).upper().replace('♯', '#').replace('♭', 'B')
    quality_str = m.group(2).strip()
    if quality_str.lower() in ['major', 'maj']:
        quality_str = ''

    root_semi = NOTE_TO_SEMITONE.get(root_str, 0)
    return build_movable_voicing(root_semi, quality_str, prefer_high_fret=prefer_fret)


def _safe_int(val, default=1):
    try:
        return int(val)
    except Exception:
        return default


def _format_finger(f_val):
    s = str(f_val or '1').strip().upper()
    if s in ['T', 'THUMB']:
        return 'T'
    if s in ['1', '2', '3', '4']:
        return s
    return '1'


def detect_lowest_sounding_string(dots, barre, markers):
    """
    기타의 6번줄(최저음)부터 1번줄(최고음)까지 검사하여
    뮤트('x')되지 않고 실제로 울리는 가장 낮은 줄 번호, 프렛 번호, 음계(Pitch Class)를 반환합니다.
    """
    markers = markers or {}
    dots = dots or []
    for s in [6, 5, 4, 3, 2, 1]:
        m = markers.get(s) or markers.get(str(s))
        if str(m).lower() in ['x', 'mute']:
            continue

        fret = None
        for d in dots:
            if isinstance(d, dict) and _safe_int(d.get('string')) == s:
                fret = _safe_int(d.get('fret'))
                break

        if fret is None and isinstance(barre, dict) and _safe_int(barre.get('fret'), 0) > 0:
            b_start = min(_safe_int(barre.get('start_string', 1)), _safe_int(barre.get('end_string', 6)))
            b_end = max(_safe_int(barre.get('start_string', 1)), _safe_int(barre.get('end_string', 6)))
            if b_start <= s <= b_end:
                fret = _safe_int(barre.get('fret'))

        if fret is None and str(m).lower() in ['o', 'open', '0']:
            fret = 0

        if fret is not None:
            pitch = (TUNING[s] + fret) % 12
            return s, fret, pitch
    return None, None, None


def reconcile_fret_with_audio(chord_name: str, fingering_dict: dict, dsp_info: dict, capo: int = 1) -> tuple:
    """
    비전 AI가 프렛을 1~2칸 밀려 세어 잘못된 코드를 반환했을 때 (예: 4프렛 C#m7을 2프렛 Bm7으로 오인),
    오디오 FFT 실음(Concert Pitch)과 카포 오프셋을 역산하여 진정한 지판 코드와 프렛 번호로 자동 보정합니다.
    """
    if not isinstance(fingering_dict, dict) or not dsp_info or not isinstance(dsp_info, dict):
        return chord_name, fingering_dict

    clean_name = re.sub(r'\(.*?\)', '', str(chord_name or '')).strip()
    m = re.match(r'^([A-G][#b♯♭]?)(.*)$', clean_name)
    if not m:
        return chord_name, fingering_dict

    v_root = m.group(1).upper().replace('♯', '#').replace('♭', 'B')
    v_qual = m.group(2).strip().lower()
    v_semi = NOTE_TO_SEMITONE.get(v_root, -1)
    if v_semi < 0:
        return chord_name, fingering_dict

    top_audio = dsp_info.get('top_chords', [])
    for tc in top_audio[:3]:
        am = re.match(r'^([A-G][#b♯♭]?)(.*)$', tc)
        if not am:
            continue
        a_root = am.group(1).upper().replace('♯', '#').replace('♭', 'B')
        a_qual = am.group(2).strip().lower()
        a_semi = NOTE_TO_SEMITONE.get(a_root, -1)
        if a_semi < 0:
            continue

        fretboard_semi = (a_semi - capo) % 12
        fretboard_root = SEMITONE_TO_NOTE[fretboard_semi]

        # 1-A. 1-현 수직 전이 함정 교정 (A-shape vs E-shape 2D 기하학적 착시)
        # 예: 4프렛 C#m7(A형 m7) vs 4프렛 G#7(E형 dom7)은 2D상 동일한 핑거링 간격
        # 5번줄 루트(C#=1)와 6번줄 루트(G#=8)는 (1 - 8) % 12 == 5 (완전4도 / 1-현 간격)
        barre_fret = _safe_int(fingering_dict.get('barre', {}).get('fret') if isinstance(fingering_dict.get('barre'), dict) else fingering_dict.get('base_fret'), 0)
        if barre_fret > 0:
            if (v_semi - fretboard_semi) % 12 == 5:
                target_qual = a_qual if a_qual else ('7' if '7' in v_qual else '')
                new_chord = f"{fretboard_root}{target_qual}"
                fingering_dict['chord'] = new_chord
                if isinstance(fingering_dict.get('dots'), list):
                    for d in fingering_dict['dots']:
                        if isinstance(d, dict) and 'string' in d:
                            d['string'] = min(6, _safe_int(d['string']) + 1)
                if isinstance(fingering_dict.get('barre'), dict) and fingering_dict['barre'].get('fret'):
                    fingering_dict['barre']['start_string'] = 1
                    fingering_dict['barre']['end_string'] = 6
                if isinstance(fingering_dict.get('markers'), dict):
                    fingering_dict['markers'].pop(6, None)
                fingering_dict['reconciliation_note'] = (
                    f"오디오 실음 화성({tc}) 및 기저 주파수를 분석하여, 5번줄 루트 폼({chord_name})의 1-현 시각 착시를 "
                    f"6번줄 루트의 E형 [{new_chord}] 폼으로 자동 교정했습니다."
                )
                return new_chord, fingering_dict

            if (fretboard_semi - v_semi) % 12 == 5:
                target_qual = a_qual if a_qual else ('m7' if '7' in v_qual else 'm')
                new_chord = f"{fretboard_root}{target_qual}"
                fingering_dict['chord'] = new_chord
                if isinstance(fingering_dict.get('dots'), list):
                    for d in fingering_dict['dots']:
                        if isinstance(d, dict) and 'string' in d:
                            d['string'] = max(1, _safe_int(d['string']) - 1)
                if isinstance(fingering_dict.get('barre'), dict) and fingering_dict['barre'].get('fret'):
                    fingering_dict['barre']['start_string'] = 1
                    fingering_dict['barre']['end_string'] = 5
                if not isinstance(fingering_dict.get('markers'), dict):
                    fingering_dict['markers'] = {}
                fingering_dict['markers'][6] = 'x'
                fingering_dict['reconciliation_note'] = (
                    f"오디오 실음 화성({tc})을 분석하여 6번줄 루트 폼({chord_name})의 1-현 시각 착시를 "
                    f"5번줄 루트의 A형 [{new_chord}] 폼으로 자동 교정했습니다."
                )
                return new_chord, fingering_dict

        # 1-B. 화성 퀄리티(Quality: Major vs Minor vs 7th) 불일치 교정
        # 같은 프렛/루트인데 비전 AI가 F#m7처럼 메이저/마이너를 잘못 라벨링한 경우
        if fretboard_semi == v_semi and v_qual != a_qual:
            dots = fingering_dict.get('dots') or []
            barre = fingering_dict.get('barre') or {}
            bfret = _safe_int(barre.get('fret'), 0) if isinstance(barre, dict) else 0

            # E형 바레 폼인 경우 (6번줄 루트)
            if bfret > 0 and (TUNING[6] + bfret) % 12 == fretboard_semi:
                # 3번줄에 (bfret + 1) 프렛 운지가 있는지 확인 -> 장3도 (Major 3rd)
                has_major_3rd = any(
                    _safe_int(d.get('string')) == 3 and _safe_int(d.get('fret')) == bfret + 1
                    for d in dots if isinstance(d, dict)
                )

                # 오디오가 Major를 가리키거나 지판에 장3도가 확실히 찍혀있는 경우
                if (a_qual in ['', 'maj', 'major', 'add9', 'maj7', '5'] or has_major_3rd) and has_major_3rd:
                    new_chord = fretboard_root
                    fingering_dict['chord'] = new_chord
                    fingering_dict['reconciliation_note'] = (
                        f"지판 3번줄 {bfret + 1}프렛(장3도 음정) 운지 및 오디오 실음({tc}) 분석을 통해, "
                        f"비전 모델의 오판[{chord_name}]을 정규 메이저 [{new_chord}] 코드로 자동 교정했습니다."
                    )
                    return new_chord, fingering_dict

                # 오디오가 Minor/m7을 가리키고 3번줄 장3도가 없는 경우
                if a_qual in ['m', 'min', 'minor', 'm7', 'min7'] and not has_major_3rd:
                    target_q = 'm7' if '7' in (v_qual + a_qual) else 'm'
                    new_chord = f"{fretboard_root}{target_q}"
                    fingering_dict['chord'] = new_chord
                    fingering_dict['reconciliation_note'] = (
                        f"지판 단3도 바레 음정 및 오디오 실음({tc}) 분석을 통해 [{new_chord}] 코드로 자동 교정했습니다."
                    )
                    return new_chord, fingering_dict

            # A형 바레 폼인 경우 (5번줄 루트)
            if bfret > 0 and (TUNING[5] + bfret) % 12 == fretboard_semi:
                # 2번줄에 (bfret + 1) 프렛 운지가 있는지 확인 -> 단3도 (Minor 3rd)
                has_minor_3rd = any(
                    _safe_int(d.get('string')) == 2 and _safe_int(d.get('fret')) == bfret + 1
                    for d in dots if isinstance(d, dict)
                )
                if (a_qual in ['m', 'min', 'minor', 'm7'] or has_minor_3rd) and has_minor_3rd:
                    target_q = 'm7' if '7' in (v_qual + a_qual) else 'm'
                    new_chord = f"{fretboard_root}{target_q}"
                    fingering_dict['chord'] = new_chord
                    fingering_dict['reconciliation_note'] = (
                        f"지판 2번줄 {bfret + 1}프렛(단3도 음정) 운지 및 오디오 실음({tc})을 바탕으로 [{new_chord}] 코드로 자동 교정했습니다."
                    )
                    return new_chord, fingering_dict

        # 화성 퀄리티 상호 호환성 검증 (m7, minor, major 등)
        qual_compat = (
            (v_qual == a_qual) or
            ('m7' in v_qual and 'm7' in a_qual) or
            ('m' in v_qual and 'm' in a_qual) or
            (v_qual in ['', 'maj', 'major'] and a_qual in ['', 'maj', 'major'])
        )

        if qual_compat and fretboard_semi != v_semi:
            diff = (fretboard_semi - v_semi) % 12
            if diff > 6:
                diff -= 12
            if abs(diff) in [1, 2, 3]:
                # 1~3프렛 범위의 시각적 프렛 계수 오차 교정
                new_chord = f"{fretboard_root}{m.group(2).strip()}"
                fingering_dict['chord'] = new_chord
                if 'base_fret' in fingering_dict and fingering_dict['base_fret']:
                    fingering_dict['base_fret'] = max(1, _safe_int(fingering_dict['base_fret']) + diff)
                if isinstance(fingering_dict.get('barre'), dict) and fingering_dict['barre'].get('fret'):
                    fingering_dict['barre']['fret'] = max(1, _safe_int(fingering_dict['barre']['fret']) + diff)
                if isinstance(fingering_dict.get('dots'), list):
                    for d in fingering_dict['dots']:
                        if isinstance(d, dict) and 'fret' in d:
                            d['fret'] = max(1, _safe_int(d['fret']) + diff)
                fingering_dict['reconciliation_note'] = (
                    f"오디오 실음 화성({tc}) 및 카포 {capo}프렛 오프셋을 역산하여, "
                    f"비전 모델의 {diff}프렛 위치 오차를 [{new_chord}]로 자동 보정했습니다."
                )
                return new_chord, fingering_dict

    return chord_name, fingering_dict


def get_sounding_pitches(fingering_dict: dict) -> tuple:
    """
    운지 딕셔너리(barre, dots, markers)에서 실제 소리 나는 음정(0~11)과 현별 음정명을 계산합니다.
    물리적 원리에 따라 바레 위에 놓인 개별 손가락 프렛이 우선 진동합니다.
    반환값: (sounding_pitches_set, string_to_note_dict)
    """
    sounding_pitches = set()
    string_notes = {}
    if not isinstance(fingering_dict, dict):
        return sounding_pitches, string_notes

    barre = fingering_dict.get("barre")
    dots = fingering_dict.get("dots") or []
    markers = fingering_dict.get("markers") or {}

    string_frets = {}

    # 1. 바레가 적용되는 줄 기본 프렛 설정
    if isinstance(barre, dict) and _safe_int(barre.get("fret"), 0) > 0:
        bfret = _safe_int(barre["fret"])
        b_start = min(_safe_int(barre.get("start_string"), 1), _safe_int(barre.get("end_string"), 6))
        b_end = max(_safe_int(barre.get("start_string"), 1), _safe_int(barre.get("end_string"), 6))
        for s in range(b_start, b_end + 1):
            if str(markers.get(s)).lower() not in ['x', 'mute']:
                string_frets[s] = bfret

    # 2. 개별 운지 점(dots)이 바레를 덮어씀 (물리적으로 더 높은 프렛이 진동)
    for d in dots:
        if isinstance(d, dict):
            s = _safe_int(d.get("string"))
            f = _safe_int(d.get("fret"))
            if 1 <= s <= 6 and f > 0:
                if str(markers.get(s)).lower() not in ['x', 'mute']:
                    string_frets[s] = f

    # 3. 개방현 설정 (바레나 운지 점이 없는 줄)
    for s, m in markers.items():
        s_int = _safe_int(s)
        if 1 <= s_int <= 6 and str(m).lower() in ['o', 'open', '0']:
            if s_int not in string_frets:
                string_frets[s_int] = 0

    # 4. 각 줄의 최종 진동 음정 계산
    for s, f in string_frets.items():
        p = (TUNING[s] + f) % 12
        sounding_pitches.add(p)
        string_notes[s] = SEMITONE_TO_NOTE[p]

    return sounding_pitches, string_notes


def evaluate_chord_confidence(chord_name: str, fingering_dict: dict, dsp_info: dict = None, capo: int = 1) -> tuple:
    """
    비전 핑거링, 추정 코드명, 오디오 DSP 정보를 종합하여 신뢰도 점수(0.0 ~ 1.0)를 산출합니다.
    기준치(0.65) 미만일 경우 Hand-Only(손 위치 전용) 모드로 전환됩니다.
    반환값: (confidence_score: float, reason: str, is_confident: bool)
    """
    if not isinstance(fingering_dict, dict):
        return 0.0, "운지 데이터 없음", False

    clean_name = str(chord_name or "").strip()
    if clean_name in ["-", "", "None", "알 수 없음", "미상"]:
        return 0.0, "코드명 미상", False

    sounding_pitches, string_notes = get_sounding_pitches(fingering_dict)
    if len(sounding_pitches) < 2:
        return 0.2, "소리 나는 유효 음정 부족 (2개 미만)", False

    # 1. 이론적 화음 성립도 (Theory Validity)
    slash_parts = clean_name.split('/')
    main_chord = slash_parts[0].strip()
    slash_bass = slash_parts[1].strip().upper() if len(slash_parts) > 1 else None

    m = re.match(r'^([A-G][#b♯♭]?)(.*)$', main_chord)
    if not m:
        return 0.3, "비표준 코드 형식", False

    root_str = m.group(1).upper().replace('♯', '#').replace('♭', 'B')
    qual = m.group(2).strip().lower()
    root_semi = NOTE_TO_SEMITONE.get(root_str, -1)
    if root_semi < 0:
        return 0.3, "알 수 없는 루트 음", False

    intervals = CHORD_INTERVALS.get(qual, [0, 4, 7])
    theory_pitches = {(root_semi + semi) % 12 for semi in intervals}
    if slash_bass and NOTE_TO_SEMITONE.get(slash_bass, -1) >= 0:
        theory_pitches.add(NOTE_TO_SEMITONE[slash_bass])

    valid_sounding = sounding_pitches.intersection(theory_pitches)
    theory_match_ratio = len(valid_sounding) / len(sounding_pitches) if sounding_pitches else 0.0

    has_root = (root_semi in sounding_pitches) or (slash_bass and NOTE_TO_SEMITONE.get(slash_bass) in sounding_pitches)
    theory_score = (theory_match_ratio * 0.7) + (0.3 if has_root else 0.0)

    # 2. 오디오 DSP 피크와의 일치도 (Audio Match)
    audio_score = 0.6
    audio_checked = False
    if dsp_info and isinstance(dsp_info, dict):
        dom_notes = dsp_info.get("dominant_notes") or []
        audio_pitches = {NOTE_TO_SEMITONE[n] for n in dom_notes if n in NOTE_TO_SEMITONE}
        if audio_pitches:
            audio_checked = True
            capo_val = _safe_int(dsp_info.get("capo", capo), 1)
            direct_overlap = len(sounding_pitches.intersection(audio_pitches)) / len(sounding_pitches) if sounding_pitches else 0.0
            capo_sounding = {(p + capo_val) % 12 for p in sounding_pitches}
            capo_overlap = len(capo_sounding.intersection(audio_pitches)) / len(capo_sounding) if capo_sounding else 0.0
            audio_overlap = max(direct_overlap, capo_overlap)
            raw_sim = float(dsp_info.get("similarity", 0.7))
            audio_score = (audio_overlap * 0.6) + (raw_sim * 0.4)

    # 3. 종합 점수 산출
    if audio_checked:
        total_score = (audio_score * 0.55) + (theory_score * 0.45)
    else:
        total_score = theory_score

    total_score = max(0.0, min(1.0, total_score))

    CONFIDENCE_THRESHOLD = 0.65
    is_confident = total_score >= CONFIDENCE_THRESHOLD

    if is_confident:
        reason = f"화음 검증 완료 (일치율 {int(total_score * 100)}%)"
    else:
        if theory_match_ratio < 0.5:
            reason = f"비표준 텐션 또는 불협화음 감지 (화성 일치율 {int(theory_match_ratio * 100)}%)"
        elif audio_checked and audio_score < 0.5:
            reason = f"오디오 음향 불일치 (음향 일치율 {int(audio_score * 100)}%)"
        else:
            reason = f"모호한 파지 형태 (신뢰도 {int(total_score * 100)}% < 65%)"

    return round(total_score, 2), reason, is_confident


def sanitize_fingering_with_theory(chord_name: str, fingering_dict: dict, prefer_fret: int = None, dsp_info: dict = None) -> dict:
    """
    AI가 반환한 운지 딕셔너리가 화성학/운지 물리 법칙을 위배할 경우
    (예: B코드에서 4번줄 3프렛 감5도 불협화음 환각, 공중에 뜬 2/4번 손가락 착오, A형/E형 바레 폼 누락 등)
    전 지판 음계 룩업테이블(LUT) 및 음향 FFT 교차 검증을 통해 정확한 물리적/화성학적 운지로 자동 보정합니다.
    분수코드(Slash chord) 및 텐션 보이싱을 자동 합성하고 감지합니다.
    """
    if not isinstance(fingering_dict, dict):
        return fingering_dict

    clean_name = str(chord_name or "").strip()
    # 0. Mute (뮤트) 코드 처리
    if 'mute' in clean_name.lower() or '뮤트' in clean_name:
        if not fingering_dict.get("markers"):
            fingering_dict["markers"] = {1: 'x', 2: 'x', 3: 'x', 4: 'x', 5: 'x', 6: 'x'}
        fingering_dict["dots"] = []
        fingering_dict["barre"] = None
        return fingering_dict

    dots = fingering_dict.get("dots") or []
    raw_dots = [d.copy() for d in dots if isinstance(d, dict)]
    fingering_dict["raw_dots"] = raw_dots

    # 0.1 오디오 FFT 실음 기반 프렛 위치 및 코드명 역추산 보정 (카포 1프렛 기준)
    if dsp_info and isinstance(dsp_info, dict):
        clean_name, fingering_dict = reconcile_fret_with_audio(clean_name, fingering_dict, dsp_info, capo=1)

    # Capo 등 부가 텍스트 제거 및 분수코드 분리
    clean_name = re.sub(r'\(.*?\)', '', clean_name).strip()
    slash_parts = clean_name.split('/')
    main_chord = slash_parts[0].strip()
    slash_bass = slash_parts[1].strip().upper().replace('♯', '#').replace('♭', 'B') if len(slash_parts) > 1 else None

    m = re.match(r'^([A-G][#b♯♭]?)(.*)$', main_chord, re.IGNORECASE)
    if not m:
        return fingering_dict

    root_str = m.group(1).upper().replace('♯', '#').replace('♭', 'B')
    quality = m.group(2).strip().lower()

    root_semi = NOTE_TO_SEMITONE.get(root_str, -1)
    if root_semi < 0:
        return fingering_dict

    # 1. markers 정리: 'x', 'o' 이외의 숫자나 불필요한 값 정리
    if isinstance(fingering_dict.get("markers"), dict):
        clean_m = {}
        for k, v in fingering_dict["markers"].items():
            v_s = str(v).strip().lower()
            if v_s in ['x', 'mute']:
                clean_m[_safe_int(k)] = 'x'
            elif v_s in ['o', 'open', '0']:
                clean_m[_safe_int(k)] = 'o'
        fingering_dict["markers"] = clean_m

    # 2. 엄지 썸오버 6번줄 2프렛 파지 시 Bm7 오판정 자동 교정:
    # 6번줄 2프렛에 엄지(T)가 위치하는 경우 이는 물리적으로 F# 계열(F#7/F#m7) 운지입니다.
    dots = fingering_dict.get("dots") or []
    has_thumb_fsharp = any(
        str(d.get("finger")).upper() in ["T", "THUMB"] and
        _safe_int(d.get("string")) == 6 and _safe_int(d.get("fret")) == 2
        for d in dots if isinstance(d, dict)
    )
    if has_thumb_fsharp and clean_name in ["Bm", "Bm7", "Bmin", "Bmin7"]:
        clean_name = "F#7"
        fingering_dict["chord"] = "F#7"
        root_str = "F#"
        root_semi = NOTE_TO_SEMITONE["F#"]
        quality = "7"
        main_chord = "F#7"

    # 3. 7(#5) / 7aug / +7 계열 특화 보이싱 보정
    if any(q in quality for q in ['7#5', '7(#5)', '7aug', 'aug7', '+7', '7b13', '7(b13)']):
        fret_6 = (root_semi - 4) % 12
        if fret_6 == 0:
            fret_6 = 12

        has_6th_root = any(_safe_int(d.get("string")) == 6 for d in dots if isinstance(d, dict))
        base_fret_in = _safe_int(fingering_dict.get("base_fret"), 0)
        if has_6th_root or base_fret_in in [fret_6, fret_6 - 1]:
            fingering_dict["base_fret"] = fret_6
            fingering_dict["barre"] = None
            fingering_dict["dots"] = [
                {"string": 6, "fret": fret_6, "finger": 1},
                {"string": 4, "fret": fret_6, "finger": 1},
                {"string": 3, "fret": fret_6 + 1, "finger": 2},
                {"string": 2, "fret": fret_6 + 1, "finger": 3},
            ]
            fingering_dict["markers"] = {5: "x", 1: "x"}
            fingering_dict["fingering_summary"] = (
                f"검지(1번)가 {fret_6}프렛 6번줄(근음 {root_str})과 4번줄(단7도)을 짚고, "
                f"중지(2번)와 약지(3번)가 {fret_6 + 1}프렛의 3번줄(3도)과 2번줄(#5도)을 누르는 {clean_name} 보이싱입니다. "
                "(새끼손가락은 줄을 누르지 않고 웅크려 있으며, 5번줄과 1번줄은 자연스럽게 뮤트됩니다)"
            )
            return fingering_dict

    # 4. 허용 음계(Pitch-Class) 계산 및 오디오 검증 결합
    intervals = CHORD_INTERVALS.get(quality, [0, 4, 7] if 'm' not in quality else [0, 3, 7])
    allowed_semis = {(root_semi + semi) % 12 for semi in intervals}
    if slash_bass and slash_bass in NOTE_TO_SEMITONE:
        allowed_semis.add(NOTE_TO_SEMITONE[slash_bass])

    # DSP 오디오 FFT에서 검출된 실음 추가
    if dsp_info and isinstance(dsp_info, dict):
        for n in dsp_info.get("active_notes", []):
            clean_n = n.upper().replace('♯', '#').replace('♭', 'B')
            if clean_n in NOTE_TO_SEMITONE:
                allowed_semis.add(NOTE_TO_SEMITONE[clean_n])

    # 5. 공중에 뜬 손가락(Floating Fingers) 및 화성학적 불협화음 필터링
    barre = fingering_dict.get("barre")
    barre_fret = _safe_int(barre.get("fret"), 0) if isinstance(barre, dict) else 0

    valid_dots = []
    for d in dots:
        if not isinstance(d, dict):
            continue
        s_num = _safe_int(d.get("string"))
        f_num = _safe_int(d.get("fret"))
        if s_num in TUNING and f_num > 0:
            pitch = (TUNING[s_num] + f_num) % 12
            if pitch in allowed_semis:
                valid_dots.append(d)
        else:
            valid_dots.append(d)

    fingering_dict["dots"] = valid_dots

    # 6. 바레 코드 정규화 (A형 / E형 바레 폼)
    # 6-A: A-shape 바레 코드 (5번줄 루트)
    is_a_shape = (barre_fret >= 1 and (TUNING[5] + barre_fret) % 12 == root_semi)
    if is_a_shape:
        target_fret = barre_fret + 2
        markers = fingering_dict.get("markers") or {}
        markers[6] = 'x'
        fingering_dict["markers"] = markers

        if quality in ['', 'maj', 'major']:
            fingering_dict["dots"] = [
                {"string": 4, "fret": target_fret, "finger": 3},
                {"string": 3, "fret": target_fret, "finger": 3},
                {"string": 2, "fret": target_fret, "finger": 3},
            ]
            fingering_dict["barre"] = {
                "fret": barre_fret,
                "start_string": 1,
                "end_string": 5,
                "finger": 1
            }
            fingering_dict["fingering_summary"] = (
                f"검지(1번)로 {barre_fret}프렛 (1~5번줄) 바레, 약지(3번)로 {target_fret}프렛의 4, 3, 2번줄을 "
                f"동시에 누르는 A형 바레 {clean_name} 코드 폼입니다. (6번줄 뮤트)"
            )
            return fingering_dict
        elif quality in ['m', 'min', 'minor', '-']:
            fingering_dict["dots"] = [
                {"string": 4, "fret": target_fret, "finger": 3},
                {"string": 3, "fret": target_fret, "finger": 4},
                {"string": 2, "fret": barre_fret + 1, "finger": 2},
            ]
            fingering_dict["barre"] = {
                "fret": barre_fret,
                "start_string": 1,
                "end_string": 5,
                "finger": 1
            }
            fingering_dict["fingering_summary"] = (
                f"검지(1번)로 {barre_fret}프렛 (1~5번줄) 바레, 약지(3번)·새끼(4번)로 {target_fret}프렛(4, 3번줄), "
                f"중지(2번)로 {barre_fret + 1}프렛(2번줄)을 누르는 {clean_name} 마이너 코드 폼입니다."
            )
            return fingering_dict
        elif quality in ['m7', 'min7', '-7']:
            fingering_dict["dots"] = [
                {"string": 4, "fret": target_fret, "finger": 3},
                {"string": 2, "fret": barre_fret + 1, "finger": 2},
            ]
            fingering_dict["barre"] = {
                "fret": barre_fret,
                "start_string": 1,
                "end_string": 5,
                "finger": 1
            }
            fingering_dict["markers"] = {6: 'x'}
            fingering_dict["fingering_summary"] = (
                f"검지(1번)로 {barre_fret}프렛 (1~5번줄) 바레, 약지(3번)로 4번줄 {target_fret}프렛, "
                f"중지(2번)로 2번줄 {barre_fret + 1}프렛을 누르는 A형 마이너7 [{clean_name}] 코드 폼입니다. (6번줄 뮤트, 새끼손가락 미사용)"
            )
            return fingering_dict
        elif quality in ['7', 'dom7']:
            fingering_dict["dots"] = [
                {"string": 4, "fret": target_fret, "finger": 3},
                {"string": 2, "fret": target_fret, "finger": 4},
            ]
            fingering_dict["barre"] = {
                "fret": barre_fret,
                "start_string": 1,
                "end_string": 5,
                "finger": 1
            }
            fingering_dict["fingering_summary"] = (
                f"검지(1번)로 {barre_fret}프렛 (1~5번줄) 바레, 약지(3번)로 4번줄 {target_fret}프렛, "
                f"새끼(4번)로 2번줄 {target_fret}프렛을 누르는 {clean_name} 도미넌트7 코드 폼입니다."
            )
            return fingering_dict

    # 6-B: E-shape 바레 코드 (6번줄 루트)
    is_e_shape = (barre_fret >= 1 and (TUNING[6] + barre_fret) % 12 == root_semi)
    if is_e_shape:
        fingering_dict["markers"] = {}
        target_fret = barre_fret + 2
        if quality in ['', 'maj', 'major']:
            fingering_dict["dots"] = [
                {"string": 5, "fret": target_fret, "finger": 3},
                {"string": 4, "fret": target_fret, "finger": 4},
                {"string": 3, "fret": barre_fret + 1, "finger": 2},
            ]
            fingering_dict["barre"] = {
                "fret": barre_fret,
                "start_string": 1,
                "end_string": 6,
                "finger": 1
            }
            fingering_dict["fingering_summary"] = (
                f"검지(1번)로 {barre_fret}프렛 (1~6번줄) 전체 바레, 약지(3번)·새끼(4번)로 {target_fret}프렛(5, 4번줄), "
                f"중지(2번)로 {barre_fret + 1}프렛(3번줄)을 누르는 E형 바레 {clean_name} 코드 폼입니다."
            )
            return fingering_dict
        elif quality in ['m', 'min', 'minor', '-']:
            fingering_dict["dots"] = [
                {"string": 5, "fret": target_fret, "finger": 3},
                {"string": 4, "fret": target_fret, "finger": 4},
            ]
            fingering_dict["barre"] = {
                "fret": barre_fret,
                "start_string": 1,
                "end_string": 6,
                "finger": 1
            }
            fingering_dict["fingering_summary"] = (
                f"검지(1번)로 {barre_fret}프렛 (1~6번줄) 전체 바레, 약지(3번)·새끼(4번)로 {target_fret}프렛(5, 4번줄)을 "
                f"누르는 E형 마이너 바레 {clean_name} 코드 폼입니다."
            )
            return fingering_dict
        elif quality in ['m7', 'min7', '-7']:
            fingering_dict["dots"] = [
                {"string": 5, "fret": target_fret, "finger": 3},
            ]
            fingering_dict["barre"] = {
                "fret": barre_fret,
                "start_string": 1,
                "end_string": 6,
                "finger": 1
            }
            fingering_dict["fingering_summary"] = (
                f"검지(1번)로 {barre_fret}프렛 (1~6번줄) 전체 바레, 약지(3번)로 {target_fret}프렛(5번줄)을 "
                f"누르는 E형 마이너7 [{clean_name}] 코드 폼입니다."
            )
            return fingering_dict
        elif quality in ['7', 'dom7']:
            fingering_dict["dots"] = [
                {"string": 5, "fret": target_fret, "finger": 3},
                {"string": 3, "fret": barre_fret + 1, "finger": 2},
            ]
            fingering_dict["barre"] = {
                "fret": barre_fret,
                "start_string": 1,
                "end_string": 6,
                "finger": 1
            }
            fingering_dict["fingering_summary"] = (
                f"검지(1번)로 {barre_fret}프렛 (1~6번줄) 전체 바레, 약지(3번)로 {target_fret}프렛(5번줄), "
                f"중지(2번)로 {barre_fret + 1}프렛(3번줄)을 누르는 E형 도미넌트7 [{clean_name}] 코드 폼입니다."
            )
            return fingering_dict

    # 7. 분수코드 (Slash Chord / Inversion) 자동 검출
    lowest_s, lowest_f, lowest_pitch = detect_lowest_sounding_string(
        fingering_dict.get("dots") or [],
        fingering_dict.get("barre"),
        fingering_dict.get("markers") or {}
    )
    if lowest_pitch is not None and lowest_pitch != root_semi:
        bass_note = SEMITONE_TO_NOTE[lowest_pitch]
        if slash_bass is None:
            synth_chord = f"{main_chord}/{bass_note}"
            fingering_dict["chord"] = synth_chord
            fingering_dict["fingering_summary"] = (
                f"{lowest_s}번 줄 {lowest_f}프렛({bass_note} 베이스 음)을 최저음으로 연주하는 "
                f"전위화음(분수코드) [{synth_chord}] 폼입니다."
            )

    # 8. 루트 음(Root Note) 최종 정합성 검증 Fallback
    dots = fingering_dict.get("dots") or []
    barre = fingering_dict.get("barre")
    if dots or barre:
        chord_notes = set()
        if isinstance(barre, dict) and _safe_int(barre.get("fret"), 0) > 0:
            bfret = _safe_int(barre["fret"])
            b_start = min(_safe_int(barre.get("start_string"), 1), _safe_int(barre.get("end_string"), 6))
            b_end = max(_safe_int(barre.get("start_string"), 1), _safe_int(barre.get("end_string"), 6))
            for s in range(b_start, b_end + 1):
                chord_notes.add((TUNING[s] + bfret) % 12)
        for d in dots:
            if isinstance(d, dict) and _safe_int(d.get("string")) in TUNING:
                chord_notes.add((TUNING[d["string"]] + _safe_int(d.get("fret"))) % 12)

        markers = fingering_dict.get("markers") or {}
        for s, m in markers.items():
            if str(m).lower() in ["o", "0", "open"] and _safe_int(s) in TUNING:
                chord_notes.add(TUNING[_safe_int(s)] % 12)

        if root_semi not in chord_notes and (slash_bass is None or NOTE_TO_SEMITONE.get(slash_bass) not in chord_notes):
            conf_score, conf_reason, is_conf = evaluate_chord_confidence(clean_name, fingering_dict, dsp_info=dsp_info)
            if not is_conf:
                # 억지 사전자료 대체 금지: 실제 감지된 손 위치 원형 복원 및 Hand-Only 모드 설정
                if fingering_dict.get("raw_dots"):
                    fingering_dict["dots"] = fingering_dict["raw_dots"]
                fingering_dict["is_confident"] = False
                fingering_dict["confidence"] = conf_score
                fingering_dict["confidence_reason"] = conf_reason
                fingering_dict["chord"] = "-"
                return fingering_dict

            sanitized = resolve_chord_data(clean_name, prefer_fret=prefer_fret or _safe_int(fingering_dict.get("base_fret"), 1))
            barre_info = sanitized.get("barre")
            dots_info = sanitized.get("dots") or []
            desc_parts = []
            if barre_info:
                desc_parts.append(f"검지가 {barre_info.get('fret', 1)}프렛 바레")
            dot_strs = [f"{d.get('string')}번줄 {d.get('fret')}프렛" for d in dots_info if isinstance(d, dict)]
            if dot_strs:
                desc_parts.append(f"{', '.join(dot_strs)} 운지")
            sanitized["fingering_summary"] = f"{clean_name} 표준 폼 연주 ({', '.join(desc_parts)})"
            return sanitized

    return fingering_dict


def generate_chord_svg(chord_name, fingering_dict=None, prefer_fret=None, dsp_info=None):
    """
    참고 이미지 스타일의 지판 다이어그램 SVG 생성
    """
    valid_custom = False
    if fingering_dict and isinstance(fingering_dict, dict):
        cname_to_sanitize = chord_name if chord_name not in ["-", "", None] else fingering_dict.get("chord", "-")
        fingering_dict = sanitize_fingering_with_theory(cname_to_sanitize, fingering_dict, prefer_fret=prefer_fret, dsp_info=dsp_info)
        dots = fingering_dict.get('dots')
        barre = fingering_dict.get('barre')
        if (isinstance(dots, list) and len(dots) > 0) or (isinstance(barre, dict) and barre.get('fret')):
            data = fingering_dict
            valid_custom = True

    if not valid_custom:
        data = resolve_chord_data(chord_name, prefer_fret=prefer_fret)

    all_frets = []
    for d in data.get('dots') or []:
        if isinstance(d, dict):
            f_val = _safe_int(d.get('fret'), 0)
            if f_val > 0:
                all_frets.append(f_val)

    barre = data.get('barre')
    if isinstance(barre, dict) and _safe_int(barre.get('fret'), 0) > 0:
        all_frets.append(_safe_int(barre['fret'], 1))

    base_fret = _safe_int(data.get('base_fret'), 1)
    if all_frets:
        min_f = min(all_frets)
        max_f = max(all_frets)
        markers_check = data.get('markers') or {}
        has_open = any(str(markers_check.get(s)).strip().lower() in ['o', 'open', '0'] for s in range(1, 7))
        if min_f >= 3 and not has_open:
            base_fret = min_f
        elif max_f <= 4 and min_f >= 1:
            base_fret = 1
        else:
            base_fret = max(1, min_f)

    width = 300
    height = 200
    start_x = 48
    fret_width = 48
    num_frets = 4
    start_y = 38
    string_gap = 22

    grid_w = fret_width * num_frets
    grid_h = string_gap * 5

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'style="background-color: #F8FAFC; border-radius: 12px; font-family: -apple-system, BlinkMacSystemFont, sans-serif; '
        f'box-shadow: 0 4px 12px rgba(0,0,0,0.12); border: 1.5px solid #CBD5E1;">'
    ]

    display_title = str(data.get('chord') or chord_name or "")
    if display_title in ["-", "None", "", "알 수 없음", "미상"]:
        display_title = f"{base_fret} Fret Shape" if base_fret > 1 else "Custom Shape"
    svg.append(
        f'<text x="{start_x}" y="24" font-size="17" font-weight="800" fill="#0F1720">{display_title}</text>'
    )

    svg.append(
        f'<rect x="{start_x}" y="{start_y}" width="{grid_w}" height="{grid_h}" fill="#E6EEF4" rx="2" />'
    )

    for f_idx in range(num_frets):
        actual_fret = base_fret + f_idx
        if actual_fret in [3, 5, 7, 9, 12, 15]:
            mx = start_x + f_idx * fret_width + (fret_width / 2)
            my = start_y + 2.5 * string_gap + 4
            svg.append(
                f'<text x="{mx}" y="{my}" font-size="13" font-weight="bold" fill="#475569" text-anchor="middle">*</text>'
            )

    for i in range(num_frets + 1):
        x = start_x + i * fret_width
        if i == 0 and base_fret == 1:
            svg.append(f'<line x1="{x-2}" y1="{start_y}" x2="{x-2}" y2="{start_y + grid_h}" stroke="#0F1720" stroke-width="2" />')
            svg.append(f'<line x1="{x+1}" y1="{start_y}" x2="{x+1}" y2="{start_y + grid_h}" stroke="#0F1720" stroke-width="2.5" />')
        else:
            svg.append(f'<line x1="{x}" y1="{start_y}" x2="{x}" y2="{start_y + grid_h}" stroke="#64748B" stroke-width="1.3" />')

    for i in range(6):
        y = start_y + i * string_gap
        str_w = 0.9 + (i * 0.3)
        svg.append(f'<line x1="{start_x}" y1="{y}" x2="{start_x + grid_w}" y2="{y}" stroke="#334155" stroke-width="{str_w:.1f}" />')

    if base_fret > 1:
        for f in range(num_frets):
            fx = start_x + f * fret_width + (fret_width / 2)
            svg.append(
                f'<text x="{fx}" y="{start_y + grid_h + 18}" font-size="12" font-weight="700" fill="#1E293B" text-anchor="middle">{base_fret + f}</text>'
            )

    markers = data.get('markers') or {}
    if isinstance(markers, dict):
        for s_key, marker in markers.items():
            s_num = _safe_int(s_key, 0)
            if marker and 1 <= s_num <= 6:
                m_str = str(marker).strip().lower()
                if m_str in ['x', 'mute']:
                    val = 'x'
                elif m_str in ['o', 'open', '0']:
                    val = 'o'
                else:
                    continue
                y = start_y + (s_num - 1) * string_gap
                svg.append(
                    f'<text x="{start_x - 14}" y="{y + 4}" font-size="13" font-weight="800" fill="#0F1720" text-anchor="middle">{val}</text>'
                )

    barre_covered_strings = set()
    if isinstance(barre, dict) and _safe_int(barre.get('fret'), 0) > 0:
        b_fret_num = _safe_int(barre['fret'], base_fret)
        b_fret = b_fret_num - base_fret
        if 0 <= b_fret < num_frets:
            bx = start_x + b_fret * fret_width + (fret_width / 2)
            s_start = min(_safe_int(barre.get('start_string'), 1), _safe_int(barre.get('end_string'), 6))
            s_end = max(_safe_int(barre.get('start_string'), 1), _safe_int(barre.get('end_string'), 6))
            s_start = max(1, min(6, s_start))
            s_end = max(1, min(6, s_end))
            y_top = start_y + (s_start - 1) * string_gap
            y_bot = start_y + (s_end - 1) * string_gap
            b_h = (y_bot - y_top) + 22
            svg.append(
                f'<rect x="{bx - 11}" y="{y_top - 11}" width="22" height="{b_h}" rx="7" fill="none" stroke="#0F1720" stroke-width="2.2" />'
            )
            b_finger = _safe_int(barre.get('finger'), 1)
            for s in [s_start, s_end]:
                barre_covered_strings.add((s, b_fret_num))
                sy = start_y + (s - 1) * string_gap
                svg.append(f'<circle cx="{bx}" cy="{sy}" r="8.5" fill="#FFFFFF" stroke="#0F1720" stroke-width="1.8" />')
                svg.append(f'<text x="{bx}" y="{sy + 4}" font-size="11" font-weight="800" fill="#0F1720" text-anchor="middle">{b_finger}</text>')

    for d in data.get('dots') or []:
        if not isinstance(d, dict):
            continue
        s_num = _safe_int(d.get('string'), 0)
        f_num = _safe_int(d.get('fret'), 0)
        if (s_num, f_num) in barre_covered_strings:
            continue
        d_fret = f_num - base_fret
        if 0 <= d_fret < num_frets and 1 <= s_num <= 6:
            cx = start_x + d_fret * fret_width + (fret_width / 2)
            cy = start_y + (s_num - 1) * string_gap
            finger = _format_finger(d.get('finger'))
            svg.append(f'<circle cx="{cx}" cy="{cy}" r="9" fill="#FFFFFF" stroke="#0F1720" stroke-width="1.8" />')
            svg.append(f'<text x="{cx}" y="{cy + 4}" font-size="11" font-weight="800" fill="#0F1720" text-anchor="middle">{finger}</text>')

    svg.append('</svg>')
    return "".join(svg)


def parse_ai_response(text: str, prefer_fret: int = None, dsp_info: dict = None):
    """
    Vision-First JSON 응답 또는 마크다운+JSON 응답에서:
    1) 화면에 표시할 2줄 마크다운 리포트 (1. 정확한 코드명, 2. 지판 위치 및 운지 요약)
    2) 추출된 코드명
    3) 구조화된 운지 딕셔너리 (base_fret, barre, dots, markers)
    4) 시작 프렛 번호
    를 반환합니다.
    """
    fingering_dict = None

    # 1. 전체가 JSON이거나 코드 블록 안에 JSON이 있는 경우 파싱
    cleaned_raw = text.strip()
    json_str = None
    fence_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', cleaned_raw, re.DOTALL)
    if fence_match:
        json_str = fence_match.group(1)
    elif cleaned_raw.startswith("{") and cleaned_raw.endswith("}"):
        json_str = cleaned_raw
    else:
        brace_start = cleaned_raw.find("{")
        brace_end = cleaned_raw.rfind("}")
        if brace_start != -1 and brace_end > brace_start:
            json_str = cleaned_raw[brace_start:brace_end + 1]

    if json_str:
        try:
            fingering_dict = json.loads(json_str)
        except Exception:
            fingering_dict = None

    if fingering_dict and isinstance(fingering_dict, dict):
        detected_chord = str(fingering_dict.get("chord") or "C").strip()
        fingering_dict = sanitize_fingering_with_theory(detected_chord, fingering_dict, prefer_fret=prefer_fret, dsp_info=dsp_info)
        detected_chord = str(fingering_dict.get("chord") or detected_chord).strip()

        # 신뢰도 평가 게이트 실행 (Confidence Gate)
        confidence, reason, is_confident = evaluate_chord_confidence(detected_chord, fingering_dict, dsp_info=dsp_info)
        fingering_dict["is_confident"] = is_confident
        fingering_dict["confidence"] = confidence
        fingering_dict["confidence_reason"] = reason

        sounding_pitches, string_notes = get_sounding_pitches(fingering_dict)
        pitch_guide = ", ".join([f"{s}번줄:{p}" for s, p in sorted(string_notes.items())])

        summary = str(fingering_dict.get("fingering_summary") or "").strip()
        visual_obs = str(fingering_dict.get("finger_observations") or "").strip()
        prefer_fret = _safe_int(fingering_dict.get("base_fret"), prefer_fret)

        if not summary and visual_obs:
            summary = visual_obs

        # 영어로 출력되었거나 내용이 부실한 경우 한국어 자동 구성
        is_english = any(w in summary.lower() for w in ["finger", "fret", "string", "barre", "plays", "chord", "index", "middle", "ring", "pinky"]) and not re.search(r'[가-힣]', summary)
        if is_english or not summary:
            finger_names = {
                1: "검지", 2: "중지", 3: "약지", 4: "새끼손가락",
                "1": "검지", "2": "중지", "3": "약지", "4": "새끼손가락",
                "T": "엄지(T)", "t": "엄지(T)"
            }
            parts = []
            barre = fingering_dict.get("barre")
            if isinstance(barre, dict) and barre.get("fret"):
                fn = finger_names.get(barre.get("finger", 1), "검지")
                parts.append(f"{fn}로 {barre['fret']}프렛 ({barre.get('start_string', 1)}~{barre.get('end_string', 6)}번 줄) 바레")
            dots = fingering_dict.get("dots")
            if isinstance(dots, list):
                for d in dots:
                    if isinstance(d, dict) and "string" in d and "fret" in d:
                        raw_f = d.get("finger", 1)
                        fn = finger_names.get(raw_f, f"{raw_f}번 손가락")
                        if str(raw_f).upper() == "T":
                            fn = "엄지(T)"
                        parts.append(f"{fn}로 {d['string']}번 줄 {d['fret']}프렛")
            if parts:
                if is_confident and detected_chord not in ["-", "", "None"]:
                    summary = f"{', '.join(parts)}을 운지하는 [{detected_chord}] 코드 폼입니다."
                else:
                    summary = f"{', '.join(parts)} 파지 형태입니다."
            else:
                summary = f"[{detected_chord}] 코드의 기본 운지 형태입니다."

        # Mode B: 신뢰도 미달(0.65 미만) 또는 미상 보이싱 시 손 위치 전용(Hand-Only) 리포트 출력
        if not is_confident or detected_chord in ["-", "", "None"]:
            detected_chord = "-"
            fingering_dict["chord"] = "-"
            if fingering_dict.get("raw_dots"):
                fingering_dict["dots"] = fingering_dict["raw_dots"]
            sounding_pitches, string_notes = get_sounding_pitches(fingering_dict)
            pitch_guide = ", ".join([f"{s}번줄:{p}" for s, p in sorted(string_notes.items())])
            clean_markdown = (
                f"1. **코드명**: **특수 보이싱 / 미상 (-)**\n"
                f"2. **지판 위치 및 운지 요약**: 계산 신뢰도가 낮거나 비표준 폼으로 판별되어 억지 코드명을 부여하지 않고, "
                f"영상에서 포착된 **실제 손가락 파지 위치**를 다이어그램으로 표시합니다.\n"
                f"- **파지 운지**: {summary}\n"
                f"- **각 현별 실음**: {pitch_guide if pitch_guide else '뮤트 또는 개방현'}\n"
                f"- **분석 상태**: {reason}"
            )
            return clean_markdown, detected_chord, fingering_dict, prefer_fret

        # Mode A: 확정 코드 모드 리포트 출력
        reconcile_note = fingering_dict.get("reconciliation_note")
        clean_markdown = (
            f"1. **정확한 코드명**: **{detected_chord}**\n"
            f"2. **지판 위치 및 운지 요약**: {summary}\n"
            f"- **분석 신뢰도**: {int(confidence * 100)}% ({reason})"
        )
        if pitch_guide:
            clean_markdown += f"\n- **구성 음정**: {pitch_guide}"
        if reconcile_note:
            clean_markdown += f"\n- **정밀 화성 역추산**: {reconcile_note}"
        return clean_markdown, detected_chord, fingering_dict, prefer_fret

    # Fallback: 일반 마크다운 파싱
    clean_markdown = re.sub(r'```(?:json)?.*?```', '', cleaned_raw, flags=re.DOTALL).strip()
    detected_chord = "C"
    for line in clean_markdown.split("\n"):
        if "코드명" in line and ":" in line:
            part = line.split(":", 1)[1].replace("**", "").replace("*", "").strip()
            detected_chord = part.split("(")[0].split(",")[0].strip()
            if detected_chord:
                break

    fret_matches = re.findall(r'(\d{1,2})\s*(?:~|-|번)?\s*프렛', clean_markdown)
    if fret_matches:
        frets = [int(f) for f in fret_matches if 1 <= int(f) <= 22]
        if frets:
            prefer_fret = min(frets)

    return clean_markdown, detected_chord, None, prefer_fret
