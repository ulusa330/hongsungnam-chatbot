#!/usr/bin/env python3
"""
====================================================================
홍성남 신부님 - 통합 벡터DB 구축기 (v4)
====================================================================
[변경사항 v4]
  - 도서 데이터 추가 (홍성남저서 / 성경묵상 / 영성자료)
  - source_type: youtube / column / book_hong / book_bible / book_spiritual

[사용법]
  python build_vectordb.py

[데이터 소스]
  - 유튜브 자막: output_홍성남신부_자막추출/15_전체교정_4omini/
  - 신문 칼럼:   output_칼럼수집/
  - 도서:        output_도서텍스트/
====================================================================
"""
import os
import re
import time
import json
import numpy as np
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
API_KEY = os.environ.get("OPENAI_API_KEY", "")

# 경로 설정
BASE_DIR   = Path("./output_홍성남신부_자막추출")
INPUT_DIR  = BASE_DIR / "15_전체교정_4omini"

COLUMN_DIR     = Path("./output_칼럼수집")
COLUMN_SUBDIRS = ["01_중앙일보", "02_가톨릭신문", "03_경향신문"]

# ★ 도서 경로 추가
BOOK_DIR     = Path("./output_도서텍스트")
BOOK_SUBDIRS = {
    "01_홍성남저서": "book_hong",
    "02_성경묵상":   "book_bible",
    "03_영성자료":   "book_spiritual",
}

VECTORDB_DIR   = Path("./vectordb_홍성남신부")
PROGRESS_FILE  = VECTORDB_DIR / "_progress.json"
EMBEDDINGS_FILE = VECTORDB_DIR / "embeddings.npz"
METADATA_FILE  = VECTORDB_DIR / "metadata.json"

EMBEDDING_MODEL      = "text-embedding-3-small"
CHUNK_SIZE           = 400
CHUNK_OVERLAP        = 50
MAX_TOKENS_PER_CHUNK = 7000
BATCH_SIZE           = 20
API_DELAY            = 1.3


def setup():
    VECTORDB_DIR.mkdir(parents=True, exist_ok=True)
    missing = []
    try: import openai
    except ImportError: missing.append("openai")
    try: import tiktoken
    except ImportError: missing.append("tiktoken")
    try: import numpy
    except ImportError: missing.append("numpy")
    if missing:
        print(f"  필요한 패키지를 설치하세요: pip install {' '.join(missing)}")
        return False
    if not API_KEY:
        print("  .env 파일에 OPENAI_API_KEY를 설정하세요.")
        return False
    return True


def parse_youtube_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f: content = f.read()
    except UnicodeDecodeError:
        with open(filepath, 'r', encoding='utf-8-sig') as f: content = f.read()

    title, upload_date, vid, url = "제목 없음", "", "", ""
    for line in content.split('\n')[:10]:
        if line.startswith('# 제목:'): title = line.replace('# 제목:', '').strip()
        elif line.startswith('# 업로드:'): upload_date = line.replace('# 업로드:', '').strip()
        elif line.startswith('# 영상 ID:'): vid = line.replace('# 영상 ID:', '').strip()
        elif line.startswith('# URL:'): url = line.replace('# URL:', '').strip()

    body_lines, past_header = [], False
    for line in content.split('\n'):
        if '=====' in line: past_header = True; continue
        if past_header: body_lines.append(line)
    body = '\n'.join(body_lines).strip() or content.strip()

    return {'title': title, 'upload_date': upload_date, 'video_id': vid,
            'url': url or (f"https://youtube.com/watch?v={vid}" if vid else ""),
            'body': body, 'filename': filepath.name, 'source_type': 'youtube'}


