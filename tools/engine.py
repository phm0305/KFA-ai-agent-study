"""KFA AI agent study: report engine skeleton.

Adds row ids and a numbered source list on top of the shared record table from
collect.py, computes metrics from those rows, and checks the numbers written in
claims against them. Engine columns go on copies only; the 15 shared columns never
change. Member-facing messages are Korean on purpose; identifiers stay English.

[한국어 안내] 이 셀은 고치지 않고 실행만 해요.
    with_ids()        공통 표의 줄마다 이름표(rid)를 붙여요. 같은 사실이 두 줄이면 멈춰요
    build_sources()   출처 목록 [S1] [S2] ...을 만들고, 줄마다 어느 출처인지(source_id) 붙여요
    compute_metrics() 지표 정의 표(METRIC_SPECS)대로 지표 [M1] [M2] ...을 계산해요. 입력 줄이 없으면 값을 비우고 이유를 적어요
    check_claims()    주장에 적은 숫자를 지표나 원본 줄과 대조해서 PASS / FIX / REVIEW로 판정해요
    render_check()    주장 목록·지표 표·숫자 대조 표·출처 목록을 마크다운 파일 하나로 저장해요
    claims_prompt()   Gemini에게 보낼 질문(규칙 + 공통 표 + 지표 표 + 글)을 만들어요
    ask_claims()      Gemini 답을 원문 그대로 저장해요. 질문이 저장된 것과 똑같으면 다시 부르지 않아요
    use_backup()      Gemini가 안 될 때, 질문이 똑같으면 스터디장이 미리 받아 둔 답(backup/)을 써요
    load_claims()     저장된 답을 주장 목록으로 읽어요. 깨진 주장은 REVIEW로 넘겨요
"""

import json
import re
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Literal
from urllib.parse import quote

import pandas as pd

from collect import REVIEW, CollectError, SkipStep, http_get, is_blank, now_kst

RID_PARTS = ["종목코드", "항목", "기준", "기준일", "출처"]
SOURCE_KEY = ["출처", "출처 URL"]
SOURCE_COLUMNS = ["source_id", "출처", "출처 URL", "수집 방법", "신뢰도", "기준일 범위", "줄 수"]
METRIC_COLUMNS = ["metric_id", "지표", "값", "단위", "계산식", "입력 rid", "source_id", "기준일", "상태", "이유"]
CHECK_COLUMNS = ["claim_id", "문장", "근거 id", "적은 숫자", "적은 단위", "실제 값", "판정", "이유", "출처 번호"]
METRIC_BASIS = "연결"
COMPUTED = "계산됨"
PASS, FIX, CHECK = "PASS", "FIX", "REVIEW"
UNITS = {
    "원": ("원", Decimal(1)),
    "천원": ("원", Decimal(10) ** 3),
    "백만원": ("원", Decimal(10) ** 6),
    "억원": ("원", Decimal(10) ** 8),
    "십억원": ("원", Decimal(10) ** 9),
    "조원": ("원", Decimal(10) ** 12),
    "%": ("%", Decimal(1)),
}


@dataclass(frozen=True)
class MetricSpec:
    """growth: inputs = (item,), compared with the same item one year earlier.
    ratio: inputs = (numerator item, denominator item), same date."""
    name: str
    unit: str
    formula: str
    kind: Literal["growth", "ratio"]
    inputs: tuple


METRIC_SPECS = (
    MetricSpec("매출 성장률", "%", "(올해 매출액(연간) − 작년 매출액(연간)) ÷ 작년 매출액(연간) × 100",
               "growth", ("매출액(연간)",)),
    MetricSpec("영업이익률", "%", "영업이익(연간) ÷ 매출액(연간) × 100", "ratio", ("영업이익(연간)", "매출액(연간)")),
    MetricSpec("부채비율", "%", "부채총계 ÷ 자본총계 × 100", "ratio", ("부채총계", "자본총계")),
)


def _text(value):
    return "" if is_blank(value) else str(value)


def _source_order(sid):
    return int(sid[1:])


def _require_tagged(records):
    missing = [col for col in ("rid", "source_id") if col not in records.columns]
    if missing:
        raise CollectError(f"공통 표에 {missing} 칸이 없어요. build_sources(with_ids(표)) 결과를 넣어 주세요")


