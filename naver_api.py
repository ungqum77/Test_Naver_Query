import streamlit as st
import time
import hmac
import hashlib
import base64
import requests
import pandas as pd

# 1. 페이지 설정
st.set_page_config(page_title="미성 종합 키워드 분석기", layout="wide")
st.title("🚀 네이버 종합 키워드 분석기 (Search + Open API)")
st.markdown("검색량(수요)과 등록된 상품/블로그 수(공급)를 결합하여 진짜 경쟁률을 추출합니다.")

# 2. 대표님 API 키 통합 세팅
CUSTOMER_ID = "2742297"
SA_API_KEY = "0100000000146a449f6395fda02653bf30b187ddc173c55d92dc3612b6c79d171b1026f037"
SA_SECRET_KEY = "AQAAAAAUakSfY5X9oCZTvzCxh93BzE77ZJtnkgMKGNqRZ72FyQ=="
OPEN_CLIENT_ID = "DlHpolPL0Gi2PetN1_ck"
OPEN_CLIENT_SECRET = "h744pW79sO"

# --- [파이프 1] 검색광고 API (검색량 추출) ---
def generate_signature(timestamp, method, uri, secret_key):
    message = f"{timestamp}.{method}.{uri}"
    signing_key = hmac.new(bytes(secret_key, 'UTF-8'), bytes(message, 'UTF-8'), hashlib.sha256).digest()
    return base64.b64encode(signing_key).decode()

def get_search_volume(keyword):
    base_url = "https://api.naver.com"
    uri = "/keywordstool"
    timestamp = str(round(time.time() * 1000))
    signature = generate_signature(timestamp, "GET", uri, SA_SECRET_KEY)

    headers = {
        "X-Timestamp": timestamp,
        "X-API-KEY": SA_API_KEY,
        "X-Customer": str(CUSTOMER_ID),
        "X-Signature": signature
    }
    
    response = requests.get(base_url + uri, params={"hintKeywords": keyword, "showDetail": "1"}, headers=headers)
    if response.status_code == 200:
        return response.json()['keywordList']
    return None

# --- [파이프 2] 오픈 API (쇼핑 & 블로그 총 개수 추출) ---
def get_total_count(keyword, search_type):
    url = f"https://openapi.naver.com/v1/search/{search_type}.json"
    headers = {
        "X-Naver-Client-Id": OPEN_CLIENT_ID,
        "X-Naver-Client-Secret": OPEN_CLIENT_SECRET
    }
    # 데이터 목록은 필요 없고, 전체 개수(total)만 필요하므로 display=1
    response = requests.get(url, headers=headers, params={"query": keyword, "display": 1})
    if response.status_code == 200:
        return response.json().get('total', 0)
    return 0

# --- UI 및 실행 로직 ---
st.markdown("---")
col1, col2 = st.columns([3, 1])
with col1:
    search_keyword = st.text_input("🔍 분석할 메인 키워드를 입력하세요", placeholder="예: 캠핑의자")
with col2:
    st.write(" ")
    run_btn = st.button("🔥 딥스캐닝 시작")

if run_btn and search_keyword:
    with st.spinner("1단계: 연관 키워드 및 검색량(수요) 추출 중..."):
        sa_data = get_search_volume(search_keyword)
        
    if sa_data:
        df = pd.DataFrame(sa_data)
        df['PC검색량'] = pd.to_numeric(df['monthlyPcQcCnt'].replace('< 10', '10'))
        df['모바일검색량'] = pd.to_numeric(df['monthlyMobileQcCnt'].replace('< 10', '10'))
        df['총검색량'] = df['PC검색량'] + df['모바일검색량']
        
        # 검색량 기준 상위 10개만 필터링 (속도 및 API Limit 보호)
        top_df = df[['relKeyword', '총검색량']].sort_values(by='총검색량', ascending=False).head(10).reset_index(drop=True)
        top_df.rename(columns={'relKeyword': '키워드'}, inplace=True)
        
        shopping_counts = []
        blog_counts = []
        
        # 상위 10개 키워드에 대해 오픈 API 호출 (공급량 확인)
        progress_text = "2단계: 블로그 및 쇼핑 포화도(공급) 분석 중..."
        my_bar = st.progress(0, text=progress_text)
        
        for index, row in top_df.iterrows():
            kw = row['키워드']
            # 쇼핑 상품 수 추출
            shop_tot = get_total_count(kw, "shop")
            shopping_counts.append(shop_tot)
            
            # 블로그 문서 수 추출
            blog_tot = get_total_count(kw, "blog")
            blog_counts.append(blog_tot)
            
            # API 과부하 방지용 딜레이
            time.sleep(0.1)
            my_bar.progress((index + 1) / 10, text=progress_text)
            
        my_bar.empty()
        
        # 데이터 병합 및 경쟁률 계산
        top_df['쇼핑_상품수'] = shopping_counts
        top_df['블로그_문서수'] = blog_counts
        
        # 경쟁률 = 공급 / 수요 (보기 좋게 소수점 2자리)
        top_df['쇼핑_경쟁률'] = round(top_df['쇼핑_상품수'] / top_df['총검색량'], 2)
        top_df['블로그_경쟁률'] = round(top_df['블로그_문서수'] / top_df['총검색량'], 2)
        
        # 컬럼 순서 정리
        final_df = top_df[['키워드', '총검색량', '쇼핑_상품수', '쇼핑_경쟁률', '블로그_문서수', '블로그_경쟁률']]
        final_df.index = final_df.index + 1
        
        st.success("✅ 완벽한 통합 분석이 완료되었습니다!")
        st.dataframe(final_df, use_container_width=True)
        
        # 강의용 인사이트 멘트
        st.info("💡 **[J.W의 데이터 인사이트]** 쇼핑/블로그 경쟁률이 낮으면서 총 검색량이 높은 키워드가 진정한 '블루오션'입니다.")
