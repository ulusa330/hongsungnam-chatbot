#!/usr/bin/env python3
"""
====================================================================
홍성남 신부님 자막 텍스트 - GPT-4o 재교정 v2
====================================================================
[변경사항 v2]
  - 원본 cleaned 텍스트(06_cleaned_text)에서 직접 GPT-4o로 교정
    (기존: 이미 망가진 4o-mini 출력을 입력으로 사용 → 품질 저하)
  - 성모신심미사 등 원본 자막 자체가 깨진 파일은 자동 제외
  - 할루시네이션 방지 프롬프트 대폭 강화
  - 청크 사이즈 축소 (8000자) → 더 정밀한 교정

[사용법]
  python llm_recorrector_v2.py

[비용]
  - 5개 파일 × GPT-4o: 약 $0.5~1 (약 700~1,500원)
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
RAW_DIR = BASE_DIR / "06_cleaned_text"           # 원본 cleaned 텍스트 (입력)
CORRECTED_DIR = BASE_DIR / "15_전체교정_4omini"   # 교정 결과 덮어쓰기 대상
OUTPUT_DIR = BASE_DIR / "22_재교정v2_4o"          # 재교정 v2 결과 백업
QUALITY_CSV = BASE_DIR / "16_품질점수.csv"
REPORT_PATH = BASE_DIR / "23_재교정v2_비교리포트.txt"

MODEL = "gpt-4o"

# 재교정 대상 파일 (60점 미만, 성모신심미사 제외)
TARGET_FILES = [
    "00000000_28장 16~20절 제자들에게 사명을 부여하시는 그리스도.txt",
    "00000000_[220423]제2부_돈에 대해서.txt",
    "00000000_[260221] 자아의 성장과정.txt",
    "00000000_[미얀마 특집]미얀마 청년들과의 대화 1편.txt",
    "00000000_[Catholic Book]홍성남신부님이 직접 겪은 마음의 병.txt",
]

# 제외 파일 (원본 자막 자체가 완전히 깨진 파일)
EXCLUDED_FILES = [
    "00000000_181201 홍성남 신부님(성모신심미사).txt",
]

# 시스템 프롬프트 (원본 raw 텍스트용 - 할루시네이션 방지 대폭 강화)
SYSTEM_PROMPT = """당신은 한국어 음성인식 텍스트 교정 전문가입니다.

아래 텍스트는 가톨릭 홍성남 신부의 '톡쏘는 영성심리' 유튜브 강의를 YouTube 자동자막으로 추출한 원본입니다.
음성인식 오류가 매우 많으므로 문맥에 맞게 교정해 주세요.

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
   - "하나님" → "하느님" (가톨릭 용어)

3. 심리학 용어: 투사, 전이, 내사, 나르시시즘, 콤플렉스, 방어기제, 신경증
   - 프로이트, 칼 융, 아들러, 에릭슨, 매슬로우, 스캇 펙

4. 문장 품질:
   - 띄어쓰기 정확하게 교정
   - 문장부호(마침표, 쉼표, 물음표) 적절히 보완
   - 반복되는 단어나 불필요한 추임새 정리
   - 구어체는 유지하되 가독성 향상

5. ⚠️ [최우선] 절대 금지 사항 ⚠️:
   - 원본에 없는 내용을 절대 추가하지 마세요
   - 문맥을 추측해서 새로운 문장을 만들지 마세요
   - 같은 문장이나 비슷한 문장을 반복하지 마세요
   - 원본의 문장 순서를 바꾸지 마세요
   - 복원이 불가능한 부분은 그대로 두거나 [인식불가]로 표시하세요
   - 교정 결과의 글자수가 원본의 70~110% 범위를 벗어나면 안 됩니다
   - 절대 요약하거나 축약하지 마세요. 모든 문장을 빠짐없이 교정하세요

