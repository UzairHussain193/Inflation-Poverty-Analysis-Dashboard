
# 🌍 Sustainly — Inflation to Poverty Analysis Dashboard

## Bridging the Gap Between Food Security and Economic Stability

<p align="center">
    <img alt="Last Commit" src="https://img.shields.io/github/last-commit/UzairHussain193/Inflation-Poverty-Analysis-Dashboard?style=flat-square&label=last%20commit&color=21262d&labelColor=21262d">
    <img alt="Python" src="https://img.shields.io/badge/python-100.0%25-blue?style=flat-square&logo=python&logoColor=white&color=007396&labelColor=007396">
    <img alt="Languages" src="https://img.shields.io/badge/languages-1-blue?style=flat-square&color=21262d&labelColor=21262d">
</p>

### Built with the tools and technologies:

<p align="center">
    <img alt="Markdown" src="https://img.shields.io/badge/Markdown-000000?style=for-the-badge&logo=markdown&logoColor=white">
    <img alt="Streamlit" src="https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white">
    <img alt="NumPy" src="https://img.shields.io/badge/NumPy-013243?style=for-the-badge&logo=numpy&logoColor=white">
    <img alt="Python" src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white">
    <img alt="Plotly" src="https://img.shields.io/badge/Plotly-273647?style=for-the-badge&logo=plotly&logoColor=white">
    <img alt="Pandas" src="https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white">
</p>

---

## 📖 Overview

**Sustainly** is a data-driven dashboard built with **Streamlit** that analyzes the complex relationship between **food price inflation**, **population growth**, **income (PPP)**, and **poverty risk**.  

It combines global datasets from the **World Bank**, **Worldometer**, and **World Food Programme (WFP)** to uncover how inflation and demographic pressure shape **purchasing power**, **hunger levels**, and **economic vulnerability** across countries.

This project was developed as part of **Hackathon 2025** under the theme _"Sustainable Development Goals (SDG 1 & SDG 2): No Poverty and Zero Hunger."_  

---

## 🚀 Features

✅ **Interactive Streamlit Dashboard**  
Visualizes complex relationships in a simple, intuitive interface.  

✅ **Cloud Data Integration (AWS S3)**  
Automatically loads and processes data from AWS cloud storage.  

✅ **Purchasing Power Estimation**  
Calculates real purchasing power using GDP per capita (PPP) and food price data.  

✅ **Inflation–Poverty Nexus Analysis**  
Assesses how food price inflation impacts poverty and food security risk.  

✅ **Global & Country-Level Insights**  
Explore regional demographics, undernourishment data, and economic patterns.  

✅ **Dynamic Visuals**  
Built with **Plotly** and **Seaborn** for high-quality charts and interactivity.

---

## 🧮 Key Analyses

| Analysis | Description |
|-----------|--------------|
| **Purchasing Power Index (FPPI)** | Measures affordability using GDP (PPP) vs real food prices |
| **Inflation-Poverty Risk Score** | Combines fertility rate, population density, and food inflation |
| **Undernourishment Analysis** | Identifies hunger hot spots globally |
| **Food Price Trends** | Tracks inflation patterns across commodities and markets |
| **Country Deep Dive** | Drill down into national trends, prices, and purchasing power |

---

## 🗂️ Project Structure

```
📦 Sustainly-Dashboard
│
├── app.py                 # Main Streamlit app
├── requirements.txt       # Project dependencies
├── data/                  # (Optional local data folder)
│   ├── population-data.xlsx
│   ├── income-data.csv
│   └── wfp_food_prices_database.csv
│
└── README.md              # Project documentation
```

---

## ⚙️ Installation & Setup

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/UzairHussain193/Inflation-Poverty-Analysis-Dashboard.git
cd sustainly-dashboard
```

### 2️⃣ Create a Virtual Environment (Optional but Recommended)
```bash
python -m venv venv
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate    # Windows
```

### 3️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```

### 4️⃣ Set Up Environment Variables
Create a `.env` file in your project root with the following (if using AWS S3):
```
AWS_ACCESS_KEY_ID=your_key_here
AWS_SECRET_ACCESS_KEY=your_secret_here
AWS_DEFAULT_REGION=us-east-1
```
Or store them securely in Streamlit Cloud `st.secrets`.

---

## ▶️ Run the Dashboard
```bash
streamlit run app.py
```
Then open the displayed local URL (usually `http://localhost:8501`) in your browser.

---

## 🌐 Data Sources

| Dataset | Source |
|----------|--------|
| **Global Food Prices** | [World Food Programme (WFP) – Kaggle](https://www.kaggle.com/datasets/salehahmedrony/global-food-prices) |
| **Population & Demographics** | [Worldometer Population Statistics](https://www.worldometers.info/world-population/) |
| **Income (PPP) & Economic Indicators** | [World Bank Open Data](https://databank.worldbank.org/source/world-development-indicators/) |

---

## 📊 Dashboard Sections

| Section | Description |
|----------|-------------|
| 🏠 **Overview** | Global metrics: total population, food price averages, and key highlights. |
| 👥 **Population Insights** | Urban vs rural distribution, fertility rates, and migration impact. |
| 🍽️ **Hunger Analysis** | Undernourishment levels and global burden of food insecurity. |
| 💰 **Food Price Trends** | Historical patterns in food prices across commodities and markets. |
| 📊 **Inflation–Poverty Nexus** | Risk scoring using demographic, inflation, and density data. |
| 🔍 **Country Deep Dive** | Country-level trends, purchasing power, and inflation rates. |

---

## 💡 Key Insights

- Countries with **high population growth** and **rising food inflation** face the greatest risk of poverty escalation.  
- **Purchasing Power** declines when income growth cannot keep up with food price inflation.  
- **Demographic trends** (young vs aging populations) heavily influence national vulnerability.  
- Regional disparities show that **urbanization** often correlates with better food access but also higher price volatility.  

---

## 🧑‍🤝‍🧑 Team Members

| Name | Role | LinkedIn |
|------|------|-----------|
| **Uzair Hussain** | Data Analyst | [Profile](https://www.linkedin.com/in/uzairhussain1) |
| **Abdul Lahad** | App Developer | [Profile](https://www.linkedin.com/in/abdul-lahad-8226ab274/) |
| **Syed Bilal Majid** | Research & Insights | [Profile](https://www.linkedin.com/in/bilal-majid-37b56225a/) |

---

## 🏆 Hackathon 2025 Submission

**Theme:** *Sustainable Development Goals (SDG 1 & 2)*  
**Title:** _Inflation to Poverty Analysis — Empowering Data-Driven Solutions for Food Security_  
**Category:** *Data Analytics & Visualization*  

---


## ⭐ Acknowledgments

Special thanks to:
- **World Food Programme (WFP)** for open access to global price data.  
- **World Bank & Worldometer** for economic and demographic datasets.  
- The **Hackathon 2025 Committee** for organizing this initiative.  
