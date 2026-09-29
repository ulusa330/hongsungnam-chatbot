import os

source_folder = r"D:\유튜브자막추출\외로움_참고용"

keywords = ["외로움", "고립", "혼자"]

scores = []
for filename in os.listdir(source_folder):
    if not filename.endswith(".txt"):
        continue
    filepath = os.path.join(source_folder, filename)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(filepath, "r", encoding="cp949", errors="ignore") as f:
            content = f.read()

    score = sum(content.count(kw) for kw in keywords)
    scores.append((score, filename))

scores.sort(reverse=True)

print("=== 상위 15개 (키워드 등장 빈도순) ===")
for score, filename in scores[:15]:
    print(f"{score}회 - {filename}")