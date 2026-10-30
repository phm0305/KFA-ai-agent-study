"""Offline behavior tests: every network call is replaced by a fake response.

Run: python -m pytest tools/test_collect.py -q
"""

import io
import json
import zipfile

import pandas as pd
import pytest
import requests

import collect as c

SECRET = "SECRET-KEY-123"


class FakeResponse:
    def __init__(self, status=200, content=b"", encoding="utf-8"):
        self.status_code = status
        self.content = content
        self.encoding = encoding
        self.apparent_encoding = "utf-8"

    @property
    def text(self):
        return self.content.decode(self.encoding or "utf-8", errors="replace")

    def json(self):
        return json.loads(self.content.decode("utf-8"))


def fake_web(monkeypatch, routes):
    """routes: {url substring: FakeResponse | Exception}; first match wins."""
    calls = []

    def get(url, params=None, timeout=None, headers=None):
        calls.append((url, params))
        for key, result in routes.items():
            if key in url:
                if isinstance(result, Exception):
                    raise result
                return result
        raise requests.ConnectionError(f"no route for {url}?crtfc_key={SECRET}")

    monkeypatch.setattr(c.requests, "get", get)
    return calls


def corp_zip(entries):
    xml = "<result>" + "".join(
        f"<list><corp_code>{cc}</corp_code><corp_name>{n}</corp_name><stock_code>{sc}</stock_code></list>"
        for cc, n, sc in entries) + "</result>"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("CORPCODE.xml", xml)
    return buf.getvalue()


def dart_row(account, sj, amount, add=None, rcept="20260814001234"):
    return {"rcept_no": rcept, "account_id": account, "sj_div": sj,
            "thstrm_amount": amount, "thstrm_add_amount": add}


DART_ROWS = [
    dart_row("ifrs-full_Assets", "BS", "500,000"),
    dart_row("ifrs-full_Liabilities", "BS", "100000"),
    dart_row("ifrs-full_Equity", "BS", "400000"),
    dart_row("ifrs-full_Revenue", "IS", "74068302000000", "153505000000000"),
    dart_row("dart_OperatingIncomeLoss", "IS", "4668000000000", "11353000000000"),
    dart_row("ifrs-full_ProfitLoss", "SCE", "999"),
    dart_row("ifrs-full_ProfitLoss", "IS", "5110000000000", ""),
    dart_row("ifrs-full_ProfitLoss", "CIS", "1"),
]


@pytest.fixture(autouse=True)
def fresh_state():
    c._DART_CORPS.clear()
    c.STEP_RESULTS.clear()


@pytest.mark.parametrize("raw, expected", [
    ("1,234", 1234), ("(1,234)", -1234), ("△500", -500), ("12.5%", 12.5), (" 3 ", 3),
    ("-", None), (".", None), ("", None), (None, None), (float("nan"), None), (7, 7), (2.5, 2.5),
    ("153505000000000", 153505000000000), ("9007199254740993", 9007199254740993),
])
def test_to_number_parses(raw, expected):
    assert c.to_number(raw) == (expected, None)


@pytest.mark.parametrize("raw", ["12억", "abc", "1.2.3", True])
def test_to_number_reports_unparseable(raw):
    value, problem = c.to_number(raw)
    assert value is None and problem.startswith("숫자로 못 바꿈")


@pytest.mark.parametrize("raw, expected", [
    ("2026-06-30", "2026-06-30"), ("2026.06.30", "2026-06-30"), ("2026.6.3.", "2026-06-03"),
    ("20260630", "2026-06-30"), ("2026년 05월 29일", "2026-05-29"), ("2026-08", "2026-08"),
    ("202608", "2026-08"), ("2026년 8월", "2026-08"), ("2026Q2", "2026Q2"), ("2026", "2026"),
    ("2026-10-23 00:00:00", "2026-10-23"), (pd.Timestamp("2026-01-02"), "2026-01-02"), (202608, "2026-08"),
])
def test_to_date_normalizes(raw, expected):
    assert c.to_date(raw) == (expected, None)


@pytest.mark.parametrize("raw", ["2026-13-01", "2026-02-30", "어제", "26/10/23"])
def test_to_date_rejects(raw):
    value, problem = c.to_date(raw)
    assert value is None and problem


