#!/usr/bin/env python3
"""
====================================================================
홍성남 신부님 자막 텍스트 - GPT-4o-mini 전체 교정 스크립트
====================================================================

[사용법]
  1. 아래 YOUR_API_KEY_HERE 부분에 OpenAI API 키를 붙여넣기
  2. python llm_corrector_full.py

[기능]
  - GPT-4o-mini로 전체 파일 교정
  - 이미 교정된 파일은 자동 건너뛰기 (중단 후 재시작 가능)
  - 교정 품질 점수 자동 평가 (이후 4o 재교정 대상 선별용)
  - hallucination 방지 프롬프트 강화

[비용]
  - 예상: $3~5 (약 4,000~7,000원)
====================================================================
"""

import os
import re
import time
import csv
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("OPENAI_API_KEY", "")

# 설정
BASE_DIR = Path("./output_홍성남신부_자막추출")
INPUT_DIR = BASE_DIR / "06_cleaned_text"
OUTPUT_DIR = BASE_DIR / "15_전체교정_4omini"
QUALITY_CSV = BASE_DIR / "16_품질점수.csv"
REPORT_PATH = BASE_DIR / "17_전체교정_리포트.txt"

MODEL = "gpt-4o-mini"

# 시스템 프롬프트 (hallucination 방지 강화)
SYSTEM_PROMPT = """당신은 한국어 음성인식 텍스트 교정 전문가입니다.

아래 텍스트는 가톨릭 홍성남 신부의 '톡쏘는 영성심리' 유튜브 강의를 YouTube 자동자막으로 추출한 것입니다.
음성인식 오류가 많으므로 문맥에 맞게 교정해 주세요.

[화자 정보]
- 홍성남(마태오) 신부, 가톨릭영성심리상담소 소장
- 인사말: "안녕하십니까? 가톨릭 영성심리상담소 소장 홍성남 신부입니다"
- 마무리: "전능하신 하느님, 성부와 성자와 성령께서는 우리 교우들에게 축복을 내려 주시길 바랍니다. 아멘. 홍성남 신부였습니다"

[교정 규칙]
1. 고유명사 복원:
   - "형성침/영선심/카톡이영선/가두리성심" 등 → "가톨릭 영성심리상담소"
   - "홍성남 숲/줍니다/시험보입니다/식품입니다" 등 → "홍성남 신부입니다"
   - "동 성남시 그렸습니다" → "홍성남 신부였습니다"
   - "전 나시 하느님" → "전능하신 하느님"

2. 종교 용어: 고해성사, 영신수련, 미사, 강론, 하느님(가톨릭), 예수님, 성모님

3. 심리학 용어: 투사, 전이, 내사, 나르시시즘, 콤플렉스, 방어기제, 신경증
   - 프로이트, 칼 융, 아들러, 에릭슨, 매슬로우, 스캇 펙

4. ⚠️ 절대 금지 사항:
   - 원본에 없는 내용을 절대 추가하지 마세요
   - 문맥을 추측해서 새로운 문장을 만들지 마세요
   - 원본의 문장 순서를 바꾸지 마세요
   - 복원이 불가능한 부분은 그대로 두거나 [인식불가]로 표시하세요
   - 원본보다 길어지면 안 됩니다

5. 교정 범위:
   - 음성인식 오류 단어 → 올바른 단어
   - 띄어쓰기, 문장부호 교정
   - 의미 파악 불가 → 그대로 두거나 [인식불가]

원본 텍스트의 의미와 분량을 최대한 유지하세요."""


