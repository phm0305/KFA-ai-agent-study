"""KFA AI agent study: shared collection toolkit (2nd session template).

Every source, whatever its collection level (1 API, 2 library, 3 file,
4 crawling, 5 manual), ends in the same record table via finalize().
Member-facing messages are Korean on purpose; identifiers stay English.
"""

import io
import json
import math
import numbers
import os
import re
import urllib.robotparser
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests

COLUMNS = [
    "종목코드", "종목명", "항목", "값", "단위", "기준", "기준일", "공시일",
    "출처", "출처 URL", "신뢰도", "수집 방법", "수집 시각", "상태", "비고",
]
REQUIRED = [
    "항목", "값", "단위", "기준", "기준일", "공시일",
    "출처", "출처 URL", "신뢰도", "수집 방법", "수집 시각",
]
NOT_APPLICABLE = "해당 없음"
NA_ALLOWED = {"종목코드", "종목명", "기준", "공시일"}
RELIABILITY = ("상", "중", "하")
LEVELS = {1: "공식 API", 2: "파이썬 라이브러리", 3: "파일 다운로드", 4: "크롤링", 5: "수동 입력"}
PASSED, REVIEW = "형식 통과", "확인 필요"
SAME_AS_DATE = "same_as_date"
CHECKED_MARKS = {"o", "y", "yes", "✅", "확인"}
NULL_TOKENS = {"", "-", ".", "\u2014", "n/a", "na", "nan", "none", "null"}
KST = timezone(timedelta(hours=9))
USER_AGENT = "KFA-AI-agent-study/0.2 (+https://github.com/phm0305/KFA-ai-agent-study)"


class CollectError(Exception):
    """Shown to members verbatim, so it must never contain keys or full URLs."""


class SkipStep(Exception):
    pass


def now_kst():
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M")


def is_blank(value):
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def to_number(value):
    if is_blank(value):
        return None, None
    if isinstance(value, bool):
        return None, f"숫자로 못 바꿈: '{value}'"
    if isinstance(value, numbers.Integral):
        return int(value), None
    if isinstance(value, numbers.Real):
        return (float(value), None) if math.isfinite(value) else (None, None)
    text = str(value).strip()
    if text.lower() in NULL_TOKENS:
        return None, None
    cleaned = text.replace(",", "").replace(" ", "").rstrip("%")
    negative = False
    if cleaned.startswith("(") and cleaned.endswith(")"):
        negative, cleaned = True, cleaned[1:-1]
    elif cleaned.startswith("△"):
        negative, cleaned = True, cleaned[1:]
    if re.fullmatch(r"[+-]?\d+", cleaned):
        number = int(cleaned)
    else:
        try:
            number = float(cleaned)
        except ValueError:
            return None, f"숫자로 못 바꿈: '{text}'"
        if not math.isfinite(number):
            return None, f"숫자로 못 바꿈: '{text}'"
    return (-number if negative else number), None


_DAY = re.compile(r"(\d{4})\s*[-./년]\s*(\d{1,2})\s*[-./월]\s*(\d{1,2})\s*일?\.?")
_COMPACT_DAY = re.compile(r"(\d{4})(\d{2})(\d{2})")
_MONTH = re.compile(r"(\d{4})\s*[-./년]\s*(\d{1,2})\s*월?\.?")
_COMPACT_MONTH = re.compile(r"(\d{4})(\d{2})")
_QUARTER = re.compile(r"(\d{4})\s*-?\s*Q([1-4])", re.IGNORECASE)
_YEAR = re.compile(r"(\d{4})\s*년?")
_TIME_SUFFIX = re.compile(r"[ T]\d{1,2}:\d{2}(:\d{2})?(\.\d+)?$")


