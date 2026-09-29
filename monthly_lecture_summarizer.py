#!/usr/bin/env python3
"""
====================================================================
홍성남 신부님 월특강 요약 스크립트 v2
====================================================================
[사용법]
  python monthly_lecture_summarizer.py

[파일 형식]
  신규: 2604_월특강.txt
  과거: [220122]제1부_행복에 대해서.srt
        [220122]제2부_행복에 대해서.srt  → 자동 합산
  저장 위치: input_월특강/ 폴더
====================================================================
"""
import os
import re
from pathlib import Path
from dotenv import load_dotenv
import openai

load_dotenv()

BASE_DIR   = Path(__file__).parent
INPUT_DIR  = BASE_DIR / "input_월특강"
OUTPUT_DIR = BASE_DIR / "output_월특강요약"
INPUT_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))


def extract_text(file_path: Path) -> str:
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        content = f.read()
    if file_path.suffix.lower() == '.srt':
        lines = content.strip().split('\n')
        text_lines = []
        for line in lines:
            line = line.strip()
            if not line or line.isdigit() or '-->' in line:
                continue
            text_lines.append(line)
        return ' '.join(text_lines)
    return content.strip()


def group_files(all_files):
    groups = {}
    for f in all_files:
        name = f.stem

        # 신규 형식: 2603_월특강
        m = re.match(r'^(\d{4})_월특강', name)
        if m:
            key = m.group(1)
            yy, mm = key[:2], key[2:]
            date_str = f"20{yy}년 {int(mm)}월"
            if key not in groups:
                groups[key] = {"key": key, "date_str": date_str, "title": "월특강", "files": []}
            groups[key]["files"].append(f)
            continue

        # 과거 형식: [220122]제1부_행복에 대해서
        m = re.match(r'^\[?(\d{6})\]?(?:제\d+부_?)?(.+)?', name)
        if m:
            key = m.group(1)
            title = re.sub(r'^제\d+부_?', '', (m.group(2) or "월특강")).strip() or "월특강"
            yy, mm, dd = key[:2], key[2:4], key[4:]
            date_str = f"20{yy}년 {int(mm)}월 {int(dd)}일"
            if key not in groups:
                groups[key] = {"key": key, "date_str": date_str, "title": title, "files": []}
            groups[key]["files"].append(f)

    for key in groups:
        groups[key]["files"].sort(key=lambda f: f.name)
    return groups


def summarize_lecture(text, date_str, title):
    chunk_size = 8000
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
    print(f"  총 {len(text):,}자 → {len(chunks)}개 청크")

    chunk_summaries = []
    for i, chunk in enumerate(chunks):
        print(f"  청크 {i+1}/{len(chunks)} 요약 중...")
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "홍성남 마태오 신부님의 강의 내용을 핵심 위주로 요약해 주세요."},
                {"role": "user", "content": f"{date_str} 영성심리특강 \"{title}\" 일부입니다.\n\n{chunk}\n\n핵심 포인트 3~5개로 요약해 주세요."}
            ],
            temperature=0.3, max_tokens=1000,
        )
        chunk_summaries.append(resp.choices[0].message.content)

    print("  최종 요약 생성 중...")
    combined = "\n\n---\n\n".join(chunk_summaries)
    final = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "홍성남 마태오 신부님의 영성심리 강의를 신부님의 따뜻하고 직접적인 말투로 요약해 주세요."},
            {"role": "user", "content": (
                f"{date_str} 영성심리특강 \"{title}\" 요약입니다.\n\n{combined}\n\n"
                "아래 형식으로 전체 요약 작성:\n"
                "1. 이번 강의 주제 (한 줄)\n"
                "2. 핵심 메시지 3가지\n"
                "3. 주요 내용 요약 (500자 내외)\n"
                "4. 신부님의 핵심 말씀 (인상적인 문장 2~3개)\n"
                "5. 실천 포인트"
            )}
        ],
        temperature=0.4, max_tokens=2000,
    )
    return final.choices[0].message.content


def save_md(summary, key, date_str, title, file_count):
    output_path = OUTPUT_DIR / f"{key}_월특강_요약.md"
    part_note = f" ({file_count}개 영상 통합 요약)" if file_count > 1 else ""
    content = f"""# 홍성남 신부님 {date_str} 영성심리특강 요약
## {title}{part_note}

> 출처: 홍성남 신부님 월 정기특강
> 채널: https://youtube.com/@fr.hongsungnam

---

{summary}

---
*본 요약은 AI가 자동 생성한 내용입니다.*
"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  저장: {output_path.name}")


def main():
    print("=" * 60)
    print("홍성남 신부님 월특강 요약 스크립트 v2")
    print("=" * 60)

    all_files = list(INPUT_DIR.glob("*.srt")) + list(INPUT_DIR.glob("*.txt"))
    if not all_files:
        print(f"\n⚠️  {INPUT_DIR} 폴더에 파일이 없습니다.")
        return

    groups = group_files(all_files)
    print(f"\n총 {len(all_files)}개 파일 → {len(groups)}개 강의 감지\n")

    for key, group in sorted(groups.items()):
        date_str = group["date_str"]
        title    = group["title"]
        files    = group["files"]

        print(f"처리 중: {date_str} - {title}")
        if len(files) > 1:
            print(f"  {len(files)}개 파일 합산: {[f.name for f in files]}")
        print("-" * 40)

        output_path = OUTPUT_DIR / f"{key}_월특강_요약.md"
        if output_path.exists():
            print(f"  이미 존재 → 건너뜀\n")
            continue

        full_text = ""
        for i, f in enumerate(files):
            text = extract_text(f)
            full_text += (f"\n\n[제{i+1}부]\n\n" if len(files) > 1 else "") + text
            print(f"  {f.name}: {len(text):,}자")

        if len(full_text) < 100:
            print("  ⚠️  텍스트 너무 짧음. 파일 확인 필요.\n")
            continue

        summary = summarize_lecture(full_text, date_str, title)
        save_md(summary, key, date_str, title, len(files))
        print(f"  ✅ 완료!\n")

    print("=" * 60)
    print(f"전체 완료! 저장 위치: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
