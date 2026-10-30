"""Offline behavior tests for engine.py on small hand-made record tables.

Run: python -m pytest tools/test_engine.py -q
"""

import pandas as pd
import pytest

import collect as c
import engine as e

DART = "DART 단일회사 전체 재무제표 API"
URL_2024 = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20250319000001"
URL_2025 = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260318000001"
PRICE = "FinanceDataReader (네이버 금융 경유, 원천 한국거래소)"


def dart(year, url, revenue):
    rows = pd.DataFrame([
        {"항목": "매출액(연간)", "값": revenue, "출처 URL": url},
        {"항목": "부채총계", "값": revenue // 2, "출처 URL": url},
    ])
    return c.finalize(rows, level=1, source=DART, reliability="상", basis="연결", unit="원",
                      base_date=f"{year}-12-31", disclosed=url[-14:-6], stock_code="000660",
                      stock_name="SK하이닉스")


def prices():
    rows = pd.DataFrame([
        {"항목": "종가", "값": 200000, "기준일": "2025-10-01"},
        {"항목": "종가", "값": 210000, "기준일": "2025-12-30"},
    ])
    return c.finalize(rows, level=2, source=PRICE, source_url="https://github.com/FinanceData/FinanceDataReader",
                      reliability="중", basis=c.NOT_APPLICABLE, unit="원", disclosed=c.SAME_AS_DATE,
                      stock_code="000660", stock_name="SK하이닉스")


def sample():
    return pd.concat([dart(2024, URL_2024, 100), dart(2025, URL_2025, 150), prices()], ignore_index=True)


def test_source_numbers_ignore_row_order_and_split_filings():
    records = sample()
    sources, tagged = e.build_sources(e.with_ids(records))
    shuffled = records.sample(frac=1, random_state=7).reset_index(drop=True)
    sources_again, tagged_again = e.build_sources(e.with_ids(shuffled))

    assert sources.equals(sources_again)
    assert dict(zip(tagged["rid"], tagged["source_id"])) == dict(zip(tagged_again["rid"], tagged_again["source_id"]))
    assert sources["출처 URL"].tolist()[:2] == [URL_2024, URL_2025]
    assert sources["줄 수"].tolist() == [2, 2, 2]
    assert sources["기준일 범위"].tolist() == ["2024-12-31", "2025-12-31", "2025-10-01 ~ 2025-12-30"]
    assert list(records.columns) == c.COLUMNS


def test_same_fact_twice_stops():
    records = pd.concat([sample(), dart(2025, URL_2025, 150)], ignore_index=True)
    with pytest.raises(c.CollectError, match="000660\\|매출액\\(연간\\)\\|연결\\|2025-12-31"):
        e.with_ids(records)


def test_one_source_with_two_reliabilities_stops():
    records = sample()
    records.loc[records["출처"] == PRICE, "신뢰도"] = ["중", "상"]
    with pytest.raises(c.CollectError, match="신뢰도"):
        e.build_sources(records)
