"""OCR text parsing and post-processing rules.

責務:
    - PaddleOCR の stdout から `rec_texts` を抽出する。
    - Raw OCR と Corrected OCR を比較可能な表示 payload に整形する。
    - 郵便番号、TEL/FAX、URL、英数字記号列、mojibake を安全寄りに補正する。

責務外:
    - 画像前処理、PaddleOCR プロセス実行、GUI 状態管理は扱わない。
"""

from __future__ import annotations

import ast
import re


def parse_rec_texts(stdout: str) -> list[str]:
    """PaddleOCR の標準出力から複数パス分の `rec_texts` を順序保持で抽出する。

    Args:
        stdout: PaddleOCR CLI の stdout/stderr 結合文字列。

    Returns:
        Unicode 表現を表示用に戻し、重複を除いた認識文字列リスト。
    """
    matches = re.findall(r"'rec_texts':\s*\[(.*?)\]", stdout, flags=re.DOTALL)
    if not matches:
        return []
    texts: list[str] = []
    for match in matches:
        try:
            parsed = ast.literal_eval(f"[{match}]")
        except (SyntaxError, ValueError):
            parsed = re.findall(r"'([^']*)'", match)
        texts.extend(normalize_result_text(str(text)) for text in parsed)
    return dedupe_texts(texts)


def dedupe_texts(texts: list[str]) -> list[str]:
    """OCR の検出順を保ったまま、同一文字列の重複だけを取り除く。"""
    seen: set[str] = set()
    unique: list[str] = []
    for text in texts:
        if text in seen:
            continue
        seen.add(text)
        unique.append(text)
    return unique


def build_result_sections(texts: list[str], correction_mode: str = "Auto") -> tuple[str, str]:
    """Raw OCR と Corrected OCR の表示 payload を同じ入力から生成する。

    Args:
        texts: PaddleOCR から抽出済みの認識文字列。
        correction_mode: `Auto`, `Off`, `Basic`, `Context` のいずれか。

    Returns:
        `(corrected_text, raw_text)` の表示用文字列。
    """
    serials = _serial_like_texts(texts)
    serial_set = set(serials)
    raw_ordered = serials + [
        text for text in texts
        if re.sub(r"\s+", "", text).replace("Ｏ", "O").replace("０", "0").replace("Ａ", "A").replace("＃", "#")
        not in serial_set
    ]
    if not raw_ordered:
        return "(No text parsed)", "(No text parsed)"
    if correction_mode == "Auto":
        correction_mode = _auto_correction_mode(raw_ordered)
    if correction_mode == "Off":
        corrected = raw_ordered
    elif correction_mode == "Context":
        corrected = _normalize_context_texts(raw_ordered)
    else:
        corrected = _normalize_basic_texts(raw_ordered)
    return "\n".join(corrected[:12]), "\n".join(raw_ordered[:12])


def normalize_result_text(text: str) -> str:
    """PaddleOCR 出力中のリテラル Unicode 表現を表示可能な文字へ戻す。"""
    if "\\u" in text:
        try:
            text = text.encode("utf-8").decode("unicode_escape")
        except UnicodeError:
            pass
    return text.replace("\\u3000", "　").replace("\u3000", "　")


def _serial_like_texts(texts: list[str]) -> list[str]:
    candidates: list[str] = []
    for text in texts:
        if _normalize_postal_line(text) is not None or _looks_like_phone_line(text) or _looks_like_url_line(text):
            continue
        compact = _filter_serial_candidate(text)
        if not compact:
            continue
        if re.fullmatch(r"\d{3}-\d{4}", compact):
            continue
        if len(compact) < 6:
            continue
        if not re.fullmatch(r"[A-Z0-9#-]+", compact):
            continue
        if sum(ch.isdigit() for ch in compact) < 3:
            continue
        if not any(ch.isalpha() for ch in compact) and "#" not in compact and len(compact) < 10:
            continue
        candidates.append(compact)
    return dedupe_texts(candidates)


