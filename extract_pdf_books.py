#!/usr/bin/env python3
"""
====================================================================
홍성남 신부님 도서 PDF 텍스트 추출 스크립트
====================================================================
[사용법]
  python extract_pdf_books.py

[폴더 구조]
  input_도서/
  ├── 01_홍성남저서/    ← 홍성남 신부님 저서
  ├── 02_성경묵상/      ← 성경 묵상집
  └── 03_영성자료/      ← 기타 영성 자료

[산출물]
  output_도서텍스트/
  ├── 01_홍성남저서/    ← 추출된 TXT 파일
  ├── 02_성경묵상/
  └── 03_영성자료/

[필수]
  pip install pypdf
====================================================================
"""

import os
from pathlib import Path

# pypdf 설치 확인
try:
    from pypdf import PdfReader
except ImportError:
    print("pypdf 설치 중...")
    os.system("pip install pypdf")
    from pypdf import PdfReader

# ── 경로 설정 ──────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
INPUT_DIR  = BASE_DIR / "input_도서"
OUTPUT_DIR = BASE_DIR / "output_도서텍스트"

# ── 카테고리 폴더 설정 ─────────────────────────────────────
CATEGORIES = {
    "01_홍성남저서": "book_hong",
    "02_성경묵상":   "book_bible",
    "03_영성자료":   "book_spiritual",
}


def extract_text_from_pdf(pdf_path: Path) -> str:
    """PDF에서 텍스트 추출"""
    try:
        reader = PdfReader(pdf_path)
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text and text.strip():
                text_parts.append(text.strip())
        return "\n\n".join(text_parts)
    except Exception as e:
        print(f"  ⚠️  오류: {e}")
        return ""


def clean_text(text: str) -> str:
    """텍스트 정제"""
    # 불필요한 공백 정리
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        line = line.strip()
        if len(line) < 2:  # 너무 짧은 줄 제거
            continue
        cleaned.append(line)
    return '\n'.join(cleaned)


def main():
    print("=" * 60)
    print("홍성남 신부님 도서 PDF 텍스트 추출 스크립트")
    print("=" * 60)

    # 입력 폴더 확인
    if not INPUT_DIR.exists():
        print(f"\n❌ {INPUT_DIR} 폴더가 없습니다.")
        print("input_도서 폴더를 만들고 하위 폴더에 PDF를 넣어주세요.")
        return

    # 출력 폴더 생성
    OUTPUT_DIR.mkdir(exist_ok=True)

    total_success = 0
    total_fail = 0
    total_empty = 0

    for folder_name, category in CATEGORIES.items():
        input_folder  = INPUT_DIR / folder_name
        output_folder = OUTPUT_DIR / folder_name
        output_folder.mkdir(exist_ok=True)

        if not input_folder.exists():
            print(f"\n⚠️  {folder_name} 폴더 없음 → 건너뜀")
            continue

        pdf_files = list(input_folder.glob("*.pdf"))
        if not pdf_files:
            print(f"\n⚠️  {folder_name} 폴더에 PDF 없음 → 건너뜀")
            continue

        print(f"\n{'='*60}")
        print(f"📁 {folder_name} ({len(pdf_files)}개 파일)")
        print('='*60)

        for pdf_path in sorted(pdf_files):
            output_path = output_folder / (pdf_path.stem + ".txt")

            # 이미 추출된 파일 건너뜀
            if output_path.exists():
                print(f"  ✓ 이미 처리됨: {pdf_path.name}")
                total_success += 1
                continue

            print(f"  처리 중: {pdf_path.name}")

            # 텍스트 추출
            text = extract_text_from_pdf(pdf_path)

            if not text.strip():
                print(f"  ⚠️  텍스트 없음 (스캔 이미지 PDF일 수 있음): {pdf_path.name}")
                total_empty += 1
                continue

            # 텍스트 정제
            cleaned = clean_text(text)

            # 파일 헤더 추가 (VectorDB 메타데이터용)
            header = f"[출처: {folder_name}] [파일: {pdf_path.stem}] [카테고리: {category}]\n\n"
            final_text = header + cleaned

            # TXT 저장
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(final_text)

            char_count = len(cleaned)
            print(f"  ✅ 완료: {char_count:,}자 → {output_path.name}")
            total_success += 1

    print(f"\n{'='*60}")
    print(f"전체 처리 완료!")
    print(f"  성공: {total_success}개")
    print(f"  텍스트 없음: {total_empty}개")
    print(f"저장 위치: {OUTPUT_DIR}")
    print('='*60)

    if total_empty > 0:
        print(f"\n⚠️  텍스트 없는 파일 {total_empty}개는 스캔 이미지 PDF일 수 있습니다.")
        print("이 경우 OCR 변환이 필요합니다. 파일명을 알려주시면 확인해 드립니다.")


if __name__ == "__main__":
    main()
