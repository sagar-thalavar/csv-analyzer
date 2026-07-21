#!/usr/bin/env python3
"""
CSV Analyzer & PDF Tools Suite - Flask Web App
Enhanced with pandas, visualizations, data cleaning, filtering & stateless PDF operations.
"""

from __future__ import annotations

import io
import json
import os
import base64
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import pandas as pd
import numpy as np
from flask import (
    Flask, request, render_template, jsonify,
    send_file
)

import pdf_tools

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB

# ─── Palette ──────────────────────────────────────────────────────────────────
PALETTE = ["#00d4aa", "#7c3aed", "#f59e0b", "#ef4444", "#3b82f6", "#10b981", "#f97316", "#8b5cf6"]
sns.set_theme(style="darkgrid", palette=PALETTE)
plt.rcParams.update({
    "figure.facecolor": "#0f0f1a",
    "axes.facecolor": "#1a1a2e",
    "axes.edgecolor": "#2d2d4e",
    "axes.labelcolor": "#c4c4e0",
    "xtick.color": "#8888aa",
    "ytick.color": "#8888aa",
    "text.color": "#c4c4e0",
    "grid.color": "#2d2d4e",
    "grid.alpha": 0.5,
})


# ─── Helpers ──────────────────────────────────────────────────────────────────

def fig_to_b64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=120)
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode()
    plt.close(fig)
    return encoded


def load_df_from_req() -> tuple[pd.DataFrame | None, str | None]:
    body = request.json or {}
    csv_data = body.get("csv_data")
    if not csv_data:
        return None, "No CSV data received"
    try:
        df = pd.read_csv(io.StringIO(csv_data))
        return df, None
    except Exception as e:
        return None, f"Failed to parse CSV: {str(e)}"


def df_summary(df: pd.DataFrame) -> dict:
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    text_cols = df.select_dtypes(exclude="number").columns.tolist()
    missing = df.isnull().sum().to_dict()
    duplicates = int(df.duplicated().sum())

    stats = {}
    for col in numeric_cols:
        s = df[col].dropna()
        stats[col] = {
            "count": int(s.count()),
            "mean": round(float(s.mean()), 3) if not s.empty else 0,
            "median": round(float(s.median()), 3) if not s.empty else 0,
            "std": round(float(s.std()), 3) if len(s) > 1 else 0,
            "min": round(float(s.min()), 3) if not s.empty else 0,
            "max": round(float(s.max()), 3) if not s.empty else 0,
            "q25": round(float(s.quantile(0.25)), 3) if not s.empty else 0,
            "q75": round(float(s.quantile(0.75)), 3) if not s.empty else 0,
        }

    text_freq = {}
    for col in text_cols:
        counts = df[col].dropna().value_counts().head(10).to_dict()
        text_freq[col] = {str(k): int(v) for k, v in counts.items()}

    return {
        "rows": len(df),
        "cols": len(df.columns),
        "columns": df.columns.tolist(),
        "numeric_cols": numeric_cols,
        "text_cols": text_cols,
        "missing": {k: int(v) for k, v in missing.items()},
        "duplicates": duplicates,
        "numeric_stats": stats,
        "text_freq": text_freq,
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
    }


# ─── Visitor Count Helper ───────────────────────────────────────────────────

import tempfile

def get_visitor_file_path() -> Path:
    # Use /tmp on Vercel / serverless if data/ is read-only
    p = Path("data/visitor_count.json")
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    except Exception:
        tmp_path = Path(tempfile.gettempdir()) / "visitor_count.json"
        return tmp_path

def get_increment_visitor_count(increment: bool = True) -> int:
    count = 0  # Real-time dynamic visitor count
    try:
        v_file = get_visitor_file_path()
        if v_file.exists():
            try:
                with open(v_file, "r") as f:
                    data = json.load(f)
                    count = data.get("count", 0)
            except Exception:
                pass
        if increment:
            count += 1
            try:
                with open(v_file, "w") as f:
                    json.dump({"count": count}, f)
            except Exception:
                pass
    except Exception:
        pass
    return count

@app.route("/api/visitor-count", methods=["GET"])
def visitor_count():
    try:
        should_inc = request.args.get("increment", "true").lower() == "true"
        c = get_increment_visitor_count(increment=should_inc)
        return jsonify({"count": c, "formatted": f"{c:,}"})
    except Exception as e:
        return jsonify({"count": 0, "formatted": "0"})


