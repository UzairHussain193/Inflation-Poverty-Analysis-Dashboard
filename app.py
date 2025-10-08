import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
from datetime import datetime
import boto3
from io import BytesIO, StringIO
from dotenv import load_dotenv
import os


# Load AWS Credentials
load_dotenv()

def get_aws_credentials():
    """Get AWS credentials from environment or Streamlit secrets"""
    try:
        if hasattr(st, 'secrets') and 'aws' in st.secrets:
            return {
                'aws_access_key_id': st.secrets.aws.AWS_ACCESS_KEY_ID,
                'aws_secret_access_key': st.secrets.aws.AWS_SECRET_ACCESS_KEY,
                'region_name': st.secrets.aws.AWS_DEFAULT_REGION
            }
    except:
        pass
    
    return {
        'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID'),
        'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY'),
        'region_name': os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    }

# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title="Inflation to Poverty Analysis",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# == Cloud Data Loading ==
@st.cache_data
def load_all_data():
    try:
        credentials = get_aws_credentials()
        
        # Check if we have valid credentials
        if credentials['aws_access_key_id'] and credentials['aws_secret_access_key']:
            st.info("🔄 Loading data from AWS S3...")
            
            # Create S3 client with credentials
            # s3 = boto3.client(
            #     's3',
            #     aws_access_key_id=credentials['aws_access_key_id'],
            #     aws_secret_access_key=credentials['aws_secret_access_key'],
            #     region_name=credentials['region_name']
            # )
            s3 = boto3.client('s3')
            bucket_name = "hackathon-project-data"

            # Excel file
            excel_obj = s3.get_object(Bucket=bucket_name, Key="population-data.xlsx")
            excel_bytes = excel_obj['Body'].read()
            excel_file = BytesIO(excel_bytes)

            region = pd.read_excel(excel_file, sheet_name="region")
            yearly = pd.read_excel(excel_file, sheet_name="yearly")
            und = pd.read_excel(excel_file, sheet_name="undernourishment")
            life = pd.read_excel(excel_file, sheet_name="life-expectancy")
            country = pd.read_excel(excel_file, sheet_name="country-wise")

            # CSV files
            income_obj = s3.get_object(Bucket=bucket_name, Key="income-data.csv")
            food_obj = s3.get_object(Bucket=bucket_name, Key="wfp_food_prices_database.csv")

            income = pd.read_csv(StringIO(income_obj['Body'].read().decode('utf-8')))
            food = pd.read_csv(StringIO(food_obj['Body'].read().decode('utf-8')))

        return food, region, yearly, und, life, country, income

    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None, None, None, None, None, None, None



# ==================== DATA LOADING & CACHING ====================
# FIX 1: Using @st.cache_data instead of redundant load_df() calls
# @st.cache_data
# def load_all_data():
#     """Load all datasets once and cache them - FIXES redundant data loading"""
#     try:
#         # Load Excel sheets
#         region = pd.read_excel("data/population-data.xlsx", sheet_name="region")
#         yearly = pd.read_excel("data/population-data.xlsx", sheet_name="yearly")
#         und = pd.read_excel("data/population-data.xlsx", sheet_name='undernourishment')
#         life = pd.read_excel("data/population-data.xlsx", sheet_name='life-expectancy')
#         country = pd.read_excel("data/population-data.xlsx", sheet_name="country-wise")
        
#         # Load CSV files
#         income = pd.read_csv("data/income-data.csv")
#         food = pd.read_csv("data/wfp_food_prices_database.csv")
        
#         return food, region, yearly, und, life, country, income
#     except Exception as e:
#         st.error(f"Error loading data: {e}")
#         return None, None, None, None, None, None, None

# ==================== UTILITY FUNCTIONS ====================
def clean_percent_col(s):
    """Clean percentage columns"""
    return pd.to_numeric(s.astype(str).str.replace('%','').str.replace(',',''), errors='coerce')

# FIX 2: Consolidated data processing functions
@st.cache_data
def process_region_data(region):
    """Process region data with urban/rural calculations"""
    region = region.copy()
    region['Urban-Pop-Perc'] = clean_percent_col(region['Urban-Pop-Perc'])
    region['Yearly-Change'] = clean_percent_col(region['Yearly-Change'])
    region['World-Share'] = clean_percent_col(region['World-Share'])
    region['Urban_Pop'] = (region['Population'] * region['Urban-Pop-Perc'] / 100)
    region['Rural_Pop'] = region['Population'] - region['Urban_Pop']
    return region

@st.cache_data
def process_country_data(country):
    """Process country data with demographic classifications"""
    country = country.copy()
    
    # Calculate net change percentage if not exists
    if 'Net_Change_perc' not in country.columns:
        country['Net_Change_perc'] = (country.get('Yearly-Change', 0) * 100)
    
    # Migration impact
    country['Migrants_per_100k'] = (country['Migrants-net'] / country['Population']) * 100000
    
    # Demographic classification
    def classify_aging(row):
        if row['Fert-Rate'] > 2.1 and row['Median-Age'] < 30:
            return 'Growing'
        elif row['Fert-Rate'] < 1.8 and row['Median-Age'] > 40:
            return 'Aging'
        else:
            return 'Stable'
    
    country['Demographic_Status'] = country.apply(classify_aging, axis=1)
    return country