def to_date(value):
    """Normalize to YYYY-MM-DD, YYYY-MM, YYYYQn or YYYY; anything else is a problem."""
    if is_blank(value):
        return None, None
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.strftime("%Y-%m-%d"), None
    text = _TIME_SUFFIX.sub("", str(value).strip())
    for pattern in (_DAY, _COMPACT_DAY):
        match = pattern.fullmatch(text)
        if match:
            try:
                return date(*map(int, match.groups())).isoformat(), None
            except ValueError:
                return None, f"없는 날짜: '{value}'"
    for pattern in (_MONTH, _COMPACT_MONTH):
        match = pattern.fullmatch(text)
        if match:
            year, month = map(int, match.groups())
            if 1 <= month <= 12:
                return f"{year:04d}-{month:02d}", None
            return None, f"없는 날짜: '{value}'"
    match = _QUARTER.fullmatch(text)
    if match:
        return f"{match.group(1)}Q{match.group(2)}", None
    match = _YEAR.fullmatch(text)
    if match:
        return match.group(1), None
    return None, f"날짜 모양을 모름: '{value}'"


def find_col(table, keyword):
    for col in table.columns:
        if keyword in str(col):
            return col
    raise CollectError(f"'{keyword}'가 들어간 칸이 없어요. 지금 표의 칸: {[str(c) for c in table.columns]}")


def long_from_table(table, items, date_col=None, keep=None):
    """Wide table (one column per item) -> one row per number.

    items: {raw column: (항목 이름, 단위)}. keep: {raw column: our column} copied per row.
    """
    if date_col is None:
        if isinstance(table.index, pd.RangeIndex):
            raise CollectError("날짜가 들어 있는 칸 이름을 date_col로 알려 주세요")
        table = table.reset_index()
        date_col = table.columns[0]
    keep = keep or {}
    missing = [c for c in [*items, date_col, *keep] if c not in table.columns]
    if missing:
        raise CollectError(f"표에 없는 칸: {missing}. 지금 표의 칸: {[str(c) for c in table.columns]}")
    parts = []
    for raw_col, (label, unit) in items.items():
        part = pd.DataFrame({
            "항목": label,
            "값": pd.Series(table[raw_col].tolist(), dtype=object),
            "단위": unit,
            "기준일": pd.Series(table[date_col].tolist(), dtype=object),
        })
        for raw, ours in keep.items():
            part[ours] = table[raw].tolist()
        parts.append(part)
    if not parts:
        raise CollectError("items가 비어 있어요. 어떤 칸을 숫자로 가져올지 적어 주세요")
    return pd.concat(parts, ignore_index=True)


def finalize(table, *, level, source=None, source_url=None, reliability=None, basis=None,
             disclosed=None, base_date=None, stock_code=None, stock_name=None, unit=None, note=None):
    """Turn any table with at least 항목/값 into the shared record table.

    A cell already in the table wins over the keyword default. disclosed may be a
    date, NOT_APPLICABLE, or SAME_AS_DATE (copy 기준일, for prices and rates).
    """
    if level not in LEVELS:
        raise ValueError(f"level must be one of {list(LEVELS)}")
    defaults = {
        "종목코드": stock_code, "종목명": stock_name, "단위": unit, "기준": basis,
        "기준일": base_date, "출처": source, "출처 URL": source_url, "신뢰도": reliability,
    }
    collected_at = now_kst()
    method = f"{level} {LEVELS[level]}"
    out = []
    for raw in table.to_dict("records"):
        row = {col: raw.get(col) for col in COLUMNS}
        for col, default in defaults.items():
            if is_blank(row[col]) and default is not None:
                row[col] = default
        notes = [n for n in (raw.get("비고"), note) if not is_blank(n)]
        reasons = []

        if is_blank(row["공시일"]):
            if disclosed == SAME_AS_DATE:
                row["공시일"] = row["기준일"]
                notes.append("공시일은 기준일과 같다고 봄")
            elif disclosed is not None:
                row["공시일"] = disclosed
        row["수집 방법"] = method
        if is_blank(row["수집 시각"]):
            row["수집 시각"] = collected_at

        value, value_problem = to_number(row["값"])
        if value_problem:
            reasons.append(value_problem)
        else:
            row["값"] = value

        for col in ("기준일", "공시일"):
            if is_blank(row[col]) or row[col] == NOT_APPLICABLE:
                continue
            normalized, problem = to_date(row[col])
            if problem:
                reasons.append(f"{col} {problem}")
            else:
                row[col] = normalized

        for col in REQUIRED:
            if is_blank(row[col]) and not (col == "값" and value_problem):
                reasons.append(f"{col} 비어 있음")
        for col in COLUMNS:
            if row[col] == NOT_APPLICABLE and col not in NA_ALLOWED:
                reasons.append(f"{col}에는 '{NOT_APPLICABLE}'을 쓸 수 없음")

        base, disc = str(row["기준일"] or ""), str(row["공시일"] or "")
        if re.fullmatch(r"\d{4}-\d{2}(-\d{2})?", base) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", disc):
            if disc[:len(base)] < base:
                reasons.append("공시일이 기준일보다 빠름")
        if not is_blank(row["신뢰도"]) and row["신뢰도"] not in RELIABILITY:
            reasons.append("신뢰도는 상/중/하 중 하나")

        checked = str(raw.get("확인") or "").strip().lower() in CHECKED_MARKS
        if level == 4 and not checked:
            reasons.append("크롤링 값: 원문 화면과 한 번 대조")
        if level == 5 and not checked:
            reasons.append("손으로 옮긴 값: 원문과 대조")

        row["상태"] = REVIEW if reasons else PASSED
        row["비고"] = "; ".join([*dict.fromkeys(notes), *(f"⚠ {r}" for r in reasons)])
        out.append(row)

    records = pd.DataFrame(out, columns=COLUMNS)
    records["값"] = pd.Series([r["값"] for r in out], dtype=object)
    return records