def setup():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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
    """GPT-4o-mini로 텍스트 교정"""
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
        return text, False, 0

    original_length = len(content)

    # 긴 텍스트 청크 분할
    max_chars = 12000
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
                    {"role": "user", "content": f"아래 텍스트를 교정해 주세요. 원본에 없는 내용을 추가하지 마세요:\n\n{chunk}"}
                ],
                temperature=0.1,
                max_tokens=16000,
            )
            corrected = response.choices[0].message.content.strip()
            corrected_chunks.append(corrected)
        except Exception as e:
            print(f"\n      ⚠️ API 오류: {e}")
            corrected_chunks.append(chunk)
            time.sleep(5)  # 오류 시 대기

    corrected_content = '\n'.join(corrected_chunks)
    corrected_length = len(corrected_content)

    # 품질 점수 계산 (0~100)
    quality_score = calculate_quality(content, corrected_content)

    result = header + '\n============================== [4o-mini 전체교정] ==============================\n\n' + corrected_content

    return result, True, quality_score


def calculate_quality(original, corrected):
    """교정 품질 점수 계산 (0~100)"""
    score = 50  # 기본 점수

    # 1. 인사말 교정 확인 (+20)
    if "홍성남 신부" in corrected:
        score += 10
    if "영성심리상담소" in corrected:
        score += 10

    # 2. 마무리 교정 확인 (+10)
    if "전능하신 하느님" in corrected or "홍성남 신부였습니다" in corrected:
        score += 10

    # 3. 길이 비율 체크 (원본 대비 ±30% 이내면 OK)
    len_ratio = len(corrected) / max(len(original), 1)
    if 0.7 <= len_ratio <= 1.3:
        score += 10
    elif len_ratio > 1.5 or len_ratio < 0.5:
        score -= 20  # hallucination 또는 과도한 삭제 의심

    # 4. 깨진 텍스트 잔여량 체크
    broken_patterns = len(re.findall(r'[가-힣]\s[가-힣]\s[가-힣]', corrected))
    if broken_patterns < 5:
        score += 10
    elif broken_patterns > 20:
        score -= 10

    # 5. 문장부호 개선 확인
    if corrected.count('.') > original.count('.'):
        score += 5
    if corrected.count(',') > original.count(','):
        score += 5

    return max(0, min(100, score))