def with_ids(records):
    """Copy with rid = 종목코드|항목|기준|기준일|출처; a repeated rid is the same fact twice and stops."""
    out = records.copy()
    out["rid"] = ["|".join(_text(v) for v in row) for row in out[RID_PARTS].itertuples(index=False)]
    repeated = out.loc[out["rid"].duplicated(keep=False), "rid"].unique().tolist()
    if repeated:
        raise CollectError(
            f"같은 사실(종목코드|항목|기준|기준일|출처)이 두 줄 이상 있어요: {repeated[:5]}. "
            "같은 자료를 두 번 붙였는지 확인해 주세요")
    return out


def build_sources(records):
    """Return (sources, records copy with source_id).

    One source = one (출처, 출처 URL) pair, so each DART filing keeps its own URL.
    Numbers follow the sorted pairs, not row order, so reordering cells keeps every S#.
    """
    out = records.copy()
    keys = [tuple(_text(v) for v in row) for row in out[SOURCE_KEY].itertuples(index=False)]
    ids = {key: f"S{n}" for n, key in enumerate(sorted(set(keys)), 1)}
    out["source_id"] = [ids[key] for key in keys]
    rows = []
    for (name, url), sid in ids.items():
        part = out[out["source_id"] == sid]
        row = {"source_id": sid, "출처": name, "출처 URL": url, "줄 수": len(part)}
        for col in ("수집 방법", "신뢰도"):
            values = part[col].map(_text).unique().tolist()
            if len(values) > 1:
                raise CollectError(f"[{sid}] {name}: 한 출처인데 {col}이(가) 여러 개예요 {values}. 하나로 맞춰 주세요")
            row[col] = values[0]
        dates = sorted(d for d in part["기준일"].map(_text) if d)
        if dates:
            row["기준일 범위"] = dates[0] if dates[0] == dates[-1] else f"{dates[0]} ~ {dates[-1]}"
        else:
            row["기준일 범위"] = ""
        rows.append(row)
    return pd.DataFrame(rows, columns=SOURCE_COLUMNS), out


def _find_input(records, stock_code, item, base_date):
    """Return (row, None) for exactly one usable consolidated row, else (row or None, reason)."""
    label = f"{item} {base_date}"
    same = records[(records["종목코드"].map(_text) == stock_code) & (records["항목"].map(_text) == item)
                   & (records["기준일"].map(_text) == base_date)]
    rows = same[same["기준"].map(_text) == METRIC_BASIS]
    if rows.empty:
        hint = " (다른 기준 줄만 있음)" if not same.empty else ""
        return None, f"{label}: 연결 줄 없음{hint}"
    if len(rows) > 1:
        return None, f"{label}: 연결 줄이 {len(rows)}개라 하나를 고를 수 없음 ({rows['출처'].tolist()})"
    row = rows.iloc[0]
    if row["상태"] == REVIEW:
        return row, f"{label}: 입력 줄이 확인 필요"
    if is_blank(row["값"]):
        return row, f"{label}: 값 없음"
    return row, None


def compute_metrics(records, specs, stock_code, base_date):
    """One row per spec, M# in spec order. A metric whose inputs are missing, flagged,
    ambiguous or have a denominator <= 0 keeps an empty value with 확인 필요 and the reasons."""
    _require_tagged(records)
    prev_date = f"{int(base_date[:4]) - 1}{base_date[4:]}"
    out = []
    for n, spec in enumerate(specs, 1):
        if spec.kind == "growth":
            wanted = [(spec.inputs[0], base_date), (spec.inputs[0], prev_date)]
        else:
            wanted = [(item, base_date) for item in spec.inputs]
        found, reasons = [], []
        for item, date in wanted:
            row, reason = _find_input(records, stock_code, item, date)
            if row is not None:
                found.append(row)
            if reason:
                reasons.append(reason)
        value = None
        if not reasons:
            first, second = (float(row["값"]) for row in found)
            if second <= 0:
                label = f"{wanted[1][0]} {wanted[1][1]}"
                if spec.kind == "growth":
                    reasons.append(f"기준값 {label}이(가) 0 이하(적자): 흑자전환 / 적자지속 / 적자확대로 표기")
                else:
                    reasons.append(f"분모 {label}이(가) 0 이하라 비율이 의미 없음")
            else:
                value = ((first - second) if spec.kind == "growth" else first) / second * 100
        out.append({
            "metric_id": f"M{n}", "지표": spec.name, "값": value, "단위": spec.unit, "계산식": spec.formula,
            "입력 rid": [row["rid"] for row in found],
            "source_id": sorted({row["source_id"] for row in found}, key=_source_order),
            "기준일": base_date, "상태": REVIEW if reasons else COMPUTED, "이유": "; ".join(reasons),
        })
    metrics = pd.DataFrame(out, columns=METRIC_COLUMNS)
    metrics["값"] = pd.Series([row["값"] for row in out], dtype=object)
    return metrics