def collect_table(table, items=None, date_col=None, keep=None, **meta):
    """Single exit for every level: raw table in, record table out.

    Without items, the table must already have 항목/값 columns (typical for manual CSVs).
    """
    if not isinstance(table, pd.DataFrame):
        raise CollectError(f"표(DataFrame)가 아니라 {type(table).__name__}가 들어왔어요")
    if items is not None:
        table = long_from_table(table, items, date_col, keep)
    elif not {"항목", "값"} <= set(table.columns):
        raise CollectError(f"items 없이 쓰려면 '항목'과 '값' 칸이 있어야 해요. 지금 칸: {[str(c) for c in table.columns]}")
    return finalize(table, **meta)


def review_reasons(records):
    reasons = Counter()
    for note in records.loc[records["상태"] == REVIEW, "비고"].fillna(""):
        for part in note.split("; "):
            if part.startswith("⚠ "):
                reasons[re.sub(r"'.*'", "'…'", part[2:])] += 1
    return reasons


def check_records(records, show=True):
    problems = []
    if not isinstance(records, pd.DataFrame):
        problems.append(f"표(DataFrame)가 아니에요: {type(records).__name__}")
    elif list(records.columns) != COLUMNS:
        missing = [c for c in COLUMNS if c not in records.columns]
        extra = [c for c in records.columns if c not in COLUMNS]
        problems.append(f"칸 이름·순서가 달라요 (빠진 칸 {missing}, 남는 칸 {extra})")
    else:
        bad_state = ~records["상태"].isin([PASSED, REVIEW])
        if bad_state.any():
            problems.append(f"상태 칸에 '{PASSED}'/'{REVIEW}' 말고 다른 값이 {int(bad_state.sum())}줄")
        blank = records[REQUIRED].apply(lambda col: col.map(is_blank)).any(axis=1)
        hidden = blank & (records["상태"] == PASSED)
        if hidden.any():
            problems.append(f"필수 칸이 비었는데 '{PASSED}'인 줄이 {int(hidden.sum())}개 (finalize를 거치지 않은 듯)")
    if show:
        if problems:
            for p in problems:
                print("❌", p)
        else:
            passed = int((records["상태"] == PASSED).sum())
            print(f"✅ 칸 모양 OK: {len(records)}줄 (형식 통과 {passed} · 확인 필요 {len(records) - passed})")
            for reason, count in review_reasons(records).most_common(5):
                print(f"   ⚠ {reason}: {count}줄")
    return not problems


def save_records(records, stem="records"):
    all_path, review_path = f"{stem}.csv", f"{stem}_확인필요.csv"
    records.to_csv(all_path, index=False, encoding="utf-8-sig")
    records[records["상태"] == REVIEW].to_csv(review_path, index=False, encoding="utf-8-sig")
    return all_path, review_path


STEP_RESULTS = []


