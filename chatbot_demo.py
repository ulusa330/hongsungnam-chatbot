#!/usr/bin/env python3
"""
====================================================================
홍성남 신부님 톡쏘는 영성심리 - AI 상담 챗봇 데모 (v4)
====================================================================
[변경사항 v4]
  - 출처별 필터링 기능 추가
    * 신문사 필터: 중앙일보, 가톨릭신문, 경향신문
    * 유튜브 시리즈 필터: 맹모닝 상담소, 마태오묵상집, 요한묵상집, 10분 강의 등
  - 질문에서 출처 키워드 자동 감지
  - 필터 적용 시 해당 출처 내에서만 검색
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

    # 2. 월특강 필터 감지 (날짜 패턴 + "월특강" 키워드)
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
            # 특정 신문사 칼럼만
            if meta.get('source_type') == 'column':
                newspaper = meta.get('newspaper', '')
                if filter_value in newspaper:
                    valid_indices.append(i)

        elif filter_type == 'youtube_series':
            # 특정 유튜브 시리즈만 (제목에 시리즈명 포함)
            if meta.get('source_type', 'youtube') == 'youtube':
                title = meta.get('title', '')
                # 시리즈 키워드 목록에서 하나라도 제목에 포함되면 매칭
                series_keywords = YOUTUBE_SERIES_FILTERS.get(filter_value, [filter_value])
                if any(kw in title for kw in series_keywords) or filter_value in title:
                    valid_indices.append(i)

        elif filter_type == 'monthly_lecture':
            # 월특강: 제목에 날짜 패턴(6자리 숫자)이 있는 영상
            if meta.get('source_type', 'youtube') == 'youtube':
                title = meta.get('title', '')
                if MONTHLY_LECTURE_PATTERN.search(title):
                    valid_indices.append(i)

        elif filter_type == 'source_type':
            # 유튜브 또는 칼럼 전체
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
        # 통계 계산 (유튜브/칼럼 구분)
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
    # 쿼리 임베딩
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=query,
    )
    query_embedding = np.array(response.data[0].embedding)

    # 필터 적용
    filter_indices = apply_filter(db, source_filter)

    if filter_indices is not None and len(filter_indices) == 0:
        # 필터에 해당하는 데이터가 없음
        return None

    # 코사인 유사도 계산
    embeddings = db['embeddings']

    if filter_indices is not None:
        # 필터된 인덱스만 검색
        filter_indices = np.array(filter_indices)
        filtered_embeddings = embeddings[filter_indices]
        similarities = np.array([
            cosine_similarity(query_embedding, emb)
            for emb in filtered_embeddings
        ])
        # 상위 N개 (필터된 인덱스 내에서)
        top_local = np.argsort(similarities)[::-1][:n_results]
        top_indices = filter_indices[top_local]
        top_sims = similarities[top_local]
    else:
        # 전체 검색
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

    # 필터 정보를 시스템 프롬프트에 반영
    filter_instruction = ""
    if source_filter:
        filter_label = source_filter.get('label', '')
        filter_instruction = f"\n\n[현재 검색 필터]\n사용자가 특정 출처를 지정하여 질문했습니다: {filter_label}\n제공된 컨텍스트는 해당 출처에서만 검색된 결과입니다. 답변 시 이 출처에서 찾은 내용임을 명시해 주세요."

    system_prompt = f"""당신은 홍성남 신부님의 말투와 관점으로 직접 상담해 주는 AI입니다. 홍성남 신부님의 유튜브 강의, 맹모닝 상담소, 신문 칼럼의 내용을 바탕으로, 마치 신부님이 직접 대화하듯이 답변하세요.

[말투 규칙 — 매우 중요]
- "홍성남 신부님은 ~라고 말씀하셨습니다" (X) → 제3자 시점 절대 금지
- "~가 중요합니다", "~해 보세요", "~하는 거예요" (O) → 신부님이 직접 말하는 것처럼
- 따뜻하면서도 때로는 직설적이고 톡 쏘는 어조를 섞어 주세요
- 상대방의 아픔에 공감하면서도 현실적인 조언을 해 주세요
- "제가 늘 강조하는 건데요", "제 강의에서도 말씀드렸지만" 같은 표현을 자연스럽게 사용하세요
- 절대 "신부님께서는", "홍성남 신부님은" 같은 3인칭 표현을 쓰지 마세요

[상담 안내 필수 규칙]
사용자가 직접 상담을 받고 싶다고 하거나, 상담 신청 방법을 물어보면 반드시 아래 안내를 포함하세요:
1. 저는 성직자 상담만 하고 있습니다.
2. talktoclinic@gmail.com로 사연을 보내주시면, 저와 맹경순 선생님이 의견을 모아 방송을 통한 상담을 해 드릴 수 있습니다.
3. 가톨릭영성심리상담소(02-727-2516, 오전 11시~오후 4시)로 연락 주시면, 전문 상담가 선생님들의 상담을 받으실 수 있습니다.

[규칙]
1. 제공된 강의 및 칼럼 내용(컨텍스트)을 기반으로만 답변하세요.
2. 컨텍스트에 없는 내용은 "이 부분은 제가 강의나 칼럼에서 직접 다루지는 않았지만..."이라고 전제하세요.
3. 의학적 진단이나 처방은 절대 하지 마세요.
4. 심각한 심리적 위기 상황이면 전문 상담 기관을 안내하세요.
5. 답변 마지막에 참고한 출처 정보를 안내하세요.
6. 한국어로 답변하세요.
7. 출처가 신문 칼럼인 경우 "제가 ○○신문에 쓴 칼럼"이라고 표현하세요.
8. 출처가 유튜브 시리즈인 경우 "제 [맹모닝 상담소] 영상", "제 [10분 강의]" 같은 식으로 표현하세요.{filter_instruction}"""

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
        max_tokens=2000,
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
            with st.expander("📚 관련 자료", expanded=False):
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
            with st.spinner("잠시만 기다려 주세요. 토마스 형제가 열심히 찾고 있습니다...."):
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
