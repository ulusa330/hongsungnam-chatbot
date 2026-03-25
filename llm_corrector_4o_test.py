#!/usr/bin/env python3
"""
====================================================================
홍성남 신부님 자막 텍스트 - GPT-4o 교정 테스트 (10개)
====================================================================

[사용법]
  1. 아래 YOUR_API_KEY_HERE 부분에 OpenAI API 키를 붙여넣기
  2. python llm_corrector_4o_test.py

[기능]
  - GPT-4o로 10개 파일 교정 (4o-mini 대비 품질 비교용)
  - 10분 강의 등 긴 파일 위주로 선택
  - 4o-mini 결과와 나란히 비교할 수 있는 비교 파일 생성

[비용]
  - GPT-4o: 입력 $2.50/1M토큰, 출력 $10.00/1M토큰
  - 10개 파일 예상 비용: 약 $1~2 (1,500~3,000원)
====================================================================
"""

import os
import re
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("OPENAI_API_KEY", "")

# 설정
BASE_DIR = Path("./output_홍성남신부_자막추출")
INPUT_DIR = BASE_DIR / "06_cleaned_text"
OUTPUT_DIR = BASE_DIR / "12_gpt4o_corrected"
MINI_DIR = BASE_DIR / "09_llm_corrected"  # 4o-mini 결과 (비교용)
COMPARISON_DIR = BASE_DIR / "13_4o_vs_4omini_비교"
REPORT_PATH = BASE_DIR / "14_gpt4o_test_report.txt"

PILOT_COUNT = 10
MODEL = "gpt-4o"

# 시스템 프롬프트 (강화 버전)
SYSTEM_PROMPT = """당신은 한국어 음성인식 텍스트 교정 전문가입니다.

아래 텍스트는 가톨릭 홍성남 신부의 '톡쏘는 영성심리' 유튜브 강의를 YouTube 자동자막으로 추출한 것입니다.
음성인식 오류가 매우 많습니다. 문맥을 깊이 이해하고 정확하게 교정해 주세요.

[화자 정보]
- 홍성남(마태오) 신부, 가톨릭영성심리상담소 소장
- 인사말 패턴: "안녕하십니까? 가톨릭 영성심리상담소 소장 홍성남 신부입니다"
- 마무리 패턴: "전능하신 하느님, 성부와 성자와 성령께서는 우리 교우들에게 축복을 내려 주시길 바랍니다. 아멘. 홍성남 신부였습니다"
- 이 패턴이 깨져 있으면 올바른 형태로 복원하세요

[핵심 교정 대상]
1. 고유명사 복원:
   - "형성침/영선심/카톡이영선/것들이형성침" → "가톨릭 영성심리상담소"
   - "홍성남 숲/줍니다/시험보입니다/줍" → "홍성남 신부입니다"
   - "동 성남시 그렸습니다" → "홍성남 신부였습니다"

2. 영어 심리학 용어가 깨진 경우 복원:
   - "패스 로지의 크리틱" → "pathological critic(병적 비평가)"
   - "인터랙션" → "introjection(내사)"
   - "나우 앤 히어 / 마오 왼 튜더" → "now and here(지금 여기)"
   - "플라시보" → "플라시보(placebo)"
   - "노세보" → "노세보(nocebo)"

3. 종교 용어:
   - 가톨릭 용어: 고해성사, 영신수련, 미사, 강론, 성체성사, 견진성사
   - "하나님" → "하느님" (가톨릭 표현)
   - 전례: 사순절, 부활절, 성탄절, 대림절
   - "전 나시 하느님" → "전능하신 하느님"

4. 심리학 용어:
   - 방어기제: 투사, 전이, 내사, 억압, 승화, 퇴행, 합리화, 반동형성
   - 개념: 나르시시즘, 콤플렉스, 리비도, 초자아, 무의식
   - 학자: 프로이트, 칼 융, 아들러, 에릭슨, 매슬로우, 스캇 펙, 위니컷, 멜라니 클라인

5. 인명이 깨진 경우:
   - 문맥으로 추정 가능하면 교정
   - 추정 불가능하면 [인명 인식불가]로 표시

[교정 원칙]
- 원래 내용의 의미를 절대 바꾸지 마세요
- 없는 내용을 추가하지 마세요 (hallucination 금지)
- 메타데이터 헤더(# 제목, # URL 등)는 그대로 두세요
- 음성인식으로 완전히 깨져서 복원 불가능한 부분은 [인식불가]로 표시
- 문장 부호와 띄어쓰기를 자연스럽게 교정하세요"""