원본 텍스트의 의미, 분량, 순서를 최대한 유지하면서 음성인식 오류만 교정하세요."""


def setup():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        import openai
    except ImportError:
        print("openai 패키지가 설치되지 않았습니다. pip install openai")
        return False
    if not API_KEY:
        print("API 키가 설정되지 않았습니다. .env 파일에 OPENAI_API_KEY를 설정하세요.")
        return False
    return True


def correct_text(client, text):
    """GPT-4o로 텍스트 교정 (원본 raw 텍스트 입력)"""
    lines = text.split('\n')
    header_lines = []
    content_start = 0

    for i, line in enumerate(lines):
        if '[정제 완료]' in line or '[4o-mini 전체교정]' in line or (line.startswith('=====') and i > 0):
            content_start = i + 1
            continue
        if content_start == 0:
            header_lines.append(line)

    header = '\n'.join(header_lines)
    content = '\n'.join(lines[content_start:]).strip()

    if not content or len(content) < 30:
        return text, False, 0

    original_len = len(content)

    # 청크 분할 (8000자 단위 - 더 정밀한 교정)
    max_chars = 8000
    chunks = []
    if len(content) > max_chars:
        paragraphs = content.split('\n')
        current_chunk = ""
        for para in paragraphs:
            if len(current_chunk) + len(para) > max_chars:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = para
            else:
                current_chunk += '\n' + para if current_chunk else para
        if current_chunk:
            chunks.append(current_chunk)
    else:
        chunks = [content]

    corrected_chunks = []
    for ci, chunk in enumerate(chunks):
        chunk_len = len(chunk)
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": (
                        f"아래 텍스트를 교정해 주세요.\n"
                        f"원본 글자수: {chunk_len}자\n"
                        f"교정 결과도 반드시 {int(chunk_len*0.7)}~{int(chunk_len*1.1)}자 범위를 유지하세요.\n"
                        f"모든 문장을 빠짐없이 하나씩 교정하세요. 절대 요약/축약/반복하지 마세요.\n\n"
                        f"{chunk}"
                    )}
                ],
                temperature=0.1,
                max_tokens=16000,
            )
            corrected = response.choices[0].message.content.strip()

            # 할루시네이션 체크: 결과가 원본의 50% 미만이거나 150% 초과면 원본 유지
            ratio = len(corrected) / max(chunk_len, 1)
            if ratio < 0.5 or ratio > 1.5:
                print(f"\n      [청크 {ci+1}] 길이 비율 {ratio:.1%} - 원본 유지", end="")
                corrected_chunks.append(chunk)
            else:
                corrected_chunks.append(corrected)

        except Exception as e:
            print(f"\n      API 오류: {e}", end="")
            corrected_chunks.append(chunk)
            time.sleep(10)

    corrected_content = '\n'.join(corrected_chunks)

    # 품질 점수 계산
    quality_score = calculate_quality(content, corrected_content)

    result = header + '\n============================== [GPT-4o 재교정v2] ==============================\n\n' + corrected_content
    return result, True, quality_score


def calculate_quality(original, corrected):
    """교정 품질 점수 계산 (0~100)"""
    score = 50

    if "홍성남 신부" in corrected:
        score += 10
    if "영성심리상담소" in corrected:
        score += 10
    if "전능하신 하느님" in corrected or "홍성남 신부였습니다" in corrected:
        score += 10

    len_ratio = len(corrected) / max(len(original), 1)
    if 0.7 <= len_ratio <= 1.3:
        score += 10
    elif len_ratio > 1.5 or len_ratio < 0.5:
        score -= 20

    broken_patterns = len(re.findall(r'[가-힣]\s[가-힣]\s[가-힣]', corrected))
    if broken_patterns < 5:
        score += 10
    elif broken_patterns > 20:
        score -= 10

    if corrected.count('.') > original.count('.'):
        score += 5
    if corrected.count(',') > original.count(','):
        score += 5

    return max(0, min(100, score))


def update_quality_csv(updated_scores):
    """기존 품질 CSV에서 재교정된 파일의 점수를 업데이트"""
    if not QUALITY_CSV.exists():
        return

    existing = []
    with open(QUALITY_CSV, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        existing = list(reader)

    update_map = {s['filename']: s for s in updated_scores}

    for row in existing:
        if row['filename'] in update_map:
            row['quality_score'] = update_map[row['filename']]['new_score']
            row['corrected_chars'] = update_map[row['filename']]['corrected_chars']

    with open(QUALITY_CSV, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=["filename", "quality_score", "original_chars", "corrected_chars"])
        writer.writeheader()
        writer.writerows(existing)


def main():
    print("\n")
    print("=" * 60)
    print("  홍성남 신부님 자막 텍스트 - GPT-4o 재교정 v2")
    print("  원본(06_cleaned_text)에서 직접 교정")
    print("=" * 60)
    print()

    if not setup():
        return

    import openai
    client = openai.OpenAI(api_key=API_KEY)

    # API 테스트
    print("[1/4] API 키 확인 중...")
    try:
        test = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "테스트"}],
            max_tokens=5,
        )
        print("   API 연결 성공!\n")
    except Exception as e:
        print(f"   API 연결 실패: {e}")
        return

    # 제외 파일 안내
    if EXCLUDED_FILES:
        print(f"[2/4] 제외 파일 ({len(EXCLUDED_FILES)}개):")
        for f in EXCLUDED_FILES:
            print(f"   - {f} (원본 자막 깨짐, 복원 불가)")
        print()

    # 재교정 대상 확인
    targets = []
    for filename in TARGET_FILES:
        raw_path = RAW_DIR / filename
        if raw_path.exists():
            targets.append(filename)
        else:
            print(f"   파일 없음: {filename}")

    total = len(targets)
    print(f"[3/4] 재교정 대상: {total}개 파일")
    print(f"   입력: 06_cleaned_text (원본)")
    print(f"   모델: GPT-4o")
    print(f"   예상 비용: $0.5~1.0")
    print(f"\n{'─' * 50}\n")

    stats = {"processed": 0, "improved": 0, "errors": 0}
    comparison = []
    updated_scores = []
    start_time = time.time()

    # 기존 품질 점수 로드
    old_scores = {}
    if QUALITY_CSV.exists():
        with open(QUALITY_CSV, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                old_scores[row['filename']] = int(row.get('quality_score', 0))

    for i, filename in enumerate(targets, 1):
        raw_path = RAW_DIR / filename
        old_score = old_scores.get(filename, 0)

        print(f"   [{i}/{total}] 재교정 중: {filename[:50]}...", end="", flush=True)

        try:
            with open(raw_path, 'r', encoding='utf-8') as f:
                raw_text = f.read()
        except:
            try:
                with open(raw_path, 'r', encoding='utf-8-sig') as f:
                    raw_text = f.read()
            except:
                print(" 읽기 실패")
                stats["errors"] += 1
                continue

        # GPT-4o 교정 (원본에서 직접)
        corrected, was_corrected, new_score = correct_text(client, raw_text)

        # 백업 저장 (22_재교정v2_4o)
        out_path = OUTPUT_DIR / filename
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(corrected)

        # 15_전체교정_4omini에 덮어쓰기 (항상 - 원본 raw보다는 낫다)
        corrected_path = CORRECTED_DIR / filename
        with open(corrected_path, 'w', encoding='utf-8') as f:
            f.write(corrected)

        if new_score > old_score:
            stats["improved"] += 1

        comparison.append({
            'filename': filename,
            'old_score': old_score,
            'new_score': new_score,
            'improved': new_score > old_score,
        })

        updated_scores.append({
            'filename': filename,
            'new_score': new_score,
            'corrected_chars': len(corrected),
        })

        stats["processed"] += 1
        change = f"+{new_score - old_score}" if new_score > old_score else str(new_score - old_score)
        print(f" {old_score}점 -> {new_score}점 ({change})")

        time.sleep(1)

    elapsed = time.time() - start_time

    # 품질 CSV 업데이트
    if updated_scores:
        update_quality_csv(updated_scores)

    # 비교 리포트 생성
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("  GPT-4o 재교정 v2 비교 리포트\n")
        f.write(f"  생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"  핵심 변경: 원본(06_cleaned_text) -> GPT-4o 직접 교정\n")
        f.write("=" * 60 + "\n\n")

        f.write(f"  재교정 대상: {total}개\n")
        f.write(f"  제외 파일: {len(EXCLUDED_FILES)}개 (원본 자막 깨짐)\n")
        f.write(f"  처리 완료: {stats['processed']}개\n")
        f.write(f"  품질 향상: {stats['improved']}개\n")
        f.write(f"  오류: {stats['errors']}개\n")
        f.write(f"  소요 시간: {elapsed/60:.1f}분\n\n")

        if comparison:
            old_avg = sum(c['old_score'] for c in comparison) / len(comparison)
            new_avg = sum(c['new_score'] for c in comparison) / len(comparison)
            f.write(f"  평균 점수 변화: {old_avg:.1f} -> {new_avg:.1f} ({new_avg - old_avg:+.1f})\n\n")

            f.write("  [ 파일별 비교 ]\n")
            for c in sorted(comparison, key=lambda x: x['new_score'] - x['old_score'], reverse=True):
                change = c['new_score'] - c['old_score']
                marker = "UP" if change > 0 else ("==" if change == 0 else "DN")
                f.write(f"  {marker} {c['old_score']:>2} -> {c['new_score']:>2} ({change:+d}) | {c['filename']}\n")

        f.write(f"\n  [ 제외된 파일 ]\n")
        for ef in EXCLUDED_FILES:
            f.write(f"  - {ef} (원본 자막 완전 깨짐, 복원 불가)\n")

        f.write(f"\n  [ 다음 단계 ]\n")
        f.write(f"  1. python post_correction_processor.py  (통합 텍스트 재생성)\n")
        f.write(f"  2. python build_vectordb.py             (벡터DB 재구축)\n")

    # 최종 요약
    print(f"\n")
    print("=" * 60)
    print("  [4/4] GPT-4o 재교정 v2 완료!")
    print("=" * 60)
    print(f"  결과: {OUTPUT_DIR}")
    print(f"  처리: {stats['processed']}개 | 향상: {stats['improved']}개")
    print(f"  소요 시간: {elapsed/60:.1f}분")
    if comparison:
        old_avg = sum(c['old_score'] for c in comparison) / len(comparison)
        new_avg = sum(c['new_score'] for c in comparison) / len(comparison)
        print(f"  평균 점수: {old_avg:.1f} -> {new_avg:.1f} ({new_avg - old_avg:+.1f})")
    print(f"  리포트: {REPORT_PATH}")
    print()
    print("  다음 단계:")
    print("  1. python post_correction_processor.py  (통합 텍스트 재생성)")
    print("  2. python build_vectordb.py             (벡터DB 재구축)")
    print()


if __name__ == "__main__":
    main()
