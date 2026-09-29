#!/usr/bin/env python3
"""
====================================================================
llm_recorrector_v3.py 실행 중 CSV 잠금(PermissionError)으로 마지막
단계가 실패했을 때, API를 다시 호출하지 않고 마무리만 하는 스크립트.

이미 재교정되어 저장된 결과(24_재교정v3_사각지대, 15_전체교정_4omini)를
그대로 읽어서:
  1. 16_품질점수.csv 업데이트
  2. 25_재교정v3_비교리포트.txt 생성

사용 전: 16_품질점수.csv 파일을 엑셀 등에서 반드시 닫아주세요.

사용법:
  python finish_v3_report.py
====================================================================
"""

import re
import csv
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("./output_홍성남신부_자막추출")
RAW_DIR = BASE_DIR / "06_cleaned_text"
OUTPUT_DIR = BASE_DIR / "24_재교정v3_사각지대"
QUALITY_CSV = BASE_DIR / "16_품질점수.csv"
REPORT_PATH = BASE_DIR / "25_재교정v3_비교리포트.txt"

TARGET_FILES = [
    "00000000_181220 도반 홍성남 신부님 (상계동 성당).txt",
    "00000000_181215 도반 홍성남 신부님 (통합).txt",
    "00000000_181213 도반 홍성남 신부님(상계동 성당).txt",
    "00000000_홍성남 신부님의 새천년복음화 연구소 특강 (오후강의).txt",
    "00000000_190209 도반 홍성남신부님 (내사introjection).txt",
    "00000000_[260221] 자아의 성장과정.txt",
    "00000000_[240720] 다양한 방어기제에 대해서.txt",
    "00000000_[240120]  방어기제, 억압에 대해서.txt",
    "00000000_[지역특강_서원동 성당]마음의 힘을 키우는 방법_수정본.txt",
    "00000000_[220917]병적인 신앙(통합본).txt",
    "00000000_[240316]  방어기제, 편향에 대해서.txt",
    "00000000_180414 도반 홍성남 신부님.txt",
    "00000000_[220820]호감에 대해서(오디오).txt",
    "00000000_[240413]  파면된 신부와 사이비 종교.txt",
    "00000000_[240608] 방어기제, 고착에 대해서.txt",
    "00000000_181215 도반 홍성남 신부님(12).txt",
    "00000000_190309 도반 홍성남신부님 (종교적 내사, 사목자인가 사육자인가).txt",
    "00000000_[230916] 금쪽이가 갖고 있는 성격적 문제.txt",
    "00000000_190112 도반 홍성남신부님.txt",
    "00000000_[240511]  사이비 종교, 두 번째 시간.txt",
    "00000000_[240217]  방어기제, 반전에 대해서.txt",
    "00000000_[가정선교회]성가정 영성미사 (9월 7일).txt",
    "00000000_[요한 묵상집]제51화 요한복음 6장  64절~69절.txt",
    "00000000_[241012] 미움에 대해서.txt",
]


def calculate_quality(original, corrected):
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


def extract_body(text):
    lines = text.split('\n')
    content_start = 0
    for i, line in enumerate(lines):
        if '[정제 완료]' in line or '[4o-mini 전체교정]' in line or '[GPT-4o 재교정' in line or (line.startswith('=====') and i > 0):
            content_start = i + 1
    return '\n'.join(lines[content_start:]).strip()


def main():
    print("CSV/리포트 마무리 시작 (API 호출 없음)\n")

    if not QUALITY_CSV.exists():
        print(f"오류: {QUALITY_CSV} 를 찾을 수 없습니다.")
        return

    # 기존 점수 로드 (old_score 파악용)
    old_scores = {}
    with open(QUALITY_CSV, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        existing = list(reader)
    for row in existing:
        old_scores[row['filename']] = int(row.get('quality_score', 0))

    comparison = []
    updated_scores = []
    missing = []

    for filename in TARGET_FILES:
        out_path = OUTPUT_DIR / filename
        raw_path = RAW_DIR / filename

        if not out_path.exists():
            missing.append(filename)
            continue

        with open(out_path, 'r', encoding='utf-8') as f:
            corrected_full = f.read()
        corrected_body = extract_body(corrected_full)

        raw_body = ""
        if raw_path.exists():
            try:
                with open(raw_path, 'r', encoding='utf-8') as f:
                    raw_body = extract_body(f.read())
            except UnicodeDecodeError:
                with open(raw_path, 'r', encoding='utf-8-sig') as f:
                    raw_body = extract_body(f.read())

        new_score = calculate_quality(raw_body, corrected_body)
        old_score = old_scores.get(filename, 0)

        comparison.append({
            'filename': filename,
            'old_score': old_score,
            'new_score': new_score,
        })
        updated_scores.append({
            'filename': filename,
            'new_score': new_score,
            'corrected_chars': len(corrected_body),
        })
        print(f"  {filename[:45]:45} {old_score}점 -> {new_score}점")

    if missing:
        print(f"\n주의: 결과 파일을 못 찾은 항목 {len(missing)}개:")
        for m in missing:
            print(f"  - {m}")

    # CSV 업데이트
    update_map = {s['filename']: s for s in updated_scores}
    for row in existing:
        if row['filename'] in update_map:
            row['quality_score'] = update_map[row['filename']]['new_score']
            row['corrected_chars'] = update_map[row['filename']]['corrected_chars']

    with open(QUALITY_CSV, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=["filename", "quality_score", "original_chars", "corrected_chars"])
        writer.writeheader()
        writer.writerows(existing)
    print(f"\n✅ {QUALITY_CSV} 업데이트 완료")

    # 리포트 생성
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("  GPT-4o 재교정 v3 비교 리포트 (사각지대 24개)\n")
        f.write(f"  생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')} (CSV 잠금 이슈로 사후 재생성)\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"  재교정 대상: {len(TARGET_FILES)}개\n")
        f.write(f"  결과 확인됨: {len(comparison)}개\n")
        f.write(f"  결과 누락: {len(missing)}개\n\n")

        if comparison:
            old_avg = sum(c['old_score'] for c in comparison) / len(comparison)
            new_avg = sum(c['new_score'] for c in comparison) / len(comparison)
            f.write(f"  평균 점수 변화: {old_avg:.1f} -> {new_avg:.1f} ({new_avg - old_avg:+.1f})\n\n")
            f.write("  [ 파일별 비교 ]\n")
            for c in sorted(comparison, key=lambda x: x['new_score'] - x['old_score'], reverse=True):
                change = c['new_score'] - c['old_score']
                marker = "UP" if change > 0 else ("==" if change == 0 else "DN")
                f.write(f"  {marker} {c['old_score']:>2} -> {c['new_score']:>2} ({change:+d}) | {c['filename']}\n")

        if missing:
            f.write(f"\n  [ 결과 파일 못 찾음 ]\n")
            for m in missing:
                f.write(f"  - {m}\n")

        f.write(f"\n  [ 다음 단계 ]\n")
        f.write(f"  1. python post_correction_processor.py  (통합 텍스트 재생성)\n")
        f.write(f"  2. vectordb_홍성남신부 폴더 백업 후 python build_vectordb.py 재실행\n")

    print(f"✅ {REPORT_PATH} 생성 완료")

    if comparison:
        old_avg = sum(c['old_score'] for c in comparison) / len(comparison)
        new_avg = sum(c['new_score'] for c in comparison) / len(comparison)
        print(f"\n평균 점수: {old_avg:.1f} -> {new_avg:.1f} ({new_avg - old_avg:+.1f})")


if __name__ == "__main__":
    main()