# ─── Base Route ───────────────────────────────────────────────────────────────

@app.route("/")
def index():
    try:
        count = get_increment_visitor_count(increment=True)
        return render_template("index.html", visitor_count=f"{count:,}")
    except Exception:
        return render_template("index.html", visitor_count="0")




# ─── Stateless CSV Analyzer API Routes ────────────────────────────────────────

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    f = request.files["file"]
    if not f.filename.endswith(".csv"):
        return jsonify({"error": "Only CSV files are supported"}), 400

    try:
        csv_bytes = f.read()
        csv_text = csv_bytes.decode("utf-8", errors="ignore")
        df = pd.read_csv(io.StringIO(csv_text))
        summary = df_summary(df)
        preview = df.head(10).fillna("").to_dict(orient="records")

        return jsonify({
            "summary": summary,
            "preview": preview,
            "filename": f.filename,
            "csv_data": csv_text
        })
    except Exception as e:
        return jsonify({"error": f"Failed to parse CSV: {str(e)}"}), 400


@app.route("/preview", methods=["POST"])
def preview():
    df, err = load_df_from_req()
    if err:
        return jsonify({"error": err}), 400
    
    body = request.json or {}
    n = int(body.get("n", 10))
    return jsonify(df.head(n).fillna("").to_dict(orient="records"))


@app.route("/filter", methods=["POST"])
def filter_data():
    df, err = load_df_from_req()
    if err:
        return jsonify({"error": err}), 400

    body = request.json or {}
    filters = body.get("filters", [])
    sort_col = body.get("sort_col")
    sort_asc = body.get("sort_asc", True)
    limit = int(body.get("limit", 100))

    result = df.copy()

    for f in filters:
        col = f.get("col")
        op = f.get("op")
        val = f.get("val")
        if col not in result.columns:
            continue
        try:
            if op == "contains":
                result = result[result[col].astype(str).str.contains(str(val), case=False, na=False)]
            elif op == "equals":
                result = result[result[col].astype(str) == str(val)]
            elif op == "gt":
                result = result[pd.to_numeric(result[col], errors="coerce") > float(val)]
            elif op == "lt":
                result = result[pd.to_numeric(result[col], errors="coerce") < float(val)]
            elif op == "gte":
                result = result[pd.to_numeric(result[col], errors="coerce") >= float(val)]
            elif op == "lte":
                result = result[pd.to_numeric(result[col], errors="coerce") <= float(val)]
            elif op == "not_null":
                result = result[result[col].notna() & (result[col].astype(str).str.strip() != "")]
            elif op == "is_null":
                result = result[result[col].isna() | (result[col].astype(str).str.strip() == "")]
        except Exception:
            pass

    if sort_col and sort_col in result.columns:
        result = result.sort_values(sort_col, ascending=sort_asc)

    total = len(result)
    result = result.head(limit)

    return jsonify({
        "rows": result.fillna("").to_dict(orient="records"),
        "total": total,
        "shown": len(result),
        "columns": result.columns.tolist(),
    })