def run_step(label, level, func):
    """Run one source without ever stopping 'Run all'; errors become a summary row."""
    entry = {"단계": f"{level} {LEVELS[level]}", "예시": label, "결과": "❌", "줄 수": 0, "확인 필요": 0, "메모": ""}
    STEP_RESULTS[:] = [e for e in STEP_RESULTS if e["예시"] != label]
    STEP_RESULTS.append(entry)
    try:
        records = func()
    except SkipStep as e:
        entry.update(결과="⏭", 메모=str(e))
        print(f"⏭ {label}: {e}")
        return None
    except CollectError as e:
        entry["메모"] = str(e)
        print(f"❌ {label}: {e}")
        return None
    except requests.RequestException as e:
        entry["메모"] = f"인터넷 연결 문제로 못 받아왔어요 ({type(e).__name__}). 잠시 뒤 이 셀만 다시 실행해 주세요"
        print(f"❌ {label}: {entry['메모']}")
        return None
    except Exception as e:
        entry["메모"] = f"예상 못 한 오류 ({type(e).__name__}). 셀을 다시 실행해 보고, 그래도 안 되면 조 톡방에 공유"
        print(f"❌ {label}: {entry['메모']}")
        return None
    if not check_records(records, show=False):
        entry["메모"] = "공통 표 모양이 아니에요. check_records(결과)로 무엇이 다른지 확인"
        check_records(records)
        return None
    review = int((records["상태"] == REVIEW).sum())
    entry.update(결과="✅", **{"줄 수": len(records), "확인 필요": review})
    print(f"✅ {label}: {len(records)}줄 (확인 필요 {review}줄)")
    return records


def step_summary():
    return pd.DataFrame(STEP_RESULTS, columns=["단계", "예시", "결과", "줄 수", "확인 필요", "메모"])


def http_get(url, params=None, timeout=30):
    host = urlparse(url).netloc
    try:
        resp = requests.get(url, params=params, timeout=timeout, headers={"User-Agent": USER_AGENT})
    except requests.Timeout:
        raise CollectError(f"{host} 응답이 {timeout}초 넘게 없어요. 잠시 뒤 다시 실행해 주세요") from None
    except requests.RequestException:
        raise CollectError(f"{host}에 연결하지 못했어요. 인터넷이나 사이트 상태를 확인해 주세요") from None
    if resp.status_code != 200:
        hint = {401: "키나 로그인이 필요해요", 403: "사이트가 접근을 막았어요", 404: "주소가 바뀌었을 수 있어요",
                429: "요청이 너무 잦아요. 1분 뒤 다시"}.get(resp.status_code, "")
        raise CollectError(f"{host}가 {resp.status_code} 응답을 줬어요. {hint}".strip())
    return resp


def read_json_table(url, rows_path, params=None):
    """Fetch JSON and return the list found at a dotted path (e.g. 'StatisticSearch.row') as a table."""
    try:
        data = http_get(url, params).json()
    except ValueError:
        raise CollectError("응답이 JSON이 아니에요. 주소의 형식(json/xml) 부분을 확인해 주세요") from None
    current = data
    for key in rows_path.split("."):
        if isinstance(current, dict) and key in current:
            current = current[key]
            continue
        here = list(current) if isinstance(current, dict) else type(current).__name__
        preview = json.dumps(data, ensure_ascii=False)[:200]
        raise CollectError(f"응답에서 '{key}'를 못 찾았어요. 그 자리에 있는 것: {here} / 응답 앞부분: {preview}")
    rows = [current] if isinstance(current, dict) else current
    if not isinstance(rows, list) or not rows:
        raise CollectError(f"'{rows_path}' 아래가 비어 있어요")
    return pd.json_normalize(rows)