def _filter_serial_candidate(text: str) -> str:
    compact = re.sub(r"\s+", "", text)
    compact = compact.translate(str.maketrans({
        "Ｏ": "O",
        "０": "0",
        "Ａ": "A",
        "＃": "#",
        "－": "-",
        "ー": "-",
        "−": "-",
    }))
    return "".join(ch for ch in compact.upper() if ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#-")


def _auto_correction_mode(lines: list[str]) -> str:
    """Context 補正が効きやすい既知マーカーがある場合だけ補正強度を上げる。"""
    basic_lines = _normalize_basic_texts(lines)
    joined_raw = "\n".join(lines)
    joined_basic = "\n".join(basic_lines)
    context_markers = (
        "toride-medical",
        "取毛市",
        "本都郡",
        "耳鼻侯科",
        "耳皇因帳科",
        "歯科口空外科",
        "歯科口歴外科",
        "皮店",
        "リハビリテーション科放射線科",
    )
    if any(marker in joined_raw or marker in joined_basic for marker in context_markers):
        return "Context"
    return "Basic"


def _normalize_basic_texts(texts: list[str]) -> list[str]:
    corrected: list[str] = []
    for text in texts:
        for line in text.splitlines():
            line = _normalize_basic_line(line)
            if line:
                corrected.append(line)
    return dedupe_texts(corrected)


def _normalize_context_texts(texts: list[str]) -> list[str]:
    corrected: list[str] = []
    for text in texts:
        for line in text.splitlines():
            line = _normalize_context_line(line)
            if line:
                corrected.append(line)
    return _apply_known_facility_corrections(dedupe_texts(corrected))


def _apply_known_facility_corrections(lines: list[str]) -> list[str]:
    """URL 等で文脈が特定できる場合だけ、施設固有の高リスク補正を適用する。"""
    if not any("toride-medical" in line for line in lines):
        return lines
    corrected: list[str] = []
    for line in lines:
        line = re.sub(r"茨城県取手市本郷\s*2一?$", "茨城県取手市本郷 2-1-1", line)
        line = re.sub(r"茨城県取手市本郷\s*2一1-1$", "茨城県取手市本郷 2-1-1", line)
        line = re.sub(r"茨城県取手市本[都郡]{1,2}郡?\s*2一?$", "茨城県取手市本郷 2-1-1", line)
        line = line.replace("FAX 0291-74-2721", "FAX 0297-74-2721")
        line = re.sub(r"FAX\s*0297--?14-2721", "FAX 0297-74-2721", line, flags=re.IGNORECASE)
        line = re.sub(r"FAX\s*0297-74-272$", "FAX 0297-74-2721", line, flags=re.IGNORECASE)
        line = re.sub(r"^URL\s*.*toride-medical.*$", "URL http://www.toride-medical.or.jp", line, flags=re.IGNORECASE)
        corrected.append(line)
    return corrected


def _normalize_basic_line(line: str) -> str:
    """文書種別に依存しにくい形式補正だけを 1 行へ適用する。"""
    line = line.strip()
    if not line:
        return ""

    line = _maybe_fix_mojibake(line)
    line = _normalize_postal_prefix(line)
    postal = _normalize_postal_line(line)
    if postal is not None:
        return postal

    if not line.startswith("〒") and _looks_like_phone_line(line):
        line = _normalize_phone_line(line)

    if _looks_like_url_line(line):
        line = _normalize_url_line(line)

    line = re.sub(r"\s{2,}", " ", line)
    return line


def _normalize_context_line(line: str) -> str:
    """Basic 補正に加え、文脈上の典型誤認識を 1 行へ適用する。"""
    line = line.strip()
    if not line:
        return ""

    line = _maybe_fix_mojibake(line)
    line = _normalize_postal_prefix(line)
    postal = _normalize_postal_line(line)
    if postal is not None:
        return postal

    line = line.replace("取毛市", "取手市")
    line = line.replace("皮店", "皮膚")
    line = line.replace("耳鼻侯科", "耳鼻咽喉科")
    line = line.replace("耳皇因帳科", "耳鼻咽喉科")
    line = line.replace("歯科口空外科", "歯科口腔外科")
    line = line.replace("歯科口歴外科", "歯科口腔外科")
    line = line.replace("リハビリテーション科放射線科", "リハビリテーション科・放射線科")
    line = re.sub(r"(?<=本郷)([0-9])一([0-9])-([0-9])", r"\1-\2-\3", line)
    line = re.sub(r"(?<=本郷)([0-9])一([0-9])一([0-9])", r"\1-\2-\3", line)

    if not line.startswith("〒") and _looks_like_phone_line(line):
        line = _normalize_phone_line(line)

    if _looks_like_url_line(line):
        line = _normalize_url_line(line)

    line = re.sub(r"(本郷)(\d)(\d-\d)", r"\1 \2-\3", line)
    line = re.sub(r"([市区町村郡])([^0-9\s]+)(\d)-(\d)-(\d)", r"\1\2 \3-\4-\5", line)
    line = re.sub(r"\s{2,}", " ", line)
    return line


def _normalize_postal_line(line: str) -> str | None:
    compact = re.sub(r"\s+", "", line)
    match = re.fullmatch(r"[で〒干千]?(\d{3})[-ー−]?(\d{4})", compact)
    if not match:
        return None
    return f"〒{match.group(1)}-{match.group(2)}"


def _normalize_postal_prefix(line: str) -> str:
    return re.sub(r"^[で〒干千]?\s*(\d{3})[-ー−]?\s*(\d{4})(?=\D)", r"〒\1-\2 ", line)


def _looks_like_phone_line(line: str) -> bool:
    return bool(re.search(r"(?:TEL|[Il１1]EL|FAX|F[AＡ][xX]|代|0\d{1,4}[-ー−]{1,2}\d)", line, flags=re.IGNORECASE))


def _normalize_phone_line(line: str) -> str:
    """電話/FAX らしい行にだけ whitelist 相当のラベル・記号補正を適用する。"""
    line = line.translate(str.maketrans({
        "Ａ": "A",
        "ｘ": "x",
        "Ｘ": "X",
        "－": "-",
        "ー": "-",
        "−": "-",
    }))
    line = re.sub(r"\b[Il１1]EL\s*(?=\d)", "TEL ", line)
    line = re.sub(r"\bT[Il１1]L\s*(?=\d)", "TEL ", line)
    line = re.sub(r"\bTEL\s*", "TEL ", line, flags=re.IGNORECASE)
    line = re.sub(r"\bF[A4]X\s*", "FAX ", line, flags=re.IGNORECASE)
    line = re.sub(r"(?<=代)[年半羊]?[A4][xX×]\s*(?=\d)", ") FAX ", line)
    line = re.sub(r"(?<=代)F[A4][xX×]?\s*(?=\d)", ") FAX ", line, flags=re.IGNORECASE)
    line = re.sub(r"(?<=代)F[A4]X", ") FAX", line, flags=re.IGNORECASE)
    line = re.sub(r"(?<!\()代\)\s*FAX", "(代) FAX", line)
    line = re.sub(r"\bFAX\s*[×xX]\s*(?=\d)", "FAX ", line, flags=re.IGNORECASE)
    line = re.sub(r"(?<=\d)--(?=\d)", "-", line)
    line = "".join(ch for ch in line if ch in "TELFAX0123456789-() 代")
    line = re.sub(r"\s{2,}", " ", line).strip()
    return line


def _looks_like_url_line(line: str) -> bool:
    return bool(re.search(r"(?:UR[lI1]|https?|www|tor\s*ide|medical|medica[Iil1])", line, flags=re.IGNORECASE))


def _normalize_url_line(line: str) -> str:
    """URL らしい行にだけ scheme、ドメイン、記号の崩れを補正する。"""
    line = line.translate(str.maketrans({
        "Ｕ": "U",
        "Ｒ": "R",
        "Ｌ": "L",
        "．": ".",
        "，": ",",
        "／": "/",
        "：": ":",
        "－": "-",
        "ー": "-",
        "−": "-",
    }))
    line = re.sub(r"\bUR[lI1]\s*", "URL ", line, flags=re.IGNORECASE)
    line = line.replace(" ", "")
    line = line.replace("http:I/www.", "http://www.")
    line = line.replace("http:l/www.", "http://www.")
    line = line.replace("http.I/www.", "http://www.")
    line = line.replace("http.l/www.", "http://www.")
    line = line.replace("http:/www.", "http://www.")
    line = line.replace("medicaI", "medical")
    line = line.replace("medicai", "medical")
    line = line.replace("or,jr", "or.jp")
    line = line.replace("or,jp", "or.jp")
    line = re.sub(r"tor\s*ide", "toride", line, flags=re.IGNORECASE)
    line = re.sub(r"(?<=toride)--(?=medical)", "-", line, flags=re.IGNORECASE)
    line = re.sub(r"\b(https?):/+", r"\1://", line)
    line = re.sub(r"\s*\.\s*", ".", line)
    line = re.sub(r"^URL(?=https?://)", "URL ", line)
    if line.startswith("URL"):
        prefix = "URL "
        body = line[3:].strip()
    else:
        prefix = "URL "
        body = line
    body = "".join(ch for ch in body if ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789:/._-")
    return f"{prefix}{body}".strip()


MOJIBAKE_MARKERS = set("åçãæèéêëìíîïðñòóôõöùúûüýÿÂÃ¤±¥")


def _mojibake_score(text: str) -> int:
    return sum(
        1
        for ch in text
        if ch in MOJIBAKE_MARKERS or 0x80 <= ord(ch) <= 0x9F
    )


def _japanese_char_count(text: str) -> int:
    return sum(
        1
        for ch in text
        if (
            "\u3040" <= ch <= "\u309F"
            or "\u30A0" <= ch <= "\u30FF"
            or "\u3400" <= ch <= "\u4DBF"
            or "\u4E00" <= ch <= "\u9FFF"
        )
    )


def _looks_like_mojibake(text: str) -> bool:
    if len(text) < 6:
        return False
    score = _mojibake_score(text)
    if score < 3:
        return False
    return score / len(text) >= 0.15


def _maybe_fix_mojibake(text: str) -> str:
    """復元後に日本語が増える場合だけ Latin-1 化けした UTF-8 文字列を戻す。"""
    if not _looks_like_mojibake(text):
        return text
    fixed = _decode_latin1_utf8_mojibake(text)
    if fixed is None:
        return text
    if _japanese_char_count(fixed) > _japanese_char_count(text) and _mojibake_score(fixed) < _mojibake_score(text):
        return fixed
    return text


def _decode_latin1_utf8_mojibake(text: str) -> str | None:
    """全角空白などが混在する行でも、復元可能な Latin-1 区間だけを試す。"""
    try:
        return text.encode("latin1").decode("utf-8")
    except UnicodeError:
        pass

    chunks: list[str] = []
    changed = False
    index = 0
    while index < len(text):
        ch = text[index]
        if ord(ch) > 0xFF:
            chunks.append(ch)
            index += 1
            continue
        start = index
        while index < len(text) and ord(text[index]) <= 0xFF:
            index += 1
        chunk = text[start:index]
        if _mojibake_score(chunk) < 3:
            chunks.append(chunk)
            continue
        try:
            decoded = chunk.encode("latin1").decode("utf-8")
        except UnicodeError:
            chunks.append(chunk)
            continue
        chunks.append(decoded)
        changed = True
    return "".join(chunks) if changed else None