def test_dart_quarter2_end_to_end(monkeypatch):
    calls = fake_web(monkeypatch, {
        "corpCode.xml": FakeResponse(content=corp_zip([("00126380", "삼성전자", "005930"), ("99999999", "비상장", " ")])),
        "fnlttSinglAcntAll": FakeResponse(content=json.dumps({"status": "000", "list": DART_ROWS}).encode()),
    })
    records = c.collect_dart("005930", 2026, 2, "CFS", SECRET)
    assert c.check_records(records, show=False)
    assert list(records.columns) == c.COLUMNS
    by_item = records.set_index("항목")
    assert len(records) == 9
    assert by_item.loc["당기순이익(3개월)", "값"] == 5110000000000
    assert by_item.loc["자산총계", "값"] == 500000
    assert by_item.loc["당기순이익(누적)", "상태"] == c.REVIEW
    assert "값 비어 있음" in by_item.loc["당기순이익(누적)", "비고"]
    passed = records[records["항목"] != "당기순이익(누적)"]
    assert (passed["상태"] == c.PASSED).all()
    assert (records["공시일"] == "2026-08-14").all() and (records["기준일"] == "2026-06-30").all()
    assert (records["기준"] == "연결").all() and (records["종목명"] == "삼성전자").all()
    assert (records["수집 방법"] == "1 공식 API").all()
    c.collect_dart("005930", 2026, 2, "CFS", SECRET)
    assert sum("corpCode" in url for url, _ in calls) == 1


def test_dart_annual_and_missing_accounts(monkeypatch):
    fake_web(monkeypatch, {
        "corpCode.xml": FakeResponse(content=corp_zip([("00126380", "삼성전자", "005930")])),
        "fnlttSinglAcntAll": FakeResponse(content=json.dumps({"status": "000", "list": DART_ROWS[:4]}).encode()),
    })
    records = c.collect_dart("005930", 2025, 4, "OFS", SECRET).set_index("항목")
    assert records.loc["매출액(연간)", "값"] == 74068302000000
    assert "연간 - 3분기 누적" in records.loc["매출액(연간)", "비고"]
    assert records.loc["영업이익", "상태"] == c.REVIEW
    assert (records["기준"] == "별도").all() and (records["기준일"] == "2025-12-31").all()


def test_dart_errors_are_friendly_and_hide_key(monkeypatch):
    fake_web(monkeypatch, {"corpCode.xml": FakeResponse(content=b'{"status":"010","message":"bad"}')})
    with pytest.raises(c.CollectError, match="등록되지 않은 키"):
        c.collect_dart("005930", 2026, 2, "CFS", SECRET)
    with pytest.raises(c.SkipStep):
        c.collect_dart("005930", 2026, 2, "CFS", None)
    fake_web(monkeypatch, {})
    records = c.run_step("DART", 1, lambda: c.collect_dart("005930", 2026, 2, "CFS", SECRET))
    assert records is None
    summary = c.step_summary()
    assert summary.loc[0, "결과"] == "❌" and SECRET not in summary.to_string()


def test_dart_unknown_stock(monkeypatch):
    fake_web(monkeypatch, {"corpCode.xml": FakeResponse(content=corp_zip([("1", "A", "000001")]))})
    with pytest.raises(c.CollectError, match="상장사 목록에 없어요"):
        c.collect_dart("005930", 2026, 2, "CFS", SECRET)


def test_library_frame_with_datetime_index():
    prices = pd.DataFrame({"Close": [70000, 71000], "Volume": [10, 20]},
                          index=pd.DatetimeIndex(["2026-10-26", "2026-10-27"], name="Date"))
    records = c.collect_table(prices, {"Close": ("종가", "원"), "Volume": ("거래량", "주")},
                              level=2, source="FDR", source_url="https://github.com/FinanceData/FinanceDataReader",
                              reliability="중", basis=c.NOT_APPLICABLE, disclosed=c.SAME_AS_DATE,
                              stock_code="005930", stock_name="삼성전자")
    assert len(records) == 4 and (records["상태"] == c.PASSED).all()
    assert records["기준일"].tolist() == records["공시일"].tolist() == ["2026-10-26", "2026-10-27"] * 2
    assert records.loc[records["항목"] == "종가", "값"].tolist() == [70000, 71000]


def test_range_index_needs_date_col():
    with pytest.raises(c.CollectError, match="date_col"):
        c.collect_table(pd.DataFrame({"x": [1]}), {"x": ("x", "원")}, level=2)


