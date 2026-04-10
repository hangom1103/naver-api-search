import streamlit as st  # 스트림릿 라이브러리 임포트
import pandas as pd  # 판다스 라이브러리 임포트
import plotly.express as px  # 플로틀리 익스프레스 임포트
import plotly.graph_objects as go  # 플로틀리 그래프 객체 임포트
from datetime import datetime, timedelta  # 날짜 관련 클래스 임포트
import requests  # HTTP 요청을 보내기 위한 라이브러리 임포트
import json  # JSON 데이터 파싱 및 생성을 위한 모듈 임포트
import urllib.parse  # URL 인코딩을 위한 모듈 임포트
import re  # 정규표현식 모듈 임포트
from collections import Counter  # 빈도수 계산을 위한 카운터 임포트
from dotenv import load_dotenv  # .env 파일 로드용 (로컬 환경 용)
import os  # 운영체제 모듈 임포트
from pathlib import Path  # 경로 처리 모듈 임포트

# --- [통합] 네이버 API 연동 로직 시작 ---

# .env 파일 로드 설정 (로컬 개발 환경용)
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

def get_credentials():
    """Streamlit Secrets 또는 환경변수에서 API 인증 정보를 가져오는 함수"""
    if "NAVER_CLIENT_ID" in st.secrets:
        client_id = st.secrets["NAVER_CLIENT_ID"]
        client_secret = st.secrets["NAVER_CLIENT_SECRET"]
    else:
        client_id = os.getenv('NAVER_CLIENT_ID')
        client_secret = os.getenv('NAVER_CLIENT_SECRET')
    return client_id, client_secret

def get_headers():
    """네이버 API 호출을 위한 인증 헤더를 생성하는 함수"""
    client_id, client_secret = get_credentials()
    return {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
        "Content-Type": "application/json"
    }

def get_datalab_trend(keywords, start_date, end_date):
    """네이버 데이터랩 통합검색어 트렌드 API 호출 함수"""
    url = "https://openapi.naver.com/v1/datalab/search"
    keyword_groups = [{"groupName": kw, "keywords": [kw]} for kw in keywords]
    data = {
        "startDate": start_date.strftime('%Y-%m-%d'),
        "endDate": end_date.strftime('%Y-%m-%d'),
        "timeUnit": "date",
        "keywordGroups": keyword_groups
    }
    try:
        response = requests.post(url, headers=get_headers(), data=json.dumps(data))
        if response.status_code == 200:
            res_json = response.json()
            all_data = []
            for group in res_json['results']:
                group_name = group['title']
                for entry in group['data']:
                    all_data.append({
                        "date": entry['period'],
                        "keyword": group_name,
                        "ratio": entry['ratio']
                    })
            return pd.DataFrame(all_data)
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Trend API Error: {e}")
        return pd.DataFrame()

def get_shopping_trend(category_id, start_date, end_date):
    """네이버 데이터랩 쇼핑인사이트 카테고리별 클릭 추이 API 호출 함수"""
    url_cat = "https://openapi.naver.com/v1/datalab/shopping/categories"
    data = {"startDate": start_date.strftime('%Y-%m-%d'), "endDate": end_date.strftime('%Y-%m-%d'),
            "timeUnit": "date", "category": [{"name": "Category", "param": [category_id]}]}
    try:
        response = requests.post(url_cat, headers=get_headers(), data=json.dumps(data))
        if response.status_code == 200:
            res_json = response.json()
            all_data = []
            for group in res_json['results']:
                for entry in group['data']:
                    all_data.append({"date": entry['period'], "ratio": entry['ratio']})
            return pd.DataFrame(all_data)
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Shopping Trend API Error: {e}")
        return pd.DataFrame()

def search_naver(category, keyword, display=100):
    """네이버 통합 검색 API 호출 함수"""
    enc_text = urllib.parse.quote(keyword)
    url = f"https://openapi.naver.com/v1/search/{category}.json?query={enc_text}&display={display}"
    try:
        response = requests.get(url, headers=get_headers())
        if response.status_code == 200:
            items = response.json().get('items', [])
            df = pd.DataFrame(items)
            if not df.empty:
                df['search_keyword'] = keyword
                df['search_category'] = category
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Search API ({category}) Error: {e}")
        return pd.DataFrame()

def get_all_data(keywords, start_date, end_date):
    """모든 데이터를 수집하여 사전 형태로 반환"""
    results = {}
    results['trend'] = get_datalab_trend(keywords, start_date, end_date)
    search_cats = ['shop', 'blog', 'cafearticle', 'news']
    for cat in search_cats:
        combined_df = pd.DataFrame()
        for kw in keywords:
            df = search_naver(cat, kw)
            if not df.empty:
                combined_df = pd.concat([combined_df, df], ignore_index=True)
        results[cat] = combined_df
    return results

# --- [통합] 네이버 API 연동 로직 끝 ---

# 대시보드 페이지 설정
st.set_page_config(page_title="네이버 API 실시간 데이터 대시보드", layout="wide", initial_sidebar_state="expanded")

