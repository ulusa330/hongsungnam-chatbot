#!/usr/bin/env python3
"""
====================================================================
홍성남 신부님 톡쏘는 영성심리 - AI 상담 챗봇 데모 (v5)
====================================================================
[변경사항 v5]
  - 홍성남 신부님 프로필·저서 정보 시스템 프롬프트에 추가
  - 책 추천 기능 지원
  - 전화 걸기 버튼 색상 개선 (금색)
  - "제" 표현 제거
  - 출처별 필터링 기능 (v4 유지)
[사용법]
  1. 필수 패키지 설치:
     pip install streamlit openai numpy python-dotenv
  2. 벡터DB 구축 (최초 1회):
     python build_vectordb.py
  3. 챗봇 실행:
     streamlit run chatbot_demo.py
  4. 외부 접속 (프레젠테이션용):
     streamlit run chatbot_demo.py --server.address 0.0.0.0 --server.port 8501
====================================================================
"""
import os
import re
import json
import numpy as np
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

# =====================================================================
# 강의 일정 로드
# =====================================================================
SCHEDULE_FILE = Path(__file__).parent / "schedule.json"

def load_schedule():
    """schedule.json에서 일정 데이터를 로드"""
    try:
        with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {
            "next_lecture": {"status": "unconfirmed"},
            "regular_schedule": {
                "pattern": "매월 셋째 주 토요일",
                "time": "오후 3시",
                "location": "가톨릭회관",
                "contact": "776-8405"
            }
        }

SCHEDULE = load_schedule()

def get_schedule_card_html():
    """초기 화면에 표시할 일정 카드 HTML 생성"""
    lecture = SCHEDULE.get("next_lecture", {})
    regular = SCHEDULE.get("regular_schedule", {})

    if lecture.get("status") == "confirmed":
        date = lecture.get("date", "")
        year = date[:4] if date else ""
        month = str(int(date[5:7])) if date else ""
        day = str(int(date[8:10])) if date else ""
        dow = lecture.get("day_of_week", "")
        t_start = lecture.get("time_start", "")
        t_end = lecture.get("time_end", "")
        # 시간 포맷
        h_start = int(t_start.split(":")[0]) if t_start else 0
        period_start = "오후" if h_start >= 12 else "오전"
        h_start_12 = h_start - 12 if h_start > 12 else h_start
        h_end = int(t_end.split(":")[0]) if t_end else 0
        period_end = "오후" if h_end >= 12 else "오전"
        h_end_12 = h_end - 12 if h_end > 12 else h_end
        time_str = f"{period_start} {h_start_12}시~{h_end_12}시"

        location = lecture.get("location", "")
        fee = lecture.get("fee", "")
        contact = lecture.get("contact", "")
        title = lecture.get("title", "영성심리특강")
        note = lecture.get("note", "")

        fee_text = f"회비 {fee}" if fee else ""
        contact_text = f"문의 {contact}" if contact else ""
        detail_parts = [p for p in [fee_text, contact_text] if p]
        detail_line = " | ".join(detail_parts)
        note_line = f'<div style="margin-top:0.4rem;font-size:0.85rem;color:#c9d4e8;">{note}</div>' if note else ""

        return f"""
        <div style="background:linear-gradient(135deg,#1B2B5E 0%,#2d4a8c 100%);border-radius:12px;padding:1.2rem 1.5rem;margin-bottom:1rem;border-left:4px solid #C9A84C;box-shadow:0 2px 12px rgba(27,43,94,0.3);">
            <div style="color:#C9A84C;font-weight:700;font-size:1.05rem;margin-bottom:0.4rem;">📅 {year}년 {month}월 {title} 안내</div>
            <div style="color:white;font-size:0.95rem;">{month}월 {day}일({dow}) {time_str} | {location}</div>
            <div style="color:#a0b0d0;font-size:0.85rem;margin-top:0.3rem;">{detail_line}</div>
            {note_line}
        </div>
        """
    else:
        pattern = regular.get("pattern", "매월 셋째 주 토요일")
        time = regular.get("time", "오후 3시")
        location = regular.get("location", "가톨릭회관")
        return f"""
        <div style="background:linear-gradient(135deg,#1B2B5E 0%,#2d4a8c 100%);border-radius:12px;padding:1.2rem 1.5rem;margin-bottom:1rem;border-left:4px solid #C9A84C;box-shadow:0 2px 12px rgba(27,43,94,0.3);">
            <div style="color:#C9A84C;font-weight:700;font-size:1.05rem;margin-bottom:0.4rem;">📅 다음 정기특강 안내</div>
            <div style="color:white;font-size:0.95rem;">{pattern} {time} | {location}</div>
            <div style="color:#a0b0d0;font-size:0.85rem;margin-top:0.3rem;">확정 일정은 추후 공지됩니다</div>
        </div>
        """

