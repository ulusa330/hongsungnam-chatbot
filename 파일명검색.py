import os

source_folders = [
    r"D:\유튜브자막추출\output_홍성남신부_자막추출\15_전체교정_4omini",
    r"D:\유튜브자막추출\교정완료_2026",
    r"D:\유튜브자막추출\외로움_참고용",
]

search_terms = ["마음의 병", "치유"]

for folder in source_folders:
    if not os.path.exists(folder):
        continue
    for filename in os.listdir(folder):
        if any(term in filename for term in search_terms):
            print(f"[{folder}]\n  → {filename}\n")