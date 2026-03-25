#!/usr/bin/env python3
"""
====================================================================
홍성남 신부님 신문 칼럼 수집기
====================================================================
3개 신문사(중앙일보, 가톨릭신문, 경향신문)에서
홍성남 신부님 관련 기사/칼럼을 수집하여 텍스트 파일로 저장합니다.

[사용법]
  1. 필요한 패키지 설치:
     pip install requests beautifulsoup4 lxml
  2. 실행:
     python column_collector.py
  3. 결과:
     output_칼럼수집/ 폴더에 신문사별로 텍스트 파일 저장
====================================================================
"""

import os
import re
import time
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, quote

# =====================================================================
# 설정
# =====================================================================
OUTPUT_DIR = Path("./output_칼럼수집")
PROGRESS_FILE = OUTPUT_DIR / "_progress.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}

# 요청 간 대기 시간 (초) — 서버 부하 방지
REQUEST_DELAY = 2

# =====================================================================
# 유틸리티 함수
# =====================================================================
def clean_text(text):
    """텍스트 정리: 불필요한 공백, 특수문자 제거"""
    if not text:
        return ""
    # 여러 공백을 하나로
    text = re.sub(r'\s+', ' ', text)
    # 앞뒤 공백 제거
    text = text.strip()
    return text

def clean_article_text(text):
    """기사 본문 정리"""
    if not text:
        return ""
    # 줄바꿈 정리
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 광고/관련기사 등 불필요한 줄 필터링
        skip_patterns = [
            '관련기사', '사진=', '▶', '©', '무단전재', '재배포금지',
            '구독신청', '좋아요', '공유하기', '카카오톡', '페이스북',
            '트위터', 'SNS', '댓글', '기자', '편집', '사진제공',
            '클릭하세요', '바로가기', '더보기', '광고', '후원',
            '저작권', 'All rights', 'Copyright'
        ]
        if any(pattern in line for pattern in skip_patterns):
            continue
        cleaned_lines.append(line)

    return '\n'.join(cleaned_lines)

def save_article(output_dir, source, title, date_str, url, content):
    """기사를 텍스트 파일로 저장"""
    # 파일명에 사용할 수 없는 문자 제거
    safe_title = re.sub(r'[\\/*?:"<>|]', '', title)[:50]
    safe_date = date_str.replace('-', '').replace('.', '').replace('/', '')[:8]

    filename = f"{safe_date}_{safe_title}.txt"
    filepath = output_dir / filename

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"=== 홍성남 신부님 칼럼/기사 ===\n")
        f.write(f"제목: {title}\n")
        f.write(f"출처: {source}\n")
        f.write(f"날짜: {date_str}\n")
        f.write(f"URL: {url}\n")
        f.write(f"수집일: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"{'='*50}\n\n")
        f.write(content)

    return filepath

def load_progress():
    """진행 상태 로드"""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"collected_urls": [], "stats": {}}

def save_progress(progress):
    """진행 상태 저장"""
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)

def fetch_page(url, retries=3):
    """페이지 가져오기 (재시도 포함)"""
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            response.encoding = response.apparent_encoding or 'utf-8'
            return response
        except Exception as e:
            if attempt < retries - 1:
                print(f"  ⚠ 재시도 {attempt+1}/{retries}: {e}")
                time.sleep(REQUEST_DELAY * 2)
            else:
                print(f"  ✗ 실패: {e}")
                return None