def get_schedule_prompt_text():
    """시스템 프롬프트에 삽입할 일정 텍스트 생성"""
    lecture = SCHEDULE.get("next_lecture", {})
    regular = SCHEDULE.get("regular_schedule", {})

    if lecture.get("status") == "confirmed":
        date = lecture.get("date", "")
        year = date[:4] if date else ""
        month = str(int(date[5:7])) if date else ""
        day = str(int(date[8:10])) if date else ""
        dow = lecture.get("day_of_week", "")
        t_start = lecture.get("time_start", "")
        t_end = lecture.get("time_end", "")
        h_start = int(t_start.split(":")[0]) if t_start else 0
        period_start = "오후" if h_start >= 12 else "오전"
        h_start_12 = h_start - 12 if h_start > 12 else h_start
        h_end = int(t_end.split(":")[0]) if t_end else 0
        period_end = "오후" if h_end >= 12 else "오전"
        h_end_12 = h_end - 12 if h_end > 12 else h_end
        time_str = f"{period_start} {h_start_12}시~{h_end_12}시"
        location = lecture.get("location", "")
        fee = lecture.get("fee", "")
        contact = lecture.get("contact", "")
        title = lecture.get("title", "영성심리특강")
        return (
            f"다음 {title} 일정: {year}년 {month}월 {day}일({dow}) {time_str}, "
            f"{location}. 회비 {fee}. 문의 {contact}."
        )
    else:
        pattern = regular.get("pattern", "매월 셋째 주 토요일")
        time = regular.get("time", "오후 3시")
        location = regular.get("location", "가톨릭회관")
        contact = regular.get("contact", "776-8405")
        return (
            f"{pattern} {time}, {location}에서 정기특강을 진행합니다만, "
            f"아직 확정된 일정이 없습니다. {contact}로 문의해 주세요."
        )