def _written_number(number):
    """Exact decimal of the number as written, so '46.80' keeps its two decimals."""
    if isinstance(number, bool):
        return None
    try:
        value = Decimal(str(number).strip().replace(",", ""))
    except InvalidOperation:
        return None
    return value if value.is_finite() else None


def _unit_scales(unit, actual_unit):
    """Return ((written scale, actual scale), None) or (None, reason).

    Identical unit text compares 1:1 whatever the unit is, because the rid or M# already
    fixes what is measured. Blank units are refused, or two blanks would match as equal text.
    """
    written, source = "".join(_text(unit).split()), "".join(_text(actual_unit).split())
    if not written or not source:
        return None, f"단위 없음 (문장 '{_text(unit)}' / 근거 '{_text(actual_unit)}')"
    if written == source:
        return (Decimal(1), Decimal(1)), None
    if written in UNITS and source in UNITS and UNITS[written][0] == UNITS[source][0]:
        return (UNITS[written][1], UNITS[source][1]), None
    return None, (f"단위가 안 맞음: 문장 '{_text(unit)}' / 근거 '{_text(actual_unit)}' "
                  "(단위 글자가 같거나, 원·천원·백만원·억원·십억원·조원끼리만 바꿔 비교)")


def _check_one(number, unit, actual, actual_unit):
    """Return (actual in the written unit or None, verdict, reason)."""
    written = _written_number(number)
    if written is None:
        return None, CHECK, f"적은 숫자 '{number}'를 숫자로 못 읽음"
    scales, problem = _unit_scales(unit, actual_unit)
    if problem:
        return None, CHECK, problem
    scale, actual_scale = scales
    actual_base = Decimal(str(actual)) * actual_scale
    tolerance = Decimal("0.5").scaleb(written.as_tuple().exponent) * scale
    shown = float(actual_base / scale)
    if abs(written * scale - actual_base) <= tolerance:
        return shown, PASS, ""
    return shown, FIX, f"실제 값은 {_format_actual(shown, written, unit)}"


def _format_actual(actual, written, unit):
    """Two more decimals than the written number, so a FIX shows how far off it is."""
    places = max(-written.as_tuple().exponent, 0) + 2
    return f"{actual:,.{places}f} {unit}"


def _lookup(evidence_id, metrics, records):
    """Return (value, unit, source ids, reason the value cannot be used or None)."""
    if not evidence_id:
        return None, None, [], "근거 id가 비어 있음 (표에 뒷받침하는 줄이 없음)"
    if evidence_id.startswith("M"):
        hit = metrics[metrics["metric_id"] == evidence_id]
        if hit.empty:
            return None, None, [], f"지표 {evidence_id}를 못 찾음"
        row = hit.iloc[0]
        if row["상태"] == REVIEW:
            return None, None, list(row["source_id"]), f"근거 지표가 확인 필요: {row['이유']}"
        return row["값"], row["단위"], list(row["source_id"]), None
    hit = records[records["rid"] == evidence_id]
    if hit.empty:
        return None, None, [], "근거 rid를 공통 표에서 못 찾음"
    row = hit.iloc[0]
    if row["상태"] == REVIEW:
        return None, None, [row["source_id"]], "근거 줄이 확인 필요"
    if is_blank(row["값"]):
        return None, None, [row["source_id"]], "근거 줄에 값 없음"
    return row["값"], _text(row["단위"]), [row["source_id"]], None


