# 2회차 · 내 소스 붙이기: 단계별 따라 하기

[2회차 가이드](README.md) 4번(내 소스 붙이기)을 **수집 방법 1~5단계별로** 펼친 문서예요.
내 소스가 몇 단계인지 고르고, 그 단계 칸만 위에서 아래로 따라 하면 돼요.

모든 단계는 같은 네 걸음이에요.

| 걸음 | 하는 일 | 단계마다 다른가 |
|---|---|---|
| ① 넣기 | 키·파일·숫자를 Colab이 읽을 수 있는 곳에 둠 | 다름 |
| ② 불러오기 | 표로 받아와서 `print(table.head())`로 칸 이름 보기 | 다름 |
| ③ 붙이기 | `collect_table(...)`로 공통 표 15칸으로 바꿈 | **같음** |
| ④ 확인 | `✅ 내 소스: N줄 (확인 필요 M줄)`이 나오면 성공 | 단계마다 M이 다름 |

> 준비: [2회차 가이드](README.md) 1~3번(템플릿 열기 → 키 확인 → [내 소스 단계 확인](README.md#3-1-수집-방법-15단계란) → 모두 실행)을 한 번 끝낸 상태여야 해요. 공통 도구 셀이 실행돼 있어야 아래 함수들이 동작해요.

---

## 0. 내 소스는 몇 단계?

단계별 뜻·예·사람이 확인할 것은 [2회차 가이드 3-1](README.md#3-1-수집-방법-15단계란) 표에 있어요. 헷갈리면 아래 질문을 위에서부터 읽다가 처음 "예"가 나오는 단계예요.

| 질문 | 예면 |
|---|---|
| 기관이 **키를 발급**해 주고 주소로 데이터를 받게 해 주나요? ("Open API", "인증키 신청") | **1단계** 공식 API |
| `pip install`로 설치하는 **코드 묶음(라이브러리)** 이 대신 받아 주나요? | **2단계** 파이썬 라이브러리 |
| 사이트에 CSV·엑셀 **다운로드 버튼**이 있나요? | **3단계** 파일 다운로드 |
| 다운로드 버튼 없이 웹페이지 **화면에 표만** 있나요? | **4단계** 크롤링 |
| PDF·리포트 차트·유료 자료라 **사람이 옮겨 적어야** 하나요? | **5단계** 수동 입력 |

- 같은 데이터가 더 위 단계로도 있으면 위 단계를 써요 (예: 한국은행 기준금리 페이지 = 4단계지만 ECOS API = 1단계).
- 조에 기여할 소스는 1~2단계를 권장해요.

---

## 공통: 내 소스 셀의 뼈대

노트북 **✍️ 과제: 내 소스 붙이기** 셀을 아래 모양으로 바꿔요. 단계별로 바뀌는 건 `# ② 불러오기` 부분과 `collect_table` 안의 값뿐이에요.

```python
MY_LEVEL = 1          # ← 내 소스 단계

def my_records():
    # ② 불러오기: 단계별 코드 (아래 각 단계 칸 참고)
    table = ...
    print(table.head())   # 칸 이름 확인용. 다 되면 지워도 돼요

    # ③ 붙이기: 공통 표로
    return collect_table(
        table,
        {"원래 칸 이름": ("항목 이름", "단위")},   # 가져올 숫자 칸
        date_col="날짜 칸 이름",                    # 날짜가 든 칸
        level=MY_LEVEL,
        source="출처 이름",
        source_url="https://데이터가 있는 페이지",
        reliability="상",            # 상 / 중 / 하
        basis=NOT_APPLICABLE,        # 재무제표면 "연결" 또는 "별도"
        disclosed=SAME_AS_DATE,      # 공시일. 아래 표 참고
    )

mine = run_step("내 소스", MY_LEVEL, my_records)
if mine is not None:
    display(mine)
```

**꼬리표 고르는 법**

| 칸 | 이렇게 정해요 |
|---|---|
| `items` | `{"표에 적힌 칸 이름 그대로": ("우리가 부를 이름", "단위")}`. 여러 칸이면 쉼표로 이어 적기 |
| `date_col` | 날짜가 든 칸 이름. `print(table.head())`에서 **날짜가 맨 왼쪽 굵은 글씨(인덱스)** 로 나오면 안 적어도 돼요 |
| `source_url` | 사이트 첫 화면 말고 **그 숫자를 다시 찾아갈 수 있는 페이지** |
| `reliability` | 상: 공시·공식 통계 / 중: 증권사 리포트·중간 사이트 / 하: 기사·블로그 |
| `basis` | 재무제표 숫자면 `"연결"` 또는 `"별도"`, 아니면 `NOT_APPLICABLE` |
| `disclosed` | 주가·환율·금리처럼 **그날 바로 공개**되면 `SAME_AS_DATE` / 발표일을 알면 `"2026-09-15"` / **모르면 줄 자체를 빼기** (지어내지 않기. 빼면 확인 필요로 가요) |
| `stock_code`, `stock_name` | 특정 회사 숫자면 `stock_code=STOCK_CODE, stock_name=STOCK_NAME` 추가 |

> 키를 쓰는 소스라면 키는 꼭 `get_key("이름")`으로 읽어요. `"abc123..."`처럼 키 값을 셀에 직접 적으면 GitHub에 올릴 때 공개돼요.

---

## 1단계 · 공식 API

### ① 넣기: 키를 Secrets에 등록

1. 기관 사이트에서 API 활용 신청 → 키 발급
   - 공공데이터포털(data.go.kr)은 키가 **Encoding / Decoding** 두 개 나와요. **Decoding 키**를 써요.
   - 신청 직후엔 바로 안 될 수 있어요. 에러가 나면 1~2시간 뒤 다시 해 봐요.
2. Colab 왼쪽 🔑 → **새 보안 비밀 추가** → 이름(예: `DATA_GO_KR_KEY`), 값에 키 붙여넣기 → **노트북 액세스** 켜기

### ② 불러오기: `read_json_table(주소, "결과 위치", params={...})`

API 설명 페이지(활용가이드)에서 세 가지를 찾아요.

| 찾을 것 | 어디에 있나 | 예 |
|---|---|---|
| 요청 주소 | "요청 주소", "End Point" | `https://apis.data.go.kr/.../getXXX` |
| 요청 변수 | "요청 변수", "Request Parameter" | `serviceKey`, `numOfRows`, 기간 |
| 응답 형식 변수 | `type`, `_type`, `resultType`, `dataType` 중 하나 | `json`으로 (기본이 XML인 곳이 많아요) |

**결과 위치(`rows_path`)를 모를 때 요령:** 일단 `"?"`를 넣고 실행해요. 에러 메시지가 그 자리에 무엇이 있는지 알려줘요.

```python
KEY = get_key("DATA_GO_KR_KEY")
URL = "https://apis.data.go.kr/.../getXXX"      # 활용가이드의 요청 주소
PARAMS = {"serviceKey": KEY, "type": "json", "numOfRows": 100, "pageNo": 1}

table = read_json_table(URL, "?", params=PARAMS)
```

```
CollectError: 응답에서 '?'를 못 찾았어요. 그 자리에 있는 것: ['response'] / 응답 앞부분: {"response": {"header": ..., "body": {"items": {"item": [ ...
```

→ `"response"`를 넣고 다시 실행 → `['header', 'body']`가 보이면 `"response.body"` → … 이렇게 한 칸씩 내려가서 **`[ ]`(목록) 바로 앞**까지 적어요. 공공데이터포털은 대부분 `"response.body.items.item"`이에요.

### ③ 붙이기

```python
MY_LEVEL = 1

def my_records():
    key = get_key("DATA_GO_KR_KEY")
    if not key:
        raise SkipStep("DATA_GO_KR_KEY가 없어요 (Secrets 등록 + 노트북 액세스)")
    table = read_json_table(
        "https://apis.data.go.kr/.../getXXX",
        "response.body.items.item",
        params={"serviceKey": key, "type": "json", "numOfRows": 100, "pageNo": 1},
    )
    print(table.head())
    return collect_table(
        table, {"smp": ("SMP 월평균", "원/kWh")}, date_col="tradeYm",
        level=MY_LEVEL, source="공공데이터포털 전력거래소 SMP API",
        source_url="https://www.data.go.kr/data/.../openapi.do", reliability="상",
        basis=NOT_APPLICABLE, disclosed=SAME_AS_DATE)

mine = run_step("내 소스", MY_LEVEL, my_records)
if mine is not None:
    display(mine)
```

(`smp`, `tradeYm`, 주소의 `...`는 예시예요. 내 API의 `print(table.head())`에 나온 칸 이름으로 바꿔요.)

### ④ 성공 모습

```
✅ 내 소스: 24줄 (확인 필요 0줄)
```

- **확인 필요 0줄이 목표**예요. 공식 API는 꼬리표를 거의 다 채울 수 있어요.
- 확인 필요가 전부 `⚠ 공시일 비어 있음`이면: ECOS처럼 그 API가 발표일을 안 주는 경우예요. 발표 일정표에서 찾아 `disclosed=`에 넣거나, 못 찾으면 이유를 한 줄 적어요.

### 막히면

| 메시지 | 해결 |
|---|---|
| `응답이 JSON이 아니에요` | 형식 변수를 `json`으로 줬는지 확인. 공공데이터포털은 키가 틀려도 XML로 에러를 돌려줘서 이 메시지가 나와요 → 키 확인 |
| 응답 앞부분에 `SERVICE_KEY_IS_NOT_REGISTERED` | Encoding 키를 썼거나 아직 승인 전. Decoding 키로 바꾸고, 그래도 안 되면 1~2시간 뒤 |
| `'...' 아래가 비어 있어요` | 기간·조건에 맞는 데이터가 없음. 기간을 넓혀 보기 |
| `...가 401 응답` / `403 응답` | 키가 틀렸거나 그 API 활용 신청이 안 됨 |

---

## 2단계 · 파이썬 라이브러리

### ① 넣기: 설치

FinanceDataReader는 템플릿 설치 셀에 이미 들어 있어요. 다른 라이브러리면 내 소스 셀 **위에** 셀을 하나 만들어 설치해요.

```python
!pip install -q pykrx
```

### ② 불러오기

라이브러리 설명서(GitHub README)에서 "데이터 가져오기" 예시 한 줄을 그대로 써요. 결과가 표(DataFrame)면 바로 ③으로 가요.

```python
import FinanceDataReader as fdr
table = fdr.DataReader("USD/KRW", "2026-10-01")
print(table.head())
```

```
                   Open         High  ...  Volume    Adj Close
2026-10-22  1325.810059  1326.520020  ...       0  1325.989990
...
```

날짜가 맨 왼쪽(인덱스)에 있으니 `date_col`은 안 적어도 돼요.

### ③ 붙이기

```python
MY_LEVEL = 2

def my_records():
    import FinanceDataReader as fdr
    table = fdr.DataReader("USD/KRW", "2026-10-01").tail(5)
    print(table.head())
    return collect_table(
        table, {"Close": ("원/달러 환율 종가", "원")},
        level=MY_LEVEL, source="FinanceDataReader (USD/KRW)",
        source_url="https://github.com/FinanceData/FinanceDataReader", reliability="중",
        basis=NOT_APPLICABLE, disclosed=SAME_AS_DATE)

mine = run_step("내 소스", MY_LEVEL, my_records)
if mine is not None:
    display(mine)
```

### ④ 성공 모습

```
✅ 내 소스: 5줄 (확인 필요 0줄)
```

- **확인 필요 0줄이 목표**예요.
- 신뢰도는 라이브러리가 **어디서 받아오는지(원천)** 를 보고 정해요. 원천을 모르면 `중`으로 두고 비고에 적어요. (예: FinanceDataReader 한국 주식은 네이버 금융 경유 → `중`)

### 막히면

| 메시지 | 해결 |
|---|---|
| `ModuleNotFoundError` (예상 못 한 오류) | 설치 셀을 먼저 실행. 런타임을 초기화했으면 다시 설치 |
| `표에 없는 칸` | 칸 이름 대소문자까지 똑같이 (`Close` ≠ `close`) |
| 표가 비어 있음 | 종목코드·기호·기간 확인. 주말·휴일만 고르면 비어요 |

---

## 3단계 · 파일 다운로드

### ① 넣기: 셋 중 하나

| 방법 | 언제 | `read_table`에 넣을 것 |
|---|---|---|
| **A. 다운로드 주소 그대로** (추천) | 다운로드 버튼에 **오른쪽 클릭 → 링크 주소 복사**가 되고, 그 주소를 새 탭에 붙이면 파일이 바로 받아질 때 | `"https://...csv"` |
| **B. 내 드라이브** | 주소가 안 잡히는 사이트(버튼을 눌러야만 받아짐) | `mount_drive() / "files" / "파일이름.xlsx"` |
| C. Colab에 바로 올리기 | 한 번만 써 볼 때 | `"/content/파일이름.xlsx"` |

- B: 받은 파일을 구글 드라이브 `KFA_자료/files/` 폴더에 올려요. 2회차 과제 3번에서 만든 폴더예요. 처음 실행하면 드라이브 연결 창이 떠요(허용).
- C: Colab 왼쪽 📁 → 업로드 버튼. **런타임을 초기화하면 파일이 사라져요.** 다음 회차에도 쓸 거면 B로.
- 파일 이름은 띄어쓰기·확장자까지 똑같이 적어요. 헷갈리면 파일 이름을 영어로 바꿔 두면 편해요.

### ② 불러오기: `read_table(...)`

```python
table = read_table(mount_drive() / "files" / "monthly_export.xlsx")
print(table.head())
```

엑셀 맨 위에 제목·단위 줄이 있으면 칸 이름이 `Unnamed: 0`처럼 나와요. **칸 이름이 있는 줄 앞에 몇 줄이 있는지** 세어서 `skiprows`로 건너뛰어요.

```python
table = read_table(mount_drive() / "files" / "monthly_export.xlsx", skiprows=3)
```

```
        기간     반도체
0  2026.07  12,345
1  2026.08  13,001
```

시트가 여러 개면 `sheet_name="시트 이름"`을 붙여요. 한글이 깨진 CSV(cp949)와 이름만 .xls인 파일은 `read_table`이 알아서 처리해요.

**연도가 가로로 놓인 표면 뒤집어요.** 통계 사이트 엑셀은 이런 모양이 많아요.

```
     항목    2024    2025
0  매출액   1,000   1,200
1  영업이익   100     130
```

`collect_table`은 "칸 하나 = 항목 하나" 모양을 받아요. 항목 칸을 기준으로 뒤집으면 날짜가 왼쪽(인덱스)으로 가서 `date_col`도 필요 없어져요.

```python
table = table.set_index("항목").T
```

```
항목      매출액  영업이익
2024    1,000     100
2025    1,200     130
```

### ③ 붙이기

```python
MY_LEVEL = 3

def my_records():
    table = read_table(mount_drive() / "files" / "monthly_export.xlsx", skiprows=3)
    print(table.head())
    return collect_table(
        table, {"반도체": ("반도체 수출액", "백만달러")}, date_col="기간",
        level=MY_LEVEL, source="한국무역협회 품목별 수출 통계",
        source_url="https://(다운로드 버튼이 있는 페이지 주소)", reliability="상",
        basis=NOT_APPLICABLE, disclosed="2026-09-15")

mine = run_step("내 소스", MY_LEVEL, my_records)
if mine is not None:
    display(mine)
```

- `source_url`은 파일 주소가 아니라 **다운로드 버튼이 있는 페이지** 주소예요. 나중에 원문을 다시 찾아가는 용도예요.
- 공시일: 통계 발표일을 알면 적고, 모르면 `disclosed=` 줄을 빼요(확인 필요로 가요).

### ④ 성공 모습

```
✅ 내 소스: 2줄 (확인 필요 0줄)
```

- 공시일을 몰라서 뺐다면 `확인 필요 2줄`(전부 `⚠ 공시일 비어 있음`)도 정상이에요. 과제 마지막에 "발표일을 못 찾음" 한 줄 적어요.
- 값 칸이 `12345`처럼 **숫자로** 바뀌었는지 봐요. `1,234` `△500` `12.5%`는 코드가 알아서 바꿔요.

### 막히면

| 메시지 | 해결 |
|---|---|
| `파일이 없어요: ...` | 파일 이름(띄어쓰기·확장자)과 폴더(`KFA_자료/files/`) 확인 |
| `내 드라이브 맨 위에 'KFA_자료' 폴더가 없어요` | 폴더 이름 밑줄까지 똑같이, 내 드라이브 맨 위에 |
| `파일 안이 표가 아닌 웹페이지예요` | A 방법 주소가 로그인 페이지·안내 페이지였어요. B 방법으로 |
| `표에 없는 칸: [...]` | `skiprows` 숫자를 바꿔 가며 `print(table.head())`에 진짜 칸 이름이 나올 때까지 |
| `CSV 글자를 못 읽었어요` | 엑셀에서 **CSV UTF-8**로 다시 저장 |

---

## 4단계 · 크롤링 (최후 수단)

### ① 넣기: 크롤링해도 되는지 확인

- 같은 데이터가 **API나 다운로드 파일로 있으면 그걸 써요.** (예: 한국은행 기준금리 페이지 = ECOS API에도 있음)
- 로그인해야 보이는 페이지, 이용약관에서 수집을 금지한 사이트는 하지 않아요.
- `read_html_table`이 **robots.txt**(사이트가 "로봇은 여기까지만" 적어둔 파일)를 먼저 확인하고, 막혀 있으면 ⏭로 건너뛰어요. 그 자료는 5단계로 옮겨요.

### ② 불러오기: `read_html_table(주소, match="표 안의 글자")`

`match`에는 **그 표 안에만 있는 글자**를 적어요(머리글이 좋아요).

```python
URL = "https://www.bok.or.kr/portal/singl/baseRate/list.do?dataSeCd=01&menuNo=200643"
table = read_html_table(URL, match="기준금리")
print(table.head())
```

```
   변경일자   변경일자.1  기준금리
0  2026  08월 27일  3.00
1  2026  07월 16일  2.75
```

화면에서 두 칸을 합친 머리글(`변경일자`)은 `변경일자`, `변경일자.1`처럼 이름이 겹쳐 나와요. 이럴 땐 칸 이름 대신 **몇 번째 칸인지**(`table.columns[0]`)로 고르거나, 이름 일부로 찾는 `find_col(table, "기준금리")`를 써요. 페이지가 조금 바뀌어도 덜 깨져요.

### ③ 붙이기

```python
MY_LEVEL = 4
URL = "https://www.bok.or.kr/portal/singl/baseRate/list.do?dataSeCd=01&menuNo=200643"

def my_records():
    table = read_html_table(URL, match="기준금리")
    print(table.head())
    year, day = table.columns[0], table.columns[1]
    rate = find_col(table, "기준금리")
    table["기준일"] = [f"{y}년 {d}" for y, d in zip(table[year], table[day])]   # "2026년 08월 27일"
    return collect_table(
        table.head(5), {rate: ("한국은행 기준금리", "%")}, date_col="기준일",
        level=MY_LEVEL, source="한국은행 기준금리 추이 페이지", source_url=URL,
        reliability="상", basis=NOT_APPLICABLE, disclosed=SAME_AS_DATE, note="변경일=발표일로 봄")

mine = run_step("내 소스", MY_LEVEL, my_records)
if mine is not None:
    display(mine)
```

### ④ 성공 모습

```
✅ 내 소스: 5줄 (확인 필요 5줄)
```

- **전부 확인 필요가 정상이에요.** 크롤링은 페이지가 바뀌면 조용히 엉뚱한 칸을 읽을 수 있어서, 사람이 원문 화면과 한 번 대조할 때까지 확인 필요로 둬요(비고 `⚠ 크롤링 값: 원문 화면과 한 번 대조`).
- 원문 화면과 숫자를 하나씩 맞춰 봤다면, `return` 바로 위에 아래 두 줄을 넣고 `collect_table`에 `keep=`을 더하면 형식 통과로 바뀌어요. **직접 대조한 경우에만** 써요.

  ```python
      table = table.head(5)
      table["확인"] = "O"
      return collect_table(table, {rate: ("한국은행 기준금리", "%")}, date_col="기준일", keep={"확인": "확인"},
                           level=MY_LEVEL, ...)   # 나머지는 위와 같게
  ```

### 막히면

| 메시지 | 해결 |
|---|---|
| ⏭ `robots.txt가 코드 수집을 막고 있어요` | 그 자료는 5단계(수동 입력 + 출처카드)로 |
| `'...'가 들어간 표를 못 찾았어요` | 표가 자바스크립트로 그려지는 페이지예요. 같은 데이터의 API·파일을 찾거나 5단계로 |
| `표가 N개뿐이에요` | `index=` 숫자를 0부터 바꿔 가며 원하는 표 찾기 |
| `'...'가 들어간 칸이 없어요` | 메시지 뒤 "지금 표의 칸" 목록을 보고 `find_col` 글자나 `columns[번호]`를 고치기 |

---

## 5단계 · 수동 입력

리포트 차트 숫자, PDF 표처럼 코드로 못 가져오는 숫자를 사람이 옮겨 적는 단계예요.

### ① 넣기: 셋 중 하나

| 방법 | 언제 |
|---|---|
| **A. 셀에 직접 적기** (추천) | 숫자가 10개 안쪽일 때 |
| B. 드라이브 출처카드 | 숫자가 많거나, 원본 파일을 같이 보관하고 싶을 때. **2회차 과제 3번**과 같은 방법 |

- 원본 PDF·리포트는 **드라이브에만** 두고 GitHub에는 올리지 않아요(레포가 Public이라 저작권 문제).
- B 방법은 내 소스 셀을 고치지 않아도 돼요. 노트북 설정 셀에서 `USE_DRIVE = True`로 바꾸고 **모두 실행**하면 요약표의 `내 드라이브 출처카드` 줄로 들어와요. 출처카드 시트 이름은 `출처카드`, 칸은 `파일명, 출처, URL, 기준일, 신뢰도`(+ 선택 `수집 방법`), 파일은 `KFA_자료/files/`에 `항목, 값, 단위, 기준일` 칸을 가진 CSV·엑셀로 넣어요.

### ② 불러오기 = 표 직접 만들기 (A 방법)

칸 이름을 **공통 표 이름 그대로**(`항목`, `값`, `단위`, `기준일`, `공시일`) 쓰면 `items`·`date_col` 없이 바로 들어가요.

### ③ 붙이기

```python
MY_LEVEL = 5

def my_records():
    table = pd.DataFrame([
        {"항목": "국내 시장 점유율", "값": "32.5%", "단위": "%", "기준일": "2026-06", "공시일": "2026-09-15", "확인": "O"},
        {"항목": "연간 생산능력",   "값": "120",   "단위": "만톤", "기준일": "2025",    "공시일": "2026-09-15"},
    ])
    return collect_table(
        table, level=MY_LEVEL, source="OO증권 산업 리포트 (2026-09-15) p.12 차트",
        source_url="https://(리포트를 다시 찾을 수 있는 페이지)", reliability="중",
        basis=NOT_APPLICABLE)

mine = run_step("내 소스", MY_LEVEL, my_records)
if mine is not None:
    display(mine)
```

- `source`에 **몇 쪽 어느 차트인지**까지 적어 두면 4회차 원본 대조가 쉬워요.
- 원문과 다시 한 번 맞춰 본 줄만 `"확인": "O"`를 적어요.
- 숫자는 보이는 그대로 적어요. `약 3조`처럼 숫자가 아닌 글자는 그대로 두면 확인 필요로 가요(지어서 바꾸지 않기).

### ④ 성공 모습

```
✅ 내 소스: 2줄 (확인 필요 1줄)
```

- `확인 O`를 적은 줄은 형식 통과, 안 적은 줄은 `⚠ 손으로 옮긴 값: 원문과 대조`로 확인 필요가 정상이에요.

---

## 마지막: 합치고 저장, 성공 판정

1. 내 소스 셀에서 `✅ 내 소스: N줄`을 확인해요.
2. 맨 아래 **📋 다 합치고 저장하기** 셀을 다시 실행해요.
3. 아래처럼 나오면 끝이에요.

```
✅ 칸 모양 OK: (32 + N)줄 (형식 통과 ... · 확인 필요 ...)
💾 저장: w02_records.csv w02_records_확인필요.csv
```

요약표의 `내 소스` 줄이 ✅이고 줄 수가 N이면 돼요. (ECOS 키가 있으면 41 + N, 크롤링 예시가 ⏭면 27 + N)

**단계별 정상 기준 한눈에**

| 단계 | 결과 | 확인 필요 | 확인 필요가 나오면 |
|---|---|---|---|
| 1 공식 API | ✅ | 0이 목표 | 공시일을 안 주는 API면 정상. 이유 한 줄 |
| 2 라이브러리 | ✅ | 0이 목표 | 비고 ⚠ 이유를 보고 꼬리표 고치기 |
| 3 파일 | ✅ | 0, 또는 공시일 모를 때 전부 | 발표일을 찾거나 이유 한 줄 |
| 4 크롤링 | ✅ | **전부** (정상) | 원문 화면과 대조. 대조했으면 `확인` O |
| 5 수동 | ✅ | `확인` O 안 적은 줄 전부 (정상) | 원문과 대조 후 O |

**✅가 나와도 눈으로 세 가지만 봐요.** "형식 통과"는 모양이 맞다는 뜻이지 숫자가 맞다는 뜻은 아니에요.

- [ ] 원문(사이트·파일·리포트)에서 한 줄을 골라 **값**이 같은지
- [ ] **단위**가 맞는지 (원 / 백만원 / 억원, % / %p 헷갈리기 쉬워요)
- [ ] **기준일**이 그 숫자의 시점이 맞는지 (발표한 날이 아니라 숫자가 가리키는 날)

그다음은 [2회차 가이드 5번(GitHub에 올리기)](README.md#5-github에-올리기)으로 가요.

> 코드가 막히면 노트북 맨 아래 **🤖 AI에게 도움받기 ①** 문장에 `print(table.head())` 결과를 붙여서 물어봐요. AI가 준 코드도 마지막 줄이 `return collect_table(...)`이어야 해요.
