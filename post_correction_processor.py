#!/usr/bin/env python3
"""
====================================================================
홍성남 신부님 - 교정 완료 후 자동 처리 스크립트
====================================================================
[사용법]
  교정(llm_corrector_full.py) 완료 후 실행:
    python post_correction_processor.py

[기능]
  STEP 1: 품질 분석 리포트 생성
    - 16_품질점수.csv 분석
    - 점수 분포, 재교정 필요 파일 목록
    - 상세 리포트 저장

  STEP 2: 전체 통합 텍스트 생성
    - 교정된 전체 파일을 하나의 텍스트로 합치기
    - 날짜순 정렬
    - 메타데이터 포함

[출력]
  - 17_품질분석_리포트.txt     # 품질 분석 결과
  - 18_통합_교정텍스트.txt     # 전체 통합 텍스트
  - 19_재교정_대상목록.csv     # 60점 미만 파일 목록
====================================================================
"""

import csv
import os
import re
from pathlib import Path
from datetime import datetime
from collections import Counter

# =====================================================================
# 설정
# =====================================================================
BASE_DIR = Path("./output_홍성남신부_자막추출")
CORRECTED_DIR = BASE_DIR / "15_전체교정_4omini"
QUALITY_CSV = BASE_DIR / "16_품질점수.csv"

# 출력 파일
REPORT_PATH = BASE_DIR / "17_품질분석_리포트.txt"
COMBINED_PATH = BASE_DIR / "18_통합_교정텍스트.txt"
RECHECK_CSV = BASE_DIR / "19_재교정_대상목록.csv"

# 품질 기준
LOW_QUALITY_THRESHOLD = 60  # 이 점수 미만은 재교정 대상