DART_URL = "https://opendart.fss.or.kr/api"
DART_REPORT = {1: "11013", 2: "11012", 3: "11014", 4: "11011"}
QUARTER_END = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}
DART_ERRORS = {
    "010": "등록되지 않은 키예요. Secrets의 키 값을 확인해 주세요",
    "011": "사용할 수 없는 키예요",
    "013": "조회된 데이터가 없어요. 아직 공시 전인 분기인지 확인해 주세요",
    "020": "오늘 요청 한도를 넘었어요. 내일 다시 해 주세요",
    "100": "요청 값이 잘못됐어요 (연도·분기·연결/별도)",
    "800": "DART 시스템 점검 중이에요",
}
DART_ITEMS = {
    "ifrs-full_Revenue": ("매출액", True),
    "dart_OperatingIncomeLoss": ("영업이익", True),
    "ifrs-full_ProfitLoss": ("당기순이익", True),
    "ifrs-full_Assets": ("자산총계", False),
    "ifrs-full_Liabilities": ("부채총계", False),
    "ifrs-full_Equity": ("자본총계", False),
}
_DART_CORPS = {}


def _dart_status(data):
    status = data.get("status")
    if status != "000":
        raise CollectError(f"DART {status}: {DART_ERRORS.get(status, data.get('message', '알 수 없는 응답'))}")


def dart_corp(stock_code, api_key):
    if not _DART_CORPS:
        resp = http_get(f"{DART_URL}/corpCode.xml", {"crtfc_key": api_key})
        try:
            xml_bytes = zipfile.ZipFile(io.BytesIO(resp.content)).read("CORPCODE.xml")
        except zipfile.BadZipFile:
            try:
                _dart_status(resp.json())
            except ValueError:
                pass
            raise CollectError("DART 회사 번호표를 받지 못했어요. 키를 확인해 주세요") from None
        for item in ET.fromstring(xml_bytes).iter("list"):
            code = (item.findtext("stock_code") or "").strip()
            if code:
                _DART_CORPS[code] = (item.findtext("corp_code"), item.findtext("corp_name"))
    if stock_code not in _DART_CORPS:
        raise CollectError(f"{stock_code}: 상장사 목록에 없어요. 종목코드 6자리를 확인해 주세요")
    return _DART_CORPS[stock_code]


def dart_rows_to_long(rows, year, quarter):
    """Pick six accounts by standard account_id; flows get 3-month and cumulative rows."""
    base_note = "기준일은 12월 결산 가정"
    out, seen = [], set()
    for row in rows:
        account = row.get("account_id")
        if account not in DART_ITEMS or account in seen:
            continue
        name, is_flow = DART_ITEMS[account]
        if is_flow and row.get("sj_div") not in ("IS", "CIS"):
            continue
        seen.add(account)
        rcept_no = row.get("rcept_no", "")
        common = {
            "단위": "원", "기준일": f"{year}-{QUARTER_END[quarter]}",
            "공시일": rcept_no[:8], "출처 URL": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}",
        }
        if not is_flow:
            parts = [(name, row.get("thstrm_amount"), base_note)]
        elif quarter == 4:
            parts = [(f"{name}(연간)", row.get("thstrm_amount"), base_note + "; 4분기 3개월치 = 연간 - 3분기 누적")]
        elif quarter == 1:
            parts = [(f"{name}(3개월)", row.get("thstrm_amount"), base_note + "; 1분기는 3개월 = 누적")]
        else:
            parts = [(f"{name}(3개월)", row.get("thstrm_amount"), base_note),
                     (f"{name}(누적)", row.get("thstrm_add_amount"), base_note)]
        for label, amount, memo in parts:
            out.append({**common, "항목": label, "값": amount, "비고": memo})
    for account, (name, _) in DART_ITEMS.items():
        if account not in seen:
            out.append({"항목": name, "값": None, "단위": "원", "기준일": f"{year}-{QUARTER_END[quarter]}",
                        "비고": f"이 회사 공시에서 표준 계정({account})을 못 찾음"})
    return pd.DataFrame(out)


def collect_dart(stock_code, year, quarter, fs_div, api_key):
    if not api_key:
        raise SkipStep("DART 키가 없어요 (Secrets에 DART_API_KEY 등록 후 다시)")
    if quarter not in DART_REPORT or fs_div not in ("CFS", "OFS"):
        raise CollectError("QUARTER는 1~4, FS_DIV는 'CFS'(연결) 또는 'OFS'(별도)")
    corp_code, corp_name = dart_corp(stock_code, api_key)
    data = http_get(f"{DART_URL}/fnlttSinglAcntAll.json", {
        "crtfc_key": api_key, "corp_code": corp_code, "bsns_year": str(year),
        "reprt_code": DART_REPORT[quarter], "fs_div": fs_div,
    }).json()
    _dart_status(data)
    return collect_table(
        dart_rows_to_long(data["list"], year, quarter),
        level=1, source="DART 단일회사 전체 재무제표 API", reliability="상",
        basis="연결" if fs_div == "CFS" else "별도", stock_code=stock_code, stock_name=corp_name,
        source_url="https://opendart.fss.or.kr",
    )


