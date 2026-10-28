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
STOCK_CODE = "005930"
STOCK_NAME = "삼성전자"
YEAR = 2026
QUARTER = 2          # 1·2·3·4 (4 = 사업보고서)
FS_DIV = "CFS"       # CFS 연결 / OFS 별도
USE_DRIVE = False    # 내 드라이브 KFA_자료 폴더를 만들었으면 True
CARD_SHEET = "출처카드"
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
dart = run_step("DART 재무제표", 1, lambda: collect_dart(STOCK_CODE, YEAR, QUARTER, FS_DIV, DART_API_KEY))
if dart is not None:
    display(dart)
""")

md("""
**API는 대부분 같은 모양이라 함수 하나로 돼요.** 주소 + 결과가 들어 있는 위치(`rows_path`)만 알면 `read_json_table()`이 표로 바꿔 줘요.
ECOS(한국은행 통계)는 키가 있을 때만 돌아요. 거시 지표를 쓸 거면 [ECOS](https://ecos.bok.or.kr/api/)에서 무료로 받아 Secrets에 `ECOS_API_KEY`로 넣어 보세요.

> 키가 있으면 9줄이 **전부 확인 필요**로 나와요. 고장이 아니에요. ECOS는 값과 기준 월은 주지만 **언제 발표했는지(공시일)는 안 줘요.** 공식 API라도 꼬리표가 다 채워지진 않는다는 걸 보여주는 예시예요. 실제로 쓸 땐 발표 일정표를 보고 공시일을 채우거나, 비워 둔 채 확인 필요로 넘겨요.
""")

code("""
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
def price_records():
    import FinanceDataReader as fdr
    start = (datetime.now(KST) - timedelta(days=30)).strftime("%Y-%m-%d")
    prices = fdr.DataReader(STOCK_CODE, start).tail(5)
    if prices.empty:
        raise CollectError("주가가 비어 있어요. 종목코드를 확인해 주세요")
    return collect_table(
        prices, {"Close": ("종가", "원"), "Volume": ("거래량", "주")},
        level=2, source="FinanceDataReader (네이버 금융 경유, 원천 한국거래소)",
        source_url="https://github.com/FinanceData/FinanceDataReader", reliability="중",
        basis=NOT_APPLICABLE, disclosed=SAME_AS_DATE, stock_code=STOCK_CODE, stock_name=STOCK_NAME)

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
def fred_records(series_id="DGS10"):
    start = (datetime.now(KST) - timedelta(days=30)).strftime("%Y-%m-%d")
    table = read_table(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd={start}").tail(5)
    return collect_table(
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

**예시: 한국은행 기준금리 추이 페이지.** 연도와 "05월 29일"이 다른 칸에 있어서 합쳐서 날짜를 만들어요.

> 💡 이 숫자는 1단계 ECOS API에도 있어요. **크롤링하기 전에 같은 데이터가 API로 있는지 먼저 찾아보는 게 원칙이에요.**
""")

code("""
BOK_RATE_URL = "https://www.bok.or.kr/portal/singl/baseRate/list.do?dataSeCd=01&menuNo=200643"

def bok_rate_records():
    table = read_html_table(BOK_RATE_URL, match="기준금리")
    year, day, rate = (find_col(table, k) for k in ("연도", "변경일자", "기준금리"))
    table["기준일"] = [f"{y}년 {d}" for y, d in zip(table[year], table[day])]
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
    if not USE_DRIVE:
        raise SkipStep("USE_DRIVE = False (KFA_자료 폴더를 만들었으면 True로)")
    root = mount_drive()
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
""")

code("""
MY_LEVEL = 1

def my_records():
    raise SkipStep("아직 내 소스를 안 채웠어요")
    table = read_json_table("https://...", "response.body.items.item", params={})
    print(table.head())
    return collect_table(
        table, {"원래 칸 이름": ("항목 이름", "단위")}, date_col="날짜 칸 이름",
        level=MY_LEVEL, source="출처 이름", source_url="https://...", reliability="상",
        basis=NOT_APPLICABLE, disclosed=SAME_AS_DATE)

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
frames = [f for f in (dart, ecos, prices, fred, bok, manual, drive, mine) if f is not None]
if frames:
    everything = pd.concat(frames, ignore_index=True)
    check_records(everything)
    print("💾 저장:", *save_records(everything, "w02_records"))
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
