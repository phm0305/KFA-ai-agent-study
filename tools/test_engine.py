"""Offline behavior tests for engine.py on small hand-made record tables.

Run: python -m pytest tools/test_engine.py -q
"""

import json
import urllib.parse

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


def test_render_check_writes_four_parts_and_fix_actual_in_written_unit(tmp_path):
    records = financials()
    sources = e.build_sources(records[c.COLUMNS])[0]
    metrics = metrics_of(records)
    claims = [
        {"claim_id": "C-1", "문장": "매출이 25% 성장했다", "근거": [("M1", 25, "%")]},
        {"claim_id": "C-2", "문장": "영업이익률은 20.4%다", "근거": [("M2", 20.4, "%")]},
    ]
    path = e.render_check(e.check_claims(claims, metrics, records), metrics, sources, tmp_path / "out" / "check.md")
    text = path.read_text(encoding="utf-8")

    for heading in ("## 주장", "## 지표", "## 숫자 대조", "## 출처"):
        assert heading in text
    assert "- C-1 매출이 25% 성장했다 [S1][S2]" in text
    assert "| C-2 영업이익률은 20.4%다 | 20.4 % | 20.000 % | FIX |" in text
    assert f"| [S3] | {PRICE} |" in text
    assert f"| [S1] | {DART} | 2024-12-31 | {URL_2024} | 상 |" in text


def test_units_same_text_money_scales_and_spaces():
    rows = pd.DataFrame([
        {"항목": "원/달러 환율", "값": 1380.5, "단위": "원/달러"},
        {"항목": "매출액(연간)", "값": 97_146_675, "단위": "백만원"},
        {"항목": "기준금리 변동", "값": 0.25, "단위": "%p"},
    ])
    records = e.build_sources(e.with_ids(c.finalize(
        rows, level=1, source="단위 테스트 표", source_url="https://example.com", reliability="상",
        basis=c.NOT_APPLICABLE, base_date="2025-12-31", disclosed=c.SAME_AS_DATE)))[1]
    rid = dict(zip(records["항목"], records["rid"]))
    claims = [
        {"claim_id": "same-text", "문장": "환율 1,380.5원/달러", "근거": [(rid["원/달러 환율"], "1,380.5", "원/달러")]},
        {"claim_id": "million-to-eok", "문장": "매출 971,467억원", "근거": [(rid["매출액(연간)"], "971,467", "억원")]},
        {"claim_id": "spaced", "문장": "매출 97.1조 원", "근거": [(rid["매출액(연간)"], "97.1", "조 원")]},
        {"claim_id": "pp-as-percent", "문장": "금리 0.25% 올랐다", "근거": [(rid["기준금리 변동"], "0.25", "%")]},
    ]
    checked = e.check_claims(claims, metrics_of(records), records)

    assert verdicts(checked) == {"same-text": e.PASS, "million-to-eok": e.PASS, "spaced": e.PASS,
                                 "pp-as-percent": e.CHECK}


def test_blank_units_on_both_sides_review():
    records = financials()
    unitless = (e.MetricSpec("단위 없는 영업이익률", "", "영업이익(연간) ÷ 매출액(연간) × 100", "ratio",
                             ("영업이익(연간)", "매출액(연간)")),)
    metrics = e.compute_metrics(records, unitless, "000660", "2025-12-31")
    checked = e.check_claims([{"claim_id": "C", "문장": "영업이익률 20", "근거": [("M1", 20, " ")]}], metrics, records)

    assert checked["판정"].tolist() == [e.CHECK]
    assert "단위 없음" in checked.loc[0, "이유"]


def answer_file(tmp_path, text):
    path = tmp_path / "answer.txt"
    path.write_text(text, encoding="utf-8")
    return path