@st.cache_data
def process_undernourishment_data(und):
    """FIX 3: Single consolidated undernourishment processing function"""
    und = und.copy()
    
    # Per capita metrics
    und["Undernourished_per_1000"] = (und["Undernourished-People"] / und["Population"]) * 1000
    und["Undernourished_Million"] = und["Undernourished-People"] / 1e6
    
    # Global burden calculations
    total_undernourished = und["Undernourished-People"].sum()
    und["Global_Burden_Share"] = (und["Undernourished-People"] / total_undernourished) * 100
    
    total_pop = und["Population"].sum()
    und["Population_Share"] = (und["Population"] / total_pop) * 100
    
    und["Burden_vs_Pop_Diff"] = und["Global_Burden_Share"] - und["Population_Share"]
    
    return und, total_undernourished, total_pop

@st.cache_data
def process_food_data(food):
    """Clean and process food price data"""
    food = food.copy()
    food = food[food['price-paid'].notna() & (food['price-paid'] > 0)]
    food['year-recorded'] = food['year-recorded'].astype(int)
    food['month-recorded'] = food['month-recorded'].astype(int)
    return food

@st.cache_data
def process_life_expectancy(life):
    """Process life expectancy data"""
    life = life.copy()
    life['Gender_Gap'] = life['Females Life Expectancy'] - life['Males Life Expectancy']
    return life

