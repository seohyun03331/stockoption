# server.py
from flask import Flask, jsonify, send_file, request
from fetch_krx import load_krx_data
import os
import pandas as pd
from io import BytesIO

app = Flask(__name__)

def apply_invest_filter(df: pd.DataFrame, choice: str):
    """choice: '1'(안정추구) / '2'(안정성장) / '3'(적극성장)"""
    # 기본값
    PER_max, PBR_max, ROE_min, DIV_min, CAP_min = 20, 2, 10, 1.5, 0
    sort_by = "ROE"

    df_work = df.copy()

    # 시가총액 quantile 계산을 위해 숫자화 보정
    if "시가총액" in df_work.columns:
        df_work["시가총액"] = pd.to_numeric(df_work["시가총액"], errors="coerce")

    if choice == "1":
        PER_max, PBR_max, ROE_min, DIV_min = 12, 1.2, 5, 3.0
        CAP_min = df_work["시가총액"].quantile(0.80) if "시가총액" in df_work.columns else 0
        sort_by = "배당수익률" if "배당수익률" in df_work.columns else "ROE"
    elif choice == "3":
        PER_max, PBR_max, ROE_min, DIV_min = 50, 5, 15, 0
        CAP_min = 0
        sort_by = "ROE"
    else:
        # 안정성장형(기본)
        PER_max, PBR_max, ROE_min, DIV_min = 20, 2, 10, 1.5
        CAP_min = df_work["시가총액"].quantile(0.50) if "시가총액" in df_work.columns else 0
        sort_by = "ROE"

    cond = pd.Series(True, index=df_work.index)

    if "PER" in df_work.columns:
        cond &= (df_work["PER"] < PER_max)
    if "PBR" in df_work.columns:
        cond &= (df_work["PBR"] < PBR_max)
    if "ROE" in df_work.columns:
        cond &= (df_work["ROE"] > ROE_min)
    if "배당수익률" in df_work.columns:
        cond &= (df_work["배당수익률"] > DIV_min)
    if "시가총액" in df_work.columns:
        cond &= (df_work["시가총액"] > CAP_min)

    out = df_work[cond].copy()

    if sort_by in out.columns:
        out = out.sort_values(by=sort_by, ascending=False)

    return out


@app.route("/api/stocks")
def api_stocks():
    try:
        market = request.args.get("market", "KOSPI")
        base_date, df = load_krx_data(market)
        return jsonify({
            "baseDate": base_date,
            "columns": df.columns.tolist(),
            "data": df.to_dict(orient="records")
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/download.xlsx")
def download_excel():
    """
    예) /download.xlsx?choice=2&market=KOSPI
    """
    try:
        choice = request.args.get("choice", "2")
        market = request.args.get("market", "KOSPI")

        base_date, df = load_krx_data(market)
        filtered = apply_invest_filter(df, choice)

        # 엑셀을 메모리(BytesIO)에 저장해서 바로 내려줌
        output = BytesIO()
        filtered.to_excel(output, index=False, engine="openpyxl")
        output.seek(0)

        filename = f"{market}_{base_date}_filtered.xlsx"
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/")
def index():
    here = os.path.dirname(os.path.abspath(__file__))
    index_path = os.path.join(here, "index.html")
    return send_file(index_path)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)