def collect_ecos(api_key, stat_code, cycle, start, end, item_code, label, unit):
    if not api_key:
        raise SkipStep("ECOS 키가 없어요 (선택 사항: ecos.bok.or.kr에서 무료 발급 후 Secrets에 ECOS_API_KEY)")
    url = f"https://ecos.bok.or.kr/api/StatisticSearch/{api_key}/json/kr/1/1000/{stat_code}/{cycle}/{start}/{end}/{item_code}"
    try:
        data = http_get(url).json()
    except ValueError:
        raise CollectError("ECOS 응답이 JSON이 아니에요") from None
    if "RESULT" in data:
        raise CollectError(f"ECOS: {data['RESULT'].get('MESSAGE', data['RESULT'])}")
    table = pd.json_normalize(data["StatisticSearch"]["row"])
    return collect_table(
        table, {"DATA_VALUE": (label, unit)}, date_col="TIME",
        level=1, source="한국은행 ECOS Open API", reliability="상", basis=NOT_APPLICABLE,
        source_url=f"https://ecos.bok.or.kr/#/SearchStat?statCode={stat_code}",
    )


def read_table(source, sheet_name=0, skiprows=None):
    """CSV/Excel from a URL or a path. Handles cp949 CSVs and HTML disguised as .xls."""
    if str(source).startswith(("http://", "https://")):
        content, name = http_get(str(source)).content, urlparse(str(source)).path.lower()
    else:
        path = Path(source)
        if not path.exists():
            raise CollectError(f"파일이 없어요: {path.name}. 경로와 파일 이름(띄어쓰기·확장자)을 확인해 주세요")
        content, name = path.read_bytes(), path.name.lower()
    if content.lstrip()[:1] == b"<":
        try:
            return pd.read_html(io.StringIO(content.decode("utf-8", errors="replace")))[0]
        except ValueError:
            raise CollectError("파일 안이 표가 아닌 웹페이지예요. 받은 파일을 열어 확인해 주세요") from None
    if name.endswith((".xlsx", ".xlsm", ".xls")):
        try:
            return pd.read_excel(io.BytesIO(content), sheet_name=sheet_name, skiprows=skiprows)
        except ImportError:
            raise CollectError("이 엑셀 형식을 읽는 도구가 없어요. 엑셀에서 .xlsx로 다시 저장해 주세요") from None
    for encoding in ("utf-8-sig", "cp949"):
        try:
            return pd.read_csv(io.BytesIO(content), encoding=encoding, skiprows=skiprows)
        except UnicodeDecodeError:
            continue
    raise CollectError("CSV 글자를 못 읽었어요 (utf-8, cp949 둘 다 실패). 엑셀에서 'CSV UTF-8'로 다시 저장해 주세요")


def robots_allowed(url):
    """True/False from robots.txt; None when it cannot be read (caller decides)."""
    parts = urlparse(url)
    try:
        resp = requests.get(f"{parts.scheme}://{parts.netloc}/robots.txt", timeout=15,
                            headers={"User-Agent": USER_AGENT})
    except requests.RequestException:
        return None
    if resp.status_code in (401, 403):
        return False
    if resp.status_code >= 400:
        return True
    parser = urllib.robotparser.RobotFileParser()
    parser.parse(resp.text.splitlines())
    return parser.can_fetch(USER_AGENT, url)