def parse_column_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f: content = f.read()
    except UnicodeDecodeError:
        with open(filepath, 'r', encoding='utf-8-sig') as f: content = f.read()

    title, source, date_str, url = "제목 없음", "", "", ""
    for line in content.split('\n')[:10]:
        if line.startswith('제목:'): title = line.replace('제목:', '').strip()
        elif line.startswith('출처:'): source = line.replace('출처:', '').strip()
        elif line.startswith('날짜:'): date_str = line.replace('날짜:', '').strip()
        elif line.startswith('URL:'): url = line.replace('URL:', '').strip()

    body_lines, past_header = [], False
    for line in content.split('\n'):
        if '=====' in line or '====' in line: past_header = True; continue
        if past_header: body_lines.append(line)
    body = '\n'.join(body_lines).strip() or content.strip()

    return {'title': title, 'upload_date': date_str, 'video_id': '', 'url': url,
            'body': body, 'filename': filepath.name, 'source_type': 'column', 'newspaper': source}


def parse_book_file(filepath, source_type):
    """도서 TXT 파일 파싱"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f: content = f.read()
    except UnicodeDecodeError:
        with open(filepath, 'r', encoding='utf-8-sig') as f: content = f.read()

    # 첫 줄에서 메타데이터 추출 ([출처: ...] [파일: ...] [카테고리: ...])
    title = filepath.stem  # 기본값: 파일명
    first_line = content.split('\n')[0] if content else ''

    m = re.search(r'\[파일:\s*(.+?)\]', first_line)
    if m: title = m.group(1).strip()

    # 본문 (첫 줄 제외)
    lines = content.split('\n')
    body = '\n'.join(lines[2:]).strip() if len(lines) > 2 else content.strip()
    if not body: body = content.strip()

    return {'title': title, 'upload_date': '', 'video_id': '', 'url': '',
            'body': body, 'filename': filepath.name, 'source_type': source_type}


def count_tokens(text):
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    if len(text) <= chunk_size: return [text]
    sentences = re.split(r'(?<=[.?!])\s+', text)
    chunks, current_chunk = [], ""
    for sentence in sentences:
        if len(sentence) > chunk_size:
            if current_chunk: chunks.append(current_chunk.strip()); current_chunk = ""
            for i in range(0, len(sentence), chunk_size): chunks.append(sentence[i:i+chunk_size].strip())
            continue
        if len(current_chunk) + len(sentence) <= chunk_size:
            current_chunk += (" " + sentence) if current_chunk else sentence
        else:
            if current_chunk: chunks.append(current_chunk.strip())
            if overlap > 0 and current_chunk:
                overlap_text = current_chunk[-overlap:]
                space_idx = overlap_text.find(' ')
                if space_idx > 0: overlap_text = overlap_text[space_idx:].strip()
                current_chunk = overlap_text + " " + sentence
            else: current_chunk = sentence
    if current_chunk.strip(): chunks.append(current_chunk.strip())

    safe_chunks = []
    for chunk in chunks:
        if count_tokens(chunk) > MAX_TOKENS_PER_CHUNK:
            mid = len(chunk) // 2
            space_idx = chunk.find(' ', mid)
            if space_idx > 0:
                safe_chunks.append(chunk[:space_idx].strip())
                safe_chunks.append(chunk[space_idx:].strip())
            else:
                safe_chunks.append(chunk[:mid].strip())
                safe_chunks.append(chunk[mid:].strip())
        else: safe_chunks.append(chunk)
    return safe_chunks


def load_progress():
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    return {"completed_files": [], "total_chunks": 0}


def save_progress(progress):
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def load_existing_data():
    embeddings_list, metadata_list, documents_list = [], [], []
    if EMBEDDINGS_FILE.exists() and METADATA_FILE.exists():
        data = np.load(EMBEDDINGS_FILE)
        embeddings_list = data['embeddings'].tolist()
        with open(METADATA_FILE, 'r', encoding='utf-8') as f:
            saved = json.load(f)
            metadata_list = saved.get('metadata', [])
            documents_list = saved.get('documents', [])
    return embeddings_list, metadata_list, documents_list


def save_data(embeddings_list, metadata_list, documents_list):
    if embeddings_list:
        np.savez_compressed(EMBEDDINGS_FILE, embeddings=np.array(embeddings_list, dtype=np.float32))
        with open(METADATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({'metadata': metadata_list, 'documents': documents_list,
                       'count': len(embeddings_list),
                       'updated': datetime.now().strftime('%Y-%m-%d %H:%M')}, f, ensure_ascii=False)


def embed_batch(client, texts):
    try:
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
        return [item.embedding for item in response.data]
    except Exception:
        print(f"\n      배치 임베딩 실패, 개별 재시도 중...")
        results = []
        for text in texts:
            try:
                resp = client.embeddings.create(model=EMBEDDING_MODEL, input=[text])
                results.append(resp.data[0].embedding)
                time.sleep(0.2)
            except Exception as e2:
                print(f"\n      개별도 실패 (토큰: {count_tokens(text)}) 오류: {e2}")
                results.append(None)
        return results

def collect_all_files():
    """유튜브 자막 + 칼럼 + 도서 파일 모두 수집"""
    files = []

    # 1. 유튜브 자막
    if INPUT_DIR.exists():
        youtube_files = sorted(INPUT_DIR.glob("*.txt"))
        for f in youtube_files: files.append(('youtube', f))
        print(f"  📹 유튜브 자막: {len(youtube_files)}개")
    else:
        print(f"  ⚠ 유튜브 자막 폴더 없음")

    # 2. 신문 칼럼
    column_count = 0
    if COLUMN_DIR.exists():
        for subdir_name in COLUMN_SUBDIRS:
            subdir = COLUMN_DIR / subdir_name
            if subdir.exists():
                col_files = sorted(subdir.glob("*.txt"))
                for f in col_files: files.append(('column', f))
                column_count += len(col_files)
                print(f"  📰 {subdir_name}: {len(col_files)}개")
        print(f"  📰 칼럼 합계: {column_count}개")

    # 3. ★ 도서 파일
    book_count = 0
    if BOOK_DIR.exists():
        for subdir_name, source_type in BOOK_SUBDIRS.items():
            subdir = BOOK_DIR / subdir_name
            if subdir.exists():
                book_files = sorted(subdir.glob("*.txt"))
                for f in book_files: files.append((source_type, f))
                book_count += len(book_files)
                print(f"  📚 {subdir_name}: {len(book_files)}개")
        print(f"  📚 도서 합계: {book_count}개")
    else:
        print(f"  ℹ 도서 폴더 없음: {BOOK_DIR} (건너뜀)")

    print(f"  📊 전체 합계: {len(files)}개")
    return files


def main():
    print("\n")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  홍성남 신부님 - 통합 벡터DB 구축기 (v4)              ║")
    print("║  유튜브 + 칼럼 + 도서 통합                             ║")
    print("╚══════════════════════════════════════════════════════════╝\n")

    if not setup(): return

    import openai
    client = openai.OpenAI(api_key=API_KEY)

    embeddings_list, metadata_list, documents_list = load_existing_data()
    print(f"  기존 벡터 수: {len(embeddings_list)}\n")

    print("  [데이터 소스 확인]")
    all_files = collect_all_files()
    total_files = len(all_files)
    if total_files == 0:
        print("  처리할 파일이 없습니다."); return

    progress = load_progress()
    completed = set(progress["completed_files"])

    remaining = []
    for source_type, f in all_files:
        file_key = f"{source_type}_{f.name}"
        if file_key not in completed:
            remaining.append((source_type, f, file_key))

    print(f"\n  전체: {total_files}개 | 완료: {len(completed)}개 | 남음: {len(remaining)}개")
    print(f"\n{'━'*50}\n")

    if not remaining:
        print(f"  모든 파일 처리 완료! 현재 벡터 수: {len(embeddings_list)}"); return

    stats = {"files": 0, "chunks": 0, "errors": 0, "youtube": 0, "column": 0, "book": 0}
    start_time = time.time()
    batch_texts, batch_metas = [], []

    for file_idx, (source_type, filepath, file_key) in enumerate(remaining, 1):
        file_progress = f"[{len(completed)+file_idx}/{total_files}]"
        icon = "📹" if source_type == 'youtube' else ("📰" if source_type == 'column' else "📚")
        print(f"   {file_progress} {icon} {filepath.name[:50]}...", end="", flush=True)

        # 파싱
        if source_type == 'youtube':
            data = parse_youtube_file(filepath); stats["youtube"] += 1
        elif source_type == 'column':
            data = parse_column_file(filepath); stats["column"] += 1
        else:
            data = parse_book_file(filepath, source_type); stats["book"] += 1

        if not data['body'] or len(data['body']) < 30:
            print(" 건너뜀 (내용 부족)"); completed.add(file_key); continue

        chunks = chunk_text(data['body'])

        for chunk_idx, chunk in enumerate(chunks):
            meta = {
                "title": data['title'], "upload_date": data['upload_date'],
                "video_id": data.get('video_id', ''), "url": data['url'],
                "filename": data['filename'], "chunk_index": chunk_idx,
                "total_chunks": len(chunks), "source_type": data['source_type'],
            }
            if 'newspaper' in data: meta['newspaper'] = data['newspaper']
            batch_texts.append(chunk)
            batch_metas.append(meta)

        stats["chunks"] += len(chunks)

        if len(batch_texts) >= BATCH_SIZE:
            embs = embed_batch(client, batch_texts)
            for emb, meta, text in zip(embs, batch_metas, batch_texts):
                if emb is not None:
                    embeddings_list.append(emb); metadata_list.append(meta); documents_list.append(text)
                else: stats["errors"] += 1
            batch_texts, batch_metas = [], []
            time.sleep(API_DELAY)

        completed.add(file_key)
        stats["files"] += 1
        print(f" OK({len(chunks)}청크)")

        if file_idx % 100 == 0:
            if batch_texts:
                embs = embed_batch(client, batch_texts)
                for emb, meta, text in zip(embs, batch_metas, batch_texts):
                    if emb is not None:
                        embeddings_list.append(emb); metadata_list.append(meta); documents_list.append(text)
                batch_texts, batch_metas = [], []
            save_data(embeddings_list, metadata_list, documents_list)
            progress["completed_files"] = list(completed)
            save_progress(progress)
            elapsed = time.time() - start_time
            print(f"\n   💾 중간 저장 ({stats['files']}파일, {len(embeddings_list)}벡터, {elapsed/60:.1f}분)\n")

    if batch_texts:
        embs = embed_batch(client, batch_texts)
        for emb, meta, text in zip(embs, batch_metas, batch_texts):
            if emb is not None:
                embeddings_list.append(emb); metadata_list.append(meta); documents_list.append(text)
            else: stats["errors"] += 1

    save_data(embeddings_list, metadata_list, documents_list)
    progress["completed_files"] = list(completed)
    save_progress(progress)
    elapsed = time.time() - start_time

    print(f"\n")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  ✅ 벡터DB 구축 완료!                                  ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║  처리 파일: {stats['files']}개")
    print(f"║    - 유튜브: {stats['youtube']}개")
    print(f"║    - 칼럼:   {stats['column']}개")
    print(f"║    - 도서:   {stats['book']}개")
    print(f"║  전체 벡터: {len(embeddings_list)}개")
    print(f"║  소요 시간: {elapsed/60:.1f}분")
    print(f"║  예상 비용: ${stats['chunks'] * 0.00002:.2f}")
    print("╚══════════════════════════════════════════════════════════╝\n")
    print("  📌 다음 단계: git add . && git commit -m 'VectorDB v4 업데이트' && git push\n")


if __name__ == "__main__":
    main()
