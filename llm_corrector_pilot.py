#!/usr/bin/env python3
"""
====================================================================
홍성남 신부님 유튜브 자막 텍스트 - LLM 문맥 교정 스크립트 (파일럿)
====================================================================

[사용법]
  1. 아래 YOUR_API_KEY_HERE 부분에 OpenAI API 키를 붙여넣기
  2. pip install openai
  3. python llm_corrector_pilot.py

[기능]
  - GPT-4o-mini가 문맥을 이해하고 음성인식 오류를 교정
  - 파일럿: 50개 파일만 먼저 처리 (비용 약 1,000~2,000원)
  - 교정 전/후 비교 샘플 자동 생성

[비용]
  - GPT-4o-mini: 입력 $0.15/1M토큰, 출력 $0.60/1M토큰
  - 50개 파일 예상 비용: 약 $0.5~1.5 (1,000~2,000원)
====================================================================
"""

import os
import time
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("OPENAI_API_KEY", "")


# 설정
BASE_DIR = Path("./output_홍성남신부_자막추출")
INPUT_DIR = BASE_DIR / "06_cleaned_text"
OUTPUT_DIR = BASE_DIR / "09_llm_corrected"
COMPARISON_DIR = BASE_DIR / "10_correction_samples"
REPORT_PATH = BASE_DIR / "11_llm_correction_report.txt"

PILOT_COUNT = 50  # 파일럿 처리 개수
MODEL = "gpt-4o-mini"

# 시스템 프롬프트
SYSTEM_PROMPT = """당신은 한국어 음성인식 텍스트 교정 전문가입니다.

아래 텍스트는 가톨릭 홍성남 신부의 '톡쏘는 영성심리' 유튜브 강의를 YouTube 자동자막으로 추출한 것입니다.
음성인식 오류가 많으므로 문맥에 맞게 교정해 주세요.

[교정 규칙]
1. 화자 정보: 홍성남 신부, 가톨릭영성심리상담소 소장
   - "홍성남 숲/줍니다/시험보입니다" → "홍성남 신부입니다"
   - "형성침/영선심/카톡이영선" 등 → "가톨릭 영성심리상담소"

2. 종교 용어 교정:
   - 고해성사, 영신수련, 미사, 강론, 성체성사, 견진성사
   - 하느님(가톨릭 표현), 예수님, 성모님, 성경
   - 사순절, 부활절, 성탄절, 대림절

3. 심리학 용어 교정:
   - 투사, 전이, 내사(introjection), 나르시시즘, 콤플렉스
   - 방어기제, 억압, 승화, 퇴행, 합리화
   - 프로이트, 융, 아들러, 에릭슨, 매슬로우, 스캇 펙

4. 교정하지 말 것:
   - 원래 내용의 의미를 바꾸지 마세요
   - 없는 내용을 추가하지 마세요
   - 문장 구조를 크게 변경하지 마세요
   - 메타데이터 헤더(# 제목, # URL 등)는 그대로 두세요

5. 교정 범위:
   - 음성인식 오류로 인한 잘못된 단어 → 올바른 단어로 교정
   - 띄어쓰기 오류 교정
   - 의미를 알 수 없는 깨진 텍스트 → [인식불가] 표시
   - 문장 부호 자연스럽게 보정

원본 텍스트의 의미와 톤을 최대한 유지하면서, 음성인식 오류만 교정해 주세요."""


