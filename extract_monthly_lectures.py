#!/usr/bin/env python3
"""
====================================================================
홍성남 신부님 월특강 자막 추출 스크립트
====================================================================
[사용법]
  python extract_monthly_lectures.py

[기능]
  - 월특강 재생목록에서 자막 자동 추출
  - SRT 형식으로 저장
  - input_월특강/ 폴더에 저장
  - 이미 다운로드된 파일은 건너뜀

[필수]
  pip install yt-dlp
====================================================================
"""

import os
import re
import subprocess
from pathlib import Path

# ── 경로 설정 ──────────────────────────────────────────────
BASE_DIR  = Path(__file__).parent
INPUT_DIR = BASE_DIR / "input_월특강"
INPUT_DIR.mkdir(exist_ok=True)

# ── 재생목록 URL 목록 ──────────────────────────────────────
PLAYLISTS = {
    "2018": "https://www.youtube.com/playlist?list=PLAtW9v-2lLBqZXrr4PbxCA8Z-NXukG8yJ",
    "2019": "https://www.youtube.com/playlist?list=PLAtW9v-2lLBqiEpQM0b4VZrkX5WgApB5W",
    "2020": "https://www.youtube.com/playlist?list=PLAtW9v-2lLBryhjRraUaDkLVHjCBx_8UY",
    "2022": "https://www.youtube.com/playlist?list=PLAtW9v-2lLBqHP7Mg2mGqC_s4dSFvg6uD",
    "2023": "https://www.youtube.com/playlist?list=PLAtW9v-2lLBobYx6iPnOJdRKO6-JtCeou",
    "2024": "https://www.youtube.com/playlist?list=PLAtW9v-2lLBookVDyALTKJTfWGBqdJroD",
    "2026": "https://www.youtube.com/playlist?list=PLAtW9v-2lLBplw3UxrD57WjXjjFU_aJxn",
}


def sanitize_filename(title: str) -> str:
    """파일명에 사용할 수 없는 문자 제거"""
    title = re.sub(r'[\\/*?:"<>|]', '', title)
    title = title.strip()
    return title[:80]  # 너무 길면 자르기


def extract_playlist(year: str, url: str):
    """재생목록에서 자막 추출"""
    print(f"\n{'='*60}")
    print(f"{year}년 특강 재생목록 처리 중...")
    print(f"URL: {url}")
    print('='*60)

    # yt-dlp로 자막 추출
    cmd = [
        "yt-dlp",
        "--write-sub",           # 자막 다운로드
        "--write-auto-sub",      # 자동 생성 자막도 포함
        "--sub-lang", "ko",      # 한국어 자막
        "--sub-format", "srt",   # SRT 형식
        "--skip-download",       # 영상 다운로드 안 함
        "--output", str(INPUT_DIR / "%(upload_date)s_%(title)s.%(ext)s"),
        "--no-overwrites",       # 이미 있으면 건너뜀
        "--ignore-errors",       # 오류 있어도 계속 진행
        url
    ]

    print("자막 추출 시작...")
    result = subprocess.run(cmd, capture_output=False, text=True)

    if result.returncode == 0:
        print(f"✅ {year}년 특강 추출 완료!")
    else:
        print(f"⚠️  일부 오류 발생 (건너뛴 영상 있을 수 있음)")


def rename_files():
    """
    yt-dlp가 저장한 파일명을 정리.
    날짜 형식: YYYYMMDD_제목.ko.srt → YYMM_제목.srt (같은 날짜면 합산 예정)
    """
    print("\n파일명 정리 중...")
    srt_files = list(INPUT_DIR.glob("*.srt"))

    renamed = 0
    for f in srt_files:
        name = f.stem  # 확장자 제거

        # yt-dlp 기본 형식: YYYYMMDD_제목.ko
        m = re.match(r'^(\d{8})_(.+?)(?:\.ko)?$', name)
        if m:
            date8  = m.group(1)   # "20220122"
            title  = m.group(2)
            yy = date8[2:4]
            mm = date8[4:6]
            dd = date8[6:8]
            # [YYMMDD]제목.srt 형식으로 변경
            new_name = f"[{yy}{mm}{dd}]{sanitize_filename(title)}.srt"
            new_path = f.parent / new_name
            if not new_path.exists():
                f.rename(new_path)
                renamed += 1

    print(f"  {renamed}개 파일명 정리 완료")


def main():
    print("=" * 60)
    print("홍성남 신부님 월특강 자막 추출 스크립트")
    print("=" * 60)
    print(f"저장 위치: {INPUT_DIR}")
    print(f"총 {len(PLAYLISTS)}개 재생목록 처리 예정")

    # yt-dlp 설치 확인
    try:
        subprocess.run(["yt-dlp", "--version"],
                      capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("\n❌ yt-dlp가 설치되어 있지 않습니다.")
        print("아래 명령어로 설치 후 다시 실행하세요:")
        print("  pip install yt-dlp")
        return

    # 특정 연도만 처리하고 싶으면 아래 주석 해제
    # target_years = ["2022", "2023"]
    # playlists = {k: v for k, v in PLAYLISTS.items() if k in target_years}
    playlists = PLAYLISTS

    for year, url in sorted(playlists.items()):
        extract_playlist(year, url)

    # 파일명 정리
    rename_files()

    print("\n" + "=" * 60)
    print("전체 추출 완료!")
    print(f"저장 위치: {INPUT_DIR}")
    print("\n다음 단계:")
    print("  python monthly_lecture_summarizer.py")
    print("  → 요약본 자동 생성")
    print("=" * 60)


if __name__ == "__main__":
    main()