# =====================================================================
# 1. 중앙일보 수집
# =====================================================================
def collect_joongang(progress):
    """중앙일보 '홍성남 신부' 기사 수집"""
    source = "중앙일보"
    output_dir = OUTPUT_DIR / "01_중앙일보"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"📰 {source} 칼럼 수집 시작")
    print(f"{'='*60}")

    collected = 0
    skipped = 0
    page = 1
    max_pages = 50  # 최대 50페이지까지 탐색

    while page <= max_pages:
        # 중앙일보 검색 URL
        search_url = (
            f"https://www.joongang.co.kr/search/news?"
            f"keyword=%ED%99%8D%EC%84%B1%EB%82%A8%20%EC%8B%A0%EB%B6%80"
            f"&page={page}&searchin=&accurateWord=&stopword="
            f"&sourceCode=1%2C3&sfield=title"
        )

        print(f"\n  📄 페이지 {page} 검색 중...")
        response = fetch_page(search_url)

        if not response:
            print(f"  ✗ 페이지 {page} 로드 실패, 다음으로 넘어감")
            break

        soup = BeautifulSoup(response.text, 'lxml')

        # 기사 목록 찾기
        articles = soup.select('ul.story_list li') or soup.select('.article_list .item') or soup.select('.search_list li')

        if not articles:
            # 다른 선택자 시도
            articles = soup.find_all('a', href=re.compile(r'/article/\d+'))
            if not articles:
                print(f"  ℹ 페이지 {page}에서 기사를 찾을 수 없음. 수집 종료.")
                break

        found_in_page = 0
        for article in articles:
            try:
                # 링크 추출
                link_tag = article if article.name == 'a' else article.find('a', href=True)
                if not link_tag or not link_tag.get('href'):
                    continue

                article_url = link_tag['href']
                if not article_url.startswith('http'):
                    article_url = urljoin('https://www.joongang.co.kr', article_url)

                # 이미 수집한 URL 건너뛰기
                if article_url in progress['collected_urls']:
                    skipped += 1
                    continue

                # 기사 페이지 접속
                time.sleep(REQUEST_DELAY)
                article_response = fetch_page(article_url)

                if not article_response:
                    continue

                article_soup = BeautifulSoup(article_response.text, 'lxml')

                # 제목 추출
                title_tag = (
                    article_soup.find('h1', class_=re.compile(r'title|headline')) or
                    article_soup.find('h1') or
                    article_soup.find('meta', property='og:title')
                )
                title = ""
                if title_tag:
                    if title_tag.name == 'meta':
                        title = title_tag.get('content', '')
                    else:
                        title = clean_text(title_tag.get_text())

                if not title:
                    continue

                # 날짜 추출
                date_tag = (
                    article_soup.find('meta', property='article:published_time') or
                    article_soup.find('meta', property='og:article:published_time') or
                    article_soup.find(class_=re.compile(r'date|time|published'))
                )
                date_str = ""
                if date_tag:
                    if date_tag.name == 'meta':
                        date_str = date_tag.get('content', '')[:10]
                    else:
                        date_str = clean_text(date_tag.get_text())[:10]

                if not date_str:
                    date_str = "날짜미상"

                # 본문 추출
                body_tag = (
                    article_soup.find('div', id='article_body') or
                    article_soup.find('div', class_=re.compile(r'article.?body|article.?content|story.?body')) or
                    article_soup.find('article') or
                    article_soup.find('div', class_='ab_article')
                )

                if body_tag:
                    # 스크립트, 스타일, 광고 등 제거
                    for tag in body_tag.find_all(['script', 'style', 'iframe', 'figure', 'aside']):
                        tag.decompose()
                    content = clean_article_text(body_tag.get_text('\n'))
                else:
                    continue

                if len(content) < 100:  # 너무 짧은 기사 건너뛰기
                    continue

                # 저장
                save_article(output_dir, source, title, date_str, article_url, content)
                progress['collected_urls'].append(article_url)
                collected += 1
                found_in_page += 1

                print(f"  ✓ [{collected}] {title[:40]}... ({date_str})")

            except Exception as e:
                print(f"  ⚠ 기사 처리 중 오류: {e}")
                continue

        if found_in_page == 0 and skipped == 0:
            print(f"  ℹ 더 이상 새 기사가 없음. 수집 종료.")
            break

        page += 1
        save_progress(progress)

    progress['stats']['중앙일보'] = collected
    print(f"\n  ✅ {source} 수집 완료: {collected}개 기사")
    return collected

