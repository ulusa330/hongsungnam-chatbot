#!/usr/bin/env python3
"""
====================================================================
홍성남 신부님 - 통합 벡터DB 구축기 (v3)
====================================================================
[변경사항 v3]
  - 유튜브 자막 + 신문 칼럼 데이터를 통합하여 벡터DB 구축
  - 칼럼 파일 파싱 함수 추가
  - 데이터 소스 구분 (youtube / column)

[사용법]
  1. 필요한 패키지 설치:
     pip install openai tiktoken numpy
  2. .env 파일에 OpenAI API 키 설정:
     OPENAI_API_KEY=sk-xxxxxxxx
  3. 실행:
     python build_vectordb.py
[구조]
  - 텍스트를 적절한 크기로 분할 (chunking)
  - OpenAI text-embedding-3-small 모델로 임베딩
  - numpy + JSON으로 벡터 저장 (ChromaDB 대체)
  - 중단 시 이어하기 지원
[출력]
  - vectordb_홍성남신부/embeddings.npz    (벡터 데이터)
  - vectordb_홍성남신부/metadata.json     (메타데이터)
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
BASE_DIR = Path("./output_홍성남신부_자막추출")
INPUT_DIR = BASE_DIR / "15_전체교정_4omini"

# 칼럼 데이터 경로 (3개 신문사)
COLUMN_DIR = Path("./output_칼럼수집")
COLUMN_SUBDIRS = ["01_중앙일보", "02_가톨릭신문", "03_경향신문"]

VECTORDB_DIR = Path("./vectordb_홍성남신부")
PROGRESS_FILE = VECTORDB_DIR / "_progress.json"
EMBEDDINGS_FILE = VECTORDB_DIR / "embeddings.npz"
METADATA_FILE = VECTORDB_DIR / "metadata.json"

# 임베딩 설정
EMBEDDING_MODEL = "text-embedding-3-small"
CHUNK_SIZE = 400       # 청크 최대 크기 (글자수 ~800토큰)
CHUNK_OVERLAP = 50     # 청크 간 겹침 글자수
MAX_TOKENS_PER_CHUNK = 7000

# 배치 설정
BATCH_SIZE = 20
API_DELAY = 0.3


def setup():
    """환경 확인 및 설정"""
    VECTORDB_DIR.mkdir(parents=True, exist_ok=True)
    missing = []
    try:
        import openai
    except ImportError:
        missing.append("openai")
    try:
        import tiktoken
    except ImportError:
        missing.append("tiktoken")
    try:
        import numpy
    except ImportError:
        missing.append("numpy")
    if missing:
        print(f"  필요한 패키지를 설치하세요: {', '.join(missing)}")
        print(f"   pip install {' '.join(missing)}")
        return False
    if not API_KEY:
        print("  API 키가 설정되지 않았습니다.")
        print("   .env 파일에 OPENAI_API_KEY를 설정하세요.")
        return False
    return True


def parse_youtube_file(filepath):
    """유튜브 자막 교정 파일 파싱"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            content = f.read()

    title = "제목 없음"
    upload_date = ""
    vid = ""
    url = ""

    for line in content.split('\n')[:10]:
        if line.startswith('# 제목:'):
            title = line.replace('# 제목:', '').strip()
        elif line.startswith('# 업로드:'):
            upload_date = line.replace('# 업로드:', '').strip()
        elif line.startswith('# 영상 ID:'):
            vid = line.replace('# 영상 ID:', '').strip()
        elif line.startswith('# URL:'):
            url = line.replace('# URL:', '').strip()

    body_lines = []
    past_header = False
    for line in content.split('\n'):
        if '=====' in line:
            past_header = True
            continue
        if past_header:
            body_lines.append(line)
    body = '\n'.join(body_lines).strip()
    if not body:
        body = content.strip()

    return {
        'title': title,
        'upload_date': upload_date,
        'video_id': vid,
        'url': url or (f"https://youtube.com/watch?v={vid}" if vid else ""),
        'body': body,
        'filename': filepath.name,
        'source_type': 'youtube',
    }