def test_wrong_item_column_lists_available():
    with pytest.raises(c.CollectError, match=r"표에 없는 칸: \['Clse'\].*Close"):
        c.long_from_table(pd.DataFrame({"Date": ["2026-01-01"], "Close": [1]}), {"Clse": ("종가", "원")}, "Date")


@pytest.mark.parametrize("header, missing", [("observation_date,DGS10", ""), ("DATE,DGS10", ".")])
def test_fred_csv_both_formats(monkeypatch, header, missing):
    body = f"{header}\n2026-10-22,4.01\n2026-10-23,{missing}\n2026-10-24,4.05\n".encode()
    fake_web(monkeypatch, {"fredgraph.csv": FakeResponse(content=body)})
    table = c.read_table("https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10")
    records = c.collect_table(table, {"DGS10": ("미국 10년물 국채금리", "%")}, date_col=table.columns[0],
                              level=3, source="FRED", source_url="https://fred.stlouisfed.org/series/DGS10",
                              reliability="상", basis=c.NOT_APPLICABLE, disclosed=c.SAME_AS_DATE)
    assert records["상태"].tolist() == [c.PASSED, c.REVIEW, c.PASSED]
    assert records["값"].tolist()[0] == 4.01


def test_cp949_csv_and_fake_xls(tmp_path):
    csv_path = tmp_path / "관세청_수출_2026-09.csv"
    csv_path.write_bytes("기간,수출액\n2026-09,123\n".encode("cp949"))
    assert c.read_table(csv_path).iloc[0]["수출액"] == 123
    xls_path = tmp_path / "krx.xls"
    xls_path.write_text("<table><tr><th>일자</th><th>종가</th></tr><tr><td>2026/10/27</td><td>1,000</td></tr></table>", encoding="utf-8")
    table = c.read_table(xls_path)
    records = c.collect_table(table, {"종가": ("종가", "원")}, date_col="일자", level=3, source="KRX",
                              source_url="http://data.krx.co.kr", reliability="상", basis=c.NOT_APPLICABLE,
                              disclosed=c.SAME_AS_DATE)
    assert records.loc[0, "값"] == 1000 and records.loc[0, "기준일"] == "2026-10-27"
    with pytest.raises(c.CollectError, match="파일이 없어요"):
        c.read_table(tmp_path / "없는파일.csv")


BOK_HTML = """<html><body><table><caption>한국은행 기준금리 변동추이</caption>
<thead><tr><th>연도</th><th>변경일자</th><th>기준금리</th></tr></thead>
<tbody><tr><td rowspan="2">2025</td><td>05월 29일</td><td>2.50</td></tr>
<tr><td>02월 25일</td><td>2.75</td></tr></tbody></table></body></html>""".encode()


def bok_records():
    table = c.read_html_table("https://www.bok.or.kr/portal/singl/baseRate/list.do", match="기준금리")
    year, day, rate = (c.find_col(table, k) for k in ("연도", "변경일자", "기준금리"))
    table["기준일"] = [f"{y}년 {d}" for y, d in zip(table[year], table[day])]
    return c.collect_table(table, {rate: ("한국은행 기준금리", "%")}, date_col="기준일", level=4,
                           source="한국은행 기준금리 추이 페이지", source_url="https://www.bok.or.kr",
                           reliability="상", basis=c.NOT_APPLICABLE, disclosed=c.SAME_AS_DATE)


def test_crawl_allowed_marks_review(monkeypatch):
    fake_web(monkeypatch, {"robots.txt": FakeResponse(content=b"User-agent: *\nDisallow: /admin\n"),
                           "baseRate": FakeResponse(content=BOK_HTML, encoding="ISO-8859-1")})
    records = bok_records()
    assert records["기준일"].tolist() == ["2025-05-29", "2025-02-25"]
    assert records["값"].tolist() == [2.5, 2.75]
    assert (records["상태"] == c.REVIEW).all()
    assert all("원문 화면과 한 번 대조" in n for n in records["비고"])


def test_crawl_blocked_by_robots_is_skip(monkeypatch):
    fake_web(monkeypatch, {"robots.txt": FakeResponse(content=b"User-agent: *\nDisallow: /\n")})
    result = c.run_step("기준금리", 4, bok_records)
    assert result is None and c.step_summary().loc[0, "결과"] == "⏭"


