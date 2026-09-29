import os

source_folders = [
    r"D:\유튜브자막추출\output_홍성남신부_자막추출\15_전체교정_4omini",
    r"D:\유튜브자막추출\교정완료_2026",
]

keywords = ["자존감", "자신감", "열등감", "비교"]

scores = []
for folder in source_folders:
    if not os.path.exists(folder):
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
        score = sum(content.count(kw) for kw in keywords)
        scores.append((score, filename))

scores.sort(reverse=True)
print("=== 자존감 클러스터 상위 20개 ===")
for score, filename in scores[:20]:
    print(f"{score}회 - {filename}")