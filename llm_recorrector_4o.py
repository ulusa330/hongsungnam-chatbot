#!/usr/bin/env python3
"""
====================================================================
홍성남 신부님 자막 텍스트 - GPT-4o 재교정 스크립트
====================================================================
[사용법]
  python llm_recorrector_4o.py

[기능]
  - 19_재교정_대상목록.csv 기반으로 60점 미만 파일만 GPT-4o로 재교정
  - 4o-mini 교정 결과(15_전체교정_4omini)를 입력으로 사용
  - 재교정 결과를 20_재교정_4o/ 폴더에 저장
  - 완료 후 15_전체교정_4omini 폴더에도 덮어쓰기 (선택)
  - 품질 점수 재측정 및 비교 리포트 생성

[비용]
  - 45개 파일 × GPT-4o: 약 $1~2 (약 1,500~3,000원)
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
INPUT_DIR = BASE_DIR / "15_전체교정_4omini"       # 4o-mini 교정 결과를 입력으로
RECHECK_CSV = BASE_DIR / "19_재교정_대상목록.csv"  # 재교정 대상 목록
OUTPUT_DIR = BASE_DIR / "20_재교정_4o"
REPORT_PATH = BASE_DIR / "21_재교정_비교리포트.txt"
QUALITY_CSV = BASE_DIR / "16_품질점수.csv"         # 기존 품질 CSV 업데이트용

MODEL = "gpt-4o"

# 시스템 프롬프트 (GPT-4o용 - 더 정밀한 교정)
SYSTEM_PROMPT = """당신은 한국어 음성인식 텍스트 교정 전문가입니다.
아래 텍스트는 가톨릭 홍성남 신부의 '톡쏘는 영성심리' 유튜브 강의를 YouTube 자동자막으로 추출한 후,
GPT-4o-mini로 1차 교정한 결과입니다. 아직 교정 품질이 낮은 부분이 있으므로 더 정밀하게 교정해 주세요.

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
   - "목사" → 문맥 확인 (다른 종교 언급 가능)

3. 심리학 용어: 투사, 전이, 내사, 나르시시즘, 콤플렉스, 방어기제, 신경증
   - 프로이트, 칼 융, 아들러, 에릭슨, 매슬로우, 스캇 펙

4. 문장 품질 향상:
   - 띄어쓰기 정확하게 교정
   - 문장부호(마침표, 쉼표, 물음표) 적절히 보완
   - 반복되는 단어나 불필요한 추임새 정리
   - 구어체는 유지하되 가독성 향상

5. ⚠️ 절대 금지 사항:
   - 원본에 없는 내용을 절대 추가하지 마세요
   - 문맥을 추측해서 새로운 문장을 만들지 마세요
   - 원본의 문장 순서를 바꾸지 마세요
   - 복원이 불가능한 부분은 그대로 두거나 [인식불가]로 표시하세요
   - 원본보다 길어지면 안 됩니다