def test_crawl_changed_layout_is_friendly(monkeypatch):
    fake_web(monkeypatch, {"robots.txt": FakeResponse(status=404),
                           "baseRate": FakeResponse(content=b"<table><tr><td>a</td></tr></table>")})
    with pytest.raises(c.CollectError, match="기준금리"):
        bok_records()


def test_manual_rows_and_checked_mark():
    manual = pd.DataFrame([
        {"항목": "예시 A", "값": "1,234", "단위": "억원", "기준일": "2026.06.30", "공시일": "2026-08-14", "확인": "O"},
        {"항목": "예시 B", "값": "12.5%", "단위": "%", "기준일": "2026년 6월", "공시일": ""},
        {"항목": "예시 C", "값": "약 3조", "단위": "원", "기준일": "2026-06-30", "공시일": "2026-06-01"},
    ])
    records = c.collect_table(manual, level=5, source="예시", source_url="https://example.com",
                              reliability="중", basis=c.NOT_APPLICABLE)
    assert records["상태"].tolist() == [c.PASSED, c.REVIEW, c.REVIEW]
    assert records.loc[0, "값"] == 1234 and records.loc[0, "기준일"] == "2026-06-30"
    assert "공시일 비어 있음" in records.loc[1, "비고"]
    assert records.loc[2, "값"] == "약 3조" and "숫자로 못 바꿈" in records.loc[2, "비고"]
    assert "공시일이 기준일보다 빠름" in records.loc[2, "비고"]
    assert "값 비어 있음" not in records.loc[2, "비고"]


def test_not_applicable_only_where_allowed():
    table = pd.DataFrame([{"항목": "x", "값": 1, "단위": c.NOT_APPLICABLE, "기준일": "2026-01-01"}])
    records = c.collect_table(table, level=2, source="s", source_url="u", reliability="상",
                              basis=c.NOT_APPLICABLE, disclosed=c.NOT_APPLICABLE)
    assert records.loc[0, "상태"] == c.REVIEW and "단위에는" in records.loc[0, "비고"]


def test_bad_reliability_flagged():
    table = pd.DataFrame([{"항목": "x", "값": 1, "단위": "원", "기준일": "2026-01-01"}])
    records = c.collect_table(table, level=1, source="s", source_url="u", reliability="높음",
                              basis=c.NOT_APPLICABLE, disclosed=c.SAME_AS_DATE)
    assert "상/중/하" in records.loc[0, "비고"]


def test_cards_read_only_listed_and_shaped_files(tmp_path):
    files = tmp_path / "files"
    files.mkdir()
    (files / "리포트_수치_2026-06.csv").write_text("항목,값,단위\n점유율,23.5,%\n", encoding="utf-8-sig")
    (files / "관세청_raw_2026-09.csv").write_text("기간,수출액\n2026-09,1\n", encoding="utf-8-sig")
    (files / "기사.txt").write_text("본문", encoding="utf-8")
    (files / "카드에_없는.csv").write_text("항목,값\nx,1\n", encoding="utf-8-sig")
    cards = pd.DataFrame([
        {"파일명": "리포트_수치_2026-06.csv", "출처": "하나증권 리포트", "URL": "https://x", "기준일": "2026-06", "신뢰도": "중"},
        {"파일명": "관세청_raw_2026-09.csv", "출처": "관세청", "URL": "https://y", "기준일": "2026-09", "신뢰도": "상"},
        {"파일명": "기사.txt", "출처": "한경", "URL": "https://z", "기준일": "2026-10-20", "신뢰도": "하"},
        {"파일명": "없는파일.csv", "출처": "?", "URL": "?", "기준일": "2026", "신뢰도": "하"},
    ])
    records = c.collect_from_cards(cards, files)
    assert len(records) == 1
    assert records.loc[0, "기준일"] == "2026-06" and records.loc[0, "수집 방법"] == "5 수동 입력"
    assert records.loc[0, "출처"] == "하나증권 리포트" and records.loc[0, "상태"] == c.REVIEW
    with pytest.raises(c.CollectError, match="출처카드에 없는 칸"):
        c.collect_from_cards(cards.drop(columns=["신뢰도"]), files)