# =====================================================================
# 2. 가톨릭신문 수집 (searchmy.php 사용)
# =====================================================================
def collect_catholictimes(progress):
    """가톨릭신문 '홍성남 신부' 기사 수집 — searchmy.php 검색 엔드포인트 사용"""
    source = "가톨릭신문"
    output_dir = OUTPUT_DIR / "02_가톨릭신문"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"✝ {source} 칼럼 수집 시작")
    print(f"{'='*60}")

    collected = 0
    skipped = 0
    page = 1
    max_pages = 20

    while page <= max_pages:
        # searchmy.php 검색 엔드포인트 사용
        search_url = f"https://db.catholictimes.org/article/searchmy.php?sa_word=%ED%99%8D%EC%84%B1%EB%82%A8&page={page}"

        print(f"\n  📄 페이지 {page} 검색 중...")
        response = fetch_page(search_url)

        if not response:
            print(f"  ✗ 페이지 {page} 로드 실패")
            break

        soup = BeautifulSoup(response.text, 'lxml')

        # article_view.php 링크 찾기
        article_links = soup.find_all('a', href=re.compile(r'article_view\.php\?aid='))

        if not article_links:
            print(f"  ℹ 페이지 {page}에서 기사를 찾을 수 없음. 수집 종료.")
            break

        found_in_page = 0
        for link_tag in article_links:
            try:
                article_url = link_tag['href']
                if not article_url.startswith('http'):
                    article_url = urljoin('https://db.catholictimes.org/article/', article_url)

                # 이미 수집한 URL 건너뛰기
                if article_url in progress['collected_urls']:
                    skipped += 1
                    continue

                # 검색 결과에서 제목/날짜 미리 추출
                link_text = clean_text(link_tag.get_text())

                # 홍성남 관련 기사만 필터링
                if '홍성남' not in link_text:
                    continue

                time.sleep(REQUEST_DELAY)

                # 기사 페이지 접속 (www.catholictimes.org 형식으로도 시도)
                # aid 번호 추출
                aid_match = re.search(r'aid=(\d+)', article_url)
                if aid_match:
                    aid = aid_match.group(1)
                    # 새 형식 URL로 접속 시도
                    new_url = f"https://www.catholictimes.org/article/{aid}"
                    article_response = fetch_page(new_url)
                    if not article_response or article_response.status_code != 200:
                        # db 형식으로 재시도
                        article_response = fetch_page(article_url)
                    else:
                        article_url = new_url
                else:
                    article_response = fetch_page(article_url)

                if not article_response:
                    continue

                article_soup = BeautifulSoup(article_response.text, 'lxml')

                # 제목 추출
                title_tag = (
                    article_soup.find('meta', property='og:title') or
                    article_soup.find('h1', class_=re.compile(r'title|headline')) or
                    article_soup.find('h2', class_=re.compile(r'title')) or
                    article_soup.find('h1')
                )
                title = ""
                if title_tag:
                    if title_tag.name == 'meta':
                        title = title_tag.get('content', '')
                    else:
                        title = clean_text(title_tag.get_text())

                if not title:
                    title = link_text[:60] if link_text else "제목없음"

                # 날짜 추출
                date_str = ""
                # 검색 결과 텍스트에서 날짜 추출 시도
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', link_text)
                if date_match:
                    date_str = date_match.group(1)
                else:
                    date_tag = (
                        article_soup.find('meta', property='article:published_time') or
                        article_soup.find(class_=re.compile(r'date|time|published'))
                    )
                    if date_tag:
                        if date_tag.name == 'meta':
                            date_str = date_tag.get('content', '')[:10]
                        else:
                            date_text = clean_text(date_tag.get_text())
                            dm = re.search(r'(\d{4}[-./]\d{1,2}[-./]\d{1,2})', date_text)
                            if dm:
                                date_str = dm.group(1)

                if not date_str:
                    date_str = "날짜미상"

                # 본문 추출
                body_tag = (
                    article_soup.find('div', class_=re.compile(r'article.?body|article.?content|view.?cont|article.?text')) or
                    article_soup.find('div', id=re.compile(r'article|content|body')) or
                    article_soup.find('article') or
                    article_soup.find('td', class_=re.compile(r'content|body'))
                )

                if body_tag:
                    for tag in body_tag.find_all(['script', 'style', 'iframe', 'figure', 'aside']):
                        tag.decompose()
                    content = clean_article_text(body_tag.get_text('\n'))
                else:
                    continue

                if len(content) < 100:
                    continue

                save_article(output_dir, source, title, date_str, article_url, content)
                progress['collected_urls'].append(article_url)
                collected += 1
                found_in_page += 1

                print(f"  ✓ [{collected}] {title[:40]}... ({date_str})")

            except Exception as e:
                print(f"  ⚠ 기사 처리 중 오류: {e}")
                continue

        if found_in_page == 0 and skipped == 0:
            print(f"  ℹ 더 이상 새 기사가 없음. 수집 종료.")
            break

        page += 1
        save_progress(progress)

    progress['stats']['가톨릭신문'] = collected
    print(f"\n  ✅ {source} 수집 완료: {collected}개 기사")
    return collected

