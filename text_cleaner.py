#!/usr/bin/env python3
"""
====================================================================
홍성남 신부님 유튜브 자막 텍스트 일괄 정제 스크립트
====================================================================

[사용법]
  python text_cleaner.py

[기능]
  1. 추임새/간투사 제거 (음.., 어.., 그.., 에.., 쩝 등)
  2. 종교 용어 자동 교정 (고해성사, 영신수련, 미사, 강론 등)
  3. 심리학 용어 자동 교정 (투사, 전이, 나르시시즘, 내사 등)
  4. [음악] 태그 및 의미없는 영문/숫자 잡음 제거
  5. 반복 단어/문장 제거
  6. 문장 부호 정리 및 가독성 향상
  7. 정제 전/후 비교 리포트 생성

[입력]  output_홍성남신부_자막추출/02_subtitles_text/
[출력]  output_홍성남신부_자막추출/06_cleaned_text/
====================================================================
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime


# =====================================================================
# 설정
# =====================================================================
BASE_DIR = Path("./output_홍성남신부_자막추출")
INPUT_DIR = BASE_DIR / "02_subtitles_text"
OUTPUT_DIR = BASE_DIR / "06_cleaned_text"
COMBINED_OUTPUT = BASE_DIR / "07_combined_cleaned_text.txt"
REPORT_PATH = BASE_DIR / "08_cleaning_report.txt"


# =====================================================================
# 1. 추임새/간투사 패턴
# =====================================================================
# 단독으로 나오거나 반복되는 추임새
FILLER_PATTERNS = [
    # 단독 추임새 (단어 경계로 매칭)
    r'\b으+\b',
    r'\b음+\b',
    r'\b어+\b',
    r'\b에+\b',
    r'\b아+\b',
    r'\b그+\b',
    r'\b네+\b',
    r'\b예+\b',
    r'\b뭐+\b',
    r'\b쩝+\b',
    r'\b흠+\b',
    r'\b헐+\b',
    r'\b하+\b',
    r'\b마+\b',
    r'\b뭔+\b',
    r'\b뭘+\b',
    # "으 으 으 으" 같은 반복 패턴
    r'(?:으\s*){2,}',
    r'(?:음\s*){2,}',
    r'(?:어\s*){2,}',
    r'(?:에\s*){2,}',
    r'(?:아\s*){2,}',
    r'(?:예\s*){2,}',
]

# 문장 시작부의 추임새 (뒤에 내용이 이어지는 경우)
SENTENCE_START_FILLERS = [
    r'^으+\s+',
    r'^음+\s+',
    r'^어+\s+',
    r'^에+\s+',
    r'^아+\s+',
    r'^그+\s+',
    r'^예+\s+',
    r'^하+\s+',
    r'^자+\s+',
]


# =====================================================================
# 2. 잡음 패턴
# =====================================================================
NOISE_PATTERNS = [
    r'\[음악\]',
    r'\[박수\]',
    r'\[웃음\]',
    r'\[박수소리\]',
    r'\[음악소리\]',
    # 의미없는 짧은 영문 (자막 오인식)
    r'\b[a-zA-Z]{1,3}\b',
    # 의미없는 단독 숫자 (문맥 없는)
    r'(?<!\d)\b\d{1}\b(?!\d|부|회|장|절|편|강|차|조|항|월|일|년|시|분|초|명|개|번)',
    # 연속 공백
    r'\s{2,}',
]


# =====================================================================
# 3. 종교 용어 교정 사전
# =====================================================================
RELIGIOUS_CORRECTIONS = {
    # 성사/전례
    "고해 성사": "고해성사",
    "고헤 성사": "고해성사",
    "고해 선사": "고해성사",
    "견진 성사": "견진성사",
    "세례 성사": "세례성사",
    "성체 성사": "성체성사",
    "혼인 성사": "혼인성사",
    "병자 성사": "병자성사",
    "성사 생활": "성사생활",
    
    # 영성/수련
    "영신 수련": "영신수련",
    "영성 수련": "영신수련",
    "영 성 심리": "영성심리",
    "영성 심리": "영성심리",
    "영성 생활": "영성생활",
    "영성 지도": "영성지도",
    "영성 상담": "영성상담",
    "영적 체험": "영적체험",
    "영적 척": "영적체험",
    "영적 책": "영적체험",
    "영적 참여": "영적체험",
    "영적 층": "영적체험",
    "영적 처음": "영적체험",
    "역적 체험": "영적체험",
    
    # 기도/전례
    "묵상 기도": "묵상기도",
    "관상 기도": "관상기도",
    "성체 조배": "성체조배",
    "화해 의 성사": "화해의 성사",
    "십자가 의 길": "십자가의 길",
    "성모 송": "성모송",
    "주님 의 기도": "주님의 기도",
    "사도 신경": "사도신경",
    
    # 성경/교회
    "구약 성경": "구약성경",
    "신약 성경": "신약성경",
    "복음 서": "복음서",
    "복음 화": "복음화",
    "새 천년 복음화": "새천년복음화",
    "강 론": "강론",
    "미 사": "미사",
    
    # 인물/직책
    "교 황": "교황",
    "추 기경": "추기경",
    "주 교": "주교",
    "본당 신부": "본당신부",
    "보좌 신부": "보좌신부",
    "신학교": "신학교",
    "수도 회": "수도회",
    "수녀 원": "수녀원",
    
    # 교리
    "원 죄": "원죄",
    "삼위 일체": "삼위일체",
    "부활 절": "부활절",
    "성탄 절": "성탄절",
    "사순 절": "사순절",
    "대림 절": "대림절",
    "연 옥": "연옥",
    "천 국": "천국",
    "구원 사": "구원사",
    
    # 자주 오인식되는 표현
    "하느님": "하느님",
    "하나님": "하느님",
    "예수 님": "예수님",
    "성모 님": "성모님",
    "성모 마리아": "성모 마리아",
    "신앙 생활": "신앙생활",
    "신앙 살": "신앙생활",
    "신앙가": "신앙과",
    "신 암살": "신앙생활",
    "신앙 생을": "신앙생활을",
    "성당 대해서": "성당 안에서",
}


# =====================================================================
# 4. 심리학 용어 교정 사전
# =====================================================================
PSYCHOLOGY_CORRECTIONS = {
    # 방어기제
    "투 사": "투사",
    "전 이": "전이",
    "내 사": "내사",
    "인터랙션": "인트로젝션",
    "내사 하는": "내사라는",
    "억 압": "억압",
    "합리 화": "합리화",
    "승 화": "승화",
    "퇴 행": "퇴행",
    "부 정": "부정",
    "반동 형성": "반동형성",
    "동일 시": "동일시",
    "해리 현상": "해리현상",
    
    # 심리학 개념
    "나르시시 즘": "나르시시즘",
    "나르시시즘": "나르시시즘",
    "나 르시 즘": "나르시시즘",
    "컴플렉스": "콤플렉스",
    "콤 플렉스": "콤플렉스",
    "오이디 푸스": "오이디푸스",
    "엘렉 트라": "엘렉트라",
    "리비 도": "리비도",
    "자아 이상": "자아이상",
    "초 자아": "초자아",
    "무 의식": "무의식",
    "잠재 의식": "잠재의식",
    "의식 화": "의식화",
    
    # 상담/치료
    "상담 심리": "상담심리",
    "영성 상담심리": "영성상담심리",
    "상담 사": "상담사",
    "심리 상담": "심리상담",
    "심리 치료": "심리치료",
    "심리 분석": "심리분석",
    "심리 학": "심리학",
    "정신 분석": "정신분석",
    "인지 행동": "인지행동",
    "신경 증": "신경증",
    "신경증적": "신경증적",
    "신경 전쟁": "신경증적",
    "정신 병리": "정신병리",
    "종교 정신 병리 약": "종교정신병리학",
    "종교 정신 병리": "종교정신병리",
    "병리 약": "병리학",
    
    # 감정/상태
    "열등 감": "열등감",
    "우울 증": "우울증",
    "불안 층": "불안증",
    "불안 증": "불안증",
    "강박 증": "강박증",
    "공황 장애": "공황장애",
    "자존 감": "자존감",
    "자기 애": "자기애",
    "분리 불안": "분리불안",
    "애착 장애": "애착장애",
    
    # 학자
    "프로이트": "프로이트",
    "프로 이드": "프로이트",
    "프로이드": "프로이트",
    "융": "융",
    "칼 융": "칼 융",
    "아들러": "아들러",
    "아 들러": "아들러",
    "에릭슨": "에릭슨",
    "에릭 슨": "에릭슨",
    "매슬로": "매슬로우",
    "매슬 로우": "매슬로우",
    "스캇 펙": "스캇 펙",
}


# =====================================================================
# 5. 일반 오인식 교정
# =====================================================================
GENERAL_CORRECTIONS = {
    "홍성남 숲": "홍성남 신부",
    "홍 성남": "홍성남",
    "9화": "구화",
    "7화": "치유",
    "500": "함정에",
    "제 강의": "제 강의",
    "그렇죠": "그렇죠",
}


# =====================================================================
# 정제 함수들
# =====================================================================

def remove_fillers(text):
    """추임새/간투사 제거"""
    # 먼저 반복 패턴 제거
    for pattern in FILLER_PATTERNS:
        text = re.sub(pattern, ' ', text)
    return text


def remove_noise(text):
    """잡음 제거 ([음악], 무의미한 영문 등)"""
    for pattern in NOISE_PATTERNS:
        text = re.sub(pattern, ' ', text)
    return text


def apply_corrections(text, corrections_dict):
    """용어 교정 사전 적용 (긴 키워드부터 매칭)"""
    # 긴 문자열부터 매칭하여 부분 매칭 오류 방지
    sorted_keys = sorted(corrections_dict.keys(), key=len, reverse=True)
    for wrong, correct in [(k, corrections_dict[k]) for k in sorted_keys]:
        text = text.replace(wrong, correct)
    return text


def clean_punctuation(text):
    """문장부호 및 공백 정리"""
    # 연속 공백 → 단일 공백
    text = re.sub(r'\s+', ' ', text)
    # 문장 끝 정리
    text = re.sub(r'\s+([.!?])', r'\1', text)
    # 쉼표 앞 공백 제거
    text = re.sub(r'\s+,', ',', text)
    # 연속 마침표 정리
    text = re.sub(r'\.{2,}', '.', text)
    return text.strip()


def remove_duplicate_phrases(text):
    """연속 중복 구절 제거 (자막 겹침 때문에 발생)"""
    words = text.split()
    if len(words) < 6:
        return text
    
    result = []
    i = 0
    while i < len(words):
        # 3~10 단어 길이의 반복 패턴 검사
        found_dup = False
        for length in range(10, 2, -1):
            if i + 2 * length <= len(words):
                chunk1 = ' '.join(words[i:i+length])
                chunk2 = ' '.join(words[i+length:i+2*length])
                if chunk1 == chunk2:
                    result.extend(words[i:i+length])
                    i += 2 * length
                    found_dup = True
                    break
        if not found_dup:
            result.append(words[i])
            i += 1
    
    return ' '.join(result)


def add_sentence_breaks(text):
    """자연스러운 문장 구분 추가"""
    # 주요 문장 종결 패턴 뒤에 줄바꿈 추가
    endings = [
        r'(합니다)\s',
        r'(습니다)\s',
        r'(됩니다)\s',
        r'(있습니다)\s',
        r'(없습니다)\s',
        r'(봅니다)\s',
        r'(겠습니다)\s',
        r'(하십시오)\s',
        r'(바랍니다)\s',
        r'(드립니다)\s',
        r'(입니다)\s',
        r'(거든요)\s',
        r'(잖아요)\s',
        r'(거예요)\s',
        r'(되겠죠)\s',
        r'(그렇죠)\s',
    ]
    for pattern in endings:
        text = re.sub(pattern, r'\1\n', text)
    return text


def clean_text(text):
    """전체 정제 파이프라인"""
    # 메타데이터 헤더 분리
    lines = text.split('\n')
    header_lines = []
    content_start = 0
    
    for i, line in enumerate(lines):
        if line.startswith('====='):
            content_start = i + 1
            break
        header_lines.append(line)
    
    header = '\n'.join(header_lines)
    content = '\n'.join(lines[content_start:]).strip()
    
    if not content:
        return text
    
    # 정제 파이프라인 실행
    content = remove_noise(content)
    content = remove_fillers(content)
    content = apply_corrections(content, RELIGIOUS_CORRECTIONS)
    content = apply_corrections(content, PSYCHOLOGY_CORRECTIONS)
    content = apply_corrections(content, GENERAL_CORRECTIONS)
    content = remove_duplicate_phrases(content)
    content = clean_punctuation(content)
    content = add_sentence_breaks(content)
    
    # 빈 줄 정리
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    return header + '\n============================== [정제 완료] ==============================\n\n' + content


# =====================================================================
# 메인 실행
# =====================================================================
def main():
    print("\n")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  홍성남 신부님 유튜브 자막 텍스트 - 일괄 정제 스크립트  ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    # 폴더 확인
    if not INPUT_DIR.exists():
        print(f"❌ 입력 폴더를 찾을 수 없습니다: {INPUT_DIR}")
        print("   먼저 youtube_subtitle_extractor_v2.py를 실행하세요.")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 파일 목록
    txt_files = sorted(INPUT_DIR.glob("*.txt"))
    total = len(txt_files)
    print(f"📂 정제할 파일: {total}개")
    print(f"📂 출력 폴더: {OUTPUT_DIR}")
    print()

    # 통계
    stats = {
        "total_files": total,
        "processed": 0,
        "total_chars_before": 0,
        "total_chars_after": 0,
        "corrections_applied": 0,
    }

    all_cleaned = []

    for i, filepath in enumerate(txt_files, 1):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                original = f.read()
        except UnicodeDecodeError:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                original = f.read()

        before_len = len(original)
        cleaned = clean_text(original)
        after_len = len(cleaned)

        # 저장
        out_path = OUTPUT_DIR / filepath.name
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(cleaned)

        stats["processed"] += 1
        stats["total_chars_before"] += before_len
        stats["total_chars_after"] += after_len

        # 진행 표시
        if i % 50 == 0 or i == total:
            pct = (i / total) * 100
            print(f"   [{i}/{total}] ({pct:.0f}%) 정제 중...")

        # 통합 텍스트에 추가
        all_cleaned.append(cleaned)

    # 통합 파일 생성
    print(f"\n📝 통합 정제 텍스트 생성 중...")
    with open(COMBINED_OUTPUT, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("홍성남 신부님 - 톡쏘는 영성심리 정제 완료 텍스트\n")
        f.write(f"정제일: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"총 파일: {stats['processed']}개\n")
        f.write("=" * 60 + "\n\n")
        for text in all_cleaned:
            f.write(text)
            f.write("\n\n" + "─" * 60 + "\n\n")

    # 리포트 생성
    reduction = stats["total_chars_before"] - stats["total_chars_after"]
    reduction_pct = (reduction / stats["total_chars_before"] * 100) if stats["total_chars_before"] > 0 else 0

    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("  텍스트 정제 리포트\n")
        f.write(f"  생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"  처리 파일 수: {stats['processed']}개\n")
        f.write(f"  정제 전 총 글자수: {stats['total_chars_before']:,}자\n")
        f.write(f"  정제 후 총 글자수: {stats['total_chars_after']:,}자\n")
        f.write(f"  제거된 분량: {reduction:,}자 ({reduction_pct:.1f}%)\n\n")
        f.write("  적용된 교정 사전:\n")
        f.write(f"    - 종교 용어: {len(RELIGIOUS_CORRECTIONS)}개 패턴\n")
        f.write(f"    - 심리학 용어: {len(PSYCHOLOGY_CORRECTIONS)}개 패턴\n")
        f.write(f"    - 일반 교정: {len(GENERAL_CORRECTIONS)}개 패턴\n")
        f.write(f"    - 추임새 패턴: {len(FILLER_PATTERNS)}개\n")
        f.write(f"    - 잡음 패턴: {len(NOISE_PATTERNS)}개\n\n")
        f.write("  출력 폴더:\n")
        f.write(f"    - 개별 파일: {OUTPUT_DIR}/\n")
        f.write(f"    - 통합 파일: {COMBINED_OUTPUT}\n\n")
        f.write("  다음 단계:\n")
        f.write("    1. 06_cleaned_text 폴더에서 샘플 파일을 열어 품질 확인\n")
        f.write("    2. 추가 교정이 필요한 용어를 발견하면 스크립트의 사전에 추가\n")
        f.write("    3. 품질 확인 후 주제별 분류 작업 진행\n")
        f.write("    4. 분류 완료 후 벡터DB 임베딩 → RAG 구축\n")

    # 최종 요약
    print("\n")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║                    ✅ 정제 완료!                        ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║  📁 정제된 파일: {OUTPUT_DIR}")
    print(f"║  📋 처리 파일: {stats['processed']}개")
    print(f"║  📝 정제 전: {stats['total_chars_before']:,}자")
    print(f"║  📝 정제 후: {stats['total_chars_after']:,}자")
    print(f"║  🗑️  제거 분량: {reduction:,}자 ({reduction_pct:.1f}%)")
    print("╚══════════════════════════════════════════════════════════╝")
    print()
    print("💡 다음 명령어: 06_cleaned_text 폴더에서 파일을 열어 품질을 확인하세요!")
    print()


if __name__ == "__main__":
    main()