def setup():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    COMPARISON_DIR.mkdir(parents=True, exist_ok=True)

    try:
        import openai
    except ImportError:
        print("❌ openai 패키지가 설치되지 않았습니다.")
        print("   pip install openai")
        return False

    if not API_KEY:
        print("❌ API 키가 설정되지 않았습니다.")
        print("   .env 파일에 OPENAI_API_KEY를 설정하세요.")
        return False

    return True


def correct_text(client, text):
    """GPT-4o로 텍스트 교정"""
    lines = text.split('\n')
    header_lines = []
    content_start = 0

    for i, line in enumerate(lines):
        if '[정제 완료]' in line or (line.startswith('=====') and i > 0):
            content_start = i + 1
            continue
        if content_start == 0:
            header_lines.append(line)

    header = '\n'.join(header_lines)
    content = '\n'.join(lines[content_start:]).strip()

    if not content or len(content) < 30:
        return text, False

    # 긴 텍스트 청크 분할
    max_chars = 10000
    chunks = []
    if len(content) > max_chars:
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

    corrected_chunks = []
    for chunk in chunks:
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"아래 텍스트를 교정해 주세요:\n\n{chunk}"}
                ],
                temperature=0.1,
                max_tokens=16000,
            )
            corrected = response.choices[0].message.content.strip()
            corrected_chunks.append(corrected)
        except Exception as e:
            print(f"\n      ⚠️ API 오류: {e}")
            corrected_chunks.append(chunk)

    corrected_content = '\n'.join(corrected_chunks)
    result = header + '\n============================== [GPT-4o 교정 완료] ==============================\n\n' + corrected_content

    return result, True


def create_3way_comparison(original, mini_corrected, gpt4o_corrected, filename):
    """원본 vs 4o-mini vs 4o 3자 비교"""
    comp = f"{'=' * 70}\n"
    comp += f"파일: {filename}\n"
    comp += f"{'=' * 70}\n\n"

    def extract_content(text):
        lines = text.split('\n')
        content = '\n'.join([l for l in lines
                            if not l.startswith('#')
                            and '=====' not in l
                            and 'LLM 교정' not in l
                            and '정제 완료' not in l
                            and 'GPT-4o 교정' not in l]).strip()
        return content

    orig = extract_content(original)
    mini = extract_content(mini_corrected) if mini_corrected else "(4o-mini 교정 결과 없음)"
    gpt4o = extract_content(gpt4o_corrected)

    comp += "[ 1. 원본 (정제 후, 처음 800자) ]\n"
    comp += "─" * 40 + "\n"
    comp += orig[:800] + "\n\n"

    comp += "[ 2. GPT-4o-mini 교정 (처음 800자) ]\n"
    comp += "─" * 40 + "\n"
    comp += mini[:800] + "\n\n"

    comp += "[ 3. GPT-4o 교정 (처음 800자) ]\n"
    comp += "─" * 40 + "\n"
    comp += gpt4o[:800] + "\n"

    return comp