def check_claims(claims, metrics, records):
    """One row per (claim, evidence). Evidence ids starting with M are metrics, others are rids.

    claims: [{"claim_id": "C-1", "문장": "...", "근거": [(id, number, unit), ...]}].
    The number may be text ("46.80", "1,100") so trailing zeros keep their precision.
    A claim carrying "형식 오류" (set by load_claims) yields one REVIEW row and nothing else.
    출처 번호 collects the S# of every evidence row, or of a metric's input rows.
    """
    _require_tagged(records)
    out = []
    for claim in claims:
        evidence = claim.get("근거") or []
        rows, sources = [], set()
        problem = claim.get("형식 오류")
        if problem or not evidence:
            rows.append({"근거 id": "", "적은 숫자": None, "적은 단위": "", "실제 값": None, "판정": CHECK,
                         "이유": f"AI 답변 형식 오류: {problem}" if problem else "근거 없음"})
            evidence = []
        for evidence_id, number, unit in evidence:
            actual, actual_unit, sids, problem = _lookup(evidence_id, metrics, records)
            sources.update(sids)
            if problem:
                shown, verdict, reason = None, CHECK, problem
            else:
                shown, verdict, reason = _check_one(number, unit, actual, actual_unit)
            rows.append({"근거 id": evidence_id, "적은 숫자": number, "적은 단위": unit, "실제 값": shown,
                         "판정": verdict, "이유": reason})
        label = "".join(f"[{sid}]" for sid in sorted(sources, key=_source_order))
        for row in rows:
            out.append({"claim_id": claim.get("claim_id"), "문장": claim.get("문장"), **row, "출처 번호": label})
    return pd.DataFrame(out, columns=CHECK_COLUMNS)


def _cell(value):
    return _text(value).replace("|", "\\|").replace("\n", " ")


def _table(header, rows):
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(_cell(v) for v in row) + " |" for row in rows]
    return lines


def _claim_number_rows(checked):
    for _, row in checked.iterrows():
        number, unit, actual = row["적은 숫자"], row["적은 단위"], row["실제 값"]
        written = _written_number(number)
        yield [
            f"{row['claim_id']} {row['문장']}",
            "" if is_blank(number) else f"{number} {unit}",
            "" if is_blank(actual) or written is None else _format_actual(actual, written, unit),
            f"{row['판정']}: {row['이유']}" if row["판정"] == CHECK else row["판정"],
        ]


def render_check(checked, metrics, sources, path):
    """Write claims, metrics, number checks and sources as one markdown file; return its path."""
    claims = checked.drop_duplicates("claim_id")
    lines = ["# 숫자 대조 결과", "", "## 주장", ""]
    lines += [f"- {row['claim_id']} {row['문장']} {row['출처 번호']}".rstrip() for _, row in claims.iterrows()]
    lines += ["", "## 지표", ""]
    lines += _table(["번호", "지표", "값", "계산식", "출처", "기준일"], [
        [row["metric_id"], row["지표"],
         f"확인 필요: {row['이유']}" if is_blank(row["값"]) else f"{row['값']:,.2f} {row['단위']}",
         row["계산식"], "".join(f"[{sid}]" for sid in row["source_id"]), row["기준일"]]
        for _, row in metrics.iterrows()])
    lines += ["", "## 숫자 대조", ""]
    lines += _table(["주장", "적은 숫자", "실제 값", "판정"], _claim_number_rows(checked))
    lines += ["", "## 출처", ""]
    lines += _table(["번호", "이름", "기준일 범위", "원본 URL", "신뢰도"], [
        [f"[{row['source_id']}]", row["출처"], row["기준일 범위"], row["출처 URL"], row["신뢰도"]]
        for _, row in sources.iterrows()])
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


BACKUP_URL = "https://raw.githubusercontent.com/phm0305/KFA-ai-agent-study/main/backup/"
RETRY_CODES = (429, 500, 503)
RETRY_WAITS = (5, 10, 20)
CLAIM_RULES = """아래 글에서 숫자가 들어간 주장을 모두 찾아, 각 숫자의 근거를 공통 표나 지표 표에서 골라 줘.

규칙
- 출력은 JSON 배열 하나만: [{"claim_id": "C-1", "문장": "...", "근거": [["근거 id", "숫자", "단위"]]}]
- claim_id는 C-1, C-2 ... 순서대로 붙여
- 문장은 글에 적힌 그대로 옮겨
- 근거 id는 공통 표의 rid나 지표 표의 metric_id(M1 ...)를 글자 그대로 복사해. 표에 없는 id를 만들지 마
- 숫자와 단위는 문장에 적힌 글자 그대로 적어 (예: "97.1", "조 원"). 단위를 바꾸거나 다시 계산하지 마
- 문장 속 숫자마다 근거를 하나씩 적어. 숫자가 가리키는 항목의 줄이나 지표를 골라. 값이 맞는지는 판단하지 마
- 증감, 포인트 차이 같은 변화량은 그 변화량 자체가 표에 있을 때만 고르고, 없으면 근거 id를 ""로 비워 (수준 지표에 변화량을 대지 마)
- 그 밖에는 항목 자체가 표에 없을 때만 근거 id를 ""로 비워
- 숫자가 없는 주장은 "근거": []로 적어"""