def read_html_table(url, match=".+", index=0):
    host = urlparse(url).netloc
    allowed = robots_allowed(url)
    if allowed is False:
        raise SkipStep(f"{host}의 robots.txt가 코드 수집을 막고 있어요. 이 자료는 5단계(수동)로 옮겨 주세요")
    if allowed is None:
        print(f"⚠ {host}의 robots.txt를 확인하지 못했어요. 사이트 이용약관을 직접 확인해 주세요")
    resp = http_get(url)
    if resp.encoding is None or resp.encoding.lower() == "iso-8859-1":
        resp.encoding = resp.apparent_encoding
    try:
        tables = pd.read_html(io.StringIO(resp.text), match=match)
    except ValueError:
        raise CollectError(f"페이지에서 '{match}'가 들어간 표를 못 찾았어요. 표가 자바스크립트로 그려지는 페이지일 수 있어요") from None
    if index >= len(tables):
        raise CollectError(f"표가 {len(tables)}개뿐이에요. index를 0~{len(tables) - 1} 중에서 골라 주세요")
    table = tables[index]
    if isinstance(table.columns, pd.MultiIndex):
        table.columns = [" ".join(dict.fromkeys(str(c) for c in col)) for col in table.columns]
    return table


DRIVE_ROOT = "/content/drive/MyDrive/KFA_자료"
CARD_COLUMNS = ["파일명", "출처", "URL", "기준일", "신뢰도"]


def mount_drive():
    try:
        from google.colab import drive
    except ImportError:
        raise CollectError("구글 드라이브 연결은 Colab에서만 돼요") from None
    drive.mount("/content/drive")
    if not Path(DRIVE_ROOT).exists():
        raise CollectError("내 드라이브 맨 위에 'KFA_자료' 폴더가 없어요 (이름의 밑줄까지 똑같이)")
    return Path(DRIVE_ROOT)


def read_source_cards(source="출처카드"):
    """A CSV path, or (in Colab) the title of a Google Sheet."""
    if str(source).lower().endswith(".csv") or Path(str(source)).exists():
        return read_table(source)
    try:
        from google.colab import auth
    except ImportError:
        raise CollectError("구글 시트는 Colab에서만 읽을 수 있어요. 여기서는 CSV 경로를 주세요") from None
    import gspread
    from google.auth import default
    auth.authenticate_user()
    creds, _ = default()
    try:
        sheet = gspread.authorize(creds).open(source).sheet1
    except gspread.SpreadsheetNotFound:
        raise CollectError(f"'{source}'라는 구글 시트를 못 찾았어요. 시트 이름을 확인해 주세요") from None
    return pd.DataFrame(sheet.get_all_records())


def collect_from_cards(cards, files_dir):
    """Read files listed on the source cards. Only CSV/XLSX already shaped as 항목/값/단위/기준일."""
    missing = [c for c in CARD_COLUMNS if c not in cards.columns]
    if missing:
        raise CollectError(f"출처카드에 없는 칸: {missing}")
    results, skipped = [], []
    for card in cards.to_dict("records"):
        name = str(card["파일명"]).strip()
        path = Path(files_dir) / name
        if not path.exists():
            skipped.append((name, "files/ 폴더에 이 이름의 파일이 없어요"))
            continue
        if path.suffix.lower() not in (".csv", ".xlsx"):
            skipped.append((name, "PDF·글 자료는 4회차에 AI가 읽어요"))
            continue
        table = read_table(path)
        if not {"항목", "값"} <= set(table.columns):
            skipped.append((name, "'항목·값·단위·기준일' 칸 모양이 아니에요. 3단계 예시처럼 items로 바꿔 주세요"))
            continue
        level_match = re.match(r"\s*([1-5])", str(card.get("수집 방법") or ""))
        results.append(collect_table(
            table, level=int(level_match.group(1)) if level_match else 5, source=card["출처"], source_url=card["URL"],
            reliability=card["신뢰도"], base_date=card["기준일"], note=f"출처카드: {name}",
        ))
    for name, why in skipped:
        print(f"   ⏭ {name}: {why}")
    if not results:
        raise SkipStep(f"출처카드 {len(cards)}줄 중 읽을 수 있는 숫자 파일이 없어요")
    return pd.concat(results, ignore_index=True)


def get_key(name):
    """Colab Secrets first, then .env / environment. Never print the value."""
    try:
        from google.colab import userdata
    except ImportError:
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
        return os.getenv(name) or None
    try:
        return userdata.get(name) or None
    except Exception:
        return None
