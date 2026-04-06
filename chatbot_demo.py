#!/usr/bin/env python3
"""
====================================================================
홍성남 신부님 톡쏘는 영성심리 - AI 상담 챗봇 데모 (v6)
====================================================================
[변경사항 v6]
  - Whisper STT: 마이크 음성 입력 지원
  - ElevenLabs TTS: 신부님 목소리로 음성 답변
  - 음성/텍스트 모드 전환 버튼 추가
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
    from datetime import date as dt_date
    today = dt_date.today()
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
        h_end_12 = h_end - 12 if h_end > 12 else h_end
        time_str = f"{period_start} {h_start_12}시~{h_end_12}시"
        location = lecture.get("location", "")
        fee = lecture.get("fee", "")
        contact = lecture.get("contact", "")
        title = lecture.get("title", "영성심리특강")
        try:
            lecture_date = dt_date(int(year), int(month), int(day))
        except Exception:
            lecture_date = None
        if lecture_date and today > lecture_date:
            return (f"[강의 일정 규칙] 아쉽게도 {month}월 {title}은 이미 종료되었습니다. 다음 달 강의 일정은 아직 등록되지 않았습니다. 문의: {contact}. 중요: 과거 영상이나 자막에 언급된 날짜의 강의 일정은 절대 안내하지 말 것.")
        else:
            return (f"[강의 일정 규칙] 다음 {title}: {year}년 {month}월 {day}일({dow}) {time_str}, {location}. 회비 {fee}. 문의 {contact}. 중요: 과거 영상이나 자막에 언급된 다른 날짜의 강의 일정은 절대 안내하지 말 것.")
    else:
        pattern = regular.get("pattern", "매월 셋째 주 토요일")
        time = regular.get("time", "오후 3시")
        location = regular.get("location", "가톨릭회관")
        contact = regular.get("contact", "776-8405")
        return (f"[강의 일정 규칙] 현재 확정된 강의 일정이 없습니다. 정기적으로 {pattern} {time}, {location}에서 진행되나 다음 일정은 아직 나오지 않았습니다. 문의: {contact}. 중요: 과거 영상이나 자막에 언급된 날짜의 강의 일정은 절대 안내하지 말 것.")


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
    .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
    .main-header { background: linear-gradient(135deg, #1B2B5E 0%, #2d4a8c 100%); color: white; padding: 2rem 2.5rem; border-radius: 16px; margin-bottom: 1.5rem; box-shadow: 0 4px 20px rgba(27, 43, 94, 0.3); }
    .main-header h1 { color: white !important; font-size: 2rem !important; margin-bottom: 0.3rem !important; }
    .main-header p { color: #c9d4e8 !important; font-size: 1rem; margin: 0; }
    .stChatMessage { border-radius: 12px !important; margin-bottom: 0.8rem !important; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #1B2B5E 0%, #162248 100%); }
    [data-testid="stSidebar"] * { color: white !important; }
    .source-card { background: white; border-left: 4px solid #C9A84C; padding: 1rem 1.2rem; margin: 0.5rem 0; border-radius: 0 8px 8px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
    .source-card .title { font-weight: 600; color: #1B2B5E; font-size: 0.95rem; margin-bottom: 0.3rem; }
    .source-card .meta { color: #666; font-size: 0.8rem; }
    .source-card a { color: #C9A84C; text-decoration: none; font-weight: 500; }
    .source-card-column { background: white; border-left: 4px solid #0D9488; padding: 1rem 1.2rem; margin: 0.5rem 0; border-radius: 0 8px 8px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
    .source-card-column .title { font-weight: 600; color: #1B2B5E; font-size: 0.95rem; margin-bottom: 0.3rem; }
    .source-card-column .meta { color: #666; font-size: 0.8rem; }
    .source-card-column a { color: #0D9488; text-decoration: none; font-weight: 500; }
    .filter-badge { display: inline-block; background: #1B2B5E; color: white !important; padding: 0.3rem 0.8rem; border-radius: 20px; font-size: 0.8rem; margin-bottom: 0.5rem; }
    .stat-card { background: rgba(255,255,255,0.1); border-radius: 10px; padding: 1rem; text-align: center; margin: 0.5rem 0; }
    .stat-card .number { font-size: 1.8rem; font-weight: 700; color: #C9A84C; }
    .stat-card .label { font-size: 0.8rem; color: #a0b0d0; }
    .voice-btn { background: linear-gradient(135deg, #C9A84C, #e0b84a); color: #1B2B5E !important; border: none; border-radius: 50px; padding: 0.8rem 2rem; font-size: 1.1rem; font-weight: 700; cursor: pointer; }
    .stTextInput input, .stChatInput textarea { background-color: #FFFFFF !important; color: #1B2B5E !important; }
    footer {visibility: hidden !important;} #MainMenu {visibility: hidden !important;} header {visibility: hidden !important;}
    .stDeployButton {display: none !important;} [data-testid="stToolbar"] {display: none !important;}
    [data-testid="stDecoration"] {display: none !important;} [data-testid="stStatusWidget"] {display: none !important;}
    [data-testid="stAudioInput"] {
          background-color: #ffffff !important;
          border-radius: 12px !important;
          padding: 0.5rem !important;
    }
    [data-testid="stAudioInput"] button {
        color: #1B2B5E !important;
    }
 
    @media (max-width: 768px) {
        [data-testid="stSidebar"] { display: none !important; }
        .main .block-container { padding: 0.5rem 1rem !important; max-width: 100% !important; }
        .main-header { padding: 1.2rem 1rem !important; border-radius: 10px !important; margin-bottom: 0.5rem !important; }
        .main-header h1 { font-size: 1.4rem !important; }
        .stChatMessage, .stChatMessage p { font-size: 1.15rem !important; line-height: 1.8 !important; }
        .stButton > button { font-size: 1.1rem !important; padding: 1rem 1.2rem !important; min-height: 60px !important; border-radius: 12px !important; white-space: normal !important; background-color: #1B2B5E !important; color: white !important; border: none !important; }
        .stChatInput textarea { font-size: 1.15rem !important; min-height: 50px !important; }
    }
</style>
""", unsafe_allow_html=True)

