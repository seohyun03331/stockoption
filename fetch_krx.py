# fetch_krx.py
import pandas as pd
from pykrx import stock
from datetime import datetime
import time

def load_krx_data(market="KOSPI"):
    # -----------------------------------------------
    # 1) 기준일(가까운 영업일) 보정
    # -----------------------------------------------
    base_date = stock.get_nearest_business_day_in_a_week(
        datetime.now().strftime("%Y%m%d")
    )

    # -----------------------------------------------
    # 2) 데이터 수집
    # -----------------------------------------------
    df_fundamental = stock.get_market_fundamental_by_ticker(base_date, market=market)
    df_cap = stock.get_market_cap_by_ticker(base_date, market=market)

    if df_fundamental.empty or df_cap.empty:
        raise ValueError(
            f"{base_date} 기준으로 KRX 데이터를 가져오지 못했습니다."
        )

    # -----------------------------------------------
    # 3) 병합 (시가총액 붙이기)
    # -----------------------------------------------
    df = pd.merge(
        df_fundamental,
        df_cap[["시가총액"]],
        left_index=True,
        right_index=True
    )

    # -----------------------------------------------
    # 4) 종목코드 → 종목명 매핑
    # -----------------------------------------------
    name_map = {}
    for ticker in df.index:
        name_map[ticker] = stock.get_market_ticker_name(ticker)
        time.sleep(0.003)

    df.insert(0, "종목명", df.index.map(name_map))

    # -----------------------------------------------
    # 5) ROE 없으면 계산해서 생성
    #   ROE(%) ≈ (EPS / BPS) * 100
    # -----------------------------------------------
    if "ROE" not in df.columns:
        if ("EPS" in df.columns) and ("BPS" in df.columns):
            df["EPS"] = pd.to_numeric(df["EPS"], errors="coerce")
            df["BPS"] = pd.to_numeric(df["BPS"], errors="coerce")
            df["ROE"] = (df["EPS"] / df["BPS"]) * 100
        else:
            df["ROE"] = pd.NA

    # -----------------------------------------------
    # 6) 숫자 컬럼 강제 변환
    # -----------------------------------------------
    cols_to_num = ["PER", "PBR", "ROE", "시가총액", "DIV"]
    for c in cols_to_num:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # -----------------------------------------------
    # 7) 기본 이상치 제거 (0/음수 제거)
    # -----------------------------------------------
    if "PER" in df.columns:
        df = df[df["PER"] > 0]
    if "PBR" in df.columns:
        df = df[df["PBR"] > 0]
    if "ROE" in df.columns:
        df = df[df["ROE"] > 0]
    if "시가총액" in df.columns:
        df = df[df["시가총액"] > 0]

    # -----------------------------------------------
    # 8) 인덱스(종목코드)를 컬럼으로 빼기 (방어)
    # -----------------------------------------------
    df = df.reset_index()
    first_col = df.columns[0]
    if first_col != "종목코드":
        df = df.rename(columns={first_col: "종목코드"})

    df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)

    # 배당수익률 컬럼명 정리
    if "DIV" in df.columns:
        df = df.rename(columns={"DIV": "배당수익률"})

    # 시총(억원) float 유지
    if "시가총액" in df.columns:
        df["시가총액(억원)"] = df["시가총액"] / 100000000

    return base_date, df


# fetch_krx.py 단독 실행 테스트용
if __name__ == "__main__":
    base_date, df = load_krx_data("KOSPI")
    print("base_date:", base_date)
    print(df.head())