def parse_column_file(filepath):
    """신문 칼럼 파일 파싱"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            content = f.read()

    title = "제목 없음"
    source = ""
    date_str = ""
    url = ""

    for line in content.split('\n')[:10]:
        if line.startswith('제목:'):
            title = line.replace('제목:', '').strip()
        elif line.startswith('출처:'):
            source = line.replace('출처:', '').strip()
        elif line.startswith('날짜:'):
            date_str = line.replace('날짜:', '').strip()
        elif line.startswith('URL:'):
            url = line.replace('URL:', '').strip()

    # 본문 추출 (구분선 이후)
    body_lines = []
    past_header = False
    for line in content.split('\n'):
        if '=====' in line or '====' in line:
            past_header = True
            continue
        if past_header:
            body_lines.append(line)
    body = '\n'.join(body_lines).strip()
    if not body:
        body = content.strip()

    return {
        'title': title,
        'upload_date': date_str,
        'video_id': '',
        'url': url,
        'body': body,
        'filename': filepath.name,
        'source_type': 'column',
        'newspaper': source,
    }


def count_tokens(text):
    """tiktoken으로 토큰 수 계산"""
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """텍스트를 청크로 분할"""
    if len(text) <= chunk_size:
        return [text]

    sentences = re.split(r'(?<=[.?!])\s+', text)
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if len(sentence) > chunk_size:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
            for i in range(0, len(sentence), chunk_size):
                chunks.append(sentence[i:i + chunk_size].strip())
            continue

        if len(current_chunk) + len(sentence) <= chunk_size:
            current_chunk += (" " + sentence) if current_chunk else sentence
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            if overlap > 0 and current_chunk:
                overlap_text = current_chunk[-overlap:]
                space_idx = overlap_text.find(' ')
                if space_idx > 0:
                    overlap_text = overlap_text[space_idx:].strip()
                current_chunk = overlap_text + " " + sentence
            else:
                current_chunk = sentence

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    # 토큰 안전 검사
    safe_chunks = []
    for chunk in chunks:
        tokens = count_tokens(chunk)
        if tokens > MAX_TOKENS_PER_CHUNK:
            mid = len(chunk) // 2
            space_idx = chunk.find(' ', mid)
            if space_idx > 0:
                safe_chunks.append(chunk[:space_idx].strip())
                safe_chunks.append(chunk[space_idx:].strip())
            else:
                safe_chunks.append(chunk[:mid].strip())
                safe_chunks.append(chunk[mid:].strip())
        else:
            safe_chunks.append(chunk)

    return safe_chunks


def load_progress():
    """진행 상태 로드"""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"completed_files": [], "total_chunks": 0}


def save_progress(progress):
    """진행 상태 저장"""
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def load_existing_data():
    """기존 데이터 로드"""
    embeddings_list = []
    metadata_list = []
    documents_list = []
    if EMBEDDINGS_FILE.exists() and METADATA_FILE.exists():
        data = np.load(EMBEDDINGS_FILE)
        embeddings_list = data['embeddings'].tolist()
        with open(METADATA_FILE, 'r', encoding='utf-8') as f:
            saved = json.load(f)
            metadata_list = saved.get('metadata', [])
            documents_list = saved.get('documents', [])
    return embeddings_list, metadata_list, documents_list


def save_data(embeddings_list, metadata_list, documents_list):
    """데이터 저장"""
    if embeddings_list:
        np.savez_compressed(
            EMBEDDINGS_FILE,
            embeddings=np.array(embeddings_list, dtype=np.float32)
        )
        with open(METADATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': metadata_list,
                'documents': documents_list,
                'count': len(embeddings_list),
                'updated': datetime.now().strftime('%Y-%m-%d %H:%M'),
            }, f, ensure_ascii=False)


def embed_batch(client, texts):
    """배치 임베딩 (실패 시 개별 재시도)"""
    try:
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=texts,
        )
        return [item.embedding for item in response.data]
    except Exception as e:
        print(f"\n      배치 임베딩 실패, 개별 재시도 중...")
        results = []
        for text in texts:
            try:
                resp = client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=[text],
                )
                results.append(resp.data[0].embedding)
                time.sleep(0.2)
            except Exception as e2:
                print(f"\n      개별도 실패 (토큰: {count_tokens(text)})")
                results.append(None)
        return results


def collect_all_files():
    """유튜브 자막 + 칼럼 파일 모두 수집"""
    files = []

    # 1. 유튜브 자막 파일
    if INPUT_DIR.exists():
        youtube_files = sorted(INPUT_DIR.glob("*.txt"))
        for f in youtube_files:
            files.append(('youtube', f))
        print(f"  📹 유튜브 자막 파일: {len(youtube_files)}개")
    else:
        print(f"  ⚠ 유튜브 자막 폴더 없음: {INPUT_DIR}")

    # 2. 칼럼 파일 (3개 신문사)
    column_count = 0
    if COLUMN_DIR.exists():
        for subdir_name in COLUMN_SUBDIRS:
            subdir = COLUMN_DIR / subdir_name
            if subdir.exists():
                col_files = sorted(subdir.glob("*.txt"))
                for f in col_files:
                    files.append(('column', f))
                column_count += len(col_files)
                print(f"  📰 {subdir_name}: {len(col_files)}개")
            else:
                print(f"  ℹ {subdir_name} 폴더 없음 (건너뜀)")
        print(f"  📰 칼럼 파일 합계: {column_count}개")
    else:
        print(f"  ℹ 칼럼 폴더 없음: {COLUMN_DIR} (건너뜀)")

    print(f"  📊 전체 파일 합계: {len(files)}개")
    return files


def main():
    print("\n")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  홍성남 신부님 - 통합 벡터DB 구축기 (v3)              ║")
    print("║  유튜브 자막 + 신문 칼럼 통합                          ║")
    print("║  numpy + JSON (ChromaDB 대체)                          ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    if not setup():
        return

    import openai
    client = openai.OpenAI(api_key=API_KEY)

    # 기존 데이터 로드
    embeddings_list, metadata_list, documents_list = load_existing_data()
    print(f"  벡터DB 경로: {VECTORDB_DIR}")
    print(f"  기존 벡터 수: {len(embeddings_list)}\n")

    # 전체 파일 수집
    print("  [데이터 소스 확인]")
    all_files = collect_all_files()
    total_files = len(all_files)

    if total_files == 0:
        print(f"\n  처리할 파일이 없습니다.")
        return

    # 진행 상태 로드
    progress = load_progress()
    completed = set(progress["completed_files"])

    # 파일 키 생성 (소스타입_파일명으로 중복 방지)
    remaining = []
    for source_type, f in all_files:
        file_key = f"{source_type}_{f.name}"
        if file_key not in completed:
            remaining.append((source_type, f, file_key))

    print(f"\n  전체 파일 수: {total_files}개")
    print(f"  완료된 파일: {len(completed)}개")
    print(f"  남은 파일 수: {len(remaining)}개")
    print(f"\n{'━' * 50}\n")

    if not remaining:
        print("  모든 파일이 이미 처리되었습니다!")
        print(f"  현재 벡터 수: {len(embeddings_list)}")
        return

    stats = {"files": 0, "chunks": 0, "errors": 0, "youtube": 0, "column": 0}
    start_time = time.time()

    # 배치 버퍼
    batch_texts = []
    batch_metas = []

    for file_idx, (source_type, filepath, file_key) in enumerate(remaining, 1):
        file_progress = f"[{len(completed) + file_idx}/{total_files}]"
        source_icon = "📹" if source_type == 'youtube' else "📰"
        print(f"   {file_progress} {source_icon} {filepath.name[:50]}...", end="", flush=True)

        # 파일 파싱
        if source_type == 'youtube':
            data = parse_youtube_file(filepath)
            stats["youtube"] += 1
        else:
            data = parse_column_file(filepath)
            stats["column"] += 1

        if not data['body'] or len(data['body']) < 30:
            print(" 건너뜀 (내용 부족)")
            completed.add(file_key)
            continue

        chunks = chunk_text(data['body'])

        for chunk_idx, chunk in enumerate(chunks):
            meta = {
                "title": data['title'],
                "upload_date": data['upload_date'],
                "video_id": data.get('video_id', ''),
                "url": data['url'],
                "filename": data['filename'],
                "chunk_index": chunk_idx,
                "total_chunks": len(chunks),
                "source_type": data['source_type'],
            }
            # 칼럼인 경우 신문사 정보 추가
            if 'newspaper' in data:
                meta['newspaper'] = data['newspaper']

            batch_texts.append(chunk)
            batch_metas.append(meta)

        stats["chunks"] += len(chunks)

        # 배치가 찼으면 임베딩
        if len(batch_texts) >= BATCH_SIZE:
            embs = embed_batch(client, batch_texts)
            for emb, meta, text in zip(embs, batch_metas, batch_texts):
                if emb is not None:
                    embeddings_list.append(emb)
                    metadata_list.append(meta)
                    documents_list.append(text)
                else:
                    stats["errors"] += 1
            batch_texts = []
            batch_metas = []
            time.sleep(API_DELAY)

        completed.add(file_key)
        stats["files"] += 1
        print(f" OK({len(chunks)}청크)")

        # 100개마다 중간 저장
        if file_idx % 100 == 0:
            if batch_texts:
                embs = embed_batch(client, batch_texts)
                for emb, meta, text in zip(embs, batch_metas, batch_texts):
                    if emb is not None:
                        embeddings_list.append(emb)
                        metadata_list.append(meta)
                        documents_list.append(text)
                batch_texts = []
                batch_metas = []

            save_data(embeddings_list, metadata_list, documents_list)
            progress["completed_files"] = list(completed)
            progress["total_chunks"] = stats["chunks"]
            save_progress(progress)
            elapsed = time.time() - start_time
            print(f"\n   💾 중간 저장 완료 ({stats['files']}파일, {len(embeddings_list)}벡터, {elapsed/60:.1f}분)\n")

    # 남은 배치 처리
    if batch_texts:
        embs = embed_batch(client, batch_texts)
        for emb, meta, text in zip(embs, batch_metas, batch_texts):
            if emb is not None:
                embeddings_list.append(emb)
                metadata_list.append(meta)
                documents_list.append(text)
            else:
                stats["errors"] += 1

    # 최종 저장
    save_data(embeddings_list, metadata_list, documents_list)
    progress["completed_files"] = list(completed)
    progress["total_chunks"] = stats["chunks"]
    save_progress(progress)

    elapsed = time.time() - start_time

    print(f"\n")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  ✅ 벡터DB 구축 완료!                                  ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║  벡터DB: {VECTORDB_DIR}")
    print(f"║  처리 파일 수: {stats['files']}개")
    print(f"║    - 유튜브 자막: {stats['youtube']}개")
    print(f"║    - 신문 칼럼: {stats['column']}개")
    print(f"║  생성 청크 수: {stats['chunks']}개")
    print(f"║  전체 DB 벡터 수: {len(embeddings_list)}")
    print(f"║  소요 시간: {elapsed/60:.1f}분")
    print(f"║  예상 비용: ${stats['chunks'] * 0.00002:.2f}")
    if stats["errors"]:
        print(f"║  오류 건수: {stats['errors']}개")
    print("╚══════════════════════════════════════════════════════════╝")
    print()
    print("  📌 다음 단계:")
    print("     streamlit run chatbot_demo.py")
    print()


if __name__ == "__main__":
    main()
