"""
벡터DB(metadata.json) 안의 실제 문서 텍스트에서 키워드를 검색하는 스크립트.

사용법 (D:\\유튜브자막추출\\vectordb_홍성남신부 폴더에서 실행):
    python search_vectordb.py "분노 관리"
    python search_vectordb.py "고성방가"
    python search_vectordb.py "일본의 모리 박사"

- 검색어는 큰따옴표로 감싸서 넣어주세요 (띄어쓰기 포함 검색 가능).
- metadata.json 안의 'documents'(실제 청크 텍스트)를 대상으로 검색합니다.
- 같은 파일(filename)에서 여러 청크가 매칭되면, 파일당 1번만 요약해서 보여줍니다.
"""

import json
import sys
from pathlib import Path

METADATA_FILE = Path("metadata.json")


def main():
    if len(sys.argv) < 2:
        print("사용법: python search_vectordb.py \"검색어\"")
        sys.exit(1)

    query = sys.argv[1].strip()
    if not query:
        print("검색어가 비어있습니다.")
        sys.exit(1)

    if not METADATA_FILE.exists():
        print(f"오류: {METADATA_FILE.resolve()} 파일을 찾을 수 없습니다.")
        print("이 스크립트는 vectordb_홍성남신부 폴더 안에서 실행해야 합니다.")
        sys.exit(1)

    print(f"metadata.json 로딩 중... (파일 크기가 크면 몇 초 걸릴 수 있어요)")
    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    metadata_list = data.get("metadata", [])
    documents_list = data.get("documents", [])

    total = min(len(metadata_list), len(documents_list))
    print(f"전체 벡터 수: {total}개")
    print(f"'{query}' 검색 중...\n")

    query_lower = query.lower()
    matched_files = {}  # filename -> {title, source_type, count, first_snippet}

    for i in range(total):
        doc_text = documents_list[i] or ""
        if query_lower in doc_text.lower():
            meta = metadata_list[i]
            filename = meta.get("filename", "(파일명 없음)")
            title = meta.get("title", "(제목 없음)")
            source_type = meta.get("source_type", "?")
            url = meta.get("url", "")

            if filename not in matched_files:
                # 검색어 앞뒤로 스니펫 추출
                idx = doc_text.lower().find(query_lower)
                start = max(0, idx - 40)
                end = min(len(doc_text), idx + len(query) + 60)
                snippet = doc_text[start:end].replace("\n", " ")

                matched_files[filename] = {
                    "title": title,
                    "source_type": source_type,
                    "url": url,
                    "count": 0,
                    "snippet": snippet,
                }
            matched_files[filename]["count"] += 1

    if not matched_files:
        print(f"❌ '{query}'가 포함된 문서를 벡터DB에서 찾지 못했습니다.")
        print("   → 이 텍스트는 아직 벡터DB에 들어가 있지 않은 것 같습니다.")
        return

    print(f"✅ 총 {len(matched_files)}개 파일에서 '{query}' 발견:\n")
    print("=" * 70)
    for filename, info in matched_files.items():
        print(f"제목      : {info['title']}")
        print(f"파일명    : {filename}")
        print(f"소스 타입 : {info['source_type']}")
        print(f"URL       : {info['url']}")
        print(f"매칭 청크 : {info['count']}개")
        print(f"미리보기  : ...{info['snippet']}...")
        print("-" * 70)


if __name__ == "__main__":
    main()
