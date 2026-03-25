#!/usr/bin/env python3
"""
====================================================================
홍성남 신부님 유튜브 채널 - 자막/텍스트 일괄 추출 스크립트
====================================================================

[사용법]
  1. yt-dlp 설치:  pip install yt-dlp
  2. 실행:         python youtube_subtitle_extractor.py

[기능]
  - 채널 전체 영상 목록 수집 (제목, URL, 업로드일, 길이, 조회수)
  - YouTube 자동생성 자막(한국어) 일괄 다운로드
  - 자막 파일(VTT/SRT) → 깨끗한 텍스트 변환
  - 전체 통계 리포트 생성
  - 영상별 개별 텍스트 파일 + 통합 텍스트 파일 생성

[출력 폴더 구조]
  output/
  ├── 00_channel_inventory.csv          # 전체 영상 목록
  ├── 01_subtitles_raw/                 # 원본 자막 파일 (VTT)
  ├── 02_subtitles_text/                # 정제된 텍스트 파일 (영상별)
  ├── 03_combined_all_texts.txt         # 전체 통합 텍스트
  ├── 04_extraction_report.txt          # 추출 결과 리포트
  └── 05_no_subtitle_list.csv           # 자막 없는 영상 목록

[참고]
  - YouTube 자동자막 정확도: 약 80~90% (후처리 필요)
  - 자동자막이 없는 영상은 별도 리스트로 저장됨
  - Whisper STT로 더 높은 정확도를 원하면 2단계 스크립트 사용
====================================================================
"""

import subprocess
import json
import csv
import os
import re
import sys
from datetime import datetime
from pathlib import Path


# =====================================================================
# 설정
# =====================================================================
CHANNEL_URL = "https://youtube.com/@fr.hongsungnam"
OUTPUT_DIR = Path("./output_홍성남신부_자막추출")
SUBTITLE_LANG = "ko"  # 한국어

# 하위 폴더
RAW_SUB_DIR = OUTPUT_DIR / "01_subtitles_raw"
TEXT_DIR = OUTPUT_DIR / "02_subtitles_text"


def setup_directories():
    """출력 폴더 생성"""
    for d in [OUTPUT_DIR, RAW_SUB_DIR, TEXT_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    print(f"✅ 출력 폴더 생성 완료: {OUTPUT_DIR}")


def check_ytdlp():
    """yt-dlp 설치 확인"""
    try:
        result = subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True)
        print(f"✅ yt-dlp 버전: {result.stdout.strip()}")
        return True
    except FileNotFoundError:
        print("❌ yt-dlp가 설치되어 있지 않습니다.")
        print("   설치 방법: pip install yt-dlp")
        return False


# =====================================================================
# STEP 1: 채널 전체 영상 목록 수집
# =====================================================================
def fetch_video_list():
    """채널의 모든 영상 메타데이터를 수집합니다."""
    print("\n" + "=" * 60)
    print("📋 STEP 1: 채널 전체 영상 목록 수집 중...")
    print("=" * 60)
    print("   (영상이 많으면 몇 분 걸릴 수 있습니다)")

    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-json",
        "--no-warnings",
        CHANNEL_URL
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    videos = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            videos.append({
                "id": data.get("id", ""),
                "title": data.get("title", "제목 없음"),
                "url": f"https://www.youtube.com/watch?v={data.get('id', '')}",
                "upload_date": data.get("upload_date", ""),
                "duration": data.get("duration", 0),
                "view_count": data.get("view_count", 0),
            })
        except json.JSONDecodeError:
            continue

    # CSV로 저장
    csv_path = OUTPUT_DIR / "00_channel_inventory.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "title", "url", "upload_date", "duration", "view_count"])
        writer.writeheader()
        writer.writerows(videos)

    total_duration = sum(v["duration"] or 0 for v in videos)
    hours = total_duration // 3600
    mins = (total_duration % 3600) // 60

    print(f"\n   📊 수집 결과:")
    print(f"   - 전체 영상 수: {len(videos)}개")
    print(f"   - 총 재생 시간: 약 {hours}시간 {mins}분")
    print(f"   - 목록 저장: {csv_path}")

    return videos