@app.route("/clean", methods=["POST"])
def clean_data():
    df, err = load_df_from_req()
    if err:
        return jsonify({"error": err}), 400

    body = request.json or {}
    ops = body.get("operations", [])
    log = []

    for op in ops:
        kind = op.get("kind")
        col = op.get("col")

        if kind == "drop_duplicates":
            before = len(df)
            df = df.drop_duplicates()
            log.append(f"Dropped {before - len(df)} duplicate rows.")

        elif kind == "drop_nulls":
            before = len(df)
            if col:
                df = df.dropna(subset=[col])
                log.append(f"Dropped rows where '{col}' is null ({before - len(df)} rows removed).")
            else:
                df = df.dropna()
                log.append(f"Dropped all rows with any null ({before - len(df)} rows removed).")

        elif kind == "fill_null":
            fill_val = op.get("value", "")
            if col:
                df[col] = df[col].fillna(fill_val)
                log.append(f"Filled nulls in '{col}' with '{fill_val}'.")

        elif kind == "fill_null_mean":
            if col and col in df.select_dtypes(include="number").columns:
                val = df[col].mean()
                df[col] = df[col].fillna(val)
                log.append(f"Filled nulls in '{col}' with mean ({val:.3f}).")

        elif kind == "fill_null_median":
            if col and col in df.select_dtypes(include="number").columns:
                val = df[col].median()
                df[col] = df[col].fillna(val)
                log.append(f"Filled nulls in '{col}' with median ({val:.3f}).")

        elif kind == "drop_col":
            if col and col in df.columns:
                df = df.drop(columns=[col])
                log.append(f"Dropped column '{col}'.")

        elif kind == "rename_col":
            new_name = op.get("new_name", "")
            if col and new_name and col in df.columns:
                df = df.rename(columns={col: new_name})
                log.append(f"Renamed '{col}' → '{new_name}'.")

        elif kind == "strip_whitespace":
            for c in df.select_dtypes(include="object").columns:
                df[c] = df[c].str.strip()
            log.append("Stripped leading/trailing whitespace from all text columns.")

        elif kind == "lowercase":
            if col and col in df.columns:
                df[col] = df[col].astype(str).str.lower()
                log.append(f"Converted '{col}' to lowercase.")

        elif kind == "to_numeric":
            if col and col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
                log.append(f"Converted '{col}' to numeric (non-parseable → NaN).")

        elif kind == "clip_outliers":
            if col and col in df.select_dtypes(include="number").columns:
                q1, q3 = df[col].quantile(0.25), df[col].quantile(0.75)
                iqr = q3 - q1
                lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
                before_outliers = ((df[col] < lo) | (df[col] > hi)).sum()
                df[col] = df[col].clip(lo, hi)
                log.append(f"Clipped {before_outliers} outliers in '{col}' to [{lo:.2f}, {hi:.2f}].")

    # Serialize cleaned dataframe back to CSV text
    out_buf = io.StringIO()
    df.to_csv(out_buf, index=False)
    cleaned_csv_data = out_buf.getvalue()

    return jsonify({
        "log": log,
        "summary": df_summary(df),
        "preview": df.head(10).fillna("").to_dict(orient="records"),
        "csv_data": cleaned_csv_data
    })


# ─── CSV Visualization Routes ───────────────────────────────────────────────

@app.route("/chart/histogram", methods=["POST"])
def chart_histogram():
    df, err = load_df_from_req()
    if err:
        return jsonify({"error": err}), 400
    
    col = request.json.get("col")
    bins = int(request.json.get("bins", 20))
    if col not in df.columns:
        return jsonify({"error": "Column not found"}), 400

    fig, ax = plt.subplots(figsize=(9, 5))
    data = df[col].dropna()
    ax.hist(data, bins=bins, color=PALETTE[0], edgecolor="#0f0f1a", alpha=0.85)
    ax.set_title(f"Distribution of {col}", color="#e0e0ff", fontsize=14, pad=12)
    ax.set_xlabel(col)
    ax.set_ylabel("Frequency")

    # Overlay KDE
    try:
        from scipy.stats import gaussian_kde
        kde = gaussian_kde(data)
        x = np.linspace(data.min(), data.max(), 200)
        ax2 = ax.twinx()
        ax2.plot(x, kde(x), color=PALETTE[1], lw=2, alpha=0.8)
        ax2.set_ylabel("Density", color=PALETTE[1])
        ax2.tick_params(axis="y", colors=PALETTE[1])
        ax2.set_facecolor("none")
    except Exception:
        pass

    return jsonify({"image": fig_to_b64(fig)})


@app.route("/chart/bar", methods=["POST"])
def chart_bar():
    df, err = load_df_from_req()
    if err:
        return jsonify({"error": err}), 400
    
    col = request.json.get("col")
    top_n = int(request.json.get("top_n", 15))
    if col not in df.columns:
        return jsonify({"error": "Column not found"}), 400

    counts = df[col].value_counts().head(top_n)
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(counts.index.astype(str), counts.values,
                   color=PALETTE[:len(counts)], edgecolor="#0f0f1a")
    ax.set_title(f"Top {top_n} values in '{col}'", color="#e0e0ff", fontsize=14, pad=12)
    ax.set_xlabel("Count")
    ax.invert_yaxis()
    for bar, val in zip(bars, counts.values):
        ax.text(bar.get_width() + counts.max() * 0.01, bar.get_y() + bar.get_height() / 2,
                str(val), va="center", color="#c4c4e0", fontsize=9)
    fig.tight_layout()
    return jsonify({"image": fig_to_b64(fig)})


