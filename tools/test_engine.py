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


EOK = 10 ** 8


def statement(year, url, values, basis="연결"):
    rows = pd.DataFrame([{"항목": item, "값": value, "출처 URL": url} for item, value in values.items()])
    return c.finalize(rows, level=1, source=DART, reliability="상", basis=basis, unit="원",
                      base_date=f"{year}-12-31", disclosed=url[-14:-6], stock_code="000660",
                      stock_name="SK하이닉스")


def dart(year, url, revenue):
    return statement(year, url, {"매출액(연간)": revenue, "부채총계": revenue // 2})


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


def financials(equity_2025=6_000 * EOK, equity_basis="연결"):
    """2024 매출 8,000억 → 2025 매출 10,000억, 영업이익 2,000억, 부채 3,000억, 자본 6,000억.
    Hand results: growth 25.0, margin 20.0, debt ratio 50.0."""
    parts = [
        statement(2024, URL_2024, {"매출액(연간)": 8_000 * EOK}),
        statement(2025, URL_2025, {"매출액(연간)": 10_000 * EOK, "영업이익(연간)": 2_000 * EOK,
                                   "부채총계": 3_000 * EOK}),
        statement(2025, URL_2025, {"자본총계": equity_2025}, basis=equity_basis),
        prices(),
    ]
    return e.build_sources(e.with_ids(pd.concat(parts, ignore_index=True)))[1]


def metrics_of(records):
    return e.compute_metrics(records, e.METRIC_SPECS, "000660", "2025-12-31")


def verdicts(checked):
    return dict(zip(checked["claim_id"], checked["판정"]))


def test_metrics_match_hand_calculation():
    metrics = metrics_of(financials())

    assert metrics["값"].tolist() == [25.0, 20.0, 50.0]
    assert metrics["상태"].tolist() == [e.COMPUTED] * 3
    assert metrics["source_id"].tolist() == [["S1", "S2"], ["S2"], ["S2"]]
    assert metrics.loc[0, "입력 rid"] == [
        "000660|매출액(연간)|연결|2025-12-31|" + DART, "000660|매출액(연간)|연결|2024-12-31|" + DART]


def test_claims_pass_fix_review():
    records = financials()
    claims = [
        {"claim_id": "pass", "문장": "매출이 25% 성장했다", "근거": [("M1", 25, "%")]},
        {"claim_id": "pass-text", "문장": "영업이익률 20.00%", "근거": [("M2", "20.00", "%")]},
        {"claim_id": "fix", "문장": "영업이익률 20.4%", "근거": [("M2", 20.4, "%")]},
        {"claim_id": "no-evidence", "문장": "업황이 좋다", "근거": []},
        {"claim_id": "unknown-unit", "문장": "매출이 25퍼센트 성장", "근거": [("M1", 25, "퍼센트")]},
        {"claim_id": "wrong-dimension", "문장": "매출 성장 25억원", "근거": [("M1", 25, "억원")]},
        {"claim_id": "missing-metric", "문장": "M9 인용", "근거": [("M9", 1, "%")]},
    ]
    checked = e.check_claims(claims, metrics_of(records), records)

    assert verdicts(checked) == {
        "pass": e.PASS, "pass-text": e.PASS, "fix": e.FIX, "no-evidence": e.CHECK,
        "unknown-unit": e.CHECK, "wrong-dimension": e.CHECK, "missing-metric": e.CHECK}
    fix = checked[checked["claim_id"] == "fix"].iloc[0]
    assert fix["실제 값"] == 20.0
    assert checked.set_index("claim_id").loc["pass", "출처 번호"] == "[S1][S2]"


def test_missing_consolidated_row_blanks_metric_and_claim_reviews():
    records = financials(equity_basis="별도")
    metrics = metrics_of(records)
    debt = metrics.iloc[2]

    assert debt["값"] is None
    assert debt["상태"] == c.REVIEW
    assert "연결 줄 없음" in debt["이유"]
    checked = e.check_claims([{"claim_id": "C", "문장": "부채비율 50%", "근거": [("M3", 50, "%")]}],
                             metrics, records)
    assert checked["판정"].tolist() == [e.CHECK]


def test_rid_cited_in_eok_or_jo_won_converts_to_won():
    records = financials()
    revenue = "000660|매출액(연간)|연결|2025-12-31|" + DART
    claims = [
        {"claim_id": "eok", "문장": "매출 10,000억원", "근거": [(revenue, "10,000", "억원")]},
        {"claim_id": "jo", "문장": "매출 1조원", "근거": [(revenue, 1, "조원")]},
        {"claim_id": "eok-off", "문장": "매출 9,999억원", "근거": [(revenue, 9_999, "억원")]},
        {"claim_id": "no-rid", "문장": "없는 줄", "근거": [("000660|없는 항목|연결|2025-12-31|" + DART, 1, "원")]},
    ]
    checked = e.check_claims(claims, metrics_of(records), records)

    assert verdicts(checked) == {"eok": e.PASS, "jo": e.PASS, "eok-off": e.FIX, "no-rid": e.CHECK}
    assert checked.set_index("claim_id").loc["eok-off", "실제 값"] == 10_000.0
    assert checked.set_index("claim_id").loc["eok", "출처 번호"] == "[S2]"


def test_claim_source_numbers_ignore_row_order():
    claims = [{"claim_id": "C", "문장": "매출이 25% 성장했다", "근거": [("M1", 25, "%")]}]
    records = financials()
    shuffled = e.build_sources(e.with_ids(records[c.COLUMNS].sample(frac=1, random_state=3)
                                          .reset_index(drop=True)))[1]

    first = e.check_claims(claims, metrics_of(records), records)
    again = e.check_claims(claims, metrics_of(shuffled), shuffled)
    assert first["출처 번호"].tolist() == again["출처 번호"].tolist() == ["[S1][S2]"]


@pytest.mark.parametrize("equity", [0, -100 * EOK])
def test_denominator_at_or_below_zero_blanks_metric(equity):
    debt = metrics_of(financials(equity_2025=equity)).iloc[2]

    assert debt["값"] is None
    assert debt["상태"] == c.REVIEW
    assert "0 이하" in debt["이유"]


def test_round_number_ending_in_zero_is_read_to_the_ones_place():
    records = e.build_sources(e.with_ids(statement(2025, URL_2025, {"매출액(연간)": 1_096 * EOK})))[1]
    revenue = "000660|매출액(연간)|연결|2025-12-31|" + DART
    claims = [
        {"claim_id": "rounded", "문장": "매출 1,100억원", "근거": [(revenue, "1,100", "억원")]},
        {"claim_id": "jo", "문장": "매출 0.11조원", "근거": [(revenue, "0.11", "조원")]},
    ]
    checked = e.check_claims(claims, metrics_of(records), records)

    assert verdicts(checked) == {"rounded": e.FIX, "jo": e.PASS}