# 커스텀 CSS 적용
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    h1, h2, h3 { color: #1e1e1e; font-family: 'Nanum Gothic', sans-serif; }
</style>
""", unsafe_allow_html=True)

# 사이드바 설정
st.sidebar.title("🔍 검색 설정")
st.sidebar.markdown("---")
default_keywords = "버터떡"
keywords_input = st.sidebar.text_input("분석 키워드 (쉼표로 구분)", value=default_keywords)
keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]
today = datetime.now()
one_year_ago = today - timedelta(days=365)
date_range = st.sidebar.date_input("날짜 범위", [one_year_ago, today], max_value=today)
categories = {"디지털/가전": "50000003", "생활/건강": "50000008", "스포츠/레저": "50000007", "패션의류": "50000000", "화장품/미용": "50000002"}
selected_cat_name = st.sidebar.selectbox("쇼핑 트렌드 카테고리", list(categories.keys()))
selected_cat_id = categories[selected_cat_name]
st.sidebar.markdown("---")
search_button = st.sidebar.button("데이터 수집 및 분석 시작", use_container_width=True)

# 데이터 수집 (캐싱 적용)
@st.cache_data(ttl=3600)
def fetch_all_data_wrapper(kw_list, start, end):
    return get_all_data(kw_list, start, end)

@st.cache_data(ttl=3600)
def fetch_shop_trend_wrapper(cat_id, start, end):
    return get_shopping_trend(cat_id, start, end)

# 데이터 로드 로직
if search_button or 'data' not in st.session_state:
    if len(date_range) == 2:
        start_date, end_date = date_range
        with st.spinner('네이버 API에서 실시간 데이터를 가져오는 중...'):
            st.session_state['data'] = fetch_all_data_wrapper(keywords, start_date, end_date)
            st.session_state['shop_trend'] = fetch_shop_trend_wrapper(selected_cat_id, start_date, end_date)
            st.session_state['last_updated'] = datetime.now()
    else:
        st.error("날짜 범위를 시작일과 종료일 모두 선택해주세요.")

# 데이터 표시
if 'data' in st.session_state:
    data = st.session_state['data']
    shop_trend = st.session_state['shop_trend']
    st.title("🚀 네이버 API 실시간 데이터 인사이트 대시보드")
    st.caption(f"마지막 업데이트: {st.session_state['last_updated'].strftime('%Y-%m-%d %H:%M:%S')}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("수집 키워드", len(keywords))
    m2.metric("쇼핑 데이터", len(data['shop']))
    m3.metric("콘텐츠", len(data['blog']) + len(data['cafearticle']) + len(data['news']))
    m4.metric("트렌드 기록", len(data['trend']))
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 데이터 요약", "📈 트렌드 분석", "🛍 쇼핑 인사이트", "📝 콘텐츠 분석", "📋 데이터 조회"])

    with tab1:
        st.subheader("데이터 프로파일링 요약")
        cols = st.columns(len(data))
        for i, (name, df) in enumerate(data.items()):
            with cols[i]:
                st.write(f"**{name.upper()}**")
                st.write(f"- 행 개수: {len(df)}")
                st.write(f"- 결측치: {df.isnull().sum().sum()}")
    
    with tab2:
        if not data['trend'].empty:
            st.plotly_chart(px.line(data['trend'], x='date', y='ratio', color='keyword', title="검색어 트렌드"), use_container_width=True)
        if not shop_trend.empty:
            st.plotly_chart(px.line(shop_trend, x='date', y='ratio', title=f"쇼핑 카테고리({selected_cat_name}) 트렌드"), use_container_width=True)

    with tab3:
        if not data['shop'].empty:
            df_shop = data['shop'].copy()
            df_shop['lprice'] = pd.to_numeric(df_shop['lprice'], errors='coerce')
            c1, c2 = st.columns(2)
            with c1:
                brand_counts = df_shop['brand'].replace('', 'Unknown').value_counts().reset_index().head(20)
                brand_counts.columns = ['brand', 'count']
                st.plotly_chart(px.treemap(brand_counts, path=['brand'], values='count', title="브랜드 점유율"), use_container_width=True)
            with c2:
                mall_counts = df_shop['mallName'].value_counts().reset_index().head(15)
                mall_counts.columns = ['mallName', 'count']
                st.plotly_chart(px.sunburst(mall_counts, path=['mallName'], values='count', title="판매처 분포"), use_container_width=True)

    with tab4:
        st.subheader("콘텐츠 단어 빈도 분석")
        content_dfs = [data[cat][['title', 'search_keyword']] for cat in ['blog', 'cafearticle', 'news'] if not data[cat].empty]
        if content_dfs:
            combined = pd.concat(content_dfs)
            for kw in keywords:
                st.write(f"### '{kw}' 연관 단어")
                titles = combined[combined['search_keyword'] == kw]['title']
                words = []
                for t in titles:
                    clean = re.sub(r'<[^>]+>', '', t)
                    clean = re.sub(r'[^가-힣a-zA-Z\s]', '', clean)
                    words.extend([w for w in clean.split() if len(w) > 1])
                top_words = Counter(words).most_common(30)
                if top_words:
                    word_df = pd.DataFrame(top_words, columns=['word', 'count'])
                    st.plotly_chart(px.bar(word_df, x='count', y='word', orientation='h', title=f"'{kw}' 빈출 단어").update_layout(yaxis={'categoryorder':'total ascending'}), use_container_width=True)

    with tab5:
        selected_table = st.selectbox("데이터셋 선택", list(data.keys()))
        st.dataframe(data[selected_table], use_container_width=True)
else:
    st.info("사이드바에서 버튼을 눌러주세요.")