def main():
    print("\n")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  홍성남 신부님 자막 텍스트 - GPT-4o-mini 전체 교정      ║")
    print("║  중단 후 재시작 가능 (이미 교정된 파일은 건너뜀)         ║")
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
        print("   ✅ API 연결 성공!\n")
    except Exception as e:
        print(f"   ❌ API 연결 실패: {e}")
        return

    # 파일 목록
    if not INPUT_DIR.exists():
        print(f"❌ 입력 폴더를 찾을 수 없습니다: {INPUT_DIR}")
        return

    all_files = sorted(INPUT_DIR.glob("*.txt"))
    total = len(all_files)

    # 이미 교정된 파일 확인 (재시작 지원)
    already_done = set()
    if OUTPUT_DIR.exists():
        already_done = {f.name for f in OUTPUT_DIR.glob("*.txt")}

    remaining = [f for f in all_files if f.name not in already_done]

    print(f"📂 전체 파일: {total}개")
    print(f"✅ 이미 교정됨: {len(already_done)}개")
    print(f"📋 남은 파일: {len(remaining)}개")
    print(f"💰 예상 비용: ${len(remaining) * 0.004:.1f}~${len(remaining) * 0.006:.1f}")
    print(f"\n{'─' * 50}")

    if not remaining:
        print("\n✅ 모든 파일이 이미 교정되었습니다!")
        return

    print(f"교정을 시작합니다... (예상 소요시간: {len(remaining) * 0.7 / 60:.0f}~{len(remaining) * 1.2 / 60:.0f}분)\n")

    # 품질 점수 CSV 준비
    quality_scores = []
    if QUALITY_CSV.exists():
        with open(QUALITY_CSV, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            quality_scores = list(reader)

    stats = {"processed": 0, "corrected": 0, "errors": 0, "skipped": 0}
    start_time = time.time()

    for i, filepath in enumerate(remaining, 1):
        filename = filepath.name
        progress = f"[{len(already_done) + i}/{total}]"
        print(f"   {progress} 교정 중: {filename[:50]}...", end="", flush=True)

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                original = f.read()
        except UnicodeDecodeError:
            try:
                with open(filepath, 'r', encoding='utf-8-sig') as f:
                    original = f.read()
            except:
                print(" ⚠️ 읽기 실패")
                stats["errors"] += 1
                continue

        # 너무 짧은 파일 건너뛰기
        content_only = '\n'.join([l for l in original.split('\n')
                                  if not l.startswith('#') and '=====' not in l]).strip()
        if len(content_only) < 30:
            # 그대로 복사
            out_path = OUTPUT_DIR / filename
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(original)
            print(" ⏭️ (너무 짧음)")
            stats["skipped"] += 1
            continue

        # LLM 교정
        corrected, was_corrected, quality = correct_text(client, original)

        # 저장
        out_path = OUTPUT_DIR / filename
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(corrected)

        # 품질 점수 기록
        quality_scores.append({
            "filename": filename,
            "quality_score": quality,
            "original_chars": len(content_only),
            "corrected_chars": len(corrected),
        })

        stats["processed"] += 1
        if was_corrected:
            stats["corrected"] += 1

        print(f" ✅ (품질: {quality}점)")

        # API 속도 제한 방지
        time.sleep(0.3)

        # 100개마다 중간 저장
        if i % 100 == 0:
            save_quality_csv(quality_scores)
            elapsed = time.time() - start_time
            print(f"\n   💾 중간 저장 완료 ({stats['processed']}개 처리, {elapsed/60:.1f}분 경과)\n")

    # 최종 품질 CSV 저장
    save_quality_csv(quality_scores)

    elapsed = time.time() - start_time

    # 품질 분석
    scores = [int(q["quality_score"]) for q in quality_scores]
    low_quality = [q for q in quality_scores if int(q["quality_score"]) < 60]
    avg_score = sum(scores) / len(scores) if scores else 0

    # 리포트 생성
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("  GPT-4o-mini 전체 교정 리포트\n")
        f.write(f"  생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"  모델: {MODEL}\n")
        f.write(f"  처리 파일: {stats['processed']}개\n")
        f.write(f"  건너뜀: {stats['skipped']}개\n")
        f.write(f"  오류: {stats['errors']}개\n")
        f.write(f"  소요 시간: {elapsed/60:.1f}분\n\n")
        f.write(f"  평균 품질 점수: {avg_score:.1f}/100\n")
        f.write(f"  품질 낮은 파일 (60점 미만): {len(low_quality)}개\n\n")
        f.write("  품질 낮은 파일 목록 (GPT-4o 재교정 대상):\n")
        for q in sorted(low_quality, key=lambda x: int(x["quality_score"])):
            f.write(f"    - [{q['quality_score']}점] {q['filename']}\n")
        f.write(f"\n  다음 단계:\n")
        f.write(f"  1. 15_전체교정_4omini/ 폴더에서 결과 확인\n")
        f.write(f"  2. 16_품질점수.csv에서 점수 낮은 파일 확인\n")
        f.write(f"  3. 60점 미만 파일 → GPT-4o로 재교정\n")

    # 최종 요약
    print(f"\n")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║              ✅ 전체 교정 완료!                          ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║  📁 교정 결과: {OUTPUT_DIR}")
    print(f"║  📋 처리: {stats['processed']}개 | 건너뜀: {stats['skipped']}개")
    print(f"║  ⏱️  소요 시간: {elapsed/60:.1f}분")
    print(f"║  📊 평균 품질: {avg_score:.1f}점")
    print(f"║  ⚠️  재교정 필요 (60점 미만): {len(low_quality)}개")
    print("╚══════════════════════════════════════════════════════════╝")
    print()
    if low_quality:
        print(f"💡 다음 단계: {len(low_quality)}개 파일을 GPT-4o로 재교정하면 품질이 올라갑니다!")
    print()


def save_quality_csv(quality_scores):
    """품질 점수 CSV 저장"""
    with open(QUALITY_CSV, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=["filename", "quality_score", "original_chars", "corrected_chars"])
        writer.writeheader()
        writer.writerows(quality_scores)


if __name__ == "__main__":
    main()
