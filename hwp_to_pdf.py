import win32com.client
from pathlib import Path

# ── 설정 ──
HWP_FOLDER = r"E:\99_개인문서\이재욱 개인\홍성남 신부님 원고"

hwp_files = list(Path(HWP_FOLDER).rglob("*.hwp"))
total = len(hwp_files)
print(f"총 {total}개 HWP 파일 발견\n")

hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
hwp.XHwpWindows.Item(0).Visible = False

success, fail = 0, 0

for i, hwp_path in enumerate(hwp_files, 1):
    out_pdf = str(hwp_path.with_suffix(".pdf"))
    print(f"[{i}/{total}] 변환 중: {hwp_path.name}")
    try:
        hwp.Open(str(hwp_path), "HWP", "forceopen:true")

        # PDF 저장 — PDFSave 액션 방식
        pset = hwp.HParameterSet.HFileSaveAs
        hwp.HAction.GetDefault("FileSaveAs_S", pset.HSet)
        pset.HSet.SetItem("FileName", out_pdf)
        pset.HSet.SetItem("Format", "PDF")
        pset.HSet.SetItem("Security", 0)
        pset.HSet.SetItem("TreatAsProtected", 0)
        pset.HSet.SetItem("PDFProtect", 0)
        result = hwp.HAction.Execute("FileSaveAs_S", pset.HSet)

        if Path(out_pdf).exists():
            print(f"  ✅ 완료")
            success += 1
        else:
            # 대안: SaveAs 직접 호출
            result2 = hwp.SaveAs(out_pdf, "PDF", "")
            if Path(out_pdf).exists():
                print(f"  ✅ 완료 (방법2)")
                success += 1
            else:
                print(f"  ❌ 실패")
                fail += 1

        hwp.Clear(1)

    except Exception as e:
        print(f"  ❌ 오류: {str(e)[:80]}")
        try:
            hwp.Clear(1)
        except:
            pass
        fail += 1

try:
    hwp.Quit()
except:
    pass

print(f"\n── 완료 ──")
print(f"성공: {success}개 / 실패: {fail}개 / 전체: {total}개")
input("\n엔터를 누르면 종료됩니다...")
