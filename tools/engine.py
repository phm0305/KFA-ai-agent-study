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
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Literal

import pandas as pd

from collect import REVIEW, CollectError, is_blank

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
    "억원": ("원", Decimal(10) ** 8),
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


def _check_one(number, unit, actual, actual_unit):
    """Return (actual in the written unit or None, verdict, reason)."""
    written = _written_number(number)
    if written is None:
        return None, CHECK, f"적은 숫자 '{number}'를 숫자로 못 읽음"
    if unit not in UNITS:
        return None, CHECK, f"모르는 단위 '{unit}' (원·억원·조원·%만 지원)"
    if actual_unit not in UNITS:
        return None, CHECK, f"근거 단위 '{actual_unit}'는 아직 지원 안 함 (원·억원·조원·%만 지원)"
    dimension, scale = UNITS[unit]
    actual_dimension, actual_scale = UNITS[actual_unit]
    if dimension != actual_dimension:
        return None, CHECK, f"단위가 안 맞음: 문장 {unit} / 근거 {actual_unit}"
    actual_base = Decimal(str(actual)) * actual_scale
    tolerance = Decimal("0.5").scaleb(written.as_tuple().exponent) * scale
    shown = float(actual_base / scale)
    if abs(written * scale - actual_base) <= tolerance:
        return shown, PASS, ""
    places = max(-written.as_tuple().exponent, 0) + 2
    return shown, FIX, f"실제 값은 {shown:,.{places}f} {unit}"


def _lookup(evidence_id, metrics, records):
    """Return (value, unit, source ids, reason the value cannot be used or None)."""
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
    출처 번호 collects the S# of every evidence row, or of a metric's input rows.
    """
    _require_tagged(records)
    out = []
    for claim in claims:
        evidence = claim.get("근거") or []
        rows, sources = [], set()
        if not evidence:
            rows.append({"근거 id": "", "적은 숫자": None, "적은 단위": "", "실제 값": None,
                         "판정": CHECK, "이유": "근거 없음"})
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