원본 텍스트의 의미와 분량을 최대한 유지하면서, 1차 교정에서 놓친 오류를 잡아주세요."""


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


def load_recheck_list():
    """재교정 대상 파일 목록 로드"""
    if not RECHECK_CSV.exists():
        print(f"❌ 재교정 대상 목록을 찾을 수 없습니다: {RECHECK_CSV}")
        return []

    targets = []
    with open(RECHECK_CSV, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            targets.append(row)
    return targets


def correct_text(client, text):
    """GPT-4o로 텍스트 재교정"""
    lines = text.split('\n')
    header_lines = []
    content_start = 0

    for i, line in enumerate(lines):
        if '[4o-mini 전체교정]' in line or '[정제 완료]' in line or (line.startswith('=====') and i > 0):
            content_start = i + 1
            continue
        if content_start == 0:
            header_lines.append(line)

    header = '\n'.join(header_lines)
    content = '\n'.join(lines[content_start:]).strip()

    if not content or len(content) < 30:
        return text, False, 0

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
                    {"role": "user", "content": f"아래 텍스트를 정밀 교정해 주세요. 1차 교정에서 놓친 오류를 잡아주세요:\n\n{chunk}"}
                ],
                temperature=0.1,
                max_tokens=16000,
            )
            corrected = response.choices[0].message.content.strip()
            corrected_chunks.append(corrected)
        except Exception as e:
            print(f"\n      ⚠️ API 오류: {e}")
            corrected_chunks.append(chunk)
            time.sleep(10)

    corrected_content = '\n'.join(corrected_chunks)

    # 품질 점수 계산
    quality_score = calculate_quality(content, corrected_content)

    result = header + '\n============================== [GPT-4o 재교정] ==============================\n\n' + corrected_content
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

    # 업데이트 맵
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
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  홍성남 신부님 자막 텍스트 - GPT-4o 재교정               ║")
    print("║  품질 60점 미만 파일 대상 정밀 교정                      ║")
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

    # 재교정 대상 로드
    targets = load_recheck_list()
    if not targets:
        print("   재교정 대상 파일이 없습니다.")
        return

    total = len(targets)
    print(f"📋 재교정 대상: {total}개 파일 (60점 미만)")
    print(f"💰 예상 비용: ${total * 0.02:.1f}~${total * 0.04:.1f}")
    print(f"⏱️  예상 시간: {total * 1.5 / 60:.0f}~{total * 2.5 / 60:.0f}분")
    print(f"\n{'─' * 50}\n")

    # 이미 재교정된 파일 확인
    already_done = set()
    if OUTPUT_DIR.exists():
        already_done = {f.name for f in OUTPUT_DIR.glob("*.txt")}

    stats = {"processed": 0, "improved": 0, "errors": 0}
    comparison = []
    updated_scores = []
    start_time = time.time()

    for i, target in enumerate(targets, 1):
        filename = target['filename']
        old_score = int(target.get('quality_score', 0))
        progress = f"[{i}/{total}]"

        # 이미 재교정됨
        if filename in already_done:
            print(f"   {progress} ⏭️  건너뜀 (이미 완료): {filename[:50]}")
            continue

        input_path = INPUT_DIR / filename
        if not input_path.exists():
            print(f"   {progress} ⚠️ 파일 없음: {filename[:50]}")
            stats["errors"] += 1
            continue

        print(f"   {progress} 재교정 중: {filename[:45]}...", end="", flush=True)

        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                original = f.read()
        except:
            try:
                with open(input_path, 'r', encoding='utf-8-sig') as f:
                    original = f.read()
            except:
                print(" ⚠️ 읽기 실패")
                stats["errors"] += 1
                continue

        # GPT-4o 재교정
        corrected, was_corrected, new_score = correct_text(client, original)

        # 저장
        out_path = OUTPUT_DIR / filename
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(corrected)

        # 15_전체교정_4omini 폴더에도 덮어쓰기 (품질 향상된 버전으로)
        if new_score > old_score:
            with open(input_path, 'w', encoding='utf-8') as f:
                f.write(corrected)
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
        print(f" ✅ {old_score}점 → {new_score}점 ({change})")

        # API 속도 제한 방지 (4o는 더 느림)
        time.sleep(1)

    elapsed = time.time() - start_time

    # 품질 CSV 업데이트
    if updated_scores:
        update_quality_csv(updated_scores)

    # 비교 리포트 생성
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("  GPT-4o 재교정 비교 리포트\n")
        f.write(f"  생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("=" * 60 + "\n\n")

        f.write(f"  재교정 대상: {total}개\n")
        f.write(f"  처리 완료: {stats['processed']}개\n")
        f.write(f"  품질 향상: {stats['improved']}개\n")
        f.write(f"  오류: {stats['errors']}개\n")
        f.write(f"  소요 시간: {elapsed/60:.1f}분\n\n")

        if comparison:
            old_avg = sum(c['old_score'] for c in comparison) / len(comparison)
            new_avg = sum(c['new_score'] for c in comparison) / len(comparison)
            f.write(f"  평균 점수 변화: {old_avg:.1f} → {new_avg:.1f} ({new_avg - old_avg:+.1f})\n\n")

            f.write("  [ 파일별 비교 ]\n")
            for c in sorted(comparison, key=lambda x: x['new_score'] - x['old_score'], reverse=True):
                change = c['new_score'] - c['old_score']
                marker = "⬆️" if change > 0 else ("➡️" if change == 0 else "⬇️")
                f.write(f"  {marker} {c['old_score']:>2} → {c['new_score']:>2} ({change:+d}) | {c['filename']}\n")

        f.write(f"\n\n  [ 다음 단계 ]\n")
        f.write(f"  1. 15_전체교정_4omini 폴더가 최신 품질로 업데이트됨\n")
        f.write(f"  2. post_correction_processor.py를 다시 실행하여 통합 텍스트 재생성\n")
        f.write(f"  3. 통합 텍스트로 RAG/벡터DB 구축 시작\n")

    # 최종 요약
    print(f"\n")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║              ✅ GPT-4o 재교정 완료!                      ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║  📁 재교정 결과: {OUTPUT_DIR}")
    print(f"║  📋 처리: {stats['processed']}개 | 향상: {stats['improved']}개")
    print(f"║  ⏱️  소요 시간: {elapsed/60:.1f}분")
    if comparison:
        old_avg = sum(c['old_score'] for c in comparison) / len(comparison)
        new_avg = sum(c['new_score'] for c in comparison) / len(comparison)
        print(f"║  📊 평균 점수: {old_avg:.1f} → {new_avg:.1f} ({new_avg - old_avg:+.1f})")
    print(f"║  📄 비교 리포트: {REPORT_PATH}")
    print("╠══════════════════════════════════════════════════════════╣")
    print("║  💡 다음 단계:                                          ║")
    print("║  1. post_correction_processor.py 재실행 (통합 텍스트 갱신)║")
    print("║  2. RAG/벡터DB 구축 시작                                 ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()


if __name__ == "__main__":
    main()