# =====================================================================
# STEP 2: 자막 일괄 다운로드
# =====================================================================
def download_subtitles(videos):
    """모든 영상의 자동생성 한국어 자막을 다운로드합니다."""
    print("\n" + "=" * 60)
    print("📥 STEP 2: 자막 일괄 다운로드 중...")
    print("=" * 60)

    success_count = 0
    fail_list = []
    total = len(videos)

    for i, video in enumerate(videos, 1):
        vid = video["id"]
        title = video["title"]
        progress = f"[{i}/{total}]"

        # 이미 다운로드된 경우 건너뛰기
        existing = list(RAW_SUB_DIR.glob(f"{vid}.*"))
        if existing:
            print(f"   {progress} ⏭️  건너뜀 (이미 존재): {title[:40]}...")
            success_count += 1
            continue

        cmd = [
            "yt-dlp",
            "--write-auto-sub",
            "--sub-lang", SUBTITLE_LANG,
            "--sub-format", "vtt",
            "--skip-download",
            "--no-warnings",
            "-o", str(RAW_SUB_DIR / f"{vid}.%(ext)s"),
            f"https://www.youtube.com/watch?v={vid}"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        # 자막 파일 존재 확인
        sub_files = list(RAW_SUB_DIR.glob(f"{vid}*.vtt"))
        if sub_files:
            success_count += 1
            print(f"   {progress} ✅ 자막 다운로드 완료: {title[:40]}...")
        else:
            fail_list.append(video)
            print(f"   {progress} ❌ 자막 없음: {title[:40]}...")

    # 자막 없는 영상 목록 저장
    if fail_list:
        fail_csv = OUTPUT_DIR / "05_no_subtitle_list.csv"
        with open(fail_csv, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["id", "title", "url", "upload_date", "duration", "view_count"])
            writer.writeheader()
            writer.writerows(fail_list)

    print(f"\n   📊 다운로드 결과:")
    print(f"   - 성공: {success_count}개")
    print(f"   - 자막 없음: {len(fail_list)}개")
    if fail_list:
        print(f"   - 자막 없는 영상 목록: {OUTPUT_DIR / '05_no_subtitle_list.csv'}")

    return success_count, fail_list


# =====================================================================
# STEP 3: VTT 자막 → 깨끗한 텍스트 변환
# =====================================================================
def clean_vtt_to_text(vtt_content):
    """VTT 자막 파일을 깨끗한 텍스트로 변환합니다.
    
    - 타임스탬프 제거
    - HTML 태그 제거
    - 중복 라인 제거 (VTT는 같은 텍스트가 반복됨)
    - 빈 줄 정리
    """
    lines = vtt_content.split("\n")
    text_lines = []
    prev_line = ""

    for line in lines:
        line = line.strip()

        # VTT 헤더, 타임스탬프, 빈 줄 건너뛰기
        if not line:
            continue
        if line.startswith("WEBVTT"):
            continue
        if line.startswith("Kind:") or line.startswith("Language:"):
            continue
        if re.match(r"^\d{2}:\d{2}:\d{2}\.\d{3}\s*-->", line):
            continue
        if re.match(r"^\d+$", line):  # 시퀀스 번호
            continue
        if line.startswith("NOTE"):
            continue

        # HTML 태그 제거
        line = re.sub(r"<[^>]+>", "", line)
        # VTT 포지셔닝 태그 제거
        line = re.sub(r"align:start position:\d+%", "", line)
        line = line.strip()

        if not line:
            continue

        # 중복 제거 (VTT는 겹치는 자막이 반복됨)
        if line != prev_line:
            text_lines.append(line)
            prev_line = line

    # 연속된 짧은 라인들을 문장으로 합치기
    combined = " ".join(text_lines)
    # 과도한 공백 정리
    combined = re.sub(r"\s+", " ", combined).strip()

    return combined


def convert_subtitles_to_text(videos):
    """다운로드된 자막 파일들을 텍스트로 변환합니다."""
    print("\n" + "=" * 60)
    print("📝 STEP 3: 자막 → 텍스트 변환 중...")
    print("=" * 60)

    converted = 0
    total_chars = 0
    all_texts = []

    # 영상 ID → 메타데이터 매핑
    video_map = {v["id"]: v for v in videos}

    for vtt_file in sorted(RAW_SUB_DIR.glob("*.vtt")):
        vid = vtt_file.stem.split(".")[0]  # ID 추출
        meta = video_map.get(vid, {})
        title = meta.get("title", "제목 미상")
        upload_date = meta.get("upload_date", "날짜 미상")

        # VTT 읽기 및 변환
        with open(vtt_file, "r", encoding="utf-8") as f:
            vtt_content = f.read()

        clean_text = clean_vtt_to_text(vtt_content)

        if not clean_text or len(clean_text) < 50:
            continue

        # 개별 텍스트 파일 저장
        # 파일명에 날짜와 제목 포함 (파일명 안전 처리)
        safe_title = re.sub(r'[\\/*?:"<>|]', "", title)[:60]
        date_str = upload_date[:8] if upload_date else "00000000"
        txt_filename = f"{date_str}_{safe_title}.txt"

        txt_path = TEXT_DIR / txt_filename
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"# 제목: {title}\n")
            f.write(f"# 업로드일: {upload_date}\n")
            f.write(f"# 영상 ID: {vid}\n")
            f.write(f"# URL: https://www.youtube.com/watch?v={vid}\n")
            f.write(f"# 글자수: {len(clean_text)}자\n")
            f.write(f"{'=' * 60}\n\n")
            f.write(clean_text)

        # 통합 텍스트에 추가
        all_texts.append({
            "title": title,
            "date": upload_date,
            "vid": vid,
            "text": clean_text,
            "char_count": len(clean_text)
        })

        total_chars += len(clean_text)
        converted += 1

    # 통합 텍스트 파일 생성
    combined_path = OUTPUT_DIR / "03_combined_all_texts.txt"
    with open(combined_path, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("홍성남 신부님 - 톡쏘는 영성심리 전체 텍스트\n")
        f.write(f"추출일: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"총 영상: {converted}개 | 총 글자수: {total_chars:,}자\n")
        f.write("=" * 60 + "\n\n")

        for item in sorted(all_texts, key=lambda x: x["date"]):
            f.write(f"\n{'─' * 60}\n")
            f.write(f"📌 {item['title']}\n")
            f.write(f"📅 {item['date']}  |  🔗 https://youtube.com/watch?v={item['vid']}\n")
            f.write(f"{'─' * 60}\n\n")
            f.write(item["text"])
            f.write("\n\n")

    print(f"\n   📊 변환 결과:")
    print(f"   - 변환 완료: {converted}개 영상")
    print(f"   - 총 텍스트 분량: {total_chars:,}자 (약 {total_chars // 1800}페이지, A4 기준)")
    print(f"   - 개별 파일: {TEXT_DIR}/")
    print(f"   - 통합 파일: {combined_path}")

    return converted, total_chars, all_texts


# =====================================================================
# STEP 4: 추출 리포트 생성
# =====================================================================
def generate_report(videos, success_count, fail_list, converted, total_chars):
    """추출 결과 리포트를 생성합니다."""
    print("\n" + "=" * 60)
    print("📊 STEP 4: 추출 리포트 생성 중...")
    print("=" * 60)

    report_path = OUTPUT_DIR / "04_extraction_report.txt"
    total_duration = sum(v["duration"] or 0 for v in videos)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("  홍성남 신부님 유튜브 채널 텍스트 추출 리포트\n")
        f.write(f"  생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("=" * 60 + "\n\n")

        f.write("[ 채널 정보 ]\n")
        f.write(f"  - 채널: 홍성남신부님의 톡쏘는 영성심리\n")
        f.write(f"  - URL: {CHANNEL_URL}\n\n")

        f.write("[ 수집 통계 ]\n")
        f.write(f"  - 전체 영상 수: {len(videos)}개\n")
        f.write(f"  - 총 재생 시간: {total_duration // 3600}시간 {(total_duration % 3600) // 60}분\n")
        f.write(f"  - 자막 다운로드 성공: {success_count}개\n")
        f.write(f"  - 자막 없는 영상: {len(fail_list)}개\n")
        f.write(f"  - 텍스트 변환 완료: {converted}개\n")
        f.write(f"  - 추출 텍스트 총 분량: {total_chars:,}자\n")
        f.write(f"  - A4 환산: 약 {total_chars // 1800}페이지\n\n")

        f.write("[ 다음 단계 ]\n")
        f.write("  1. 02_subtitles_text/ 폴더의 텍스트를 검토하세요\n")
        f.write("  2. 자동자막 오류가 많은 경우 Whisper STT로 재추출을 고려하세요\n")
        f.write("  3. 텍스트 품질이 확인되면 주제별 분류 작업을 시작하세요\n")
        f.write("  4. 분류된 텍스트를 벡터DB에 임베딩하여 RAG 구축에 활용하세요\n")

    print(f"   ✅ 리포트 저장: {report_path}")


# =====================================================================
# 메인 실행
# =====================================================================
def main():
    print("\n")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  홍성남 신부님 유튜브 채널 - 자막/텍스트 일괄 추출기    ║")
    print("║  채널: 톡쏘는 영성심리                                  ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    # 사전 확인
    if not check_ytdlp():
        sys.exit(1)

    setup_directories()

    # STEP 1: 영상 목록 수집
    videos = fetch_video_list()
    if not videos:
        print("❌ 영상을 찾을 수 없습니다. 채널 URL을 확인하세요.")
        sys.exit(1)

    # STEP 2: 자막 다운로드
    success_count, fail_list = download_subtitles(videos)

    # STEP 3: 텍스트 변환
    converted, total_chars, all_texts = convert_subtitles_to_text(videos)

    # STEP 4: 리포트 생성
    generate_report(videos, success_count, fail_list, converted, total_chars)

    # 최종 요약
    print("\n")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║                    ✅ 작업 완료!                        ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║  📁 출력 폴더: {str(OUTPUT_DIR):<41} ║")
    print(f"║  📋 영상 수: {len(videos)}개                                     ║")
    print(f"║  📝 텍스트 추출: {converted}개                                  ║")
    print(f"║  📄 총 분량: {total_chars:,}자                              ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()


if __name__ == "__main__":
    main()