# =====================================================================
# STEP 1: 품질 분석 리포트
# =====================================================================
def analyze_quality():
    """품질 점수 CSV를 분석하여 상세 리포트를 생성합니다."""
    print("\n" + "=" * 60)
    print("📊 STEP 1: 품질 분석 리포트 생성 중...")
    print("=" * 60)

    if not QUALITY_CSV.exists():
        print("   ❌ 품질점수 CSV를 찾을 수 없습니다.")
        print(f"      경로: {QUALITY_CSV}")
        return None

    # CSV 읽기
    scores_data = []
    with open(QUALITY_CSV, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                row['quality_score'] = int(row.get('quality_score', 0))
                row['original_chars'] = int(row.get('original_chars', 0))
                row['corrected_chars'] = int(row.get('corrected_chars', 0))
                scores_data.append(row)
            except (ValueError, KeyError):
                continue

    if not scores_data:
        print("   ❌ 품질 데이터가 비어 있습니다.")
        return None

    total = len(scores_data)
    scores = [d['quality_score'] for d in scores_data]
    avg_score = sum(scores) / total
    min_score = min(scores)
    max_score = max(scores)

    # 등급별 분류
    grade_a = [d for d in scores_data if d['quality_score'] >= 80]  # 우수
    grade_b = [d for d in scores_data if 60 <= d['quality_score'] < 80]  # 양호
    grade_c = [d for d in scores_data if 40 <= d['quality_score'] < 60]  # 보통 (재교정 권장)
    grade_d = [d for d in scores_data if d['quality_score'] < 40]  # 미흡 (재교정 필수)

    low_quality = [d for d in scores_data if d['quality_score'] < LOW_QUALITY_THRESHOLD]

    # 점수 분포 (10점 단위)
    distribution = Counter()
    for s in scores:
        bracket = (s // 10) * 10
        distribution[bracket] += 1

    # 총 글자수 통계
    total_original = sum(d['original_chars'] for d in scores_data)
    total_corrected = sum(d['corrected_chars'] for d in scores_data)

    # --- 리포트 작성 ---
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("  홍성남 신부님 자막 텍스트 - 품질 분석 리포트\n")
        f.write(f"  생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("=" * 60 + "\n\n")

        f.write("[ 전체 요약 ]\n")
        f.write(f"  - 분석 파일 수: {total}개\n")
        f.write(f"  - 평균 품질 점수: {avg_score:.1f} / 100\n")
        f.write(f"  - 최저 점수: {min_score}점\n")
        f.write(f"  - 최고 점수: {max_score}점\n")
        f.write(f"  - 원본 총 글자수: {total_original:,}자\n")
        f.write(f"  - 교정 후 총 글자수: {total_corrected:,}자\n")
        f.write(f"  - 글자수 변화율: {((total_corrected - total_original) / max(total_original, 1)) * 100:+.1f}%\n\n")

        f.write("[ 등급별 분류 ]\n")
        f.write(f"  🟢 A등급 (80점 이상, 우수):    {len(grade_a):>4}개 ({len(grade_a)/total*100:.1f}%)\n")
        f.write(f"  🟡 B등급 (60~79점, 양호):      {len(grade_b):>4}개 ({len(grade_b)/total*100:.1f}%)\n")
        f.write(f"  🟠 C등급 (40~59점, 재교정 권장): {len(grade_c):>4}개 ({len(grade_c)/total*100:.1f}%)\n")
        f.write(f"  🔴 D등급 (40점 미만, 재교정 필수): {len(grade_d):>4}개 ({len(grade_d)/total*100:.1f}%)\n\n")

        f.write("[ 점수 분포 ]\n")
        for bracket in sorted(distribution.keys()):
            bar = "█" * (distribution[bracket] // 5) + "▌" * (1 if distribution[bracket] % 5 >= 3 else 0)
            f.write(f"  {bracket:>2}~{bracket+9:<2}점: {distribution[bracket]:>4}개 {bar}\n")
        f.write("\n")

        f.write(f"[ 재교정 대상 ({LOW_QUALITY_THRESHOLD}점 미만) ]\n")
        f.write(f"  - 총 {len(low_quality)}개 파일\n\n")

        if low_quality:
            # 점수 낮은 순으로 정렬
            for d in sorted(low_quality, key=lambda x: x['quality_score']):
                f.write(f"  [{d['quality_score']:>2}점] {d['filename']}\n")

        f.write(f"\n\n[ 다음 단계 권장 ]\n")
        if len(low_quality) > 0:
            f.write(f"  1. {len(low_quality)}개 파일을 GPT-4o로 재교정하면 품질 향상 가능\n")
            f.write(f"  2. 19_재교정_대상목록.csv 참고\n")
        else:
            f.write(f"  1. 모든 파일이 {LOW_QUALITY_THRESHOLD}점 이상! 재교정 불필요\n")
        f.write(f"  3. 18_통합_교정텍스트.txt로 RAG/벡터DB 구축 진행\n")
        f.write(f"  4. 주제별 분류 작업 시작\n")

    # --- 재교정 대상 CSV 저장 ---
    if low_quality:
        with open(RECHECK_CSV, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=["filename", "quality_score", "original_chars", "corrected_chars"])
            writer.writeheader()
            writer.writerows(sorted(low_quality, key=lambda x: x['quality_score']))

    # --- 콘솔 출력 ---
    print(f"\n   📊 분석 결과:")
    print(f"   - 전체 파일: {total}개")
    print(f"   - 평균 점수: {avg_score:.1f}점")
    print(f"   - A등급(80+): {len(grade_a)}개 | B등급(60~79): {len(grade_b)}개")
    print(f"   - C등급(40~59): {len(grade_c)}개 | D등급(~39): {len(grade_d)}개")
    print(f"   - 재교정 대상: {len(low_quality)}개")
    print(f"   - 리포트: {REPORT_PATH}")
    if low_quality:
        print(f"   - 재교정 목록: {RECHECK_CSV}")

    return scores_data


# =====================================================================
# STEP 2: 전체 통합 텍스트 생성
# =====================================================================
def generate_combined_text():
    """교정된 전체 파일을 하나의 통합 텍스트로 합칩니다."""
    print("\n" + "=" * 60)
    print("📝 STEP 2: 전체 통합 텍스트 생성 중...")
    print("=" * 60)

    if not CORRECTED_DIR.exists():
        print(f"   ❌ 교정 폴더를 찾을 수 없습니다: {CORRECTED_DIR}")
        return

    all_files = sorted(CORRECTED_DIR.glob("*.txt"))
    total = len(all_files)

    if total == 0:
        print("   ❌ 교정된 파일이 없습니다.")
        return

    print(f"   📂 교정된 파일: {total}개")
    print(f"   통합 중...", end="", flush=True)

    entries = []
    total_chars = 0
    errors = 0

    for filepath in all_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(filepath, 'r', encoding='utf-8-sig') as f:
                    content = f.read()
            except:
                errors += 1
                continue

        # 메타데이터 추출 (헤더에서)
        title = "제목 미상"
        upload_date = "00000000"
        vid = ""
        url = ""

        for line in content.split('\n')[:10]:
            if line.startswith('# 제목:'):
                title = line.replace('# 제목:', '').strip()
            elif line.startswith('# 업로드일:'):
                upload_date = line.replace('# 업로드일:', '').strip()
            elif line.startswith('# 영상 ID:'):
                vid = line.replace('# 영상 ID:', '').strip()
            elif line.startswith('# URL:'):
                url = line.replace('# URL:', '').strip()

        # 본문 추출 (헤더 이후)
        body_lines = []
        past_header = False
        for line in content.split('\n'):
            if '=====' in line and not past_header:
                past_header = True
                continue
            if past_header:
                body_lines.append(line)

        body = '\n'.join(body_lines).strip()
        if not body:
            # 헤더 구분이 없는 경우 전체를 본문으로
            body = content.strip()

        char_count = len(body)
        total_chars += char_count

        entries.append({
            'title': title,
            'date': upload_date,
            'vid': vid,
            'url': url or (f"https://youtube.com/watch?v={vid}" if vid else ""),
            'body': body,
            'chars': char_count,
            'filename': filepath.name,
        })

    # 날짜순 정렬
    entries.sort(key=lambda x: x['date'])

    # --- 통합 파일 작성 ---
    with open(COMBINED_PATH, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("  홍성남 신부님 - 톡쏘는 영성심리 전체 교정 텍스트\n")
        f.write(f"  생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"  총 영상: {len(entries)}개 | 총 글자수: {total_chars:,}자\n")
        f.write(f"  교정 모델: GPT-4o-mini\n")
        f.write("=" * 70 + "\n\n")

        for i, entry in enumerate(entries, 1):
            f.write(f"\n{'━' * 70}\n")
            f.write(f"  [{i}/{len(entries)}] {entry['title']}\n")
            f.write(f"  📅 {entry['date']}  |  📝 {entry['chars']:,}자")
            if entry['url']:
                f.write(f"  |  🔗 {entry['url']}")
            f.write(f"\n{'━' * 70}\n\n")
            f.write(entry['body'])
            f.write("\n\n")

    pages = total_chars // 1800

    print(f" 완료!")
    print(f"\n   📊 통합 결과:")
    print(f"   - 통합 파일 수: {len(entries)}개")
    print(f"   - 총 글자수: {total_chars:,}자 (A4 약 {pages}페이지)")
    print(f"   - 읽기 오류: {errors}개")
    print(f"   - 저장: {COMBINED_PATH}")

    return len(entries), total_chars


# =====================================================================
# 메인 실행
# =====================================================================
def main():
    print("\n")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  홍성남 신부님 자막 텍스트 - 교정 후처리 스크립트           ║")
    print("║  품질 분석 + 통합 텍스트 생성                               ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    # 교정 폴더 존재 확인
    if not CORRECTED_DIR.exists():
        print(f"❌ 교정 폴더가 존재하지 않습니다: {CORRECTED_DIR}")
        print("   llm_corrector_full.py를 먼저 실행하세요.")
        return

    corrected_count = len(list(CORRECTED_DIR.glob("*.txt")))
    print(f"📂 교정된 파일: {corrected_count}개")
    print()

    # STEP 1: 품질 분석
    scores_data = analyze_quality()

    # STEP 2: 통합 텍스트
    result = generate_combined_text()

    # 최종 요약
    print("\n")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║                    ✅ 후처리 완료!                          ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print(f"║  📊 품질 리포트: 17_품질분석_리포트.txt                      ║")
    print(f"║  📝 통합 텍스트: 18_통합_교정텍스트.txt                      ║")
    print(f"║  📋 재교정 목록: 19_재교정_대상목록.csv                      ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print("║  💡 다음 단계:                                              ║")
    print("║  1. 품질 리포트 확인 → 재교정 필요 여부 판단                 ║")
    print("║  2. 통합 텍스트로 RAG/벡터DB 구축 시작                       ║")
    print("║  3. 주제별 분류 작업 진행                                    ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()


if __name__ == "__main__":
    main()