# =====================================================================
# 출처 필터링 시스템
# =====================================================================
NEWSPAPER_FILTERS = {
    '중앙일보': ['중앙일보', '중앙'],
    '가톨릭신문': ['가톨릭신문', '가톨릭 신문'],
    '경향신문': ['경향신문', '경향 신문', '경향'],
}
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
MONTHLY_LECTURE_PATTERN = re.compile(r'\[?\d{6}\]?')
SOURCE_TYPE_FILTERS = {
    'column': ['칼럼', '신문', '기고', '신문 칼럼', '신문칼럼'],
    'youtube': ['유튜브', '영상', '동영상', '강의 영상'],
}
SCHEDULE_KEYWORDS = ['강의 일정', '특강 일정', '언제', '다음 강의', '강의 날짜', '다음 특강', '몇월', '몇 월', '4월 특강', '5월 특강', '6월 특강', '특강', '일정']

def detect_source_filter(query):
    query_lower = query.lower().strip()
    if any(kw in query for kw in SCHEDULE_KEYWORDS):
        return None
    for newspaper, keywords in NEWSPAPER_FILTERS.items():
        for kw in keywords:
            if kw in query_lower:
                return {'type': 'newspaper', 'value': newspaper, 'label': f"📰 {newspaper} 칼럼에서 검색"}
    if '월특강' in query_lower or '월 특강' in query_lower:
        return {'type': 'monthly_lecture', 'value': 'monthly', 'label': "📹 월특강에서 검색"}
    for series, keywords in YOUTUBE_SERIES_FILTERS.items():
        for kw in keywords:
            if kw in query_lower:
                return {'type': 'youtube_series', 'value': series, 'label': f"📹 [{series}] 시리즈에서 검색"}
    for source_type, keywords in SOURCE_TYPE_FILTERS.items():
        for kw in keywords:
            if kw in query_lower:
                if source_type == 'column':
                    return {'type': 'source_type', 'value': 'column', 'label': "📰 신문 칼럼에서 검색"}
                else:
                    return {'type': 'source_type', 'value': 'youtube', 'label': "📹 유튜브 영상에서 검색"}
    return None