def test_ecos_success_and_error(monkeypatch):
    ok = {"StatisticSearch": {"list_total_count": 2, "row": [
        {"TIME": "202608", "DATA_VALUE": "2.5", "UNIT_NAME": "연%"},
        {"TIME": "202609", "DATA_VALUE": "2.5", "UNIT_NAME": "연%"}]}}
    fake_web(monkeypatch, {"ecos.bok.or.kr": FakeResponse(content=json.dumps(ok).encode())})
    records = c.collect_ecos(SECRET, "722Y001", "M", "202608", "202609", "0101000", "한국은행 기준금리", "%")
    assert records["기준일"].tolist() == ["2026-08", "2026-09"]
    assert "공시일 비어 있음" in records.loc[0, "비고"]
    err = {"RESULT": {"CODE": "INFO-100", "MESSAGE": "인증키가 유효하지 않습니다."}}
    fake_web(monkeypatch, {"ecos.bok.or.kr": FakeResponse(content=json.dumps(err).encode())})
    with pytest.raises(c.CollectError, match="인증키") as info:
        c.collect_ecos(SECRET, "722Y001", "M", "202608", "202609", "0101000", "x", "%")
    assert SECRET not in str(info.value)


def test_json_path_error_shows_where(monkeypatch):
    fake_web(monkeypatch, {"api.example": FakeResponse(content=b'{"response": {"body": {"items": []}}}')})
    with pytest.raises(c.CollectError, match="비어 있어요"):
        c.read_json_table("https://api.example/x", "response.body.items")
    with pytest.raises(c.CollectError, match=r"'item'.*\['items'\]"):
        c.read_json_table("https://api.example/x", "response.body.item")


def test_http_errors_hide_key(monkeypatch):
    fake_web(monkeypatch, {"timeout.example": requests.Timeout(f"k={SECRET}"),
                           "forbidden.example": FakeResponse(status=403)})
    for url, pattern in [("https://timeout.example/a", "초 넘게"), ("https://forbidden.example/a", "403"),
                         (f"https://nowhere.example/{SECRET}", "연결하지 못했어요")]:
        with pytest.raises(c.CollectError, match=pattern) as info:
            c.http_get(url, {"crtfc_key": SECRET})
        assert SECRET not in str(info.value)
        assert info.value.__context__ is None or info.value.__suppress_context__


def test_check_records_catches_hand_made_tables():
    assert not c.check_records(pd.DataFrame({"값": [1]}), show=False)
    good = c.collect_table(pd.DataFrame([{"항목": "x", "값": 1, "단위": "원", "기준일": "2026-01-01"}]),
                           level=1, source="s", source_url="u", reliability="상",
                           basis=c.NOT_APPLICABLE, disclosed=c.SAME_AS_DATE)
    assert c.check_records(good, show=False)
    tampered = good.copy()
    tampered.loc[0, "출처"] = ""
    assert not c.check_records(tampered, show=False)


def test_run_step_rejects_wrong_shape_and_reruns_replace():
    assert c.run_step("내 소스", 2, lambda: pd.DataFrame({"값": [1]})) is None
    assert c.step_summary().loc[0, "결과"] == "❌"
    c.run_step("내 소스", 2, lambda: (_ for _ in ()).throw(ZeroDivisionError()))
    assert len(c.step_summary()) == 1 and "ZeroDivisionError" in c.step_summary().loc[0, "메모"]


def test_save_records_writes_both_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    records = c.collect_table(pd.DataFrame([{"항목": "x", "값": 1, "단위": "원", "기준일": "2026-01-01"},
                                            {"항목": "y", "값": "?", "단위": "원", "기준일": "2026-01-01"}]),
                              level=1, source="s", source_url="u", reliability="상",
                              basis=c.NOT_APPLICABLE, disclosed=c.SAME_AS_DATE)
    all_path, review_path = c.save_records(records, "w02")
    assert len(pd.read_csv(all_path)) == 2 and len(pd.read_csv(review_path)) == 1
    assert open(all_path, "rb").read(3) == b"\xef\xbb\xbf"


def test_run_step_library_network_error_is_explained():
    def boom():
        raise requests.ConnectionError(f"https://x/?key={SECRET}")
    assert c.run_step("주가", 2, boom) is None
    memo = c.step_summary().loc[0, "메모"]
    assert "인터넷 연결 문제" in memo and SECRET not in memo