@app.route("/chart/scatter", methods=["POST"])
def chart_scatter():
    df, err = load_df_from_req()
    if err:
        return jsonify({"error": err}), 400
    
    x_col = request.json.get("x")
    y_col = request.json.get("y")
    hue_col = request.json.get("hue")
    if x_col not in df.columns or y_col not in df.columns:
        return jsonify({"error": "Column(s) not found"}), 400

    fig, ax = plt.subplots(figsize=(9, 6))
    sub = df[[x_col, y_col] + ([hue_col] if hue_col else [])].dropna()

    if hue_col and hue_col in df.columns:
        categories = sub[hue_col].unique()[:8]
        for i, cat in enumerate(categories):
            mask = sub[hue_col] == cat
            ax.scatter(sub.loc[mask, x_col], sub.loc[mask, y_col],
                       color=PALETTE[i % len(PALETTE)], label=str(cat), alpha=0.7, s=25)
        ax.legend(title=hue_col, framealpha=0.2)
    else:
        ax.scatter(sub[x_col], sub[y_col], color=PALETTE[0], alpha=0.6, s=20)

    ax.set_title(f"{x_col} vs {y_col}", color="#e0e0ff", fontsize=14, pad=12)
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    fig.tight_layout()
    return jsonify({"image": fig_to_b64(fig)})


@app.route("/chart/correlation", methods=["POST"])
def chart_correlation():
    df, err = load_df_from_req()
    if err:
        return jsonify({"error": err}), 400
    
    numeric = df.select_dtypes(include="number")
    if numeric.shape[1] < 2:
        return jsonify({"error": "Need at least 2 numeric columns"}), 400

    corr = numeric.corr()
    fig, ax = plt.subplots(figsize=(max(7, len(corr) * 0.8), max(6, len(corr) * 0.7)))
    cmap = sns.diverging_palette(260, 20, as_cmap=True)
    sns.heatmap(corr, annot=True, fmt=".2f", cmap=cmap, center=0,
                linewidths=0.5, linecolor="#0f0f1a", ax=ax,
                annot_kws={"size": 9, "color": "#e0e0ff"})
    ax.set_title("Correlation Matrix", color="#e0e0ff", fontsize=14, pad=12)
    fig.tight_layout()
    return jsonify({"image": fig_to_b64(fig)})


@app.route("/chart/boxplot", methods=["POST"])
def chart_boxplot():
    df, err = load_df_from_req()
    if err:
        return jsonify({"error": err}), 400
    
    col = request.json.get("col")
    group_col = request.json.get("group")
    if col not in df.columns:
        return jsonify({"error": "Column not found"}), 400

    fig, ax = plt.subplots(figsize=(10, 5))
    if group_col and group_col in df.columns:
        groups = df[group_col].value_counts().head(8).index.tolist()
        data_grouped = [df.loc[df[group_col] == g, col].dropna().values for g in groups]
        bp = ax.boxplot(data_grouped, patch_artist=True, labels=groups,
                        medianprops={"color": "#ffffff", "linewidth": 2})
        for patch, color in zip(bp["boxes"], PALETTE):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        ax.set_xlabel(group_col)
    else:
        bp = ax.boxplot(df[col].dropna(), patch_artist=True,
                        medianprops={"color": "#ffffff", "linewidth": 2})
        bp["boxes"][0].set_facecolor(PALETTE[0])
        bp["boxes"][0].set_alpha(0.7)

    ax.set_title(f"Box Plot — {col}", color="#e0e0ff", fontsize=14, pad=12)
    ax.set_ylabel(col)
    fig.tight_layout()
    return jsonify({"image": fig_to_b64(fig)})