def main():
    print("\n")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  GPT-4o 교정 테스트 (10개 파일)                         ║")
    print("║  4o-mini 결과와 품질 비교                                ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    if not setup():
        return

    import openai
    client = openai.OpenAI(api_key=API_KEY)

    # API 테스트
    print("🔑 API 키 확인 중...")
    try:
        test = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "테스트"}],
            max_tokens=5,
        )
        print("   ✅ GPT-4o 연결 성공!")
    except Exception as e:
        print(f"   ❌ API 연결 실패: {e}")
        return

    # "10분 강의" 파일 우선 선택
    if not INPUT_DIR.exists():
        print(f"❌ 입력 폴더를 찾을 수 없습니다: {INPUT_DIR}")
        return

    all_files = list(INPUT_DIR.glob("*.txt"))

    # 10분 강의 파일 우선, 그 다음 큰 파일
    lecture_files = [f for f in all_files if "10분" in f.name or "강의" in f.name]
    other_files = sorted([f for f in all_files if f not in lecture_files],
                         key=lambda f: f.stat().st_size, reverse=True)

    # 10분 강의 7개 + 긴 강의 3개
    pilot_files = lecture_files[:7] + other_files[:3]
    pilot_files = pilot_files[:PILOT_COUNT]

    print(f"\n📂 전체 파일: {len(all_files)}개")
    print(f"📋 테스트 대상: {len(pilot_files)}개 (10분 강의 위주)")
    print(f"💰 예상 비용: $1~2 (1,500~3,000원)")
    print(f"🤖 모델: {MODEL}")
    print(f"\n{'─' * 50}")
    print("교정을 시작합니다...\n")

    stats = {"processed": 0, "corrected": 0}
    start_time = time.time()

    for i, filepath in enumerate(pilot_files, 1):
        filename = filepath.name
        print(f"   [{i}/{len(pilot_files)}] 교정 중: {filename[:55]}...", end="", flush=True)

        # 원본 읽기
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                original = f.read()
        except UnicodeDecodeError:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                original = f.read()

        # GPT-4o 교정
        corrected, was_corrected = correct_text(client, original)

        # 저장
        out_path = OUTPUT_DIR / filename
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(corrected)

        # 4o-mini 결과 읽기 (있으면)
        mini_path = MINI_DIR / filename
        mini_text = None
        if mini_path.exists():
            try:
                with open(mini_path, 'r', encoding='utf-8') as f:
                    mini_text = f.read()
            except:
                pass

        # 3자 비교 생성
        comp = create_3way_comparison(original, mini_text, corrected, filename)
        comp_path = COMPARISON_DIR / f"비교_{i:02d}_{filename}"
        with open(comp_path, 'w', encoding='utf-8') as f:
            f.write(comp)

        stats["processed"] += 1
        if was_corrected:
            stats["corrected"] += 1
        print(" ✅")

        time.sleep(1)  # API 속도 제한 방지

    elapsed = time.time() - start_time

    # 리포트
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("  GPT-4o 교정 테스트 리포트\n")
        f.write(f"  생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"  모델: {MODEL}\n")
        f.write(f"  처리 파일: {stats['processed']}개\n")
        f.write(f"  소요 시간: {elapsed/60:.1f}분\n\n")
        f.write("  비교 결과:\n")
        f.write(f"  → {COMPARISON_DIR}/ 폴더에서 원본 vs 4o-mini vs 4o 비교 확인\n\n")
        f.write("  다음 단계:\n")
        f.write("  1. 13_4o_vs_4omini_비교/ 폴더에서 품질 차이 확인\n")
        f.write("  2. 4o가 확실히 낫다면 → 전체 파일 4o로 교정 ($50~70)\n")
        f.write("  3. 차이가 크지 않다면 → 4o-mini로 전체 진행 ($3~5)\n")

    print(f"\n")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║                ✅ GPT-4o 테스트 완료!                    ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║  📁 교정 결과: {OUTPUT_DIR}")
    print(f"║  📊 3자 비교: {COMPARISON_DIR}")
    print(f"║  📋 처리: {stats['processed']}개 | ⏱️ {elapsed/60:.1f}분")
    print("╚══════════════════════════════════════════════════════════╝")
    print()
    print("💡 13_4o_vs_4omini_비교 폴더에서 원본/4o-mini/4o 결과를 비교해 보세요!")
    print()


if __name__ == "__main__":
    main()