def claims_prompt(records, metrics, text):
    """Question text for Gemini: rules, the tables it may cite, then the text to read."""
    rows = records[["rid", "항목", "값", "단위", "기준일"]].to_csv(index=False, lineterminator="\n")
    metric_rows = metrics[["metric_id", "지표", "값", "단위"]].to_csv(index=False, lineterminator="\n")
    return f"{CLAIM_RULES}\n\n[공통 표]\n{rows}\n[지표 표]\n{metric_rows}\n[글]\n{text.strip()}\n"


def _call_gemini(prompt, api_key, model, fallback_model):
    """Return (answer text, model that answered). Same retry rule as setup/00_setup_check.ipynb:
    wait 5/10/20 s on 429/500/503, then try the fallback model once."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(response_mime_type="application/json", temperature=0)

    def ask(name):
        return client.models.generate_content(model=name, contents=prompt, config=config).text or ""

    try:
        for attempt, wait in enumerate((*RETRY_WAITS, None)):
            try:
                return ask(model), model
            except Exception as error:
                if getattr(error, "code", None) not in RETRY_CODES:
                    raise
                if wait is None:
                    break
                print(f"⏳ Gemini가 붐벼요. {wait}초 기다렸다가 다시 시도해요 ({attempt + 1}/{len(RETRY_WAITS)})")
                time.sleep(wait)
        print(f"⏳ 계속 안 돼서 예비 모델({fallback_model})로 한 번 더 시도해요")
        return ask(fallback_model), fallback_model
    except Exception as error:
        raise CollectError(_gemini_failure(getattr(error, "code", None), type(error).__name__)) from None


def _gemini_failure(code, error_name):
    """Member-facing reason a Gemini call failed. Only server-side trouble says 'try later';
    a key or model problem names what to fix instead."""
    if code in (400, 401, 403):
        return f"Gemini가 키를 받아 주지 않았어요 ({code}). Secrets의 GEMINI_API_KEY 값을 다시 확인해 주세요 (SETUP.md 9번)"
    if code == 404:
        return "Gemini 모델 이름을 찾을 수 없어요 (404). 스터디장에게 알려 주세요"
    if code in RETRY_CODES:
        return f"Gemini 서버가 계속 붐비거나 오류가 나요 ({code}). 내 설정 문제가 아니에요. 잠시 뒤 다시 실행해 주세요"
    return f"Gemini를 부르지 못했어요 ({code or error_name}). 인터넷 연결을 확인하고 잠시 뒤 다시 실행해 주세요"


def _record_path(path):
    return path.with_name(f"{path.stem}_기록.json")


def ask_claims(prompt, api_key, path, model, fallback_model, overwrite=False):
    """Save Gemini's raw answer at path and a record (question, model, time) beside it; return path.

    The saved answer is reused only when the saved question is identical to this one,
    so editing the text never checks an old answer. The record is removed before the
    answer is rewritten, so a record on disk always belongs to the answer next to it.
    """
    path = Path(path)
    record_path = _record_path(path)
    if not overwrite and path.exists() and record_path.exists():
        try:
            saved = json.loads(record_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            saved = {}
        if saved.get("질문") == prompt:
            print(f"♻ 같은 질문의 저장된 답을 다시 써요 ({saved.get('모델')}, {saved.get('호출 시각')})")
            return path
    if not api_key:
        raise SkipStep("Gemini 키가 없어요. Secrets에 GEMINI_API_KEY를 등록하고 노트북 액세스를 켠 뒤 다시 실행해 주세요 (SETUP.md 9번)")
    answer, used_model = _call_gemini(prompt, api_key, model, fallback_model)
    path.parent.mkdir(parents=True, exist_ok=True)
    record_path.unlink(missing_ok=True)
    path.write_text(answer, encoding="utf-8")
    record = {"질문": prompt, "모델": used_model, "호출 시각": now_kst()}
    record_path.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✅ Gemini 답 저장: {path} ({used_model})")
    return path


def use_backup(prompt, path, name):
    """Fall back to the answer the study lead saved in backup/<name>.txt when Gemini fails.

    Used only when the backup's question is identical to this one, so a member who changed
    the text or the company never gets an answer to a different question. Returns path or None.
    """
    path = Path(path)
    try:
        record = json.loads(http_get(BACKUP_URL + quote(f"{name}_기록.json")).content.decode("utf-8"))
        if record.get("질문") != prompt:
            print("⏭ 미리 받아 둔 답은 기본 글·기본 종목용이라 지금 질문에는 쓸 수 없어요. 위 ⚠ 줄대로 고친 뒤 다시 실행해 주세요")
            return None
        answer = http_get(BACKUP_URL + quote(f"{name}.txt")).content.decode("utf-8")
    except (CollectError, json.JSONDecodeError):
        print("⏭ 미리 받아 둔 답이 없어요. 위 ⚠ 줄대로 고친 뒤 다시 실행해 주세요")
        return None
    record_path = _record_path(path)
    record_path.unlink(missing_ok=True)
    path.write_text(answer, encoding="utf-8")
    record_path.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"🗂 Gemini 호출이 안 돼서 스터디장이 미리 받아 둔 답을 썼어요 ({record.get('모델')}, {record.get('호출 시각')})")
    return path


def _salvage(text):
    """Split a broken answer into claim objects; a piece that does not parse stays a string.
    Claims hold no nested objects, so every '{' starts a new claim."""
    decoder, items = json.JSONDecoder(), []
    start = text.find("{")
    while start != -1:
        try:
            item, end = decoder.raw_decode(text, start)
        except json.JSONDecodeError:
            end = text.find("{", start + 1)
            items.append(text[start:end if end != -1 else len(text)])
            start = end
            continue
        items.append(item)
        start = text.find("{", end)
    return items


def _claim_from_answer(item, n, seen):
    if not isinstance(item, dict):
        found = re.search(r'"claim_id"\s*:\s*"([^"]+)"', item) if isinstance(item, str) else None
        claim_id = found.group(1) if found and found.group(1) not in seen else f"AI-{n}"
        seen.add(claim_id)
        return {"claim_id": claim_id, "문장": "", "근거": [],
                "형식 오류": f"JSON이 깨짐: {_text(item).strip()[:80]}"}
    problems = []
    claim_id = item.get("claim_id")
    if not isinstance(claim_id, str) or not claim_id.strip():
        problems.append("claim_id 없음")
        claim_id = f"AI-{n}"
    elif claim_id in seen:
        problems.append(f"claim_id {claim_id} 중복")
        claim_id = f"{claim_id} (AI-{n})"
    seen.add(claim_id)
    sentence = item.get("문장")
    if not isinstance(sentence, str):
        problems.append("문장 없음")
    evidence = item.get("근거")
    if not isinstance(evidence, list) or any(not isinstance(ev, list) or len(ev) != 3 for ev in evidence):
        problems.append("근거는 [근거 id, 숫자, 단위] 목록이어야 함")
        evidence = []
    claim = {"claim_id": claim_id, "문장": _text(sentence),
             "근거": [(_text(ev_id).strip(), number, _text(unit)) for ev_id, number, unit in evidence]}
    if problems:
        claim["형식 오류"] = "; ".join(problems)
    return claim


def load_claims(path):
    """Read a saved Gemini answer into check_claims input. Never raises on a bad answer:
    each claim that cannot be read becomes a claim carrying "형식 오류"."""
    text = Path(path).read_text(encoding="utf-8")
    body = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", text)
    try:
        items = json.loads(body)
        items = items if isinstance(items, list) else [items]
    except json.JSONDecodeError:
        items = _salvage(body)
    seen = set()
    claims = [_claim_from_answer(item, n, seen) for n, item in enumerate(items, 1)]
    return claims or [{"claim_id": "AI-1", "문장": "", "근거": [], "형식 오류": "AI 답변에서 주장을 하나도 못 찾음"}]