@app.route("/chart/line", methods=["POST"])
def chart_line():
    df, err = load_df_from_req()
    if err:
        return jsonify({"error": err}), 400
    
    x_col = request.json.get("x")
    y_col = request.json.get("y")
    if x_col not in df.columns or y_col not in df.columns:
        return jsonify({"error": "Column(s) not found"}), 400

    sub = df[[x_col, y_col]].dropna().sort_values(x_col)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(sub[x_col].astype(str), sub[y_col], color=PALETTE[0], lw=2, marker="o", markersize=3)
    ax.fill_between(range(len(sub)), sub[y_col], alpha=0.15, color=PALETTE[0])
    ax.set_title(f"{y_col} over {x_col}", color="#e0e0ff", fontsize=14, pad=12)
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    step = max(1, len(sub) // 10)
    ax.set_xticks(range(0, len(sub), step))
    ax.set_xticklabels(sub[x_col].astype(str).iloc[::step], rotation=35, ha="right", fontsize=8)
    fig.tight_layout()
    return jsonify({"image": fig_to_b64(fig)})


@app.route("/chart/missing", methods=["POST"])
def chart_missing():
    df, err = load_df_from_req()
    if err:
        return jsonify({"error": err}), 400
    
    missing = df.isnull().sum()
    missing = missing[missing > 0]
    if missing.empty:
        return jsonify({"image": None, "message": "No missing values found!"})

    fig, ax = plt.subplots(figsize=(9, max(4, len(missing) * 0.5)))
    pct = (missing / len(df) * 100).round(1)
    bars = ax.barh(missing.index.tolist(), pct.values, color=PALETTE[3], alpha=0.8)
    ax.set_title("Missing Values (%)", color="#e0e0ff", fontsize=14, pad=12)
    ax.set_xlabel("% Missing")
    ax.set_xlim(0, 105)
    for bar, val in zip(bars, pct.values):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                f"{val}%", va="center", color="#c4c4e0", fontsize=9)
    fig.tight_layout()
    return jsonify({"image": fig_to_b64(fig)})


# ─── CSV Stats Routes ───────────────────────────────────────────────────────

@app.route("/stats/outliers", methods=["POST"])
def stats_outliers():
    df, err = load_df_from_req()
    if err:
        return jsonify({"error": err}), 400
    
    col = request.json.get("col")
    if col not in df.select_dtypes(include="number").columns:
        return jsonify({"error": "Column must be numeric"}), 400

    s = df[col].dropna()
    if s.empty:
        return jsonify({"error": "Selected column contains no numeric elements."}), 400

    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    outliers = df[(df[col] < lo) | (df[col] > hi)]

    return jsonify({
        "col": col,
        "q1": round(float(q1), 3),
        "q3": round(float(q3), 3),
        "iqr": round(float(iqr), 3),
        "lower_fence": round(float(lo), 3),
        "upper_fence": round(float(hi), 3),
        "outlier_count": int(len(outliers)),
        "outlier_pct": round(len(outliers) / len(df) * 100, 2),
        "outlier_rows": outliers.head(20).fillna("").to_dict(orient="records"),
    })


@app.route("/stats/groupby", methods=["POST"])
def stats_groupby():
    df, err = load_df_from_req()
    if err:
        return jsonify({"error": err}), 400
    
    group_col = request.json.get("group_col")
    agg_col = request.json.get("agg_col")
    agg_func = request.json.get("agg_func", "mean")

    if group_col not in df.columns or agg_col not in df.columns:
        return jsonify({"error": "Column(s) not found"}), 400

    funcs = {"mean": "mean", "sum": "sum", "count": "count", "min": "min", "max": "max", "median": "median"}
    if agg_func not in funcs:
        return jsonify({"error": "Unknown aggregation"}), 400

    result = df.groupby(group_col)[agg_col].agg(agg_func).reset_index()
    result.columns = [group_col, f"{agg_func}_{agg_col}"]
    result = result.sort_values(f"{agg_func}_{agg_col}", ascending=False).head(30)

    return jsonify({
        "rows": result.fillna("").to_dict(orient="records"),
        "columns": result.columns.tolist(),
    })


# ─── CSV Export Routes ───────────────────────────────────────────────────────