def apply_filter(db, source_filter):
    if source_filter is None:
        return None
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
# 벡터DB 및 OpenAI 초기화
# =====================================================================
VECTORDB_DIR = Path("./vectordb_홍성남신부")
EMBEDDINGS_FILE = VECTORDB_DIR / "embeddings.npz"
METADATA_FILE = VECTORDB_DIR / "metadata.json"

@st.cache_resource
def init_vectordb():
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
    import openai
    api_key = st.secrets.get("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
    if not api_key:
        return None
    return openai.OpenAI(api_key=api_key)

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def search_similar(db, query, n_results=5, source_filter=None):
    openai_client = init_openai()
    if not openai_client or db is None:
        return None
    response = openai_client.embeddings.create(model="text-embedding-3-small", input=query)
    query_embedding = np.array(response.data[0].embedding)
    filter_indices = apply_filter(db, source_filter)
    if filter_indices is not None and len(filter_indices) == 0:
        return None
    embeddings = db['embeddings']
    if filter_indices is not None:
        filter_indices = np.array(filter_indices)
        filtered_embeddings = embeddings[filter_indices]
        similarities = np.array([cosine_similarity(query_embedding, emb) for emb in filtered_embeddings])
        top_local = np.argsort(similarities)[::-1][:n_results]
        top_indices = filter_indices[top_local]
        top_sims = similarities[top_local]
    else:
        similarities = np.array([cosine_similarity(query_embedding, emb) for emb in embeddings])
        top_indices = np.argsort(similarities)[::-1][:n_results]
        top_sims = similarities[top_indices]
    return {
        'documents': [db['documents'][i] for i in top_indices],
        'metadatas': [db['metadata'][i] for i in top_indices],
        'similarities': [float(s) for s in top_sims],
    }

# =====================================================================
# 음성 관련 함수 (Whisper STT + ElevenLabs TTS)
# =====================================================================
def transcribe_audio(audio_bytes):
    """Whisper로 음성 → 텍스트 변환"""
    openai_client = init_openai()
    if not openai_client:
        return None
    try:
        import io
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.wav"
        transcript = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="ko"
        )
        return transcript.text
    except Exception as e:
        st.error(f"음성 인식 오류: {e}")
        return None

def text_to_speech(text):
    """ElevenLabs로 텍스트 → 신부님 목소리 변환"""
    api_key = st.secrets.get("ELEVENLABS_API_KEY", os.environ.get("ELEVENLABS_API_KEY", ""))
    voice_id = st.secrets.get("ELEVENLABS_VOICE_ID", os.environ.get("ELEVENLABS_VOICE_ID", ""))
    if not api_key or not voice_id:
        return None
    try:
        import requests
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "text": text[:2500],  # ElevenLabs Starter 제한
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            return response.content  # MP3 bytes
        else:
            st.error(f"TTS 오류: {response.status_code} - {response.text[:100]}")
            return None
    except Exception as e:
        st.error(f"TTS 오류: {e}")
        return None

