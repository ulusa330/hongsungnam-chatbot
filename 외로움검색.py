import os
import shutil

source_folders = [
    r"D:\유튜브자막추출\output_홍성남신부_자막추출\15_전체교정_4omini",
    r"D:\유튜브자막추출\교정완료_2026",
]

target_folder = r"D:\유튜브자막추출\외로움_참고용"

keywords = ["외로움", "고립", "혼자"]

os.makedirs(target_folder, exist_ok=True)

found_count = 0
for folder in source_folders:
    if not os.path.exists(folder):
        print(f"⚠️ 폴더 없음: {folder}")
        continue
    for filename in os.listdir(folder):
        if not filename.endswith(".txt"):
            continue
        filepath = os.path.join(folder, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(filepath, "r", encoding="cp949", errors="ignore") as f:
                content = f.read()

        if any(kw in content for kw in keywords):
            shutil.copy(filepath, os.path.join(target_folder, filename))
            found_count += 1
            print(f"복사됨: {filename}")

print(f"\n총 {found_count}개 파일을 {target_folder} 로 복사했습니다.")