@app.route("/export/csv", methods=["POST"])
def export_csv():
    df, err = load_df_from_req()
    if err:
        return jsonify({"error": err}), 400
    
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return send_file(
        io.BytesIO(buf.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="cleaned_data.csv",
    )


@app.route("/export/excel", methods=["POST"])
def export_excel():
    df, err = load_df_from_req()
    if err:
        return jsonify({"error": err}), 400
    
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Data")
        summary = df_summary(df)
        stats_rows = []
        for col, st in summary["numeric_stats"].items():
            stats_rows.append({"Column": col, **st})
        if stats_rows:
            pd.DataFrame(stats_rows).to_excel(writer, index=False, sheet_name="Stats")
    buf.seek(0)
    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="data_export.xlsx",
    )


@app.route("/export/json", methods=["POST"])
def export_json():
    df, err = load_df_from_req()
    if err:
        return jsonify({"error": err}), 400
    
    buf = io.BytesIO(df.to_json(orient="records", indent=2).encode())
    return send_file(buf, mimetype="application/json", as_attachment=True, download_name="data.json")


# ─── Stateless PDF Routes ────────────────────────────────────────────────────

@app.route("/pdf/merge", methods=["POST"])
def pdf_merge_route():
    files = request.files.getlist("files")
    if not files or len(files) < 2:
        return jsonify({"error": "Provide at least 2 PDF files to merge"}), 400
    
    try:
        bytes_list = [f.read() for f in files if f.filename.endswith(".pdf")]
        merged = pdf_tools.merge_pdfs(bytes_list)
        return send_file(
            io.BytesIO(merged),
            mimetype="application/pdf",
            as_attachment=True,
            download_name="merged.pdf"
        )
    except Exception as e:
        return jsonify({"error": f"Merge failed: {str(e)}"}), 500


@app.route("/pdf/organize", methods=["POST"])
def pdf_organize_route():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    f = request.files["file"]
    action = request.form.get("action")
    
    try:
        f_bytes = f.read()
        
        if action == "split":
            ranges_json = request.form.get("ranges")
            ranges = json.loads(ranges_json) # expect [[start, end], [start, end]]
            merge_ranges = request.form.get("merge_ranges") == "true"
            
            split_files = pdf_tools.split_pdf(f_bytes, [(r[0], r[1]) for r in ranges])
            
            if merge_ranges:
                res = pdf_tools.merge_pdfs(split_files)
                return send_file(
                    io.BytesIO(res),
                    mimetype="application/pdf",
                    as_attachment=True,
                    download_name="split_merged.pdf"
                )
            
            # If split generated only 1 file, return directly
            if len(split_files) == 1:
                return send_file(
                    io.BytesIO(split_files[0]),
                    mimetype="application/pdf",
                    as_attachment=True,
                    download_name="split.pdf"
                )
            
            # package split files in zip
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w") as zf:
                for idx, split_bytes in enumerate(split_files):
                    zf.writestr(f"split_part_{idx + 1}.pdf", split_bytes)
            zip_buf.seek(0)
            return send_file(
                zip_buf,
                mimetype="application/zip",
                as_attachment=True,
                download_name="split_pdfs.zip"
            )
            
        elif action == "delete_pages":
            pages = json.loads(request.form.get("pages", "[]"))
            res = pdf_tools.delete_pdf_pages(f_bytes, pages)
            
        elif action == "rotate":
            pages = json.loads(request.form.get("pages", "[]"))
            angle = int(request.form.get("angle", 90))
            res = pdf_tools.rotate_pdf_pages(f_bytes, pages, angle)
            
        elif action == "crop":
            pages = json.loads(request.form.get("pages", "[]"))
            left = float(request.form.get("left", 0))
            right = float(request.form.get("right", 0))
            top = float(request.form.get("top", 0))
            bottom = float(request.form.get("bottom", 0))
            res = pdf_tools.crop_pdf_pages(f_bytes, pages, left, right, top, bottom)
            
        elif action == "extract_pages":
            pages = json.loads(request.form.get("pages", "[]"))
            res = pdf_tools.extract_pdf_pages(f_bytes, pages)
            
        elif action == "rearrange":
            order = json.loads(request.form.get("order", "[]"))
            res = pdf_tools.rearrange_pdf_pages(f_bytes, order)
            
        elif action == "add_pages":
            positions = json.loads(request.form.get("positions", "[]"))
            res = pdf_tools.add_blank_pages(f_bytes, positions)
            
        elif action == "add_page_numbers":
            style = request.form.get("style", "bottom_right")
            res = pdf_tools.add_page_numbers(f_bytes, style)
            
        else:
            return jsonify({"error": f"Invalid action: {action}"}), 400

        return send_file(
            io.BytesIO(res),
            mimetype="application/pdf",
            as_attachment=True,
            download_name="edited.pdf"
        )
    except Exception as e:
        return jsonify({"error": f"PDF Organize failed: {str(e)}"}), 500


