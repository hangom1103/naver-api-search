import streamlit as st  # 스트림릿 라이브러리 임포트
import pandas as pd  # 판다스 라이브러리 임포트
import plotly.express as px  # 플로틀리 익스프레스 임포트
import plotly.graph_objects as go  # 플로틀리 그래프 객체 임포트
from datetime import datetime, timedelta  # 날짜 관련 클래스 임포트
from naver_api import get_all_data, get_shopping_trend  # 네이버 API 연동 모듈 임포트
import re  # 정규표현식 모듈 임포트
from collections import Counter  # 빈도수 계산을 위한 카운터 임포트

# 대시보드 페이지 기본 설정 (타이틀, 레이아웃 등)
st.set_page_config(page_title="네이버 API 실시간 데이터 대시보드", layout="wide", initial_sidebar_state="expanded") # 페이지 속성 설정

# 스타일링을 위한 커스텀 CSS 적용
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;  /* 메인 배경색 설정 */
    }
    .stMetric {
        background-color: #ffffff;  /* 지표 카드 배경색 */
        padding: 15px;  /* 안쪽 여백 */
        border-radius: 10px;  /* 모서리 곡률 */
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);  /* 그림자 효과 */
    }
    h1, h2, h3 {
        color: #1e1e1e;  /* 헤더 글자색 */
        font-family: 'Nanum Gothic', sans-serif;  /* 한글 폰트 설정 */
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;  /* 탭 간격 설정 */
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;  /* 탭 높이 */
        white-space: pre-wrap;  /* 텍스트 줄바꿈 허용 */
        background-color: #ffffff;  /* 탭 배경색 */
        border-radius: 5px 5px 0 0;  /* 탭 상단 곡률 */
        gap: 1px;  # 간격
        padding-top: 10px;  # 상단 여백
        padding-bottom: 10px;  # 하단 여백
    }