# =====================================================================
# 3. 경향신문 수집 (search.khan.co.kr 사용)
# =====================================================================
def collect_khan(progress):
    """경향신문 '홍성남 신부' 기사 수집 — search.khan.co.kr 검색 사용"""
    source = "경향신문"
    output_dir = OUTPUT_DIR / "03_경향신문"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"📰 {source} 기사 수집 시작")
    print(f"{'='*60}")

    collected = 0
    skipped = 0
    page = 1
    max_pages = 10

    while page <= max_pages:
        # search.khan.co.kr 검색 엔드포인트 사용
        search_url = f"https://search.khan.co.kr/search.html?stb=khan&q=%ED%99%8D%EC%84%B1%EB%82%A8+%EC%8B%A0%EB%B6%80&page={page}"

        print(f"\n  📄 페이지 {page} 검색 중...")
        response = fetch_page(search_url)

        if not response:
            print(f"  ✗ 페이지 {page} 로드 실패")
            break

        soup = BeautifulSoup(response.text, 'lxml')

        # /article/ 패턴의 링크 찾기
        article_links = soup.find_all('a', href=re.compile(r'khan\.co\.kr/article/\d+'))

        if not article_links:
            # 대체: 모든 링크에서 article 패턴 찾기
            article_links = soup.find_all('a', href=re.compile(r'/article/\d+'))

        if not article_links:
            print(f"  ℹ 페이지 {page}에서 기사를 찾을 수 없음. 수집 종료.")
            break

        # 중복 URL 제거
        seen_urls = set()
        unique_links = []
        for link in article_links:
            url = link.get('href', '')
            if url not in seen_urls:
                seen_urls.add(url)
                unique_links.append(link)
        article_links = unique_links

        found_in_page = 0
        for link_tag in article_links:
            try:
                article_url = link_tag['href']
                if not article_url.startswith('http'):
                    article_url = urljoin('https://www.khan.co.kr', article_url)

                # /articles 목록 페이지 건너뛰기 (개별 기사만)
                if article_url.endswith('/articles'):
                    continue

                if article_url in progress['collected_urls']:
                    skipped += 1
                    continue

                time.sleep(REQUEST_DELAY)
                article_response = fetch_page(article_url)

                if not article_response:
                    continue

                article_soup = BeautifulSoup(article_response.text, 'lxml')

                # 홍성남 관련 기사만 필터링
                page_text = article_soup.get_text()
                if '홍성남' not in page_text:
                    continue

                # 제목
                title_tag = (
                    article_soup.find('meta', property='og:title') or
                    article_soup.find('h1', class_=re.compile(r'title|headline')) or
                    article_soup.find('h1')
                )
                title = ""
                if title_tag:
                    if title_tag.name == 'meta':
                        title = title_tag.get('content', '')
                    else:
                        title = clean_text(title_tag.get_text())

                if not title:
                    continue

                # 날짜
                date_tag = (
                    article_soup.find('meta', property='article:published_time') or
                    article_soup.find(class_=re.compile(r'byline|date|time|published'))
                )
                date_str = ""
                if date_tag:
                    if date_tag.name == 'meta':
                        date_str = date_tag.get('content', '')[:10]
                    else:
                        date_text = clean_text(date_tag.get_text())
                        date_match = re.search(r'(\d{4}[-./]\d{1,2}[-./]\d{1,2})', date_text)
                        if date_match:
                            date_str = date_match.group(1)

                if not date_str:
                    date_str = "날짜미상"

                # 본문
                body_tag = (
                    article_soup.find('div', class_=re.compile(r'art_body|article.?body')) or
                    article_soup.find('div', id=re.compile(r'article.?body|content')) or
                    article_soup.find('article')
                )

                if body_tag:
                    for tag in body_tag.find_all(['script', 'style', 'iframe', 'figure', 'aside']):
                        tag.decompose()
                    content = clean_article_text(body_tag.get_text('\n'))
                else:
                    continue

                if len(content) < 100:
                    continue

                save_article(output_dir, source, title, date_str, article_url, content)
                progress['collected_urls'].append(article_url)
                collected += 1
                found_in_page += 1

                print(f"  ✓ [{collected}] {title[:40]}... ({date_str})")

            except Exception as e:
                print(f"  ⚠ 기사 처리 중 오류: {e}")
                continue

        if found_in_page == 0 and skipped == 0:
            print(f"  ℹ 더 이상 새 기사가 없음. 수집 종료.")
            break

        page += 1
        save_progress(progress)

    progress['stats']['경향신문'] = collected
    print(f"\n  ✅ {source} 수집 완료: {collected}개 기사")
    return collected

