#!/usr/bin/env python3
"""
CSV Analyzer - Flask Web App
Enhanced with pandas, visualizations, data cleaning, filtering & querying.
"""

from __future__ import annotations

import io
import json
import os
import base64
import tempfile
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
    send_file, session
)

app = Flask(__name__)
app.secret_key = "csv-analyzer-secret-2024"
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB

UPLOAD_FOLDER = Path(tempfile.gettempdir()) / "csv_analyzer_uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)

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


def load_df() -> pd.DataFrame | None:
    path = session.get("csv_path")
    if not path or not Path(path).exists():
        return None
    return pd.read_csv(path)


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
            "mean": round(float(s.mean()), 3),
            "median": round(float(s.median()), 3),
            "std": round(float(s.std()), 3),
            "min": round(float(s.min()), 3),
            "max": round(float(s.max()), 3),
            "q25": round(float(s.quantile(0.25)), 3),
            "q75": round(float(s.quantile(0.75)), 3),
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


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    f = request.files["file"]
    if not f.filename.endswith(".csv"):
        return jsonify({"error": "Only CSV files are supported"}), 400

    save_path = UPLOAD_FOLDER / f.filename
    f.save(str(save_path))
    session["csv_path"] = str(save_path)
    session["filename"] = f.filename

    df = pd.read_csv(str(save_path))
    summary = df_summary(df)
    preview = df.head(10).fillna("").to_dict(orient="records")

    return jsonify({
        "summary": summary,
        "preview": preview,
        "filename": f.filename,
    })


@app.route("/summary")
def summary():
    df = load_df()
    if df is None:
        return jsonify({"error": "No file loaded"}), 400
    return jsonify(df_summary(df))


@app.route("/preview")
def preview():
    df = load_df()
    if df is None:
        return jsonify({"error": "No file loaded"}), 400
    n = int(request.args.get("n", 10))
    return jsonify(df.head(n).fillna("").to_dict(orient="records"))


# ─── Filtering & Querying ────────────────────────────────────────────────────

@app.route("/filter", methods=["POST"])
def filter_data():
    df = load_df()
    if df is None:
        return jsonify({"error": "No file loaded"}), 400

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


# ─── Data Cleaning ────────────────────────────────────────────────────────────

@app.route("/clean", methods=["POST"])
def clean_data():
    df = load_df()
    if df is None:
        return jsonify({"error": "No file loaded"}), 400

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

    # Save cleaned version
    path = session.get("csv_path")
    if path:
        df.to_csv(path, index=False)

    return jsonify({
        "log": log,
        "summary": df_summary(df),
        "preview": df.head(10).fillna("").to_dict(orient="records"),
    })


# ─── Visualizations ──────────────────────────────────────────────────────────

@app.route("/chart/histogram", methods=["POST"])
def chart_histogram():
    df = load_df()
    if df is None:
        return jsonify({"error": "No file loaded"}), 400
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
    df = load_df()
    if df is None:
        return jsonify({"error": "No file loaded"}), 400
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
    df = load_df()
    if df is None:
        return jsonify({"error": "No file loaded"}), 400
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
    df = load_df()
    if df is None:
        return jsonify({"error": "No file loaded"}), 400
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
    df = load_df()
    if df is None:
        return jsonify({"error": "No file loaded"}), 400
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
    df = load_df()
    if df is None:
        return jsonify({"error": "No file loaded"}), 400
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


@app.route("/chart/missing", methods=["GET"])
def chart_missing():
    df = load_df()
    if df is None:
        return jsonify({"error": "No file loaded"}), 400
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


# ─── Advanced Stats ───────────────────────────────────────────────────────────

@app.route("/stats/outliers", methods=["POST"])
def stats_outliers():
    df = load_df()
    if df is None:
        return jsonify({"error": "No file loaded"}), 400
    col = request.json.get("col")
    if col not in df.select_dtypes(include="number").columns:
        return jsonify({"error": "Column must be numeric"}), 400

    s = df[col].dropna()
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
    df = load_df()
    if df is None:
        return jsonify({"error": "No file loaded"}), 400
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


# ─── Export ───────────────────────────────────────────────────────────────────

@app.route("/export/csv")
def export_csv():
    df = load_df()
    if df is None:
        return jsonify({"error": "No file loaded"}), 400
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return send_file(
        io.BytesIO(buf.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="cleaned_data.csv",
    )


@app.route("/export/excel")
def export_excel():
    df = load_df()
    if df is None:
        return jsonify({"error": "No file loaded"}), 400
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


@app.route("/export/json")
def export_json():
    df = load_df()
    if df is None:
        return jsonify({"error": "No file loaded"}), 400
    buf = io.BytesIO(df.to_json(orient="records", indent=2).encode())
    return send_file(buf, mimetype="application/json", as_attachment=True, download_name="data.json")


if __name__ == "__main__":
    app.run(debug=True, port=5050)