@app.route("/pdf/convert-from", methods=["POST"])
def pdf_convert_from_route():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    f = request.files["file"]
    fmt = request.form.get("format", "text")
    
    try:
        f_bytes = f.read()
        
        if fmt == "images":
            img_format = request.form.get("img_format", "PNG")
            img_list = pdf_tools.pdf_to_images(f_bytes, img_format)
            
            if len(img_list) == 1:
                return send_file(
                    io.BytesIO(img_list[0]),
                    mimetype=f"image/{img_format.lower()}",
                    as_attachment=True,
                    download_name=f"page_1.{img_format.lower()}"
                )
                
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w") as zf:
                for idx, img_bytes in enumerate(img_list):
                    zf.writestr(f"page_{idx + 1}.{img_format.lower()}", img_bytes)
            zip_buf.seek(0)
            return send_file(
                zip_buf,
                mimetype="application/zip",
                as_attachment=True,
                download_name="pdf_images.zip"
            )
            
        elif fmt == "text":
            txt = pdf_tools.pdf_to_text(f_bytes)
            return send_file(
                io.BytesIO(txt.encode("utf-8")),
                mimetype="text/plain",
                as_attachment=True,
                download_name="extracted_text.txt"
            )
            
        elif fmt == "word":
            docx = pdf_tools.pdf_to_word(f_bytes)
            return send_file(
                io.BytesIO(docx),
                mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                as_attachment=True,
                download_name="converted.docx"
            )
            
        elif fmt == "excel":
            xlsx = pdf_tools.pdf_to_excel(f_bytes)
            return send_file(
                io.BytesIO(xlsx),
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                as_attachment=True,
                download_name="converted.xlsx"
            )
            
        elif fmt == "html":
            html = pdf_tools.pdf_to_html(f_bytes)
            return send_file(
                io.BytesIO(html.encode("utf-8")),
                mimetype="text/html",
                as_attachment=True,
                download_name="converted.html"
            )
            
        else:
            return jsonify({"error": f"Invalid format conversion target: {fmt}"}), 400
            
    except Exception as e:
        return jsonify({"error": f"Conversion failed: {str(e)}"}), 500


@app.route("/pdf/convert-to", methods=["POST"])
def pdf_convert_to_route():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    f = request.files["file"]
    source_fmt = request.form.get("source_format")
    
    try:
        f_bytes = f.read()
        
        if source_fmt in ("jpg", "png", "bmp", "gif", "tiff", "image"):
            # Pillow handles multiple formats easily
            res = pdf_tools.images_to_pdf([f_bytes])
        elif source_fmt == "text":
            text_str = f_bytes.decode("utf-8", errors="ignore")
            res = pdf_tools.text_to_pdf(text_str)
        elif source_fmt == "word":
            res = pdf_tools.docx_to_pdf(f_bytes)
        elif source_fmt == "excel":
            res = pdf_tools.xlsx_to_pdf(f_bytes)
        elif source_fmt == "html":
            html_str = f_bytes.decode("utf-8", errors="ignore")
            res = pdf_tools.html_to_pdf(html_str)
        elif source_fmt == "rtf":
            res = pdf_tools.rtf_to_pdf(f_bytes)
        else:
            return jsonify({"error": f"Unsupported source format: {source_fmt}"}), 400
            
        return send_file(
            io.BytesIO(res),
            mimetype="application/pdf",
            as_attachment=True,
            download_name="converted.pdf"
        )
    except Exception as e:
        return jsonify({"error": f"Convert to PDF failed: {str(e)}"}), 500