def test_saved_answer_in_code_fence_is_checked_the_same_every_read(tmp_path):
    records = financials()
    metrics = metrics_of(records)
    path = answer_file(tmp_path, """```json
[{"claim_id": "C-1", "문장": "매출이 25% 늘었다", "근거": [["M1", "25", "%"]]},
 {"claim_id": "C-2", "문장": "영업이익률은 20.4%, 전년보다 3%포인트 높다", "근거": [["M2", "20.4", "%"], ["", "3", "%포인트"]]},
 {"claim_id": "C-3", "문장": "HBM이 실적을 이끌었다", "근거": []}]
```""")
    checked = e.check_claims(e.load_claims(path), metrics, records)

    assert checked["판정"].tolist() == [e.PASS, e.FIX, e.CHECK, e.CHECK]
    assert checked["이유"].tolist()[2:] == ["근거 id가 비어 있음 (표에 뒷받침하는 줄이 없음)", "근거 없음"]
    assert checked.equals(e.check_claims(e.load_claims(path), metrics, records))


def test_one_broken_claim_reviews_alone(tmp_path):
    records = financials()
    path = answer_file(tmp_path, """[{"claim_id": "C-1", "문장": "매출이 25% 늘었다", "근거": [["M1", "25", "%"]]},
 {"claim_id": "C-2", "문장": "영업이익률 20%" "근거": [["M2", "20", "%"]]},
 {"claim_id": "C-3", "문장": "부채비율 50%", "근거": [["M3", "50", "%"]]}]""")
    checked = e.check_claims(e.load_claims(path), metrics_of(records), records)

    assert verdicts(checked) == {"C-1": e.PASS, "C-2": e.CHECK, "C-3": e.PASS}
    assert checked.set_index("claim_id").loc["C-2", "이유"].startswith("AI 답변 형식 오류: JSON이 깨짐")


def test_answer_without_json_reviews_without_stopping(tmp_path):
    records = financials()
    path = answer_file(tmp_path, "죄송해요, 이 글에서는 주장을 찾지 못했어요.")
    checked = e.check_claims(e.load_claims(path), metrics_of(records), records)

    assert checked["판정"].tolist() == [e.CHECK]
    assert "주장을 하나도 못 찾음" in checked.loc[0, "이유"]


def test_saved_answer_reused_only_for_the_same_question(tmp_path, monkeypatch):
    calls = []

    def fake_call(prompt, api_key, model, fallback_model):
        calls.append(prompt)
        return f"answer {len(calls)}", model

    monkeypatch.setattr(e, "_call_gemini", fake_call)
    path = tmp_path / "ai_claims.txt"
    ask = lambda prompt, **kw: e.ask_claims(prompt, "key", path, "flash", "flash-lite", **kw)

    ask("question A")
    ask("question A")
    assert len(calls) == 1
    ask("question B")
    assert path.read_text(encoding="utf-8") == "answer 2"
    record = json.loads((tmp_path / "ai_claims_기록.json").read_text(encoding="utf-8"))
    assert (record["질문"], record["모델"]) == ("question B", "flash")
    ask("question B", overwrite=True)
    assert calls == ["question A", "question B", "question B"]
    (tmp_path / "ai_claims_기록.json").unlink()
    ask("question B")
    assert len(calls) == 4


def test_backup_answer_used_only_for_the_same_question(tmp_path, monkeypatch, capsys):
    record = {"질문": "default question", "모델": "flash", "호출 시각": "2026-11-09 01:05"}
    files = {"ai_claims_000660_2025.txt": "saved answer", "ai_claims_000660_2025_기록.json": json.dumps(record)}

    class Response:
        def __init__(self, text):
            self.content = text.encode("utf-8")

    def fake_get(url):
        name = urllib.parse.unquote(url.rsplit("/", 1)[1])
        if name not in files:
            raise c.CollectError("404")
        return Response(files[name])

    monkeypatch.setattr(e, "http_get", fake_get)
    path = tmp_path / "w04_ai_claims.txt"

    assert e.use_backup("edited question", path, "ai_claims_000660_2025") is None
    assert not path.exists()
    assert e.use_backup("default question", path, "ai_claims_000660_2025") == path
    assert path.read_text(encoding="utf-8") == "saved answer"
    assert "스터디장이 미리 받아 둔 답" in capsys.readouterr().out
    assert e.use_backup("default question", path, "ai_claims_005930_2025") is None
