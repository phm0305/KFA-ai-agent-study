"""Build notebooks/02_template_collect.ipynb from tools/collect.py.

collect.py is the single source of the shared code; the notebook embeds it in one
collapsed cell so members can 'Run all' without importing anything.
Run from the repo root: python tools/build_notebook.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = (ROOT / "tools" / "collect.py").read_text(encoding="utf-8")
OUT = ROOT / "notebooks" / "02_template_collect.ipynb"

cells = []


def md(text):
    cells.append(("markdown", text.strip("\n")))


def code(text):
    cells.append(("code", text.strip("\n")))


md("""
# 🧩 2회차 템플릿: 어떤 소스든 같은 표로 모으기

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/phm0305/KFA-ai-agent-study/blob/main/notebooks/02_template_collect.ipynb)

수집 방법 1~5단계마다 데이터를 받아오는 방법은 다르지만, **끝은 항상 같은 표 하나**예요.
이 노트북은 단계별 예시를 하나씩 돌려서 그걸 직접 확인하고, 맨 아래에서 **내 소스**를 붙이는 연습을 해요.

```
1 공식 API ──────┐
2 파이썬 라이브러리 ─┤
3 파일 다운로드 ────┼──▶  collect_table()  ──▶  공통 표 (15칸)  ──▶  형식 통과 / 확인 필요
4 크롤링 ─────────┤        (출구는 하나)
5 수동 입력 ───────┘
```

**실행 전에** [2회차 가이드 3-1](https://github.com/phm0305/KFA-ai-agent-study/blob/main/docs/sessions/02/README.md#3-1-수집-방법-15단계란)에서 **내 소스가 몇 단계인지** 먼저 확인하세요.

**사용법:** 위 메뉴 **런타임 → 모두 실행**. 2~3분 걸려요. 중간에 뭐가 실패해도 멈추지 않고 끝까지 가요.
"보안 비밀 액세스 허용" 창이 뜨면 **허용**을 눌러요.

**정상이면 맨 아래 요약표가 대략 이렇게 나와요**

| 단계 | 예시 | 결과 | 줄 수 | 확인 필요 |
|---|---|---|---|---|
| 1 공식 API | DART 재무제표 | ✅ | 9 | 0 |
| 1 공식 API | ECOS 기준금리 | ⏭ (ECOS 키 없으면 정상) / 키 있으면 ✅ | 0 / 9 | 0 / 9 |
| 2 파이썬 라이브러리 | 주가 | ✅ | 10 | 0 |
| 3 파일 다운로드 | FRED 미국 금리 | ✅ | 5 | 0~1 |
| 4 크롤링 | 한국은행 기준금리 페이지 | ✅ 또는 ⏭ | 5 | 5 |
| 5 수동 입력 | 손으로 옮긴 숫자 예시 | ✅ | 3 | 2 |
| 5 수동 입력 | 내 드라이브 출처카드 | ⏭ (USE_DRIVE=False면 정상) | 0 | 0 |
| (과제) | 내 소스 | ⏭ (아직 안 채웠으면 정상) | 0 | 0 |

> **✅·⏭는 둘 다 정상이에요.** ⏭는 "준비가 안 돼서 건너뜀"이고, 이유가 메모 칸에 적혀요. ❌만 고치면 돼요.
>
> **확인 필요도 실패가 아니에요.** 코드가 혼자 판단할 수 없는 숫자를 사람에게 넘긴 거예요. 4·5단계는 일부러 전부 확인 필요로 보내요.
""")

code("""
# ⚙️ 설정: 바꿀 일이 있으면 여기만
# 아래 셀들은 이 이름(변수)을 가져다 써요. 여기서 한 번 바꾸면 노트북 전체에 적용돼요.
# 바꾼 뒤에는 '런타임 → 모두 실행'을 다시 눌러요.

STOCK_CODE = "005930"   # 종목코드 6자리 (따옴표 안에, 앞의 0까지)
STOCK_NAME = "삼성전자"   # 표에 같이 적을 회사 이름
YEAR = 2026             # DART 재무제표 연도
QUARTER = 2             # 1·2·3·4 (4 = 사업보고서). 아직 공시 전인 분기면 DART가 '데이터 없음'을 줘요
FS_DIV = "CFS"          # CFS 연결 / OFS 별도
USE_DRIVE = False       # 내 드라이브 KFA_자료 폴더를 만들었으면 True (첫 글자 대문자)
CARD_SHEET = "출처카드"   # 출처카드 구글 시트 제목
""")

code("""
#@title 📦 설치 (1분) { display-mode: "form" }
import subprocess, sys
proc = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "finance-datareader", "python-dotenv"],
                      capture_output=True, text=True)