# =====================================================================
# RAG 응답 생성
# =====================================================================
def generate_response(query, context_docs, context_metas, source_filter=None):
    openai_client = init_openai()
    if not openai_client:
        return "OpenAI API 키가 설정되지 않았습니다."

    is_schedule_query = any(kw in query for kw in SCHEDULE_KEYWORDS)
    if is_schedule_query:
        schedule_text = get_schedule_prompt_text()
        schedule_response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"당신은 홍성남 마태오 신부입니다. 따뜻하고 친근한 신부님 말투로 답변하세요. 출처나 참고자료는 절대 표시하지 마세요.\n\n{schedule_text}"},
                {"role": "user", "content": query}
            ],
            temperature=0.5,
            max_tokens=500,
        )
        return schedule_response.choices[0].message.content

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
        filter_instruction = f"\n\n[현재 검색 필터]\n사용자가 특정 출처를 지정하여 질문했습니다: {filter_label}"

    system_prompt = f"""당신은 홍성남 마태오 신부의 말투와 관점으로 직접 상담해 주는 AI입니다.

[나는 누구인가 — 홍성남 마태오 신부 프로필]
- 이름: 홍성남 마태오
- 소속: 천주교 서울대교구, 특수사목
- 현 소임: 서울대교구 가톨릭영성심리상담소 소장
- 사제 서품: 1987년 2월 6일
- 방송: cpbc TV, 유튜브 '톡쏘는 영성심리' 채널
- 스타일: 심리 상담과 영성지도를 결합, 직설적이고 현실적인 언어 사용

[맹모닝 상담소 파트너 — 맹경순 베로니카]
- 이름: 맹경순 (세례명 베로니카)
- cpbc 아나운서, 현재 유튜브 '톡쏘는 영성심리' 채널에서 함께 진행

[나의 저서]
최근·대표작: 「끝까지 나를 사랑하는 마음」「나는 생각보다 괜찮은 사람」「거꾸로 보는 종교」「혼자서 마음을 치유하는 법」「내 마음이 어때서」「나로 사는 걸 깜빡했어요」「챙기고 사세요」
이전 저서: 「화나면 화내고 힘들 땐 쉬어」「아! 어쩘나」 시리즈「풀어야 산다」「행복을 위한 탈출」「새장 밖으로」

[말투 규칙]
- "홍성남 신부님은 ~라고 말씀하셨습니다" 절대 금지 — 1인칭으로만 말하세요
- 따뜻하면서도 직설적이고 톡 쏘는 어조
- "늘 강조하는 건데요", "강의에서도 말씀드렸지만" 같은 표현 자연스럽게 사용

[상담 안내 규칙]
- 상담 요청 시: 먼저 고민 파악 → "저는 현재 성직자 상담만 하고 있어서 일반 신자분들과 개인 상담은 어렵습니다." 반드시 포함
- 전문 상담: 가톨릭영성심리상담소(02-727-2516, 오전 11시~오후 4시) 안내

[규칙]
1. 제공된 컨텍스트를 기반으로 답변하세요.
2. 의학적 진단이나 처방은 절대 하지 마세요.
3. 한국어로 답변하세요.
4. 강의 일정·상담소 연락처 안내 시 출처를 표시하지 마세요.{filter_instruction}"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"질문: {query}\n\n참고할 내용:\n{context}\n\n위 내용을 바탕으로 답변해 주세요."},
    ]
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
        st.markdown(f'<div class="stat-card"><div class="number">{db["count"]:,}</div><div class="label">학습된 텍스트 조각</div></div>', unsafe_allow_html=True)
        youtube_count = db.get('youtube_count', 1037)
        column_count = db.get('column_count', 0)
        st.markdown(f'<div class="stat-card"><div class="number">{youtube_count:,}</div><div class="label">📹 분석된 강의 영상</div></div>', unsafe_allow_html=True)
        if column_count > 0:
            st.markdown(f'<div class="stat-card"><div class="number">{column_count:,}</div><div class="label">📰 수집된 신문 칼럼</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    # 🎙️ 음성 모드 토글
    voice_api_key = st.secrets.get("ELEVENLABS_API_KEY", os.environ.get("ELEVENLABS_API_KEY", ""))
    if voice_api_key:
        st.markdown("**🎙️ 음성 응답 설정**")
        voice_mode = st.toggle("신부님 목소리로 답변 듣기", value=False, key="voice_mode")
        if voice_mode:
            st.success("🔊 음성 답변 ON")
        else:
            st.info("💬 텍스트 답변 모드")
        st.markdown("---")

    n_results = st.slider("참고 문서 수", 3, 10, 5)
    st.markdown("---")
    st.markdown("**시스템 상태**")
    if db:
        st.success("벡터DB 연결됨")
    else:
        st.error("벡터DB 없음")
    if openai_client:
        st.success("OpenAI API 연결됨")
    else:
        st.error("API 키 미설정")
    if voice_api_key:
        st.success("ElevenLabs 연결됨")
    else:
        st.warning("ElevenLabs 미설정")

    st.markdown("---")
    st.markdown("""
    <div style="font-size: 0.75rem; color: #8899bb;">
        <b>개발: 이재욱 토마스</b><br>
        talktoclinic@gmail.com<br>
        유튜브: youtube.com/@fr.hongsungnam<br><br>
        <b>Powered by</b><br>
        OpenAI GPT-4o-mini + Whisper<br>
        ElevenLabs TTS<br>
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
if "voice_mode" not in st.session_state:
    st.session_state.voice_mode = False

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

