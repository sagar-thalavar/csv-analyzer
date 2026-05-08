# 📊 CSV Analyzer Pro

A full-featured web application for exploring, cleaning, visualizing, and exporting CSV data — built with Python (Flask) and a dark, terminal-inspired UI.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-2.x-lightgrey?style=flat-square&logo=flask)
![Pandas](https://img.shields.io/badge/Pandas-2.x-purple?style=flat-square&logo=pandas)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## ✨ Features

### 📈 Data Analysis & Statistics
- Full descriptive stats per numeric column: count, mean, median, std dev, Q25, Q75, min, max
- Outlier detection using the IQR (interquartile range) method
- Group By aggregation — mean, sum, count, min, max, median across any column grouping
- Missing value detection across all columns

### 📉 Visualizations
- **Histogram** with optional KDE density overlay
- **Bar Chart** — top-N value counts for any column
- **Scatter Plot** — with optional color-by grouping
- **Box Plot** — single column or grouped by category
- **Line Chart** — trend over any X axis
- **Correlation Heatmap** — for all numeric columns
- **Missing Data Chart** — percentage missing per column

### 🧹 Data Cleaning
- Drop duplicate rows
- Drop null rows (globally or per column)
- Fill nulls with a custom value, column mean, or column median
- Strip leading/trailing whitespace from all text columns
- Convert a column to numeric (non-parseable values become NaN)
- Clip outliers to IQR fences
- Lowercase a text column
- Rename or drop any column

### 🔍 Filter & Query Builder
- Visual multi-filter builder — add as many conditions as needed
- Operators: `contains`, `equals`, `>`, `<`, `≥`, `≤`, `is null`, `is not null`
- Sort by any column (ascending or descending)
- Configurable row limit

### 📤 Export
- **CSV** — cleaned/filtered data
- **Excel (.xlsx)** — includes a Stats sheet with all numeric summaries
- **JSON** — full dataset as a JSON array

---

## 🗂️ Project Structure

```
csv_analyzer/
├── app.py                  # Flask backend — all routes and analysis logic
├── templates/
│   └── index.html          # Single-page frontend (HTML + CSS + JS)
├── sample_employees.csv    # Sample dataset for testing (308 rows, 16 columns)
└── README.md
```

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/csv-analyzer.git
cd csv-analyzer
```

### 2. Install dependencies

```bash
pip install flask pandas matplotlib seaborn openpyxl
```

> Python 3.8 or higher is required.

### 3. Run the app

```bash
python app.py
```

### 4. Open in your browser

```
http://localhost:5050
```

---

## 🧪 Testing with Sample Data

A sample dataset `sample_employees.csv` is included with 308 rows and 16 columns:

| Column | Type | Description |
|---|---|---|
| `employee_id` | Text | Unique employee identifier |
| `full_name` | Text | Employee name |
| `age` | Numeric | Age in years |
| `gender` | Text | Gender (with ~3% missing) |
| `department` | Text | Department (6 categories) |
| `job_level` | Text | Junior / Mid / Senior / Lead / Manager |
| `city` | Text | Office city (7 cities) |
| `remote_work` | Text | Yes / No / Hybrid |
| `years_experience` | Numeric | Years of experience |
| `salary` | Numeric | Annual salary (includes 2 outliers) |
| `bonus` | Numeric | Annual bonus (~5% missing) |
| `performance_score` | Numeric | 1.0 – 5.0 rating |
| `projects_completed` | Numeric | Number of projects |
| `satisfaction_score` | Numeric | 1.0 – 10.0 (~4% missing) |
| `training_hours` | Numeric | Hours of training per year |
| `attrition_risk` | Text | Low / Medium / High |

### Things to try

- **Outlier detection** on `salary` — catches the two extreme values (₹12K and ₹350K)
- **Correlation heatmap** — salary vs. experience vs. performance
- **Group By** — mean salary by `department` or `job_level`
- **Filter** — `attrition_risk` equals `High`, sort by `performance_score` descending
- **Clean** — fill nulls in `bonus` with median, then export as Excel

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `flask` | Web framework |
| `pandas` | Data loading, cleaning, aggregation |
| `matplotlib` | Chart rendering |
| `seaborn` | Correlation heatmap styling |
| `openpyxl` | Excel export |

---

## 🛠️ How It Works

- The Flask backend loads CSV files into a **pandas DataFrame** stored per session
- All cleaning operations mutate the in-session DataFrame and overwrite the uploaded file, so changes persist across views
- Charts are rendered server-side with **matplotlib/seaborn** and returned as **base64-encoded PNG** images — no additional chart library needed on the frontend
- The frontend is a single HTML file with vanilla JS — no frameworks or build tools required

---

## 📄 License

MIT License — free to use, modify, and distribute.