@app.route("/pdf/security", methods=["POST"])
def pdf_security_route():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    f = request.files["file"]
    action = request.form.get("action")
    password = request.form.get("password", "")
    
    if action == "encrypt" and not password:
        return jsonify({"error": "Password is required to encrypt a PDF"}), 400
        
    try:
        f_bytes = f.read()
        if action == "encrypt":
            res = pdf_tools.encrypt_pdf(f_bytes, password)
        elif action == "decrypt":
            res = pdf_tools.decrypt_pdf(f_bytes, password)
        else:
            return jsonify({"error": f"Invalid security action: {action}"}), 400
            
        return send_file(
            io.BytesIO(res),
            mimetype="application/pdf",
            as_attachment=True,
            download_name="unlocked.pdf" if action == "decrypt" else "secured.pdf"
        )
    except Exception as e:
        return jsonify({"error": f"Security action failed: {str(e)}"}), 500


@app.route("/pdf/sign", methods=["POST"])
def pdf_sign_route():
    if "file" not in request.files or "signature" not in request.files:
        return jsonify({"error": "Both PDF document and signature graphic files are required"}), 400
        
    f_doc = request.files["file"]
    f_sig = request.files["signature"]
    
    try:
        page_num = int(request.form.get("page", 1))
        x = float(request.form.get("x", 100))
        y = float(request.form.get("y", 100))
        width = float(request.form.get("width", 150))
        height = float(request.form.get("height", 80))
        
        doc_bytes = f_doc.read()
        sig_bytes = f_sig.read()
        
        res = pdf_tools.sign_pdf(doc_bytes, sig_bytes, page_num, x, y, width, height)
        return send_file(
            io.BytesIO(res),
            mimetype="application/pdf",
            as_attachment=True,
            download_name="signed.pdf"
        )
    except Exception as e:
        return jsonify({"error": f"Signing failed: {str(e)}"}), 500


@app.route("/pdf/info", methods=["POST"])
def pdf_info_route():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    f = request.files["file"]
    try:
        reader = pypdf.PdfReader(io.BytesIO(f.read()))
        return jsonify({
            "pages": len(reader.pages),
            "filename": f.filename
        })
    except Exception as e:
        return jsonify({"error": f"Failed to read PDF metadata: {str(e)}"}), 500


@app.route("/pdf/page-image", methods=["POST"])
def pdf_page_image_route():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    f = request.files["file"]
    page_num = int(request.form.get("page", 1))
    try:
        img_bytes = pdf_tools.render_pdf_page(f.read(), page_num - 1)
        return send_file(io.BytesIO(img_bytes), mimetype="image/png")
    except Exception as e:
        return jsonify({"error": f"Failed to render page: {str(e)}"}), 500


@app.route("/api/reduce_file_size", methods=["POST"])
def reduce_file_size_route():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    f = request.files["file"]
    filename = f.filename or "compressed_file"
    file_bytes = f.read()
    
    try:
        quality = int(request.form.get("quality", 65))
        scale_percent = float(request.form.get("scale", 1.0))
        width_percent = float(request.form.get("width_percent", 100.0))
        height_percent = float(request.form.get("height_percent", 100.0))
        target_size_kb = request.form.get("target_size_kb")
        target_size_kb = float(target_size_kb) if target_size_kb and target_size_kb.strip() else None
        mode = request.form.get("mode", "download")
        
        compressed_bytes, meta = pdf_tools.reduce_file_size(
            file_bytes, filename, quality=quality, scale_percent=scale_percent,
            width_percent=width_percent, height_percent=height_percent, target_size_kb=target_size_kb
        )
        
        if mode == "json":
            # Return JSON metadata with base64 data URL for instant client download
            ext = os.path.splitext(filename.lower())[1]
            b64_data = base64.b64encode(compressed_bytes).decode("utf-8")
            meta["data_b64"] = b64_data
            meta["ext"] = ext
            return jsonify(meta)
        else:
            ext = os.path.splitext(filename.lower())[1]
            base_name = os.path.splitext(filename)[0]
            out_filename = f"{base_name}_min{ext}"
            mtype = "application/octet-stream"
            if ext in ('.jpg', '.jpeg'): mtype = "image/jpeg"
            elif ext == '.png': mtype = "image/png"
            elif ext == '.webp': mtype = "image/webp"
            elif ext == '.pdf': mtype = "application/pdf"
            
            return send_file(
                io.BytesIO(compressed_bytes),
                mimetype=mtype,
                as_attachment=True,
                download_name=out_filename
            )
    except Exception as e:
        return jsonify({"error": f"Compression failed: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5050)