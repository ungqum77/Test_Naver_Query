import streamlit as st
import time
import hmac
import hashlib
import base64
import requests
import pandas as pd

# 1. 페이지 설정
st.set_page_config(page_title="네이버 API 실습 - 미성상회", layout="wide")
st.title("🚀 네이버 검색광고 API 실시간 연동 테스트 (Ver 1.0)")

# 2. 대표님 계정 정보 (내부 로직용)
CUSTOMER_ID = "2742297"
API_KEY = "0100000000146a449f6395fda02653bf30b187ddc173c55d92dc3612b6c79d171b1026f037"
SECRET_KEY = "AQAAAAAUakSfY5X9oCZTvzCxh93BzE77ZJtnkgMKGNqRZ72FyQ=="

def generate_signature(timestamp, method, uri, secret_key):
    message = f"{timestamp}.{method}.{uri}"
    secret_key_bytes = bytes(secret_key, 'UTF-8')
    message_bytes = bytes(message, 'UTF-8')
    signing_key = hmac.new(secret_key_bytes, message_bytes, hashlib.sha256).digest()
    return base64.b64encode(signing_key).decode()

def get_naver_data(keyword):
    base_url = "https://api.naver.com"
    uri = "/keywordstool"
    method = "GET"
    timestamp = str(round(time.time() * 1000))
    signature = generate_signature(timestamp, method, uri, SECRET_KEY)

    headers = {
        "X-Timestamp": timestamp,
        "X-API-KEY": API_KEY,
        "X-Customer": str(CUSTOMER_ID),
        "X-Signature": signature
    }

    params = {"hintKeywords": keyword, "showDetail": "1"}
    
    try:
        response = requests.get(base_url + uri, params=params, headers=headers)
        if response.status_code == 200:
            return response.json()['keywordList']
        else:
            st.error(f"API 요청 실패: {response.status_code}")
            st.write(response.text)
            return None
    except Exception as e:
        st.error(f"연결 에러: {str(e)}")
        return None

# UI 구성
st.markdown("---")
col1, col2 = st.columns([3, 1])
with col1:
    search_keyword = st.text_input("🔍 분석할 키워드를 입력하세요", placeholder="예: 캠핑의자, 목살, 한우")
with col2:
    st.write(" ") # 간격 맞춤
    run_btn = st.button("데이터 퍼오기")

if run_btn and search_keyword:
    with st.spinner("네이버 API 서버와 통신 중..."):
        data = get_naver_data(search_keyword)
        
        if data:
            df = pd.DataFrame(data)
            # 필요한 컬럼만 추출 및 이름 변경
            df = df[['relKeyword', 'monthlyPcQcCnt', 'monthlyMobileQcCnt', 'compIdx']]
            df.columns = ['키워드', 'PC검색량', '모바일검색량', '경쟁강도']
            
            # 숫자 변환 (10 미만인 경우 '10'으로 처리)
            df['PC검색량'] = pd.to_numeric(df['PC검색량'].replace('< 10', '10'))
            df['모바일검색량'] = pd.to_numeric(df['모바일검색량'].replace('< 10', '10'))
            df['총검색량'] = df['PC검색량'] + df['모바일검색량']
            
            # 결과 정렬 및 출력
            df = df[['키워드', '총검색량', 'PC검색량', '모바일검색량', '경쟁강도']]
            df = df.sort_values(by='총검색량', ascending=False).reset_index(drop=True)
            df.index = df.index + 1
            
            st.success(f"✅ '{search_keyword}' 관련 키워드 {len(df)}개를 불러왔습니다.")
            st.dataframe(df, use_container_width=True)
            
            # CSV 다운로드 기능
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("엑셀용 CSV 다운로드", data=csv, file_name=f"{search_keyword}_분석결과.csv")