# 🎙️ 음성 입력 섹션
st.markdown("#### 🎙️ 음성으로 질문하기")
audio_input = st.audio_input("마이크 버튼을 눌러 질문하세요", key="audio_input")
if audio_input:
    with st.spinner("🎙️ 음성을 텍스트로 변환 중..."):
        audio_bytes = audio_input.read()
        transcribed = transcribe_audio(audio_bytes)
        if transcribed:
            st.info(f"🗣️ 인식된 질문: **{transcribed}**")
            st.session_state.pending_question = transcribed
            st.rerun()

st.markdown("---")

# 기존 메시지 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"], avatar="🙋" if message["role"] == "user" else "🕊️"):
        st.markdown(message["content"])
        # 음성 답변 재생 (저장된 경우)
        if message["role"] == "assistant" and "audio" in message:
            st.audio(message["audio"], format="audio/mp3")
        if message["role"] == "assistant" and "sources" in message:
            if not message.get("is_schedule", False):
                with st.expander("📚 참고 자료", expanded=False):
                    for src in message["sources"]:
                        source_type = src.get('source_type', 'youtube')
                        if source_type == 'column':
                            newspaper = src.get('newspaper', '신문')
                            st.markdown(f'<div class="source-card-column"><div class="title">📰 {src["title"]}</div><div class="meta">📅 {src.get("date","")} | {newspaper} | <a href="{src.get("url","#")}" target="_blank">🔗 칼럼 보기</a></div></div>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<div class="source-card"><div class="title">📹 {src["title"]}</div><div class="meta">📅 {src.get("date","")} | <a href="{src.get("url","#")}" target="_blank">🔗 영상 보기</a></div></div>', unsafe_allow_html=True)

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
            st.error("벡터DB가 초기화되지 않았습니다.")
        elif not openai_client:
            st.error("OpenAI API 키가 설정되지 않았습니다.")
        else:
            with st.spinner("잠시만 기다려 주세요..."):
                is_schedule_query = any(kw in prompt for kw in SCHEDULE_KEYWORDS)
                source_filter = detect_source_filter(prompt)
                results = search_similar(db, prompt, n_results=n_results, source_filter=source_filter)

                if (results is None or not results.get('documents')) and source_filter is not None:
                    st.info(f"🔍 {source_filter['label']}에서 관련 내용을 찾지 못해 전체에서 검색합니다.")
                    source_filter = None
                    results = search_similar(db, prompt, n_results=n_results, source_filter=None)

                if results and results['documents']:
                    docs = results['documents']
                    metas = results['metadatas']
                    sims = results['similarities']

                    if source_filter:
                        st.markdown(f'<span class="filter-badge">{source_filter["label"]}</span>', unsafe_allow_html=True)

                    response = generate_response(prompt, docs, metas, source_filter)
                    st.markdown(response)

                    # 🔊 ElevenLabs TTS 음성 생성
                    audio_data = None
                    if st.session_state.get("voice_mode", False):
                        with st.spinner("🔊 신부님 목소리로 변환 중..."):
                            audio_data = text_to_speech(response)
                            if audio_data:
                                st.audio(audio_data, format="audio/mp3")

                    # 전화 버튼
                    counseling_keywords = ['상담 받고', '상담받고', '상담 신청', '상담하고 싶', '상담을 받', '상담 원', '상담소 번호', '상담소 전화', '전화번호 알려']
                    if any(kw in prompt for kw in counseling_keywords) and '02-727-2516' in response:
                        st.markdown("""
                        <a href="tel:02-727-2516" target="_blank" style="display:inline-block;background:linear-gradient(135deg,#C9A84C,#e0b84a);color:#1B2B5E !important;padding:0.8rem 1.5rem;border-radius:12px;text-decoration:none;font-size:1.1rem;font-weight:600;margin:1rem 0;box-shadow:0 2px 8px rgba(201,168,76,0.4);">
                        📞 가톨릭영성심리상담소 바로 전화 걸기<br>
                        <span style="font-size:0.85rem;font-weight:400;">02-727-2516 (오전 11시~오후 4시)</span></a>
                        """, unsafe_allow_html=True)

                    seen_titles = set()
                    sources = []
                    for meta, sim in zip(metas, sims):
                        title = meta.get('title', '제목 미상')
                        if title not in seen_titles:
                            seen_titles.add(title)
                            source_type = meta.get('source_type', 'youtube')
                            source_info = {'title': title, 'date': meta.get('upload_date', ''), 'url': meta.get('url', ''), 'relevance': f"{sim * 100:.0f}%", 'source_type': source_type}
                            if source_type == 'column':
                                source_info['newspaper'] = meta.get('newspaper', '신문')
                            sources.append(source_info)

                    if not is_schedule_query:
                        with st.expander("📚 참고 자료", expanded=True):
                            for src in sources:
                                source_type = src.get('source_type', 'youtube')
                                if source_type == 'column':
                                    newspaper = src.get('newspaper', '신문')
                                    st.markdown(f'<div class="source-card-column"><div class="title">📰 {src["title"]}</div><div class="meta">📅 {src["date"]} | {newspaper} | 관련도: {src["relevance"]} | <a href="{src["url"]}" target="_blank">🔗 칼럼 보기</a></div></div>', unsafe_allow_html=True)
                                else:
                                    st.markdown(f'<div class="source-card"><div class="title">📹 {src["title"]}</div><div class="meta">📅 {src["date"]} | 관련도: {src["relevance"]} | <a href="{src["url"]}" target="_blank">🔗 영상 보기</a></div></div>', unsafe_allow_html=True)

                    msg = {"role": "assistant", "content": response, "sources": sources, "is_schedule": is_schedule_query}
                    if audio_data:
                        msg["audio"] = audio_data
                    st.session_state.messages.append(msg)
                else:
                    fallback = "죄송합니다. 관련 내용을 찾지 못했습니다. 다른 방식으로 질문해 보시겠어요?"
                    st.markdown(fallback)
                    st.session_state.messages.append({"role": "assistant", "content": fallback})

# =====================================================================
# 푸터
# =====================================================================
st.markdown("""
<div style="width:100%;text-align:center;color:#888888;font-size:0.8rem;line-height:1.6;padding:20px 0;border-top:1px solid #eeeeee;margin-top:50px;">
    🕊️ 톡쏘는 영성심리 AI 상담 | 홍성남 신부님 유튜브 강의 및 신문 칼럼 기반<br>
    본 서비스는 AI 기반 참고 상담이며, 전문 심리상담을 대체하지 않습니다.<br>
    © 2026 JADE AI | Powered by GPT-4o-mini + Whisper + ElevenLabs
</div>
""", unsafe_allow_html=True)