def setup():
    """초기 설정"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    COMPARISON_DIR.mkdir(parents=True, exist_ok=True)

    # openai 설치 확인
    try:
        import openai
    except ImportError:
        print("❌ openai 패키지가 설치되지 않았습니다.")
        print("   아래 명령어로 설치하세요:")
        print("   pip install openai")
        return False

    if not API_KEY:
        print("❌ API 키가 설정되지 않았습니다.")
        print("   .env 파일에 OPENAI_API_KEY를 설정하세요.")
        return False

    return True


def correct_text(client, text):
    """GPT-4o-mini로 텍스트 교정"""
    # 메타데이터 헤더 분리
    lines = text.split('\n')
    header_lines = []
    content_start = 0

    for i, line in enumerate(lines):
        if '[정제 완료]' in line or line.startswith('====='):
            content_start = i + 1
            continue
        if content_start == 0:
            header_lines.append(line)

    header = '\n'.join(header_lines)
    content = '\n'.join(lines[content_start:]).strip()

    if not content or len(content) < 30:
        return text, False

    # 긴 텍스트는 청크로 분할 (GPT-4o-mini 컨텍스트 고려)
    max_chars = 12000
    chunks = []
    if len(content) > max_chars:
        # 문장 단위로 분할
        sentences = content.split('\n')
        current_chunk = ""
        for sent in sentences:
            if len(current_chunk) + len(sent) > max_chars:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sent
            else:
                current_chunk += '\n' + sent if current_chunk else sent
        if current_chunk:
            chunks.append(current_chunk)
    else:
        chunks = [content]

    # 각 청크 교정
    corrected_chunks = []
    for chunk in chunks:
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"아래 텍스트를 교정해 주세요:\n\n{chunk}"}
                ],
                temperature=0.1,  # 낮은 temperature로 일관된 교정
                max_tokens=16000,
            )
            corrected = response.choices[0].message.content.strip()
            corrected_chunks.append(corrected)
        except Exception as e:
            print(f"      ⚠️ API 오류: {e}")
            corrected_chunks.append(chunk)  # 오류 시 원본 유지

    corrected_content = '\n'.join(corrected_chunks)
    result = header + '\n============================== [LLM 교정 완료] ==============================\n\n' + corrected_content

    return result, True


def create_comparison(original, corrected, filename):
    """교정 전/후 비교 파일 생성"""
    comparison = f"{'=' * 70}\n"
    comparison += f"파일: {filename}\n"
    comparison += f"{'=' * 70}\n\n"

    # 원본에서 처음 500자
    orig_lines = original.split('\n')
    orig_content = '\n'.join([l for l in orig_lines if not l.startswith('#') and '=====' not in l]).strip()

    corr_lines = corrected.split('\n')
    corr_content = '\n'.join([l for l in corr_lines if not l.startswith('#') and '=====' not in l and 'LLM 교정' not in l and '정제 완료' not in l]).strip()

    comparison += "[ 교정 전 (처음 500자) ]\n"
    comparison += "-" * 40 + "\n"
    comparison += orig_content[:500] + "\n\n"
    comparison += "[ 교정 후 (처음 500자) ]\n"
    comparison += "-" * 40 + "\n"
    comparison += corr_content[:500] + "\n"

    return comparison


def main():
    print("\n")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  홍성남 신부님 자막 텍스트 - LLM 문맥 교정 (파일럿)     ║")
    print("║  모델: GPT-4o-mini  |  대상: 50개 파일                  ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    if not setup():
        return

    import openai
    client = openai.OpenAI(api_key=API_KEY)

    # API 키 테스트
    print("🔑 API 키 확인 중...")
    try:
        test = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "테스트"}],
            max_tokens=5,
        )
        print("   ✅ API 연결 성공!")
    except Exception as e:
        print(f"   ❌ API 연결 실패: {e}")
        print("   API 키를 확인하세요.")
        return

    # 파일 목록 (크기 순 정렬 - 작은 파일부터)
    if not INPUT_DIR.exists():
        print(f"❌ 입력 폴더를 찾을 수 없습니다: {INPUT_DIR}")
        return

    txt_files = sorted(INPUT_DIR.glob("*.txt"), key=lambda f: f.stat().st_size)

    # 파일럿: 다양한 크기의 파일 50개 선택
    # 작은 파일 20개 + 중간 파일 20개 + 큰 파일 10개
    total = len(txt_files)
    if total == 0:
        print("❌ 처리할 파일이 없습니다.")
        return

    small = txt_files[:total//3][:20]
    medium = txt_files[total//3:2*total//3][:20]
    large = txt_files[2*total//3:][:10]
    pilot_files = small + medium + large
    pilot_files = pilot_files[:PILOT_COUNT]

    print(f"\n📂 전체 파일: {total}개")
    print(f"📋 파일럿 대상: {len(pilot_files)}개")
    print(f"💰 예상 비용: $0.5~1.5 (약 1,000~2,000원)")
    print(f"\n{'─' * 50}")
    print("교정을 시작합니다...\n")

    # 처리
    stats = {
        "processed": 0,
        "corrected": 0,
        "errors": 0,
        "total_chars_before": 0,
        "total_chars_after": 0,
    }

    comparisons = []
    start_time = time.time()

    for i, filepath in enumerate(pilot_files, 1):
        filename = filepath.name
        print(f"   [{i}/{len(pilot_files)}] 교정 중: {filename[:50]}...", end="", flush=True)

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                original = f.read()
        except UnicodeDecodeError:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                original = f.read()

        stats["total_chars_before"] += len(original)

        # LLM 교정
        corrected, was_corrected = correct_text(client, original)

        stats["total_chars_after"] += len(corrected)

        if was_corrected:
            stats["corrected"] += 1

        # 저장
        out_path = OUTPUT_DIR / filename
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(corrected)

        # 비교 샘플 (처음 5개만)
        if i <= 5:
            comp = create_comparison(original, corrected, filename)
            comparisons.append(comp)

            comp_path = COMPARISON_DIR / f"비교_{i:02d}_{filename}"
            with open(comp_path, 'w', encoding='utf-8') as f:
                f.write(comp)

        stats["processed"] += 1
        print(" ✅")

        # API 속도 제한 방지
        time.sleep(0.5)

    elapsed = time.time() - start_time

    # 리포트 생성
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("  LLM 문맥 교정 리포트 (파일럿)\n")
        f.write(f"  생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"  모델: {MODEL}\n")
        f.write(f"  처리 파일: {stats['processed']}개\n")
        f.write(f"  교정 완료: {stats['corrected']}개\n")
        f.write(f"  소요 시간: {elapsed/60:.1f}분\n\n")
        f.write(f"  교정 전 총 글자수: {stats['total_chars_before']:,}자\n")
        f.write(f"  교정 후 총 글자수: {stats['total_chars_after']:,}자\n\n")
        f.write("  교정 전/후 비교 샘플:\n")
        f.write(f"  → {COMPARISON_DIR}/ 폴더에서 확인하세요\n\n")
        f.write("  다음 단계:\n")
        f.write("  1. 10_correction_samples/ 폴더의 비교 파일을 열어 품질 확인\n")
        f.write("  2. 만족스러우면 전체 파일 교정 진행\n")
        f.write("  3. 품질이 낮은 파일은 Whisper 재추출 대상으로 분류\n")

    # 최종 요약
    print(f"\n")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║                    ✅ 파일럿 교정 완료!                  ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║  📁 교정된 파일: {OUTPUT_DIR}")
    print(f"║  📋 처리: {stats['processed']}개 / 교정: {stats['corrected']}개")
    print(f"║  ⏱️  소요 시간: {elapsed/60:.1f}분")
    print(f"║  📊 비교 샘플: {COMPARISON_DIR}")
    print("╚══════════════════════════════════════════════════════════╝")
    print()
    print("💡 다음 단계: 10_correction_samples 폴더에서 교정 전/후를 비교해 보세요!")
    print()


if __name__ == "__main__":
    main()
