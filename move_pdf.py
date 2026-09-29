import shutil
from pathlib import Path

# ── 설정 ──
HWP_FOLDER = r"E:\99_개인문서\이재욱 개인\홍성남 신부님 원고"
PDF_OUTPUT = r"C:\유튜브자막추출\PDF"

# PDF 폴더 생성
Path(PDF_OUTPUT).mkdir(parents=True, exist_ok=True)
print(f"PDF 폴더 생성: {PDF_OUTPUT}\n")

# PDF 파일 전체 수집 (하위 폴더 포함)
pdf_files = list(Path(HWP_FOLDER).rglob("*.pdf"))
total = len(pdf_files)
print(f"총 {total}개 PDF 파일 발견\n")

success, skip = 0, 0

for i, pdf_path in enumerate(pdf_files, 1):
    dest = Path(PDF_OUTPUT) / pdf_path.name
    
    # 동일 파일명 있으면 뒤에 숫자 붙이기
    if dest.exists():
        stem = pdf_path.stem
        suffix = pdf_path.suffix
        counter = 1
        while dest.exists():
            dest = Path(PDF_OUTPUT) / f"{stem}_{counter}{suffix}"
            counter += 1

    print(f"[{i}/{total}] 이동 중: {pdf_path.name}")
    shutil.copy2(str(pdf_path), str(dest))
    success += 1

print(f"\n── 완료 ──")
print(f"이동 완료: {success}개")
print(f"저장 위치: {PDF_OUTPUT}")
input("\n엔터를 누르면 종료됩니다...")
