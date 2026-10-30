"""KFA AI agent study: report engine skeleton (3rd session).

Adds row ids and a numbered source list on top of the shared record table from
collect.py. Engine columns go on copies only; the 15 shared columns never change.
Member-facing messages are Korean on purpose; identifiers stay English.

[한국어 안내] 이 셀은 고치지 않고 실행만 해요.
    with_ids()       공통 표의 줄마다 이름표(rid)를 붙여요. 같은 사실이 두 줄이면 멈춰요
    build_sources()  출처 목록 [S1] [S2] ...을 만들고, 줄마다 어느 출처인지(source_id) 붙여요
"""

import pandas as pd

from collect import CollectError, is_blank

RID_PARTS = ["종목코드", "항목", "기준", "기준일", "출처"]
SOURCE_KEY = ["출처", "출처 URL"]
SOURCE_COLUMNS = ["source_id", "출처", "출처 URL", "수집 방법", "신뢰도", "기준일 범위", "줄 수"]


def _text(value):
    return "" if is_blank(value) else str(value)


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