print("✅ 설치 완료" if proc.returncode == 0 else "❌ 설치 실패: 런타임 → 런타임 다시 시작 → 모두 실행")
""")

code("#@title 🧰 공통 도구 (고치지 말고 실행만. 코드가 궁금하면 이 셀을 더블클릭) { display-mode: \"form\" }\n"
     + TOOLS.strip("\n")
     + "\n\nSTEP_RESULTS.clear()\nprint(\"✅ 공통 도구 준비 완료\")")

code("""
# 🔑 키 불러오기 (값은 절대 출력하지 않아요)
# get_key("이름"): 왼쪽 🔑(Secrets)에 그 이름으로 저장한 키를 읽어요. 없으면 None(비어 있음).
# 키를 "abc123"처럼 셀에 직접 적으면 GitHub에 올릴 때 공개되니까, 항상 이렇게 이름으로만 불러요.
# 아래 print는 키 값이 아니라 '있다/없다'만 보여줘요.
DART_API_KEY = get_key("DART_API_KEY")
ECOS_API_KEY = get_key("ECOS_API_KEY")
print("DART 키:", "등록됨 ✅" if DART_API_KEY else "없음 ⏭ (Secrets에 DART_API_KEY + 노트북 액세스 켜기)")
print("ECOS 키:", "등록됨 ✅" if ECOS_API_KEY else "없음 ⏭ (선택 사항)")
""")

md("""
## 공통 표: 숫자 하나 = 한 줄, 15칸

| 칸 | 뜻 | 비어도 되나 |
|---|---|---|
| 종목코드 · 종목명 | 어느 회사 숫자인지 | 거시 지표면 비워도 돼요 |
| 항목 | 무슨 숫자인지 (매출액(3개월), 종가 …) | ❌ |
| 값 | 숫자. `1,234` `12.5%` `(500)` `△500`은 코드가 알아서 숫자로 바꿔요 | ❌ |
| 단위 | 원, 억원, %, 주 … | ❌ |
| 기준 | 연결 / 별도. 재무제표 숫자가 아니면 **`해당 없음`** | ❌ |
| 기준일 | 이 숫자가 **언제 시점** 숫자인지 | ❌ |
| 공시일 | 이 숫자가 **세상에 공개된 날**. 주가·금리처럼 그날 공개되면 기준일과 같게 | ❌ |
| 출처 · 출처 URL | 어디서 왔는지, 원문을 다시 찾아갈 주소 | ❌ |
| 신뢰도 | 상(공시·공식 통계) / 중(증권사 리포트·중간 사이트) / 하(기사·블로그) | ❌ |
| 수집 방법 | 1~5단계 (코드가 자동으로 적어요) | 자동 |
| 수집 시각 | 내가 받아온 시각 (자동) | 자동 |
| 상태 | **형식 통과** / **확인 필요** (자동) | 자동 |
| 비고 | 메모 + ⚠ 확인 필요한 이유 (자동으로 붙어요) | ⭕ |

**확인 필요로 넘어가는 경우:** 필수 칸이 비었을 때 · 값이 숫자로 안 바뀔 때(`약 3조`, `12억`) · 날짜 모양이 이상할 때 · 공시일이 기준일보다 빠를 때 · 신뢰도가 상/중/하가 아닐 때 · **4단계(크롤링)·5단계(수동)는 사람이 원문과 대조해서 `확인` 칸에 O를 적기 전까지 전부**

> "빈칸"과 "해당 없음"은 달라요. 빈칸은 **모른다**, `해당 없음`은 **이 숫자엔 그런 개념이 없다**예요.
> "형식 통과"는 **모양이 맞다**는 뜻이지 **숫자가 맞다**는 뜻은 아니에요. 진짜 맞는지는 4회차 검증기가 원본과 대조해요.
""")

md("""
## 1단계 · 공식 API