# =====================================================================
# 메인 실행
# =====================================================================
def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  홍성남 신부님 신문 칼럼 수집기                        ║")
    print("║  대상: 중앙일보 · 가톨릭신문 · 경향신문               ║")
    print("╚══════════════════════════════════════════════════════════╝")

    # 출력 디렉토리 생성
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 진행 상태 로드 (이어하기 지원)
    progress = load_progress()
    already = len(progress.get('collected_urls', []))
    if already > 0:
        print(f"\n  ℹ 이전 수집 기록 발견: {already}개 기사 수집됨 (중복 건너뜀)")

    start_time = time.time()
    total = 0

    # 1. 중앙일보 수집
    try:
        total += collect_joongang(progress)
    except Exception as e:
        print(f"\n  ✗ 중앙일보 수집 중 오류: {e}")

    # 2. 가톨릭신문 수집
    try:
        total += collect_catholictimes(progress)
    except Exception as e:
        print(f"\n  ✗ 가톨릭신문 수집 중 오류: {e}")

    # 3. 경향신문 수집
    try:
        total += collect_khan(progress)
    except Exception as e:
        print(f"\n  ✗ 경향신문 수집 중 오류: {e}")

    # 최종 결과 저장
    save_progress(progress)

    elapsed = time.time() - start_time

    print(f"\n{'='*60}")
    print(f"╔══════════════════════════════════════════════════════════╗")
    print(f"║  ✅ 전체 수집 완료!                                    ║")
    print(f"╠══════════════════════════════════════════════════════════╣")
    print(f"║  이번 수집: {total}개 기사")
    print(f"║  누적 수집: {len(progress['collected_urls'])}개 기사")
    for source, count in progress.get('stats', {}).items():
        print(f"║    - {source}: {count}개")
    print(f"║  소요 시간: {elapsed/60:.1f}분")
    print(f"║  저장 위치: {OUTPUT_DIR.absolute()}")
    print(f"╚══════════════════════════════════════════════════════════╝")
    print(f"\n  📌 다음 단계: 수집된 칼럼을 벡터DB에 추가하세요.")
    print(f"     python build_vectordb.py 를 다시 실행하면 됩니다.")

if __name__ == "__main__":
    main()
