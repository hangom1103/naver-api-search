import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import json
import urllib.parse
import re
from collections import Counter
import os

# --- 네이버 API 연동 엔진 (통합 버전) ---

def get_credentials():
    """Streamlit Secrets 또는 환경변수에서 인증 정보 추출"""
    # 1. Streamlit Cloud Secrets (우선)
    try:
        if "NAVER_CLIENT_ID" in st.secrets:
            return st.secrets["NAVER_CLIENT_ID"], st.secrets["NAVER_CLIENT_SECRET"]
    except:
        pass
    
    # 2. 로컬 환경변수 (차선)
    return os.getenv('NAVER_CLIENT_ID'), os.getenv('NAVER_CLIENT_SECRET')

def get_headers():
    client_id, client_secret = get_credentials()
    return {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
        "Content-Type": "application/json"
    }

def get_datalab_trend(keywords, start_date, end_date):
    url = "https://openapi.naver.com/v1/datalab/search"
    keyword_groups = [{"groupName": kw, "keywords": [kw]} for kw in keywords]
    data = {
        "startDate": start_date.strftime('%Y-%m-%d'),
        "endDate": end_date.strftime('%Y-%m-%d'),
        "timeUnit": "date",
        "keywordGroups": keyword_groups
    }
    try:
        res = requests.post(url, headers=get_headers(), data=json.dumps(data))
        if res.status_code == 200:
            res_json = res.json()
            all_data = []
            for group in res_json['results']:
                for entry in group['data']:
                    all_data.append({"date": entry['period'], "keyword": group['title'], "ratio": entry['ratio']})
            return pd.DataFrame(all_data)
        return pd.DataFrame()
    except:
        return pd.DataFrame()

def get_shopping_trend(category_id, start_date, end_date):
    url = "https://openapi.naver.com/v1/datalab/shopping/categories"
    data = {"startDate": start_date.strftime('%Y-%m-%d'), "endDate": end_date.strftime('%Y-%m-%d'),
            "timeUnit": "date", "category": [{"name": "Cat", "param": [category_id]}]}
    try:
        res = requests.post(url, headers=get_headers(), data=json.dumps(data))
        if res.status_code == 200:
            all_data = [{"date": e['period'], "ratio": e['ratio']} for e in res.json()['results'][0]['data']]
            return pd.DataFrame(all_data)
        return pd.DataFrame()
    except:
        return pd.DataFrame()

def search_naver(category, keyword, display=100):
    enc_text = urllib.parse.quote(keyword)
    url = f"https://openapi.naver.com/v1/search/{category}.json?query={enc_text}&display={display}"
    try:
        res = requests.get(url, headers=get_headers())
        if res.status_code == 200:
            items = res.json().get('items', [])
            df = pd.DataFrame(items)
            if not df.empty:
                df['search_keyword'] = keyword
            return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

# --- Streamlit UI 로직 ---

st.set_page_config(page_title="Naver Dashboard", layout="wide")

st.sidebar.title("🔍 검색 설정")
keywords_input = st.sidebar.text_input("분석 키워드 (쉼표 구분)", value="버터떡")
keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]
date_range = st.sidebar.date_input("날짜 범위", [datetime.now() - timedelta(days=365), datetime.now()])
cat_map = {"디지털": "50000003", "생활": "50000008", "스포츠": "50000007", "패션": "50000000"}
sel_cat = st.sidebar.selectbox("카테고리", list(cat_map.keys()))
search_btn = st.sidebar.button("데이터 분석 시작", use_container_width=True)

if search_btn or 'data' not in st.session_state:
    if len(date_range) == 2:
        with st.spinner('수집 중...'):
            st.session_state['data'] = {
                'trend': get_datalab_trend(keywords, date_range[0], date_range[1]),
                'shop': pd.concat([search_naver('shop', k) for k in keywords]),
                'blog': pd.concat([search_naver('blog', k) for k in keywords]),
                'news': pd.concat([search_naver('news', k) for k in keywords])
            }
            st.session_state['shop_trend'] = get_shopping_trend(cat_map[sel_cat], date_range[0], date_range[1])

if 'data' in st.session_state:
    st.title("🚀 네이버 실시간 인사이트")
    tab1, tab2, tab3 = st.tabs(["📈 트렌드", "🛍 쇼핑", "📝 콘텐츠"])
    
    with tab1:
        if not st.session_state['data']['trend'].empty:
            st.plotly_chart(px.line(st.session_state['data']['trend'], x='date', y='ratio', color='keyword'), use_container_width=True)
        if not st.session_state['shop_trend'].empty:
            st.plotly_chart(px.line(st.session_state['shop_trend'], x='date', y='ratio', title="쇼핑 클릭 트렌드"), use_container_width=True)
            
    with tab2:
        df_shop = st.session_state['data']['shop']
        if not df_shop.empty:
            df_shop['lprice'] = pd.to_numeric(df_shop['lprice'], errors='coerce')
            st.plotly_chart(px.treemap(df_shop.value_counts('brand').reset_index().head(20), path=['brand'], values='count'), use_container_width=True)
            st.dataframe(df_shop, use_container_width=True)
            
    with tab3:
        st.write("제목 키워드 분석")
        all_titles = pd.concat([st.session_state['data'][c]['title'] for c in ['blog', 'news'] if not st.session_state['data'][c].empty])
        words = []
        for t in all_titles:
            clean = re.sub(r'<[^>]+>', '', t)
            words.extend([w for w in clean.split() if len(w) > 1])
        if words:
            word_df = pd.DataFrame(Counter(words).most_common(30), columns=['word', 'count'])
            st.plotly_chart(px.bar(word_df, x='count', y='word', orientation='h').update_layout(yaxis={'categoryorder':'total ascending'}), use_container_width=True)