기관이 "코드로 가져가세요" 하고 열어둔 문이에요. 가장 믿을 만하고, 꼬리표(공시일·출처 URL)를 거의 다 자동으로 채울 수 있어요.

**예시: DART 재무제표.** 손익 항목은 3개월치와 누적을 따로 적어요(섞으면 대표적인 함정). 공시일은 접수번호 앞 8자리에서 뽑아요.
""")

code("""
# run_step(이름, 단계, 실행할 함수): 예시 하나를 '안전하게' 돌리는 포장지예요.
#   - 성공하면 ✅ + 결과 표를 돌려줘요.
#   - 준비가 안 됐으면(키 없음 등) ⏭, 실패하면 ❌를 요약표에 한 줄 남기고 None(결과 없음)을 돌려줘요.
#   - 어느 경우든 노트북은 멈추지 않고 다음 셀로 넘어가요. 그래서 '모두 실행'이 끝까지 가요.
# lambda: 는 "지금 바로 말고, run_step이 부를 때 실행해"라는 뜻이에요.
# collect_dart(...): 위 설정 셀의 종목·연도·분기로 DART 재무제표 6개 계정을 받아 공통 표로 만들어요.
dart = run_step("DART 재무제표", 1, lambda: collect_dart(STOCK_CODE, YEAR, QUARTER, FS_DIV, DART_API_KEY))

# 결과가 있을 때만(None이 아닐 때만) 표를 화면에 보여줘요.
if dart is not None:
    display(dart)