# ==================== MAIN APP ====================
def main():
    # Load data
    with st.spinner('🔄 Loading data...'):
        food, region, yearly, und, life, country, income = load_all_data()
        
        if food is None:
            st.error("Failed to load data. Please check if data files exist in the 'data' folder.")
            return
        
        # Process data
        region = process_region_data(region)
        country = process_country_data(country)
        und, total_undernourished, total_pop = process_undernourishment_data(und)
        food = process_food_data(food)
        life = process_life_expectancy(life)
    
    # ==================== SIDEBAR ====================
    with st.sidebar:
        # st.image("https://img.freepik.com/free-vector/deer-care-icon-logo-design_474888-2791.jpg?semt=ais_hybrid&w=740&q=80", use_container_width=True)
        st.image("data/logo.png", use_container_width=True)
        
        st.title("Dashboard Controls")
        st.markdown("---")
        
        st.markdown("""
        ### About This Dashboard
        This dashboard analyzes the critical connection between 
        **food price inflation** and **poverty risk**, aligned with:
        
        - 🔴 **SDG 1**: No Poverty
        - 🟡 **SDG 2**: Zero Hunger
        
        Use the tabs above to explore different aspects of global inequality.
        """)
        
        st.markdown("---")
        st.markdown("### 📊 Data Sources")
        st.info(f"""
        **Dataset Overview**
        - **{len(country)} Countries** analyzed
        - **{food['year-recorded'].nunique()} Years** of food price data
        - **{food['comm-purchased'].nunique()} Commodities** tracked
        - **{len(food):,} Price Records**
        - **{len(region)} Regions** with population demographics
        - **{income.shape[1]-1} Years** of income data ({income.columns[1]} to {income.columns[-1]})
        """)
                
        
        st.markdown("---")
        st.markdown("## Original Data Sources")
        
        # Food Prices Data
        st.markdown("""
        **Food Prices Database**  
        [Global Food Prices Dataset - Kaggle](https://www.kaggle.com/datasets/salehahmedrony/global-food-prices/)  
        *World Food Programme (WFP) food price monitoring*
        """)
        
        # Population Data
        st.markdown("""
        **Population & Demographics**  
        [Worldometer Population Statistics](https://www.worldometers.info/world-population/)  
        *Real-time world population data and demographics*
        """)
        
        # Income Data
        st.markdown("""
        **Income & Economic Indicators**  
        [World Bank Open Data - World Development Indicators](https://databank.worldbank.org/source/world-development-indicators/Series/PA.NUS.PPP#)  
        *Purchasing Power Parity and economic data*
        """)
        
        st.markdown("---")
        st.markdown("### 👥 Team Members")
        
        # Team Member 1
        st.markdown("""
        **🧑‍💻 Uzair Hussain**  
            [See Profile](https://linkedin.com/in/uzairhussain1)            
        """)
        
        # Team Member 2
        st.markdown("""
        **👩‍💻 Abdul Lahad**  
            [See Profile](https://linkedin.com/in/member2-profile)
        """)
        
        # Team Member 3
        st.markdown("""
        **🧑‍💼 Syed Bilal Majid**  
            [See Profile](https://linkedin.com/in/member3-profile)
        """)
        

        st.markdown("---")
        st.markdown("""
        <div style='text-align: center; padding: 10px; background-color: #000000; border-radius: 5px;'>
            <b>🏆 Hackathon Project 2025</b><br>
            <small>Inflation to Poverty Analysis</small>
        </div>
        """, unsafe_allow_html=True)
    
    # ==================== HEADER ====================
    st.title("🌍 Sustainly - Inflation to Poverty Analysis Dashboard")
    st.markdown("### *Bridging the Gap Between Food Security and Economic Stability*")
    st.markdown("---")
    
    # ==================== TABS ====================
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🏠 Overview",
        "👥 Population Insights", 
        "🍽️ Hunger Analysis",
        "💰 Food Price Trends",
        "📊 Inflation-Poverty Nexus",
        "🔍 Country Deep Dive"
    ])
    
    # ==================== TAB 1: OVERVIEW ====================
    with tab1:
        st.header("📈 Global Overview & Key Metrics")
        
        # Key Metrics Row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="🌍 Total Population",
                value=f"{und['Population'].sum() / 1e9:.2f}B",
                delta="Global Population"
            )
        
        with col2:
            st.metric(
                label="😔 Undernourished People",
                value=f"{total_undernourished / 1e6:.1f}M",
                delta=f"{(total_undernourished/und['Population'].sum()*100):.1f}% of population",
                delta_color="inverse"
            )
        
        with col3:
            avg_food_price = food['price-paid'].mean()
            st.metric(
                label="💵 Avg Food Price",
                value=f"${avg_food_price:.2f}",
                delta=f"±{food['price-paid'].std():.2f} std dev"
            )
        
        with col4:
            growing_countries = (country['Demographic_Status'] == 'Growing').sum()
            st.metric(
                label="📈 Growing Populations",
                value=f"{growing_countries}",
                delta=f"out of {len(country)} countries"
            )
        
        st.markdown("---")
        
        # World Population Growth
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("🌐 World Population Growth Over Time")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=yearly['Year'], 
                y=yearly['Population']/1e9,
                mode='lines+markers', 
                name='Population (Billions)',
                line=dict(color='#E5243B', width=3),
                marker=dict(size=8)
            ))
            fig.update_layout(
                xaxis_title='Year',
                yaxis_title='Population (Billions)',
                hovermode='x unified',
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("⚖️ Demographic Status")
            demo_counts = country['Demographic_Status'].value_counts()
            fig = px.pie(
                values=demo_counts.values,
                names=demo_counts.index,
                color=demo_counts.index,
                color_discrete_map={'Growing': '#4C9F38', 'Stable': '#DDA63A', 'Aging': '#E5243B'},
                hole=0.4
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(height=400, showlegend=True)
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # Key Insights
        st.subheader("💡 Key Insights")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div style='background-color: #fff3cd; padding: 15px; border-radius: 10px; border-left: 4px solid #000000;'>
                <h4 style='color:#5a3e1b;'>🌾 Food Security Crisis</h4>
                <p style='color:#5a3e1b;'>Over <b>{:.1f} million</b> people worldwide are undernourished, 
                representing a critical challenge to achieving Zero Hunger by 2030.</p>
            </div>
            """.format(total_undernourished / 1e6), unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div style='background-color: #d1ecf1; padding: 15px; border-radius: 10px; border-left: 4px solid #00689D;'>
                <h4 style='color:#5a3e1b;'>📊 Price Volatility</h4>
                <p style='color:#5a3e1b;'>Food prices show significant variation across regions, with an average 
                price of <b>${:.2f}</b> and high standard deviation indicating instability.</p>
            </div>
            """.format(avg_food_price), unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div style='background-color: #f8d7da; padding: 15px; border-radius: 10px; border-left: 4px solid #E5243B;'>
                <h4 style='color:#5a3e1b;'>👥 Population Pressure</h4>
                <p style='color:#5a3e1b;'><b>{}</b> countries are experiencing rapid population growth, 
                intensifying the challenge of food security and poverty alleviation.</p>
            </div>
            """.format(growing_countries), unsafe_allow_html=True)
    
    # ==================== TAB 2: POPULATION INSIGHTS ====================
    with tab2:
        st.header("👥 Global Population Insights")
        
        # Regional Overview
        st.subheader("🌍 Regional Population Distribution")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Urban vs Rural by Region
            df_sorted = region.sort_values('Population', ascending=False)
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name='Rural Population',
                y=df_sorted['Region'],
                x=df_sorted['Rural_Pop']/1e6,
                orientation='h',
                marker=dict(color='#4C9F38')
            ))
            fig.add_trace(go.Bar(
                name='Urban Population',
                y=df_sorted['Region'],
                x=df_sorted['Urban_Pop']/1e6,
                orientation='h',
                marker=dict(color='#00689D')
            ))
            
            fig.update_layout(
                barmode='stack',
                title='Urban vs Rural Population by Region (Millions)',
                xaxis_title='Population (Millions)',
                height=400,
                legend=dict(x=0.7, y=0.95),  # Position legend better
                showlegend=True
            )
            st.plotly_chart(fig, use_container_width=True)
            
        
        with col2:
            # Fertility vs Median Age
            fig = px.scatter(
                region, 
                x='Median-Age', 
                y='Fert-Rate', 
                size='Population',
                hover_name='Region', 
                color='Region',
                title='Fertility Rate vs Median Age by Region',
                labels={'Median-Age': 'Median Age', 'Fert-Rate': 'Fertility Rate'}
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # Country-level analysis
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📈 Fastest Growing Countries")
            if 'Net_Change_perc' in country.columns:
                top_growth = country.nlargest(10, 'Net_Change_perc')[['Country', 'Net_Change_perc']]
                fig = px.bar(
                    top_growth,
                    y='Country',
                    x='Net_Change_perc',
                    orientation='h',
                    color='Net_Change_perc',
                    color_continuous_scale='Reds',
                    labels={'Net_Change_perc': 'Growth Rate (%)'}
                )
                fig.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("🔄 Migration Impact")
            migration_top = country.nlargest(10, 'Migrants_per_100k')[['Country', 'Migrants_per_100k']]
            fig = px.bar(
                migration_top,
                y='Country',
                x='Migrants_per_100k',
                orientation='h',
                color='Migrants_per_100k',
                color_continuous_scale='Viridis',
                labels={'Migrants_per_100k': 'Migrants per 100k Population'}
            )
            fig.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # Life Expectancy
        st.subheader("❤️ Life Expectancy Analysis")
        top_life = life.nlargest(10, 'Life Expectancy Combined')
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name='Male',
            y=top_life['Country'],
            x=top_life['Males Life Expectancy'],
            orientation='h',
            marker=dict(color='#00689D')
        ))
        fig.add_trace(go.Bar(
            name='Female',
            y=top_life['Country'],
            x=top_life['Females Life Expectancy'],
            orientation='h',
            marker=dict(color='#E5243B')
        ))
        
        fig.update_layout(
            barmode='group',
            title='Top 10 Countries by Life Expectancy',
            xaxis_title='Years',
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Display table
        with st.expander("📋 View Detailed Life Expectancy Data"):
            st.dataframe(
                top_life[['Country', 'Life Expectancy Combined', 'Males Life Expectancy', 
                         'Females Life Expectancy', 'Gender_Gap']].style.format({
                    'Life Expectancy Combined': '{:.1f}',
                    'Males Life Expectancy': '{:.1f}',
                    'Females Life Expectancy': '{:.1f}',
                    'Gender_Gap': '{:.1f}'
                }),
                use_container_width=True
            )
    
    # ==================== TAB 3: HUNGER ANALYSIS ====================
    with tab3:
        st.header("🍽️ Global Hunger & Undernourishment Analysis")
        
        # Key metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Total Undernourished",
                f"{total_undernourished / 1e6:.1f}M",
                delta="Critical Global Issue"
            )
        
        with col2:
            avg_rate = und['Undernourished_per_1000'].mean()
            st.metric(
                "Avg Rate per 1000",
                f"{avg_rate:.1f}",
                delta=f"Global average"
            )
        
        with col3:
            worst_affected = (und['Undernourished_per_1000'] > 100).sum()
            st.metric(
                "Severely Affected Countries",
                f"{worst_affected}",
                delta="Rate > 100 per 1000"
            )
        
        st.markdown("---")
        
        # Top undernourished countries
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🔴 Top 10 Countries by Total Undernourished")
            top_und = und.nlargest(10, 'Undernourished-People')
            
            fig = px.bar(
                top_und,
                x='Undernourished_Million',
                y='Country',
                orientation='h',
                color='Undernourished_Million',
                color_continuous_scale='Reds',
                labels={'Undernourished_Million': 'Undernourished (Millions)'}
            )
            fig.update_layout(yaxis={'categoryorder':'total ascending'}, height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("📊 Undernourishment Rate per 1000")
            top_rate = und.nlargest(10, 'Undernourished_per_1000')
            
            fig = px.bar(
                top_rate,
                x='Undernourished_per_1000',
                y='Country',
                orientation='h',
                color='Undernourished_per_1000',
                color_continuous_scale='Oranges',
                labels={'Undernourished_per_1000': 'Per 1000 Population'}
            )
            fig.update_layout(yaxis={'categoryorder':'total ascending'}, height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # Global burden analysis
        st.subheader("🌐 Global Burden Distribution")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Top 15 countries by global burden share
            top_burden = und.nlargest(15, 'Global_Burden_Share')
            
            fig = px.treemap(
                top_burden,
                path=['Country'],
                values='Global_Burden_Share',
                color='Global_Burden_Share',
                color_continuous_scale='RdYlGn_r',
                title='Top 15 Countries Contributing to Global Undernourishment'
            )
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("""
            ### 📌 Understanding the Data
            
            **Undernourishment Rate**: Number of people who lack regular access to 
            sufficient, safe, and nutritious food.
            
            **Global Burden Share**: Each country's contribution to total global 
            undernourishment.
            
            **Key Findings**:
            - Concentrated in specific regions
            - Often correlates with conflict zones
            - Linked to climate vulnerability
            - Exacerbated by food price inflation
            """)
        
        st.markdown("---")
        
        # Detailed table
        with st.expander("📋 View Complete Undernourishment Data"):
            display_cols = ['Country', 'Population', 'Undernourished-People', 
                           'Undernourished_per_1000', 'Global_Burden_Share', 'Burden_vs_Pop_Diff']
            st.dataframe(
                und[display_cols].sort_values('Undernourished-People', ascending=False).style.format({
                    'Population': '{:,.0f}',
                    'Undernourished-People': '{:,.0f}',
                    'Undernourished_per_1000': '{:.2f}',
                    'Global_Burden_Share': '{:.2f}%',
                    'Burden_vs_Pop_Diff': '{:.2f}%'
                }),
                use_container_width=True,
                height=400
            )
    
    # ==================== TAB 4: FOOD PRICE TRENDS ====================
    with tab4:
        st.header("💰 Food Price Analysis & Trends")
        
        # Overview metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📦 Commodities Tracked", f"{food['comm-purchased'].nunique()}")
        
        with col2:
            st.metric("🌍 Countries Covered", f"{food['country-name'].nunique()}")
        
        with col3:
            st.metric("📅 Years of Data", f"{food['year-recorded'].nunique()}")
        
        with col4:
            st.metric("💵 Avg Price", f"${food['price-paid'].mean():.2f}")
        
        st.markdown("---")
        
        # Commodity price increases
        st.subheader("📈 Commodities with Highest Price Increases")
        
        price_by_year = food.groupby(['comm-purchased', 'year-recorded'])['price-paid'].mean().reset_index()
        price_change = price_by_year.groupby('comm-purchased').agg({
            'price-paid': lambda x: x.iloc[-1] - x.iloc[0] if len(x) > 1 else 0
        }).reset_index()
        price_change.columns = ['comm-purchased', 'price_change']
        top_10_increase = price_change.sort_values(by='price_change', ascending=False).head(10)
        
        fig = px.bar(
            top_10_increase,
            y='comm-purchased',
            x='price_change',
            orientation='h',
            color='price_change',
            color_continuous_scale='Reds',
            labels={'price_change': 'Price Change', 'comm-purchased': 'Commodity'},
            title='Top 10 Commodities with Highest Price Increase (First to Last Year)'
        )
        fig.update_layout(yaxis={'categoryorder':'total ascending'}, height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # Market type comparison
        st.subheader("🏪 Retail vs Wholesale Price Trends")
        
        # FIX 4: Replaced ipywidgets with Streamlit widgets
        year_range = st.slider(
            "Select Year Range",
            min_value=int(food['year-recorded'].min()),
            max_value=int(food['year-recorded'].max()),
            value=(int(food['year-recorded'].min()), int(food['year-recorded'].max())),
            key='market_year_slider'
        )
        
        filtered_food = food[
            (food['year-recorded'] >= year_range[0]) & 
            (food['year-recorded'] <= year_range[1])
        ]
        
        if not filtered_food.empty and 'market-type' in filtered_food.columns:
            avg_market_type = filtered_food.groupby(['market-type', 'year-recorded'])['price-paid'].mean().reset_index()
            
            fig = px.line(
                avg_market_type,
                x='year-recorded',
                y='price-paid',
                color='market-type',
                markers=True,
                title=f"Retail vs Wholesale Price Trends ({year_range[0]}—{year_range[1]})",
                labels={'year-recorded': 'Year', 'price-paid': 'Average Price', 'market-type': 'Market Type'}
            )
            fig.update_layout(hovermode='x unified', height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No market type data available for selected range")
        
        st.markdown("---")
        
        # Country-specific price trends
        st.subheader("🌍 Country-Specific Price Exploration")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            available_countries = sorted(food['country-name'].unique())
            selected_country_food = st.selectbox(
                "Select Country",
                available_countries,
                key='food_country_select'
            )
            
            year_range_country = st.slider(
                "Year Range",
                min_value=int(food['year-recorded'].min()),
                max_value=int(food['year-recorded'].max()),
                value=(2015, int(food['year-recorded'].max())),
                key='country_year_slider'
            )
        
        with col2:
            # Filter and plot
            filtered_country = food[
                (food['country-name'] == selected_country_food) &
                (food['year-recorded'] >= year_range_country[0]) &
                (food['year-recorded'] <= year_range_country[1])
            ]
            
            if not filtered_country.empty:
                avg_price_year = filtered_country.groupby('year-recorded')['price-paid'].mean().reset_index()
                
                fig = px.line(
                    avg_price_year,
                    x='year-recorded',
                    y='price-paid',
                    markers=True,
                    title=f"Average Food Price Trend in {selected_country_food.upper()} ({year_range_country[0]}-{year_range_country[1]})",
                    labels={'year-recorded': 'Year', 'price-paid': 'Average Price'}
                )
                fig.update_traces(marker=dict(size=10, color='green'), line=dict(color='orange', width=3))
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(f"No data available for {selected_country_food} in selected range")
    
    # ==================== TAB 5: INFLATION-POVERTY NEXUS ====================
    with tab5:
        st.header("📊 Inflation-Poverty Nexus Analysis")
        
        st.markdown("""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 20px; border-radius: 10px; color: white; margin-bottom: 20px;'>
            <h3>Understanding the Connection</h3>
            <p>This analysis combines <b>food price inflation</b>, <b>demographic pressure</b>, 
            and <b>population density</b> to identify countries at highest risk of poverty escalation.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Calculate inflation-poverty risk score
        st.subheader("⚠️ High Inflation-Poverty Risk Countries")
        
        # Prepare data for merging
        country_clean = country.copy()
        country_clean['Country'] = country_clean['Country'].str.strip().str.lower()
        food_clean = food.copy()
        food_clean['country-name'] = food_clean['country-name'].str.strip().str.lower()
        
        # Calculate food inflation
        food_agg = food_clean.groupby(['country-name', 'year-recorded'])['price-paid'].mean().reset_index()
        food_agg['food_inflation'] = food_agg.groupby('country-name')['price-paid'].pct_change() * 100
        food_trends = food_agg.groupby('country-name')['food_inflation'].mean().reset_index()
        food_trends.columns = ['country-name', 'avg_food_inflation']
        
        # Merge datasets
        merged_df = pd.merge(
            country_clean,
            food_trends,
            how='inner',
            left_on='Country',
            right_on='country-name'
        )
        
        # Calculate composite risk score
        # FIX 5: Enhanced risk calculation with proper weighting
        merged_df['poverty_risk_score'] = (
            merged_df['Fert-Rate'] * 0.3 +
            (merged_df['Density'] / 1000) * 0.2 +  # Normalized density
            merged_df['avg_food_inflation'].abs() * 0.5
        )
        
        top_risk = merged_df[['Country', 'poverty_risk_score', 'Fert-Rate', 'Density', 'avg_food_inflation']].sort_values(
            by='poverty_risk_score', ascending=False
        ).head(15)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            fig = px.bar(
                top_risk.head(10),
                y='Country',
                x='poverty_risk_score',
                orientation='h',
                color='poverty_risk_score',
                color_continuous_scale='Reds',
                title='Top 10 High Inflation-Poverty Risk Countries',
                labels={'poverty_risk_score': 'Composite Risk Score'}
            )
            fig.update_layout(yaxis={'categoryorder':'total ascending'}, height=450)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("""
            ### 📊 Risk Score Components
            
            **Formula:**
            - Fertility Rate (30%)
            - Population Density (20%)
            - Food Inflation (50%)
            
            **Interpretation:**
            - **High Score**: Critical intervention needed
            - **Medium Score**: Monitor closely
            - **Low Score**: Relatively stable
            
            Countries with high scores face:
            - 📈 Rising food costs
            - 👨‍👩‍👧‍👦 Population pressure
            - 🏘️ Resource constraints
            """)
        
        st.markdown("---")
        
        # Detailed risk analysis table
        with st.expander("📋 View Detailed Risk Analysis"):
            st.dataframe(
                top_risk.style.format({
                    'poverty_risk_score': '{:.2f}',
                    'Fert-Rate': '{:.2f}',
                    'Density': '{:.1f}',
                    'avg_food_inflation': '{:.2f}%'
                }).background_gradient(subset=['poverty_risk_score'], cmap='Reds'),
                use_container_width=True,
                height=400
            )
        
        st.markdown("---")
        
        # Scatter plot analysis
        st.subheader("Multi-Dimensional Risk Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Inflation vs Fertility
            fig = px.scatter(
                merged_df,
                x='avg_food_inflation',
                y='Fert-Rate',
                size='Population',
                color='poverty_risk_score',
                hover_name='Country',
                title='Food Inflation vs Fertility Rate',
                labels={'avg_food_inflation': 'Avg Food Inflation (%)', 'Fert-Rate': 'Fertility Rate'},
                color_continuous_scale='RdYlGn_r'
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Density vs Risk Score
            fig = px.scatter(
                merged_df,
                x='Density',
                y='poverty_risk_score',
                size='Population',
                color='avg_food_inflation',
                hover_name='Country',
                title='Population Density vs Risk Score',
                labels={'Density': 'Population Density', 'poverty_risk_score': 'Risk Score'},
                color_continuous_scale='Viridis'
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # Purchasing Power Analysis
        st.subheader("Purchasing Power vs Food Prices")
        
        # Prepare income-food merged data
        income_clean = income.copy()
        income_clean['Country'] = income_clean['Country'].str.strip().str.lower()
        
        income_long = income_clean.melt(id_vars='Country', var_name='Year', value_name='Income')
        income_long['Year'] = income_long['Year'].astype(str)
        
        food_avg = food_clean.groupby(['country-name', 'year-recorded'])['price-paid'].mean().reset_index()
        food_avg['Year'] = food_avg['year-recorded'].astype(str)
        
        merged_pp = pd.merge(
            income_long, 
            food_avg, 
            left_on=['Country', 'Year'], 
            right_on=['country-name', 'Year']
        )
        
        merged_pp['Income'] = pd.to_numeric(merged_pp['Income'], errors='coerce')
        merged_pp['price-paid'] = pd.to_numeric(merged_pp['price-paid'], errors='coerce')
        merged_pp['Purchasing_Power'] = (merged_pp['Income'] / merged_pp['price-paid']).round(2)
        merged_pp = merged_pp.dropna(subset=['Purchasing_Power'])
        
        if not merged_pp.empty:
            # Top and bottom purchasing power
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 💪 Highest Purchasing Power")
                top_pp = merged_pp.nlargest(10, 'Purchasing_Power')
                fig = px.bar(
                    top_pp,
                    y='Country',
                    x='Purchasing_Power',
                    orientation='h',
                    color='Purchasing_Power',
                    color_continuous_scale='Greens',
                    labels={'Purchasing_Power': 'Purchasing Power Index'}
                )
                fig.update_layout(yaxis={'categoryorder':'total ascending'}, height=400, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.markdown("#### 📈 Highest Food Price Inflation")
                # Show countries with highest food price inflation instead
                high_inflation = merged_df.nlargest(10, 'avg_food_inflation')
                
                fig = px.bar(
                    high_inflation,
                    y='Country',
                    x='avg_food_inflation',
                    orientation='h',
                    color='avg_food_inflation',
                    color_continuous_scale='Reds',
                    labels={'avg_food_inflation': 'Average Food Inflation (%)'},
                    title='Countries with Highest Food Price Inflation'
                )
                fig.update_layout(yaxis={'categoryorder':'total ascending'}, height=400, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Insufficient data for purchasing power analysis")
    
    # ==================== TAB 6: COUNTRY DEEP DIVE ====================
    with tab6:
        st.header("🔍 Country-Level Deep Dive Analysis")
        
        st.markdown("""
        Explore detailed insights for individual countries including price trends, 
        inflation rates, and purchasing power dynamics.
        """)
        
        st.markdown("---")
        
        # Country selector
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            # Get countries that exist in both food and income datasets
            food_countries = set(food['country-name'].str.strip().str.lower().unique())
            income_countries = set(income['Country'].str.strip().str.lower().unique())
            common_countries = sorted(list(food_countries & income_countries))
            
            if common_countries:
                selected_country_deep = st.selectbox(
                    "Select Country for Analysis",
                    [c.title() for c in common_countries],
                    key='deep_dive_country'
                )
                selected_country_lower = selected_country_deep.lower()
            else:
                st.error("No common countries found between datasets")
                return
        
        with col2:
            year_start_deep = st.number_input(
                "Start Year",
                min_value=int(food['year-recorded'].min()),
                max_value=int(food['year-recorded'].max()),
                value=2015,
                key='deep_start_year'
            )
        
        with col3:
            year_end_deep = st.number_input(
                "End Year",
                min_value=int(food['year-recorded'].min()),
                max_value=int(food['year-recorded'].max()),
                value=int(food['year-recorded'].max()),
                key='deep_end_year'
            )
        
        if year_start_deep > year_end_deep:
            st.error("Start year must be before end year!")
            return
        
        st.markdown("---")
        
        # Filter data for selected country
        country_food_data = food[
            (food['country-name'].str.lower() == selected_country_lower) &
            (food['year-recorded'] >= year_start_deep) &
            (food['year-recorded'] <= year_end_deep)
        ]
        
        if country_food_data.empty:
            st.warning(f"No food price data available for {selected_country_deep} in the selected year range.")
        else:
            # 1. Yearly Average Price Trend
            st.subheader(f"📈 Average Food Price Trend - {selected_country_deep}")
            
            avg_price_yearly = country_food_data.groupby('year-recorded')['price-paid'].mean().reset_index()
            
            fig = px.line(
                avg_price_yearly,
                x='year-recorded',
                y='price-paid',
                markers=True,
                title=f"Average Food Price Trend in {selected_country_deep.upper()} ({year_start_deep}-{year_end_deep})",
                labels={'year-recorded': 'Year', 'price-paid': 'Average Price'}
            )
            fig.update_traces(marker=dict(size=12, color='Green'), line=dict(color='orange', width=3))
            fig.update_layout(hovermode='x unified')
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            
            # 2. Monthly Inflation Rate
            st.subheader(f"📊 Monthly Inflation Rate - {selected_country_deep}")
            
            # Calculate monthly inflation
            avg_price_month = country_food_data.groupby(['year-recorded', 'month-recorded'])['price-paid'].mean().reset_index()
            avg_price_month = avg_price_month.sort_values(['year-recorded', 'month-recorded'])
            avg_price_month['inflation_rate'] = avg_price_month['price-paid'].pct_change() * 100
            
            if not avg_price_month.empty:
                fig = px.line(
                    avg_price_month,
                    x='month-recorded',
                    y='inflation_rate',
                    color='year-recorded',
                    markers=True,
                    title=f"Monthly Inflation Rate (%) in {selected_country_deep} ({year_start_deep}-{year_end_deep})",
                    labels={'month-recorded': 'Month', 'inflation_rate': 'Inflation Rate (%)', 'year-recorded': 'Year'}
                )
                fig.update_layout(hovermode='x unified')
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            
            # 3. Dual-axis: Price vs Purchasing Power
            st.subheader(f"💰 Price vs Purchasing Power - {selected_country_deep}")
            
            # Get purchasing power data
            country_pp_data = merged_pp[merged_pp['Country'] == selected_country_lower]
            
            if not country_pp_data.empty:
                country_pp_data['Year_int'] = country_pp_data['Year'].astype(int)
                country_pp_data = country_pp_data[
                    (country_pp_data['Year_int'] >= year_start_deep) &
                    (country_pp_data['Year_int'] <= year_end_deep)
                ].sort_values('Year_int')
                
                if not country_pp_data.empty:
                    # Create dual-axis plot
                    fig = go.Figure()
                    
                    fig.add_trace(go.Scatter(
                        x=country_pp_data['Year_int'],
                        y=country_pp_data['price-paid'],
                        mode='lines+markers',
                        name='Avg Food Price',
                        marker=dict(color='royalblue', size=10),
                        line=dict(color='royalblue', width=3),
                        yaxis='y1'
                    ))
                    
                    fig.add_trace(go.Scatter(
                        x=country_pp_data['Year_int'],
                        y=country_pp_data['Purchasing_Power'],
                        mode='lines+markers',
                        name='Purchasing Power',
                        marker=dict(color='darkorange', size=10),
                        line=dict(color='darkorange', width=3),
                        yaxis='y2'
                    ))
                    
                    fig.update_layout(
                        title=f'Food Price vs Purchasing Power — {selected_country_deep} ({year_start_deep}-{year_end_deep})',
                        xaxis=dict(title='Year', tickmode='linear'),
                        yaxis=dict(
                            title='Avg Food Price',
                            titlefont=dict(color='royalblue'),
                            tickfont=dict(color='royalblue')
                        ),
                        yaxis2=dict(
                            title='Purchasing Power Index',
                            titlefont=dict(color='darkorange'),
                            tickfont=dict(color='darkorange'),
                            overlaying='y',
                            side='right'
                        ),
                        hovermode='x unified',
                        legend=dict(x=0.01, y=0.99)
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Summary metrics
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        avg_price = country_pp_data['price-paid'].mean()
                        st.metric("Avg Food Price", f"${avg_price:.2f}")
                    
                    with col2:
                        price_change = ((country_pp_data['price-paid'].iloc[-1] / country_pp_data['price-paid'].iloc[0]) - 1) * 100
                        st.metric("Price Change", f"{price_change:.1f}%", delta=f"{year_start_deep}-{year_end_deep}")
                    
                    with col3:
                        avg_pp = country_pp_data['Purchasing_Power'].mean()
                        st.metric("Avg Purchasing Power", f"{avg_pp:.2f}")
                    
                    with col4:
                        avg_income = country_pp_data['Income'].mean()
                        st.metric("Avg Income", f"${avg_income:.2f}")
                else:
                    st.info(f"No purchasing power data available for {selected_country_deep} in selected range")
            else:
                st.info(f"No income data available for {selected_country_deep}")
            
            st.markdown("---")
            
            # 4. Commodity breakdown
            st.subheader(f"🛒 Top Commodities Tracked - {selected_country_deep}")
            
            commodity_prices = country_food_data.groupby('comm-purchased')['price-paid'].agg(['mean', 'count']).reset_index()
            commodity_prices = commodity_prices.sort_values('mean', ascending=False).head(10)
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.bar(
                    commodity_prices,
                    y='comm-purchased',
                    x='mean',
                    orientation='h',
                    color='mean',
                    color_continuous_scale='Blues',
                    labels={'mean': 'Average Price', 'comm-purchased': 'Commodity'},
                    title='Top 10 Commodities by Average Price'
                )
                fig.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.bar(
                    commodity_prices,
                    y='comm-purchased',
                    x='count',
                    orientation='h',
                    color='count',
                    color_continuous_scale='Greens',
                    labels={'count': 'Number of Records', 'comm-purchased': 'Commodity'},
                    title='Top 10 Most Tracked Commodities'
                )
                fig.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            
            # 5. Year-over-year comparison table
            with st.expander("📅 View Yearly Price Summary"):
                yearly_summary = country_food_data.groupby('year-recorded')['price-paid'].agg([
                    ('Average Price', 'mean'),
                    ('Min Price', 'min'),
                    ('Max Price', 'max'),
                    ('Std Dev', 'std'),
                    ('Records', 'count')
                ]).reset_index()
                
                st.dataframe(
                    yearly_summary.style.format({
                        'Average Price': '${:.2f}',
                        'Min Price': '${:.2f}',
                        'Max Price': '${:.2f}',
                        'Std Dev': '${:.2f}',
                        'Records': '{:.0f}'
                    }).background_gradient(subset=['Average Price'], cmap='RdYlGn_r'),
                    use_container_width=True
                )

# ==================== RUN APP ====================
if __name__ == "__main__":
    main()