# =====================================================================
# 페이지 설정
# =====================================================================
st.set_page_config(
    page_title="톡쏘는 영성심리 AI 상담",
    page_icon="🕊️",
    layout="wide",
    initial_sidebar_state="expanded",
)
# =====================================================================
# 커스텀 CSS
# =====================================================================
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    .main-header {
        background: linear-gradient(135deg, #1B2B5E 0%, #2d4a8c 100%);
        color: white;
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 20px rgba(27, 43, 94, 0.3);
    }
    .main-header h1 {
        color: white !important;
        font-size: 2rem !important;
        margin-bottom: 0.3rem !important;
    }
    .main-header p {
        color: #c9d4e8 !important;
        font-size: 1rem;
        margin: 0;
    }
    .stChatMessage {
        border-radius: 12px !important;
        margin-bottom: 0.8rem !important;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1B2B5E 0%, #162248 100%);
    }
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stSlider label {
        color: #c9d4e8 !important;
    }
    .source-card {
        background: white;
        border-left: 4px solid #C9A84C;
        padding: 1rem 1.2rem;
        margin: 0.5rem 0;
        border-radius: 0 8px 8px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        transition: transform 0.2s;
    }
    .source-card:hover {
        transform: translateX(4px);
    }
    .source-card .title {
        font-weight: 600;
        color: #1B2B5E;
        font-size: 0.95rem;
        margin-bottom: 0.3rem;
    }
    .source-card .meta {
        color: #666;
        font-size: 0.8rem;
    }
    .source-card a {
        color: #C9A84C;
        text-decoration: none;
        font-weight: 500;
    }
    .source-card-column {
        background: white;
        border-left: 4px solid #0D9488;
        padding: 1rem 1.2rem;
        margin: 0.5rem 0;
        border-radius: 0 8px 8px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        transition: transform 0.2s;
    }
    .source-card-column:hover {
        transform: translateX(4px);
    }
    .source-card-column .title {
        font-weight: 600;
        color: #1B2B5E;
        font-size: 0.95rem;
        margin-bottom: 0.3rem;
    }
    .source-card-column .meta {
        color: #666;
        font-size: 0.8rem;
    }
    .source-card-column a {
        color: #0D9488;
        text-decoration: none;
        font-weight: 500;
    }
    .filter-badge {
        display: inline-block;
        background: #1B2B5E;
        color: white !important;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        margin-bottom: 0.5rem;
    }
    .stat-card {
        background: rgba(255,255,255,0.1);
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        margin: 0.5rem 0;
    }
    .stat-card .number {
        font-size: 1.8rem;
        font-weight: 700;
        color: #C9A84C;
    }
    .stat-card .label {
        font-size: 0.8rem;
        color: #a0b0d0;
    }
    .footer {
        text-align: center;
        color: #888;
        font-size: 0.75rem;
        padding: 2rem 0 1rem;
        border-top: 1px solid #e0e0e0;
        margin-top: 2rem;
    }
  .stTextInput input, .stChatInput textarea {
    background-color: #FFFFFF !important;
    color: #1B2B5E !important;
}
.stChatInput {
    background-color: #FFFFFF !important;
}

 /* Streamlit 하단 배지 및 관리 버튼 숨기기 */
    footer {visibility: hidden !important;}
    #MainMenu {visibility: hidden !important;}
    header {visibility: hidden !important;}
    .stDeployButton {display: none !important;}
    [data-testid="stToolbar"] {display: none !important;}
    [data-testid="stDecoration"] {display: none !important;}
    [data-testid="stStatusWidget"] {display: none !important;}
    [data-testid="manage-app-button"] {display: none !important;}
    .viewerBadge_container__r5tak {display: none !important;}
    .stAppDeployButton {display: none !important;}
    a[href="https://streamlit.io"] {display: none !important;}
    iframe[title="streamlit_badge"] {display: none !important;}
    [data-testid="stAppViewBlockContainer"] + div {display: none !important;}
    .reportview-container .main footer {display: none !important;}
    div[class*="viewerBadge"] {display: none !important;}
    div[class*="stStreamlitBadge"] {display: none !important;}
    section[data-testid="stSidebar"] + div + footer {display: none !important;}


/* 모바일 최적화 (50~80대 사용자 대응) */
.stApp { font-size: 1.1rem !important; }
@media (max-width: 768px) {
    [data-testid="stSidebar"] { display: none !important; }
    .main .block-container { padding: 0.5rem 1rem !important; max-width: 100% !important; }
    .main-header { padding: 1.2rem 1rem !important; border-radius: 10px !important; margin-bottom: 0.5rem !important; }
    .main-header h1 { font-size: 1.4rem !important; }
    h4 { font-size: 1.1rem !important; margin-top: 0 !important; }
    .stChatMessage, .stChatMessage p { font-size: 1.15rem !important; line-height: 1.8 !important; }
    .stButton > button { font-size: 1.1rem !important; padding: 1rem 1.2rem !important; min-height: 60px !important; border-radius: 12px !important; white-space: normal !important; background-color: #1B2B5E !important; color: white !important; border: none !important; }
    .stChatInput textarea { font-size: 1.15rem !important; min-height: 50px !important; background-color: #FFFFFF !important; color: #1B2B5E !important; }
    [data-testid="column"] { width: 100% !important; flex: 100% !important; min-width: 100% !important; }
    .footer { font-size: 0.8rem !important; }
}
</style>
""", unsafe_allow_html=True)
# =====================================================================
# 출처 필터링 시스템
# =====================================================================
# 신문사 필터 키워드
NEWSPAPER_FILTERS = {
    '중앙일보': ['중앙일보', '중앙'],
    '가톨릭신문': ['가톨릭신문', '가톨릭 신문'],
    '경향신문': ['경향신문', '경향 신문', '경향'],
}
# 유튜브 시리즈 필터 키워드 (제목에 포함된 패턴)
YOUTUBE_SERIES_FILTERS = {
    '맹모닝 상담소': ['맹모닝', '맹모닝 상담소', '맹모닝상담소'],
    '마태오묵상집': ['마태오묵상', '마태오 묵상', '마태오묵상집'],
    '요한묵상집': ['요한묵상', '요한 묵상', '요한묵상집'],
    '창세기묵상집': ['창세기묵상', '창세기 묵상', '창세기묵상집'],
    '10분 강의': ['10분 강의', '10분강의', '십분 강의'],
    '톡쏘는 영성심리': ['톡쏘는', '영성심리'],
    '사수영': ['사수영', '사제와 수도자', '사제와수도자'],
    'cpbc': ['cpbc특강', 'cpbc뉴스', 'cpbc', '가톨릭 청춘어게인', '청춘어게인'],
}

# 월특강 감지 (날짜 패턴: [240101], 180609 등)
MONTHLY_LECTURE_PATTERN = re.compile(r'\[?\d{6}\]?')

# 일반 출처 타입 필터
SOURCE_TYPE_FILTERS = {
    'column': ['칼럼', '신문', '기고', '신문 칼럼', '신문칼럼'],
    'youtube': ['유튜브', '영상', '동영상', '강의 영상'],
}

def detect_source_filter(query):
    """질문에서 출처 필터 키워드를 감지"""
    query_lower = query.lower().strip()

    # 1. 특정 신문사 필터 감지
    for newspaper, keywords in NEWSPAPER_FILTERS.items():
        for kw in keywords:
            if kw in query_lower:
                return {
                    'type': 'newspaper',
                    'value': newspaper,
                    'label': f"📰 {newspaper} 칼럼에서 검색",
                }

    # 2. 월특강 필터 감지
    if '월특강' in query_lower or '월 특강' in query_lower:
        return {
            'type': 'monthly_lecture',
            'value': 'monthly',
            'label': "📹 월특강에서 검색",
        }

    # 3. 유튜브 시리즈 필터 감지
    for series, keywords in YOUTUBE_SERIES_FILTERS.items():
        for kw in keywords:
            if kw in query_lower:
                return {
                    'type': 'youtube_series',
                    'value': series,
                    'label': f"📹 [{series}] 시리즈에서 검색",
                }

    # 4. 일반 출처 타입 필터 감지
    for source_type, keywords in SOURCE_TYPE_FILTERS.items():
        for kw in keywords:
            if kw in query_lower:
                if source_type == 'column':
                    return {
                        'type': 'source_type',
                        'value': 'column',
                        'label': "📰 신문 칼럼에서 검색",
                    }
                else:
                    return {
                        'type': 'source_type',
                        'value': 'youtube',
                        'label': "📹 유튜브 영상에서 검색",
                    }

    # 필터 없음 (전체 검색)
    return None


def apply_filter(db, source_filter):
    """필터 조건에 맞는 인덱스 목록 반환"""
    if source_filter is None:
        return None  # 전체 검색

    metadata = db['metadata']
    valid_indices = []

    for i, meta in enumerate(metadata):
        filter_type = source_filter['type']
        filter_value = source_filter['value']

        if filter_type == 'newspaper':
            if meta.get('source_type') == 'column':
                newspaper = meta.get('newspaper', '')
                if filter_value in newspaper:
                    valid_indices.append(i)

        elif filter_type == 'youtube_series':
            if meta.get('source_type', 'youtube') == 'youtube':
                title = meta.get('title', '')
                series_keywords = YOUTUBE_SERIES_FILTERS.get(filter_value, [filter_value])
                if any(kw in title for kw in series_keywords) or filter_value in title:
                    valid_indices.append(i)

        elif filter_type == 'monthly_lecture':
            if meta.get('source_type', 'youtube') == 'youtube':
                title = meta.get('title', '')
                if MONTHLY_LECTURE_PATTERN.search(title):
                    valid_indices.append(i)

        elif filter_type == 'source_type':
            if meta.get('source_type', 'youtube') == filter_value:
                valid_indices.append(i)

    return valid_indices

# =====================================================================
# 벡터DB 초기화 (numpy + JSON 기반)
# =====================================================================
VECTORDB_DIR = Path("./vectordb_홍성남신부")
EMBEDDINGS_FILE = VECTORDB_DIR / "embeddings.npz"
METADATA_FILE = VECTORDB_DIR / "metadata.json"
@st.cache_resource
def init_vectordb():
    """벡터DB 로드 (numpy + JSON)"""
    if not EMBEDDINGS_FILE.exists() or not METADATA_FILE.exists():
        return None
    try:
        data = np.load(EMBEDDINGS_FILE)
        embeddings = data['embeddings']
        with open(METADATA_FILE, 'r', encoding='utf-8') as f:
            saved = json.load(f)
        metadata_list = saved.get('metadata', [])
        youtube_titles = set()
        column_count = 0
        for m in metadata_list:
            source_type = m.get('source_type', 'youtube')
            if source_type == 'youtube':
                youtube_titles.add(m.get('title', ''))
            elif source_type == 'column':
                column_count += 1
        return {
            'embeddings': embeddings,
            'metadata': metadata_list,
            'documents': saved.get('documents', []),
            'count': len(embeddings),
            'youtube_count': len(youtube_titles),
            'column_count': column_count,
        }
    except Exception as e:
        st.error(f"벡터DB 로드 오류: {e}")
        return None
@st.cache_resource
def init_openai():
    """OpenAI 클라이언트 초기화"""
    import openai
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return None
    return openai.OpenAI(api_key=api_key)
def cosine_similarity(a, b):
    """코사인 유사도 계산"""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
def search_similar(db, query, n_results=5, source_filter=None):
    """벡터DB에서 유사 문서 검색 (필터 지원)"""
    openai_client = init_openai()
    if not openai_client or db is None:
        return None
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=query,
    )
    query_embedding = np.array(response.data[0].embedding)

    filter_indices = apply_filter(db, source_filter)

    if filter_indices is not None and len(filter_indices) == 0:
        return None

    embeddings = db['embeddings']

    if filter_indices is not None:
        filter_indices = np.array(filter_indices)
        filtered_embeddings = embeddings[filter_indices]
        similarities = np.array([
            cosine_similarity(query_embedding, emb)
            for emb in filtered_embeddings
        ])
        top_local = np.argsort(similarities)[::-1][:n_results]
        top_indices = filter_indices[top_local]
        top_sims = similarities[top_local]
    else:
        similarities = np.array([
            cosine_similarity(query_embedding, emb)
            for emb in embeddings
        ])
        top_indices = np.argsort(similarities)[::-1][:n_results]
        top_sims = similarities[top_indices]

    results = {
        'documents': [db['documents'][i] for i in top_indices],
        'metadatas': [db['metadata'][i] for i in top_indices],
        'similarities': [float(s) for s in top_sims],
    }
    return results
def generate_response(query, context_docs, context_metas, source_filter=None):
    """RAG 기반 응답 생성"""
    openai_client = init_openai()
    if not openai_client:
        return "OpenAI API 키가 설정되지 않았습니다."
    context_parts = []
    for i, (doc, meta) in enumerate(zip(context_docs, context_metas)):
        title = meta.get('title', '제목 미상')
        source_type = meta.get('source_type', 'youtube')
        if source_type == 'column':
            newspaper = meta.get('newspaper', '신문')
            source_label = f"신문 칼럼 - {newspaper}"
        else:
            source_label = "유튜브 강의"
        context_parts.append(f"[출처 {i+1}: {title} ({source_label})]\n{doc}")
    context = "\n\n---\n\n".join(context_parts)

    filter_instruction = ""
    if source_filter:
        filter_label = source_filter.get('label', '')
        filter_instruction = f"\n\n[현재 검색 필터]\n사용자가 특정 출처를 지정하여 질문했습니다: {filter_label}\n제공된 컨텍스트는 해당 출처에서만 검색된 결과입니다. 답변 시 이 출처에서 찾은 내용임을 명시해 주세요."

    # 일정 키워드 감지 시 시스템 프롬프트에 일정 정보 추가
    schedule_instruction = ""
    schedule_keywords = ['강의 일정', '특강', '언제', '일정', '다음 강의', '강의 날짜', '특강 날짜', '다음 특강']
    if any(kw in query for kw in schedule_keywords):
        schedule_text = get_schedule_prompt_text()
        schedule_instruction = f"\n\n[강의 일정 정보]\n{schedule_text}\n사용자가 일정에 대해 물었으므로 위 정보를 참고하여 안내해 주세요."

    system_prompt = f"""당신은 홍성남 마태오 신부의 말투와 관점으로 직접 상담해 주는 AI입니다. 홍성남 신부의 유튜브 강의, 맹모닝 상담소, 신문 칼럼의 내용을 바탕으로, 마치 신부님이 직접 대화하듯이 답변하세요.

[나는 누구인가 — 홍성남 마태오 신부 프로필]
- 이름: 홍성남 마태오
- 소속: 천주교 서울대교구, 특수사목
- 현 소임: 서울대교구 가톨릭영성심리상담소 소장, 영성·심리 상담과 치유 사목 중심 활동
- 사제 서품: 1987년 2월 6일
- 과거 소임: 잠실·명동성당 보좌, 마석·학동·상계동·가좌동 성당 주임
- 방송: cpbc TV 「홍성남 신부의 사주풀이」, 유튜브 '톡쏘는 영성심리' 채널 메인 게스트
- 활동: 「행복한 신앙」「기쁜 신앙」 영성 특강, '웃어야 산다' 치유·웃음 특강, 맹경순 선생님과 '맹모닝 상담소' 진행
- 스타일: 심리 상담과 영성지도를 결합, 상처·우울·자존감 문제를 신앙 안에서 바라보도록 돕는 치유 사목. 직설적이고 현실적인 언어를 사용하면서도 하느님의 자비와 자기 수용을 강조

[맹모닝 상담소 파트너 — 맹경순 베로니카]
- 이름: 맹경순 (세례명 베로니카)
- 출생: 1950년 9월 24일, 서울
- 학력: 이화여자대학교 국문학과 졸업
- 경력: 1973년 동아방송 아나운서 입사 → 1975년 동아방송 언론자유 운동(민주언론운동)으로 해직 → 프리랜서로 MBC·TBC·KBS 라디오 진행 → 1990년 가톨릭평화방송(cpbc) 아나운서 팀장 합류, 이후 아나운서부 부장·실장 역임
- 방송: cpbc에서 「추억의 가요산책」「FM 음악공감」「성서 못자리」「신앙상담 따뜻한 동행」「맹경순의 아름다운 세상」 등 다수 프로그램 진행. 현재 유튜브 '톡쏘는 영성심리' 채널에서 홍성남 신부와 함께 '맹모닝 상담소' 진행
- 수상: 1999년 한국방송대상 아나운서상, 2007년 대한민국아나운서대상
- 특이사항: 1975년 동아방송 해직은 박정희 유신정권의 언론 통제에 맞선 자유언론실천선언 참여 결과. 2001년 민주화운동 관련자로 공식 인정. "자유언론은 뒷날 영광이었고, 당시는 그냥 동료를 버릴 수 없었을 뿐"이라고 회고
- "맹경순 선생님은 누구세요?" 같은 질문에는 위 정보를 바탕으로 따뜻하게 소개하세요. 나와 함께 맹모닝 상담소를 이끌어가는 소중한 파트너라고 표현하세요.

[맹모닝 상담소 안내]
- "맹모닝"은 맹경순 선생님의 "맹" + "모닝(morning)"을 합친 이름이다.
- "맥모닝"이 아니라 반드시 "맹모닝"으로 표기해야 한다. 절대 "맥모닝"이라고 쓰지 말 것.
- 맹모닝 상담소는 홍성남 신부와 맹경순 선생님이 함께 진행하는 유튜브 상담 프로그램이다.
- 시청자들의 사연을 받아 심리·영성 관점에서 상담해주는 형식이다.

[나의 저서 — 책 추천 시 활용]
최근·대표작:
- 「끝까지 나를 사랑하는 마음」
- 「나는 생각보다 괜찮은 사람」
- 「거꾸로 보는 종교」
- 「혼자서 마음을 치유하는 법」
- 「내 마음이 어때서」
- 「나로 사는 걸 깜빡했어요」
- 「챙기고 사세요」

이전부터 많이 읽힌 책:
- 「화나면 화내고 힘들 땐 쉬어」
- 「아! 어쩌나」 시리즈 (신앙생활 편 / 자존감 편 / 영성심리 편)
- 「풀어야 산다」
- 「행복을 위한 탈출」
- 「새장 밖으로」

책 추천 가이드:
- 상처·트라우마, 자기혐오 → 「끝까지 나를 사랑하는 마음」「나는 생각보다 괜찮은 사람」「나로 사는 걸 깜빡했어요」
- 마음이 힘들고 스스로 돌보는 법 → 「혼자서 마음을 치유하는 법」「내 마음이 어때서」
- 화·분노 조절 → 「화나면 화내고 힘들 땐 쉬어」「풀어야 산다」
- 신앙생활·영성심리 전반 → 「아! 어쩌나」 시리즈, 「새장 밖으로」「행복을 위한 탈출」
- 사용자가 "책 추천해 주세요"라고 하면 고민의 유형에 맞는 책을 위 가이드에 따라 추천하세요

[말투 규칙 — 매우 중요]
- "홍성남 신부님은 ~라고 말씀하셨습니다" (X) → 제3자 시점 절대 금지
- "~가 중요합니다", "~해 보세요", "~하는 거예요" (O) → 직접 말하는 것처럼
- 따뜻하면서도 때로는 직설적이고 톡 쏘는 어조를 섞어 주세요
- 상대방의 아픔에 공감하면서도 현실적인 조언을 해 주세요
- "늘 강조하는 건데요", "강의에서도 말씀드렸지만" 같은 표현을 자연스럽게 사용하세요
- 절대 "신부님께서는", "홍성남 신부님은" 같은 3인칭 표현을 쓰지 마세요
- "나는 누구세요?" 같은 질문에는 위 프로필 정보를 바탕으로 1인칭으로 자연스럽게 자기소개하세요

[상담 안내 필수 규칙 — 매우 중요]
사용자가 "상담 받고 싶다", "상담 신청", "직접 만나서 상담" 등 상담을 요청하면:

1단계 — 먼저 물어보세요:
"혹시 저(홍성남 신부)와의 상담을 원하시는 건가요, 아니면 전문 심리상담을 받고 싶으신 건가요?"

2단계 — 답변에 따라 안내:
(A) 홍성남 신부와 상담을 원하는 경우:
- 반드시 "저는 현재 성직자 상담만 하고 있어서, 일반 신자분들과 개인적으로 만나서 상담하기는 어렵습니다."라고 먼저 말하세요.
- "대신, talktoclinic@gmail.com로 사연을 보내주시면, 저와 맹경순 선생님이 의견을 모아 방송(유튜브)을 통한 상담을 해 드릴 수 있습니다."
- "성직자 상담만 한다"는 것을 절대 빠뜨리지 마세요.

(B) 전문 심리상담을 원하는 경우:
- "가톨릭영성심리상담소(02-727-2516, 오전 11시~오후 4시)로 연락 주시면, 전문 상담가 선생님들의 상담을 받으실 수 있습니다."

사용자가 "개인 상담이 왜 안 되나요?"라고 물으면:
- "저는 현재 성직자 상담만 하고 있기 때문입니다. 대신 사연을 보내주시면 방송을 통해 상담해 드리고, 전문 상담이 필요하시면 가톨릭영성심리상담소를 안내해 드립니다."라고 답하세요.

[규칙]
1. 제공된 강의 및 칼럼 내용(컨텍스트)을 기반으로만 답변하세요.
2. 컨텍스트에 없는 내용은 "이 부분은 강의나 칼럼에서 직접 다루지는 않았지만..."이라고 전제하세요.
3. 의학적 진단이나 처방은 절대 하지 마세요.
4. 심각한 심리적 위기 상황이면 전문 상담 기관을 안내하세요.
5. 답변 마지막에 참고한 출처 정보를 안내하세요.
6. 한국어로 답변하세요.
7. 출처가 신문 칼럼인 경우 "○○신문 칼럼"이라고 표현하세요.
8. 출처가 유튜브 시리즈인 경우 "[맹모닝 상담소] 영상", "[10분 강의]" 같은 식으로 표현하세요.{filter_instruction}{schedule_instruction}"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"""질문: {query}

참고할 내용:
{context}

위 내용을 바탕으로 답변해 주세요. 답변 끝에 참고한 출처(유튜브 강의 제목 또는 신문 칼럼 제목)를 알려주세요."""},
    ]

    # 대화 히스토리 추가 (최근 4개)
    if "messages" in st.session_state and len(st.session_state.messages) > 0:
        history = st.session_state.messages[-4:]
        history_messages = [{"role": m["role"], "content": m["content"]} for m in history]
        messages = [messages[0]] + history_messages + [messages[1]]

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.3,
        max_tokens=4000,
    )
    return response.choices[0].message.content
# =====================================================================
# 사이드바
# =====================================================================
with st.sidebar:
    st.markdown("### 🕊️ 톡쏘는 영성심리")
    st.markdown("**AI 심리상담 도우미**")
    st.markdown("---")

    db = init_vectordb()
    openai_client = init_openai()

    if db:
        st.markdown("""
        <div style="background: rgba(255,255,255,0.15); border-radius: 8px; padding: 0.8rem; margin-top: 1rem; text-align: center; border: 1px solid rgba(255,255,255,0.2);">
            <span style="color: #C9A84C; font-size: 0.85rem;">⚠ 이 프로그램은 테스트 용도로 만들어진 것입니다.</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="stat-card">
            <div class="number">{db['count']:,}</div>
            <div class="label">학습된 텍스트 조각</div>
        </div>
        """, unsafe_allow_html=True)

        youtube_count = db.get('youtube_count', 1037)
        column_count = db.get('column_count', 0)

        st.markdown(f"""
        <div class="stat-card">
            <div class="number">{youtube_count:,}</div>
            <div class="label">📹 분석된 강의 영상</div>
        </div>
        """, unsafe_allow_html=True)

        if column_count > 0:
            st.markdown(f"""
            <div class="stat-card">
                <div class="number">{column_count:,}</div>
                <div class="label">📰 수집된 신문 칼럼</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    n_results = st.slider("참고 문서 수", 3, 10, 5, help="답변 시 참고할 텍스트 수")

    st.markdown("---")
    st.markdown("**시스템 상태**")
    if db:
        st.success("벡터DB 연결됨")
    else:
        st.error("벡터DB 없음 — build_vectordb.py 실행 필요")
    if openai_client:
        st.success("OpenAI API 연결됨")
    else:
        st.error("API 키 미설정")

    st.markdown("---")
    st.markdown("""
    <div style="font-size: 0.75rem; color: #8899bb;">
        <b> 개발 : 이재욱 토마스 </b><br>
         talktoclinic@gmail.com <br>
        유튜브: youtube.com/@fr.hongsungnam<br><br>
        <b>Powered by</b><br>
        OpenAI GPT-4o-mini<br>
        벡터 검색 (numpy)
    </div>
    """, unsafe_allow_html=True)
# =====================================================================
# 메인 영역
# =====================================================================
st.markdown("""
<div class="main-header">
    <h1>🕊️ 톡쏘는 영성심리 AI 상담</h1>
    <p>유튜브 채널 "홍성남 신부님의 톡쏘는 영성심리"의 영상들과 신문 칼럼, 저서들을 학습한 AI가 심리 및 영성 상담을 도와 드립니다</p>
</div>
""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

# 예시 질문
if not st.session_state.messages:
    st.markdown(get_schedule_card_html(), unsafe_allow_html=True)
    st.markdown("#### 💬 이런 질문을 해보세요")
    col1, col2 = st.columns(2)
    example_questions = [
        "화가 날 때 어떻게 해야 하나요?",
        "나르시시스트 상사와 어떻게 지내야 하나요?",
        "자존감이 낮은데 어떻게 해야 할까요?",
        "부모님과의 관계가 힘들어요",
        "용서한다는 것은 어떤 의미인가요?",
        "우울할 때 신앙이 도움이 되나요?",
    ]
    for i, q in enumerate(example_questions):
        col = col1 if i % 2 == 0 else col2
        if col.button(q, key=f"example_{i}", use_container_width=True):
            st.session_state.pending_question = q
            st.rerun()
    st.markdown("---")

# 기존 메시지 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"], avatar="🙋" if message["role"] == "user" else "🕊️"):
        st.markdown(message["content"])
        if message["role"] == "assistant" and "sources" in message:
            with st.expander("📚 참고 자료", expanded=False):
                for src in message["sources"]:
                    source_type = src.get('source_type', 'youtube')
                    if source_type == 'column':
                        newspaper = src.get('newspaper', '신문')
                        st.markdown(f"""
                        <div class="source-card-column">
                            <div class="title">📰 {src['title']}</div>
                            <div class="meta">📅 {src.get('date', '')} &nbsp;|&nbsp; {newspaper} &nbsp;|&nbsp;
                            <a href="{src.get('url', '#')}" target="_blank">🔗 칼럼 보기</a></div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="source-card">
                            <div class="title">📹 {src['title']}</div>
                            <div class="meta">📅 {src.get('date', '')} &nbsp;|&nbsp;
                            <a href="{src.get('url', '#')}" target="_blank">🔗 영상 보기</a></div>
                        </div>
                        """, unsafe_allow_html=True)

# =====================================================================
# 채팅 입력 처리
# =====================================================================
pending = st.session_state.pop("pending_question", None)
prompt = st.chat_input("심리·영성 관련 질문을 해보세요...")
if pending:
    prompt = pending

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🙋"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🕊️"):
        if not db:
            st.error("벡터DB가 초기화되지 않았습니다. `python build_vectordb.py`를 먼저 실행하세요.")
        elif not openai_client:
            st.error("OpenAI API 키가 설정되지 않았습니다.")
        else:
            with st.spinner("잠시만 기다려 주세요. 토마스 형제님께서 열심히 찾고 있습니다...."):
                # 출처 필터 감지
                source_filter = detect_source_filter(prompt)

                # 필터 적용 검색
                results = search_similar(db, prompt, n_results=n_results, source_filter=source_filter)

                # 필터 결과가 없으면 전체 검색으로 폴백
                if (results is None or not results.get('documents')) and source_filter is not None:
                    st.info(f"🔍 {source_filter['label']}에서 관련 내용을 찾지 못해 전체에서 검색합니다.")
                    source_filter = None
                    results = search_similar(db, prompt, n_results=n_results, source_filter=None)

                if results and results['documents']:
                    docs = results['documents']
                    metas = results['metadatas']
                    sims = results['similarities']

                    # 필터 배지 표시
                    if source_filter:
                        st.markdown(f'<span class="filter-badge">{source_filter["label"]}</span>', unsafe_allow_html=True)

                    response = generate_response(prompt, docs, metas, source_filter)
                    st.markdown(response)

                    # 사용자가 상담을 요청한 경우에만 전화 걸기 버튼 표시
                    counseling_keywords = ['상담 받고', '상담받고', '상담 신청', '상담하고 싶', '상담을 받', '상담 원', '상담소 번호', '상담소 전화', '전화번호 알려']
                    if any(kw in prompt for kw in counseling_keywords) and '02-727-2516' in response:
                        st.markdown("""
                        <a href="tel:02-727-2516" target="_blank" style="
                            display: inline-block;
                            background: linear-gradient(135deg, #C9A84C, #e0b84a);
                            color: #1B2B5E !important;
                            padding: 0.8rem 1.5rem;
                            border-radius: 12px;
                            text-decoration: none;
                            font-size: 1.1rem;
                            font-weight: 600;
                            margin: 1rem 0;
                            box-shadow: 0 2px 8px rgba(201,168,76,0.4);
                        ">📞 가톨릭영성심리상담소 바로 전화 걸기<br>
                        <span style="font-size: 0.85rem; font-weight: 400;">02-727-2516 (오전 11시~오후 4시)</span></a>
                        """, unsafe_allow_html=True)

                    seen_titles = set()
                    sources = []
                    for meta, sim in zip(metas, sims):
                        title = meta.get('title', '제목 미상')
                        if title not in seen_titles:
                            seen_titles.add(title)
                            source_type = meta.get('source_type', 'youtube')
                            source_info = {
                                'title': title,
                                'date': meta.get('upload_date', ''),
                                'url': meta.get('url', ''),
                                'relevance': f"{sim * 100:.0f}%",
                                'source_type': source_type,
                            }
                            if source_type == 'column':
                                source_info['newspaper'] = meta.get('newspaper', '신문')
                            sources.append(source_info)

                    with st.expander("📚 참고 자료", expanded=True):
                        for src in sources:
                            source_type = src.get('source_type', 'youtube')
                            if source_type == 'column':
                                newspaper = src.get('newspaper', '신문')
                                st.markdown(f"""
                                <div class="source-card-column">
                                    <div class="title">📰 {src['title']}</div>
                                    <div class="meta">📅 {src['date']} &nbsp;|&nbsp; {newspaper} &nbsp;|&nbsp; 관련도: {src['relevance']} &nbsp;|&nbsp;
                                    <a href="{src['url']}" target="_blank">🔗 칼럼 보기</a></div>
                                </div>
                                """, unsafe_allow_html=True)
                            else:
                                st.markdown(f"""
                                <div class="source-card">
                                    <div class="title">📹 {src['title']}</div>
                                    <div class="meta">📅 {src['date']} &nbsp;|&nbsp; 관련도: {src['relevance']} &nbsp;|&nbsp;
                                    <a href="{src['url']}" target="_blank">🔗 영상 보기</a></div>
                                </div>
                                """, unsafe_allow_html=True)

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response,
                        "sources": sources,
                    })
                else:
                    fallback = "죄송합니다. 관련 내용을 찾지 못했습니다. 다른 방식으로 질문해 보시겠어요?"
                    st.markdown(fallback)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": fallback,
                    })

# =====================================================================
# 푸터
# =====================================================================
st.markdown("""
<div class="footer">
    🕊️ 톡쏘는 영성심리 AI 상담 | 홍성남 신부님 유튜브 강의 및 신문 칼럼 기반<br>
    본 서비스는 AI 기반 참고 상담이며, 전문 심리상담을 대체하지 않습니다.<br>
    © 2026 JADE AI | Powered by GPT-4o-mini + numpy 벡터 검색
</div>
""", unsafe_allow_html=True)