""")

md("""
**API는 대부분 같은 모양이라 함수 하나로 돼요.** 주소 + 결과가 들어 있는 위치(`rows_path`)만 알면 `read_json_table()`이 표로 바꿔 줘요.
ECOS(한국은행 통계)는 키가 있을 때만 돌아요. 거시 지표를 쓸 거면 [ECOS](https://ecos.bok.or.kr/api/)에서 무료로 받아 Secrets에 `ECOS_API_KEY`로 넣어 보세요.

> 키가 있으면 9줄이 **전부 확인 필요**로 나와요. 고장이 아니에요. ECOS는 값과 기준 월은 주지만 **언제 발표했는지(공시일)는 안 줘요.** 공식 API라도 꼬리표가 다 채워지진 않는다는 걸 보여주는 예시예요. 실제로 쓸 땐 발표 일정표를 보고 공시일을 채우거나, 비워 둔 채 확인 필요로 넘겨요.
""")

code("""
# ECOS 키가 없으면 collect_ecos가 SkipStep을 일으켜요.
# SkipStep = "준비가 안 돼서 건너뜀" 신호예요. run_step이 받아서 요약표에 ⏭와 이유를 적어요. 오류가 아니에요.
# stat_code·item_code는 ECOS 통계표 번호예요(722Y001 = 한국은행 기준금리). cycle="M"은 월별.
ecos = run_step("ECOS 기준금리", 1, lambda: collect_ecos(
    ECOS_API_KEY, stat_code="722Y001", cycle="M", start=f"{YEAR}01", end=f"{YEAR}12",
    item_code="0101000", label="한국은행 기준금리", unit="%"))
if ecos is not None:
    display(ecos.tail())
""")

md("""
## 2단계 · 파이썬 라이브러리

누가 API나 웹사이트를 대신 불러 주는 코드 묶음이에요. 쓰기 제일 편하지만 **중간 다리**라서 원천이 어딘지 알고 써야 해요.
FinanceDataReader는 한국 주식을 기본으로 **네이버 금융**에서 받아와요(원천은 한국거래소). 그래서 신뢰도를 `중`으로 적었어요. 5회차에 조별로 다시 정해요.
""")

code("""
# def 함수이름(): 아래 들여쓴 줄들을 한 묶음(함수)으로 만들어 두는 거예요. 만들기만 하고 실행은 run_step이 해요.
def price_records():
    import FinanceDataReader as fdr

    # 오늘부터 30일 전 날짜를 "2026-09-29" 같은 글자로 만들어요 (휴일을 넉넉히 감안).
    start = (datetime.now(KST) - timedelta(days=30)).strftime("%Y-%m-%d")
    # 그 날짜부터 주가를 받아서 .tail(5)로 마지막 5거래일만 남겨요.
    prices = fdr.DataReader(STOCK_CODE, start).tail(5)
    if prices.empty:
        # CollectError = "실패" 신호. run_step이 ❌와 이 문장을 요약표에 적어요.
        raise CollectError("주가가 비어 있어요. 종목코드를 확인해 주세요")

    # ── collect_table: 모든 단계의 공통 출구 ──────────────────────────────
    # 받아온 표를 공통 표 15칸(숫자 하나 = 한 줄)으로 바꿔요. 내 소스 함수도 마지막 줄은 항상 이거예요.
    return collect_table(
        prices,
        # items = {"원래 표의 칸 이름": ("우리가 부를 항목 이름", "단위")}
        #   원래 표의 Close 칸 → '종가'(원), Volume 칸 → '거래량'(주)으로 가져와요. 적지 않은 칸(Open 등)은 버려요.
        {"Close": ("종가", "원"), "Volume": ("거래량", "주")},
        # date_col = 날짜가 든 칸 이름. 여기선 안 적었어요:
        #   주가 표는 날짜가 맨 왼쪽 굵은 글씨(인덱스)에 있어서, 안 적으면 그걸 날짜로 써요.
        level=2,                                  # 수집 방법 단계 (1~5)
        source="FinanceDataReader (네이버 금융 경유, 원천 한국거래소)",
        source_url="https://github.com/FinanceData/FinanceDataReader",  # 원문을 다시 찾아갈 주소
        reliability="중",                         # 상 / 중 / 하. 원천이 아니라 중간 사이트라 '중'
        # NOT_APPLICABLE = "해당 없음": 이 숫자엔 그런 개념이 없다는 뜻.
        #   주가에는 연결/별도 구분이 없으니 basis(기준)는 해당 없음. ('모른다'면 비워 둬야 해요)
        basis=NOT_APPLICABLE,
        # SAME_AS_DATE: 공시일을 기준일과 같게 채워요. 주가처럼 그날 바로 공개되는 숫자에만 써요.
        #   발표일을 알면 "2026-09-15"처럼 적고, 모르면 이 줄을 빼요(→ 확인 필요로 넘어가요).
        disclosed=SAME_AS_DATE,
        stock_code=STOCK_CODE, stock_name=STOCK_NAME)

prices = run_step("주가", 2, price_records)
if prices is not None:
    display(prices)
""")

md("""
## 3단계 · 파일 다운로드

사이트에서 CSV·엑셀을 내려받는 방식이에요. `read_table()`은 주소든 내 파일 경로든 읽고, 한국 사이트에서 자주 나오는 **한글 깨짐(cp949)**, **이름만 .xls인 웹페이지 파일**도 처리해요.

**예시: FRED 미국 10년물 국채금리 CSV.** 첫 칸 이름이 `DATE`이기도 하고 `observation_date`이기도 해서, 이름 대신 "첫 번째 칸"을 날짜로 써요. 휴일은 값이 비어서 확인 필요로 가는 게 정상이에요.
""")

code("""
# series_id="DGS10": FRED의 통계 번호(미국 10년물 국채금리). 다른 번호를 넣으면 다른 지표를 받아요.
def fred_records(series_id="DGS10"):
    start = (datetime.now(KST) - timedelta(days=30)).strftime("%Y-%m-%d")
    # read_table(주소 또는 파일 경로): CSV·엑셀을 표로 읽어요.
    #   f"...{series_id}..."는 글자 안에 { } 속 값을 끼워 넣는 문법이에요.
    table = read_table(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd={start}").tail(5)
    return collect_table(
        # 이번엔 날짜가 일반 칸에 있어서 date_col을 적어요.
        #   칸 이름이 DATE일 때도, observation_date일 때도 있어서 이름 대신 '첫 번째 칸'(columns[0])으로 골라요.
        table, {series_id: ("미국 10년물 국채금리", "%")}, date_col=table.columns[0],
        level=3, source="FRED (미국 세인트루이스 연준)", source_url=f"https://fred.stlouisfed.org/series/{series_id}",
        reliability="상", basis=NOT_APPLICABLE, disclosed=SAME_AS_DATE,
        note="일별 금리라 공시일은 기준일로 봄(실제 게시는 다음 영업일일 수 있음)")

fred = run_step("FRED 미국 금리", 3, fred_records)
if fred is not None:
    display(fred)
""")

md("""
## 4단계 · 크롤링 (최후 수단)

웹페이지 화면에 보이는 표를 코드로 긁어오는 방식이에요. 페이지 디자인이 바뀌면 바로 깨지고, 사이트가 허락하지 않을 수도 있어요.
그래서 `read_html_table()`은 먼저 **robots.txt**(사이트가 "로봇은 여기까지만" 적어둔 파일)를 확인하고, 막혀 있으면 ⏭로 건너뛰어요. 가져온 값은 **전부 확인 필요**로 보내요.

**예시: 한국은행 기준금리 추이 페이지.** 화면의 `변경일자` 머리글 하나 아래에 연도(`2026`)와 날짜(`08월 27일`)가 두 칸으로 나뉘어 있어요. 그래서 칸 이름이 `변경일자`, `변경일자.1`로 겹쳐 읽혀요. 이름 대신 **첫 번째·두 번째 칸**으로 골라서 합쳐 날짜를 만들어요.

> 💡 이 숫자는 1단계 ECOS API에도 있어요. **크롤링하기 전에 같은 데이터가 API로 있는지 먼저 찾아보는 게 원칙이에요.**
""")

code("""
BOK_RATE_URL = "https://www.bok.or.kr/portal/singl/baseRate/list.do?dataSeCd=01&menuNo=200643"

def bok_rate_records():
    # read_html_table(주소, match="표 안의 글자"): 페이지에서 그 글자가 들어간 표를 찾아 읽어요.
    #   읽기 전에 robots.txt(사이트가 '로봇은 여기까지만' 적어둔 파일)를 먼저 보고, 막혀 있으면 ⏭로 건너뛰어요.
    table = read_html_table(BOK_RATE_URL, match="기준금리")

    # 머리글 '변경일자' 하나가 두 칸(연도 | 월일)을 덮고 있어서 이름이 겹쳐요 → 칸 순서로 골라요.
    year, day = table.columns[0], table.columns[1]
    # find_col(표, "글자"): 이름에 그 글자가 들어간 칸을 찾아요. 페이지가 조금 바뀌어도 덜 깨져요.
    rate = find_col(table, "기준금리")

    # 두 칸을 이어 붙여 "2026년 08월 27일" 같은 날짜 칸을 새로 만들어요. (collect_table이 2026-08-27로 바꿔요)
    table["기준일"] = [f"{y}년 {d}" for y, d in zip(table[year], table[day])]

    # 4단계 값은 전부 '확인 필요'로 가요. 페이지가 바뀌면 엉뚱한 칸을 조용히 읽을 수 있어서
    # 사람이 원문 화면과 한 번 대조해야 하거든요. 고장이 아니에요.
    return collect_table(
        table.head(5), {rate: ("한국은행 기준금리", "%")}, date_col="기준일",
        level=4, source="한국은행 기준금리 추이 페이지", source_url=BOK_RATE_URL,
        reliability="상", basis=NOT_APPLICABLE, disclosed=SAME_AS_DATE,
        note="변경일=발표일로 봄")

bok = run_step("한국은행 기준금리 페이지", 4, bok_rate_records)
if bok is not None:
    display(bok)
""")

md("""
## 5단계 · 수동 입력 (자동 수집이 안 되는 자료)

리포트 속 차트 숫자처럼 코드로 못 가져오는 건 **사람이 옮겨 적고 출처를 남겨요.** 칸 이름만 공통 표와 맞추면 `items` 없이 바로 들어가요.
아래 숫자는 **연습용 가짜 숫자**예요. 세 줄이 각각 다른 상황을 보여줘요.

- A: 원문과 대조했다고 `확인` 칸에 O → 형식 통과
- B: 공시일을 몰라서 비움 → 확인 필요
- C: `약 3조`처럼 숫자가 아닌 글자 + 공시일이 기준일보다 빠름 → 확인 필요
""")

code("""
def manual_records():
    # pd.DataFrame([{...}, {...}]): { } 하나가 표의 한 줄이에요.
    # 칸 이름을 공통 표 이름 그대로(항목, 값, 단위, 기준일, 공시일) 쓰면 items·date_col 없이 바로 들어가요.
    # "확인": "O"는 '원문과 직접 대조했다'는 표시예요. 이게 있는 줄만 형식 통과가 돼요.
    # 값은 "1,234", "12.5%"처럼 보이는 그대로 적어도 숫자로 바꿔 줘요. "약 3조"는 못 바꿔서 확인 필요로 가요.
    typed = pd.DataFrame([
        {"항목": "예시 항목 A", "값": "1,234", "단위": "억원", "기준일": "2026.06.30", "공시일": "2026-08-14", "확인": "O"},
        {"항목": "예시 항목 B", "값": "12.5%", "단위": "%", "기준일": "2026년 6월", "공시일": ""},
        {"항목": "예시 항목 C", "값": "약 3조", "단위": "원", "기준일": "2026-06-30", "공시일": "2026-06-01"},
    ])
    return collect_table(typed, level=5, source="연습용 예시 (실제 자료 아님)", source_url="https://example.com",
                         reliability="중", basis=NOT_APPLICABLE)

manual = run_step("손으로 옮긴 숫자 예시", 5, manual_records)
if manual is not None:
    display(manual)
""")

md("""
**내 드라이브의 출처카드로 읽기 (2회차 과제의 `KFA_자료` 폴더).** `USE_DRIVE = True`로 바꾸고 이 셀을 다시 실행하면, 드라이브 연결 창과 구글 로그인 창이 차례로 떠요(둘 다 허용).

- 출처카드에 **적힌 파일만** 읽어요. 적히지 않은 파일은 안 읽어요.
- 지금은 `항목, 값, 단위, 기준일` 칸으로 정리한 CSV·엑셀만 숫자로 읽어요. PDF·기사는 4회차에 AI가 읽고, 모양이 다른 원본 엑셀은 3단계 예시처럼 `items`로 바꿔 줘야 해요. 건너뛴 파일은 이유가 한 줄씩 나와요.
- 출처카드에 `수집 방법` 칸(3 또는 5)을 추가하면 그 값으로 적혀요. 없으면 5로 봐요.
""")

code("""
def drive_records():
    # 설정 셀에서 USE_DRIVE를 안 켰으면 직접 SkipStep을 일으켜 ⏭로 넘어가요.
    if not USE_DRIVE:
        raise SkipStep("USE_DRIVE = False (KFA_자료 폴더를 만들었으면 True로)")
    # 구글 드라이브를 연결하고 '내 드라이브/KFA_자료' 폴더 위치를 받아요.
    root = mount_drive()
    # 출처카드 시트를 읽고 → KFA_자료/files/ 안에서 카드에 적힌 파일만 공통 표로 바꿔요.
    #   root / "files"는 'KFA_자료 폴더 안의 files 폴더'라는 경로 표기예요.
    return collect_from_cards(read_source_cards(CARD_SHEET), root / "files")

drive = run_step("내 드라이브 출처카드", 5, drive_records)
if drive is not None:
    display(drive)
""")

md("""
## ✍️ 과제: 내 소스 붙이기

담당 소스로 아래 셀을 채워요. **표를 받아오는 부분만 소스마다 다르고, `collect_table(...)`로 끝나는 건 같아요.**

| 내 소스가 | 표를 이렇게 받아요 | 예시 셀 |
|---|---|---|
| 1단계 API (JSON) | `read_json_table(주소, "결과가 든 위치", params={...})` | ECOS |
| 2단계 라이브러리 | 라이브러리 함수 결과(DataFrame) 그대로 | 주가 |
| 3단계 파일 | `read_table("주소 또는 파일 경로")` | FRED |
| 4단계 웹페이지 표 | `read_html_table(주소, match="표 안의 글자")` | 한국은행 |
| 5단계 손으로 옮김 | `pd.DataFrame([...])` 또는 출처카드 | 수동 입력 |

**순서:** ① 첫 줄 `raise SkipStep(...)`을 지워요 ② 표를 받아와서 `print(table.head())`로 칸 이름을 확인해요 ③ `items`에 `{"원래 칸 이름": ("항목 이름", "단위")}`를 적어요 ④ 꼬리표(source, source_url, reliability, basis, disclosed)를 채워요 ⑤ 실행해서 ✅가 나오면 끝. 확인 필요가 있으면 비고의 ⚠ 이유를 읽고 고치거나, 왜 못 채우는지 한 줄 남겨요.

> 📘 **단계별로 따라 하기:** 내 소스 단계에 맞춰 키·파일을 어디에 넣고, 어떻게 불러오고, 어떤 코드를 붙이고, 어떻게 나오면 성공인지를 [단계별 가이드](https://github.com/phm0305/KFA-ai-agent-study/blob/main/docs/sessions/02/my_source_guide.md)에 단계마다 붙여 쓸 수 있는 코드와 함께 정리했어요. 아래 셀의 `▼ 단계마다 바뀜` 표시가 그 가이드에서 바꿔 넣을 부분이에요.
""")

code("""
# ✍️ 내 소스 붙이기
# 단계별 코드 예시: docs/sessions/02/my_source_guide.md (위 설명의 '단계별 가이드' 링크)
#   1단계 API → 가이드 '1단계 · 공식 API'      2단계 라이브러리 → '2단계 · 파이썬 라이브러리'
#   3단계 파일 → '3단계 · 파일 다운로드'        4단계 웹페이지 표 → '4단계 · 크롤링'
#   5단계 손으로 옮김 → '5단계 · 수동 입력'
# 'raise SkipStep' 줄 아래가 지금은 1단계(API) 모양이에요. 다른 단계면 ▼ 표시 부분을 가이드 코드로 바꿔요.

MY_LEVEL = 1   # ▼ 단계마다 바뀜: 내 소스의 수집 방법 단계 1~5

def my_records():
    raise SkipStep("아직 내 소스를 안 채웠어요")   # ① 내 소스를 채우기 시작할 때 이 줄을 지워요

    # ② 불러오기 ▼ 단계마다 바뀜 ─────────────────────────────────
    #   1단계: read_json_table(주소, "결과 위치", params={...})  ← 키는 get_key("이름")으로
    #   2단계: 라이브러리 함수 결과 그대로 (예: fdr.DataReader(...))
    #   3단계: read_table("파일 주소") 또는 read_table(mount_drive() / "files" / "파일이름.xlsx")
    #   4단계: read_html_table(주소, match="표 안의 글자")
    #   5단계: pd.DataFrame([{"항목": ..., "값": ..., "단위": ..., "기준일": ..., "공시일": ...}])
    table = read_json_table("https://...", "response.body.items.item", params={})
    print(table.head())   # 칸 이름 확인용. 여기 나온 이름을 아래 items·date_col에 그대로 옮겨 적어요

    # ③ 붙이기: 모양은 모든 단계가 같아요. ▼ 값만 내 소스에 맞게 바꿔요
    return collect_table(
        table,
        {"원래 칸 이름": ("항목 이름", "단위")},   # ▼ items (5단계처럼 칸 이름이 이미 '항목·값'이면 이 줄 삭제)
        date_col="날짜 칸 이름",                   # ▼ 날짜 칸 (날짜가 맨 왼쪽 인덱스면 이 줄 삭제)
        level=MY_LEVEL,
        source="출처 이름",                        # ▼ 출처 이름
        source_url="https://...",                  # ▼ 데이터가 있는 페이지 주소 (사이트 첫 화면 말고)
        reliability="상",                          # ▼ 상 / 중 / 하
        basis=NOT_APPLICABLE,                      # ▼ 재무제표면 "연결" 또는 "별도"
        disclosed=SAME_AS_DATE)                    # ▼ 발표일 "YYYY-MM-DD" / 그날 공개면 SAME_AS_DATE / 모르면 줄 삭제

# ④ 확인: '✅ 내 소스: N줄 (확인 필요 M줄)'이 나오면 성공. 단계별 정상 M은 가이드 각 단계의 '④ 성공 모습'
mine = run_step("내 소스", MY_LEVEL, my_records)
if mine is not None:
    display(mine)
""")

md("""
## 📋 다 합치고 저장하기

단계가 달라도 칸이 같으니까 그냥 이어 붙여지면 성공이에요. CSV 두 개가 저장돼요(왼쪽 📁 파일 탭).

- `w02_records.csv`: 전부
- `w02_records_확인필요.csv`: 사람이 봐야 하는 줄만 (나중에 엔진이 "확인 필요 목록"으로 넘기는 바로 그 파일)
""")

code("""
# 위에서 만든 결과들 중 성공한 것(None이 아닌 것)만 모아요.
frames = [f for f in (dart, ecos, prices, fred, bok, manual, drive, mine) if f is not None]
if frames:
    # pd.concat: 표들을 위아래로 이어 붙여요. 칸이 15개로 같아서 그냥 붙어요. 이게 '공통 표'의 힘이에요.
    everything = pd.concat(frames, ignore_index=True)
    # check_records: 칸 이름·순서·상태가 약속대로인지 검사하고 '✅ 칸 모양 OK: N줄' 요약을 보여줘요.
    check_records(everything)
    # save_records: CSV 두 개로 저장 (전부 / 확인 필요만). 왼쪽 📁에서 내려받을 수 있어요.
    print("💾 저장:", *save_records(everything, "w02_records"))

# 예시마다 ✅ ⏭ ❌ 한 줄씩. 이 표가 노트북 첫 셀의 '정상 결과' 표와 비슷하면 OK.
display(step_summary())
""")

md("""
## 🤖 AI에게 도움받기

**① 내 소스 함수 만들기**: 아래를 복사하고 `[ ]`만 채워서 AI에게 보내요.

```
나는 금융 데이터 수집 스터디를 하고 있어. Colab 노트북에 공통 도구가 이미 실행돼 있어.
쓸 수 있는 함수: read_json_table(url, rows_path, params), read_table(주소나 경로),
read_html_table(url, match), collect_table(table, items, date_col, level, source,
source_url, reliability, basis, disclosed, stock_code, stock_name, note), SkipStep, CollectError,
NOT_APPLICABLE, SAME_AS_DATE.

[내 소스]에서 [받고 싶은 숫자]를 받아서 collect_table로 끝나는 함수 my_records()를 만들어 줘.
- 내 소스: [예: 공공데이터포털 한국전력거래소 계통한계가격 API / 주소: ...]
- 수집 방법 단계: [1~5]
- 이 소스의 응답 예시나 칸 이름: [print(table.head()) 결과를 붙여넣기]
규칙: 공통 도구는 다시 만들지 말 것. 키는 get_key("이름")으로만 읽고 print하지 말 것.
모르는 꼬리표는 지어내지 말고 비워 둘 것(그러면 자동으로 확인 필요가 돼).
```

**② 확인 필요 줄 다듬기**: 확인 필요가 많으면 그 줄을 보여주고 물어봐요.

```
아래는 내 수집 결과 중 '확인 필요'로 분류된 줄이야. 비고의 ⚠ 이유별로
(1) 코드를 고치면 해결되는 것 → 고친 코드
(2) 소스에 정보가 없어서 사람이 판단해야 하는 것 → 어디서 확인하면 되는지
로 나눠서 알려 줘. 숫자를 추측해서 채우지는 마.
[display(everything[everything['상태']=='확인 필요']) 결과 붙여넣기]
```

> AI가 준 코드가 공통 표 모양을 안 지키면 `run_step`이 ❌로 알려줘요. 그때는 `check_records(결과)`를 실행해서 나온 메시지를 AI에게 그대로 보여주면 돼요.

## 📤 제출

**파일 → GitHub에 사본 저장** → 내 레포 `kfa-ai-agent` → 파일 경로 `w02_내소스수집.ipynb` → 커밋 메시지 `2회차 과제`.
자세한 순서는 [2회차 가이드](https://github.com/phm0305/KFA-ai-agent-study/blob/main/docs/sessions/02/README.md)를 봐 주세요.
내 소스가 잘 안 붙으면 [단계별 가이드](https://github.com/phm0305/KFA-ai-agent-study/blob/main/docs/sessions/02/my_source_guide.md)에서 내 단계 칸을 다시 따라 해 봐요.
""")


def to_source(text):
    lines = text.split("\n")
    return [line + "\n" for line in lines[:-1]] + [lines[-1]]


notebook = {
    "cells": [
        {"cell_type": kind, "metadata": {}, "source": to_source(text),
         **({"execution_count": None, "outputs": []} if kind == "code" else {})}
        for kind, text in cells
    ],
    "metadata": {
        "colab": {"provenance": []},
        "kernelspec": {"display_name": "Python 3", "name": "python3"},
        "language_info": {"name": "python"},
    },
    "nbformat": 4,
    "nbformat_minor": 0,
}

OUT.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(f"wrote {OUT.relative_to(ROOT)} ({len(cells)} cells)")