</style>
""", unsafe_allow_html=True) # HTML 허용 옵션으로 마크다운 출력

# 사이드바 영역 제목 및 구분선 표시
st.sidebar.title("🔍 검색 설정") # 사이드바 제목
st.sidebar.markdown("---") # 구분선

# 분석을 수행할 기본 키워드 정의 및 입력 처리
default_keywords = "버터떡" # 기본 키워드 설정
keywords_input = st.sidebar.text_input("분석 키워드 (쉼표로 구분)", value=default_keywords) # 텍스트 입력창 생성
keywords = [k.strip() for k in keywords_input.split(",") if k.strip()] # 입력된 문자열을 키워드 리스트로 변환

# 트렌드 분석을 위한 날짜 범위 선택 위젯
today = datetime.now() # 오늘 날짜 가져오기
one_year_ago = today - timedelta(days=365) # 1년 전 날짜 계산
date_range = st.sidebar.date_input("날짜 범위", [one_year_ago, today], max_value=today) # 날짜 선택기 생성

# 쇼핑 트렌드 조회를 위한 카테고리 ID 매핑 정보
categories = {
    "디지털/가전": "50000003", # 디지털 가전 ID
    "생활/건강": "50000008", # 생활 건강 ID
    "스포츠/레저": "50000007", # 스포츠 레저 ID
    "패션의류": "50000000", # 패션 의류 ID
    "화장품/미용": "50000002" # 화장품 미용 ID
}
selected_cat_name = st.sidebar.selectbox("쇼핑 트렌드 카테고리", list(categories.keys())) # 카테고리 선택 상자
selected_cat_id = categories[selected_cat_name] # 선택된 카테고리의 ID 추출

st.sidebar.markdown("---") # 사이드바 내부 구분선
search_button = st.sidebar.button("데이터 수집 및 분석 시작", use_container_width=True) # 분석 실행 버튼

# 네이버 검색 및 트렌드 데이터 수집을 위한 캐싱 처리 함수
@st.cache_data(ttl=3600) # 1시간 동안 결과 캐싱
def fetch_data(kw_list, start, end): # 통합 데이터 수집 함수
    return get_all_data(kw_list, start, end) # naver_api 모듈의 함수 호출

@st.cache_data(ttl=3600) # 1시간 동안 결과 캐싱
def fetch_shop_trend(cat_id, start, end): # 쇼핑 트렌드 수집 함수
    return get_shopping_trend(cat_id, start, end) # naver_api 모듈의 쇼핑 트렌드 함수 호출

# 사용자가 버튼을 클릭하거나 데이터가 없는 경우 데이터 로드 수행
if search_button or 'data' not in st.session_state: # 버튼 클릭 시 또는 세션 상태에 데이터 부재 시
    if len(date_range) == 2: # 시작일과 종료일이 모두 선택된 경우
        start_date, end_date = date_range # 각각의 날짜 변수에 할당
        with st.spinner('네이버 API에서 실시간 데이터를 가져오는 중...'): # 로딩 스피너 표시
            st.session_state['data'] = fetch_data(keywords, start_date, end_date) # 전체 데이터 수집 및 세션 저장
            st.session_state['shop_trend'] = fetch_shop_trend(selected_cat_id, start_date, end_date) # 쇼핑 트렌드 수집 및 세션 저장
            st.session_state['last_updated'] = datetime.now() # 업데이트 시간 기록
    else: # 날짜가 하나만 선택된 경우 경고
        st.error("날짜 범위를 시작일과 종료일 모두 선택해주세요.") # 에러 메시지 출력

# 데이터 로딩 성공 시 대시보드 콘텐츠 렌더링 시작
if 'data' in st.session_state: # 세션에 데이터가 존재하는 경우
    data = st.session_state['data'] # 수집된 데이터 세션에서 가져오기
    shop_trend = st.session_state['shop_trend'] # 쇼핑 트렌드 세션에서 가져오기
    
    st.title("🚀 네이버 API 실시간 데이터 인사이트 대시보드") # 메인 타이틀 출력
    st.caption(f"마지막 업데이트: {st.session_state['last_updated'].strftime('%Y-%m-%d %H:%M:%S')}") # 엡데이트 시각 캡션
    
    # 대시보드 상단 로 요약 정보를 위한 메트릭 컬럼 구성
    m1, m2, m3, m4 = st.columns(4) # 4개의 컬럼 생성
    m1.metric("수집 키워드", len(keywords)) # 검색된 키워드 수 표시
    m2.metric("쇼핑 데이터", len(data['shop'])) # 수집된 쇼핑 상품 수 표시
    m3.metric("콘텐츠(블로그/카페/뉴스)", len(data['blog']) + len(data['cafearticle']) + len(data['news'])) # 전체 콘텐츠 수 합산 표시
    m4.metric("트렌드 기록수", len(data['trend'])) # 트렌드 데이터 행 수 표시

    # 대시보드 메인 영역의 탭 구성
    tab1, tab2, tab3, tab4, tab5 = st.tabs([ # 5개의 탭 헤더 설정
        "📊 데이터 요약", "📈 트렌드 분석", "🛍 쇼핑 인사이트", "📝 콘텐츠 분석", "📋 데이터 조회"
    ])

    # 첫 번째 탭: 데이터 수집 현황 및 프로파일링
    with tab1: # Tab 1 영역 활성화
        st.subheader("데이터 프로파일링 요약") # 소제목 표시
        cols = st.columns(len(data)) # 수집된 데이터 유형별 컬럼 생성
        for i, (name, df) in enumerate(data.items()): # 데이터 유형별 반복
            with cols[i]: # 각 컬럼에 데이터 요약 정보 출력
                st.write(f"**{name.upper()}**") # 데이터셋 명칭 출력
                st.write(f"- 행 개수: {len(df)}") # 데이터 행 수
                st.write(f"- 열 개수: {len(df.columns)}") # 데이터 열 수
                st.write(f"- 결측치: {df.isnull().sum().sum()}") # 전체 결측치 개수
        
        st.markdown("---") # 구분선
        st.write("### 주요 변수 기초 통계") # 기초 통계 제목
        if not data['shop'].empty: # 쇼핑 데이터가 있는 경우
            st.write("#### 쇼핑 데이터 수치형 변수") # 쇼핑 통계 제목
            df_shop = data['shop'].copy() # 쇼핑 데이터 복사본 생성
            df_shop['lprice'] = pd.to_numeric(df_shop['lprice'], errors='coerce') # 가격 데이터를 숫자로 변환
            st.dataframe(df_shop[['lprice']].describe().T, use_container_width=True) # 통계치 요약표 출력

    # 두 번째 탭: 검색량 추이 및 쇼핑 트렌드 그래프
    with tab2: # Tab 2 영역 활성화
        st.subheader("검색어 및 쇼핑 트렌드") # 소제목 표시
        if not data['trend'].empty: # 검색 트렌드 데이터가 있는 경우
            # Plotly 선형 그래프 생성
            fig_trend = px.line(data['trend'], x='date', y='ratio', color='keyword', 
                               title="통합 검색어 트렌드 추이", template="plotly_white") # 전체 검색 트렌드 시각화
            st.plotly_chart(fig_trend, use_container_width=True) # 대시보드에 그래프 출력
            
        if not shop_trend.empty: # 쇼핑 트렌드 데이터가 있는 경우
            # 쇼핑 카테고리 클릭 트렌드 선형 그래프 생성
            fig_shop_trend = px.line(shop_trend, x='date', y='ratio', 
                                    title=f"쇼핑 카테고리({selected_cat_name}) 클릭 트렌드", 
                                    template="plotly_white", color_discrete_sequence=['#ff7f0e']) # 쇼핑 트렌드 시각화
            st.plotly_chart(fig_shop_trend, use_container_width=True) # 그래프 출력

    # 세 번째 탭: 쇼핑 데이터 심층 분석 (브랜드, 가격 등)
    with tab3: # Tab 3 영역 활성화
        st.subheader("쇼핑 데이터 분석") # 소제목 표시
        if not data['shop'].empty: # 쇼핑 데이터 존재 여부 확인
            df_shop = data['shop'].copy() # 데이터 복사
            df_shop['lprice'] = pd.to_numeric(df_shop['lprice'], errors='coerce') # 가격 데이터 수치화
            c1, c2 = st.columns(2) # 2단 레이아웃 구성
            with c1: # 왼쪽 컬럼
                # 브랜드별 비중 트리맵 시각화
                brand_counts = df_shop['brand'].replace('', 'Unknown').value_counts().reset_index() # 브랜드별 개수 집계
                brand_counts.columns = ['brand', 'count'] # 컬럼명 재설정
                fig_tree = px.treemap(brand_counts.head(20), path=['brand'], values='count',
                                     title="상위 20개 브랜드 점유율 (TreeMap)") # 트리맵 차트 생성
                st.plotly_chart(fig_tree, use_container_width=True) # 차트 출력
            with c2: # 오른쪽 컬럼
                # 상위 판매몰 분포 선버스트 시각화
                mall_counts = df_shop['mallName'].value_counts().reset_index() # 판매몰별 개수 집계
                mall_counts.columns = ['mallName', 'count'] # 컬럼명 설정
                fig_sun = px.sunburst(mall_counts.head(15), path=['mallName'], values='count',
                                     title="상위 15개 판매처 분포 (Sunburst)") # 선버스트 차트 생성
                st.plotly_chart(fig_sun, use_container_width=True) # 차트 출력
            st.markdown("---") # 구분선
            st.write("#### 가격대별 상품 분포 (Histogram)") # 가격 분포 제목
            # 가격대별 히스토그램 시각화
            fig_price = px.histogram(df_shop, x='lprice', color='search_keyword', nbins=50,
                                    title="검색어별 가격 분포", barmode='overlay', template="plotly_white") # 히스토그램 생성
            st.plotly_chart(fig_price, use_container_width=True) # 차트 출력

    # 네 번째 탭: 블로그/카페/뉴스 제목 빈도수 분석
    with tab4: # Tab 4 영역 활성화
        st.subheader("콘텐츠 제목 빈도 분석 (Top 30)") # 소제목 표시
        content_dfs = [] # 텍스트 데이터를 모을 리스트
        for cat in ['blog', 'cafearticle', 'news']: # 상위 기 카테고리에 대해 반복
            if not data[cat].empty: # 데이터가 있는 경우
                df = data[cat][['title', 'search_keyword']].copy() # 제목과 키워드만 선택
                df['category'] = cat # 데이터 소스 정보 추가
                content_dfs.append(df) # 리스트에 추가
        if content_dfs: # 콘텐츠 데이터가 수집된 경우
            combined_content = pd.concat(content_dfs) # 모든 콘텐츠 데이터 통합
            # 단어 빈도수 계산을 위한 내부 함수
            def get_top_words(titles, top_n=30): # 제목 리스트와 상위 N개 개수 인자
                words = [] # 단어를 저장할 리스트
                for title in titles: # 모든 제목 순회
                    clean_title = re.sub(r'<[^>]+>', '', title) # HTML 태그 제거
                    clean_title = re.sub(r'[^가-힣a-zA-Z\s]', '', clean_title) # 특수문자 제거 (한글/영문만 남김)
                    words.extend(clean_title.split()) # 공백 기준으로 분리 후 리스트 합치기
                words = [w for w in words if len(w) > 1] # 1글자 단어 필터링
                return Counter(words).most_common(top_n) # 최빈 단어 N개 반환
            for kw in keywords: # 분석 대상 키워드별로 반복 수행
                st.write(f"### '{kw}' 연관 키워드 빈도") # 키워드 빈도 제목 출력
                kw_titles = combined_content[combined_content['search_keyword'] == kw]['title'] # 해당 키워드의 제목 데이터 추출
                top_words = get_top_words(kw_titles) # 빈도 분석 함수 호출
                if top_words: # 분석 결과가 있는 경우
                    word_df = pd.DataFrame(top_words, columns=['word', 'count']) # 결과 데이터프레임 생성
                    # 수평 바 차트 시각화
                    fig_word = px.bar(word_df, x='count', y='word', orientation='h',
                                     title=f"'{kw}' 검색결과 제목 내 빈출 단어", 
                                     color='count', color_continuous_scale='Viridis') # 바 차트 생성
                    fig_word.update_layout(yaxis={'categoryorder':'total ascending'}) # 빈도순 정렬
                    st.plotly_chart(fig_word, use_container_width=True) # 차트 출력
                else: # 데이터 부족 시 안내 메세지
                    st.info(f"'{kw}'에 대한 충분한 텍스트 데이터가 없습니다.") # 정보 알림
        else: # 전체 콘텐츠 데이터 부재 시 경고
            st.warning("수집된 콘텐츠 데이터가 없습니다.") # 경고 메세지 출력

    # 다섯 번째 탭: 원본 데이터 조회 및 다운로드 기능
    with tab5: # Tab 5 영역 활성화
        st.subheader("수집 데이터 원본 확인") # 소제목 표시
        selected_table = st.selectbox("조회할 데이터셋 선택", list(data.keys())) # 표시할 테이블 선택 상자
        st.dataframe(data[selected_table], use_container_width=True) # 선택된 데이터프레임 표 형태로 출력
        csv = data[selected_table].to_csv(index=False, encoding='utf-8-sig') # CSV 형식으로 데이터 변환
        st.download_button( # 다운로드 버튼 생성
            label=f"{selected_table} 데이터 다운로드", # 버튼 라벨
            data=csv, # 다운로드할 데이터
            file_name=f"naver_{selected_table}_{datetime.now().strftime('%Y%m%d')}.csv", # 파일명 설정
            mime='text/csv', # MIME 타입 설정
        )
else: # 데이터가 수집되지 않은 초기 상태 화면
    st.info("사이드바에서 검색어를 입력하고 '데이터 수집 시작' 버튼을 눌러주세요.") # 안내 문구 표시
