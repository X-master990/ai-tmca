"""從『承辦-續約函模板.docx』(含範例值) 產生 docxtpl jinja 模板。

把範例值就地換成 {{ }} 佔位符 —— 只改目標 run 的文字，保留所有字型 / 換行 /
版面。每個 jinja tag 完整落在單一 run 內，docxtpl 才解析得到。

產出 → templates/承辦/續約函模板.docx（會 commit，隨映像進 /var/tmca/templates）。

每個替換點都先 assert 原文，來源若被改動會大聲報錯，不會默默產出錯模板。

用法:
    python scripts/build_renewal_letter_template.py [SRC_DOCX] [OUT_DOCX]
"""
from __future__ import annotations

import sys
from pathlib import Path

from docx import Document
from docx.text.paragraph import Paragraph

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SRC = Path.home() / "Downloads" / "iLoveZIP_Create" / "承辦-續約函模板.docx"
DEFAULT_OUT = REPO_ROOT / "templates" / "承辦" / "續約函模板.docx"


def find_para(doc: Document, predicate) -> Paragraph:
    for p in doc.paragraphs:
        if predicate(p.text):
            return p
    raise SystemExit(f"❌ 找不到符合的段落（來源結構可能變了）：{predicate}")


def expect(actual: str, want: str, where: str) -> None:
    if actual != want:
        raise SystemExit(
            f"❌ {where} 原文不符，來源可能變了。\n  期望 {want!r}\n  實際 {actual!r}"
        )


def build(src: Path, out: Path) -> None:
    doc = Document(str(src))

    # 2. ★繳費期限115年6月30日 → ★繳費期限{{ pay_deadline }}
    p = find_para(doc, lambda t: t.strip().startswith("★繳費期限"))
    expect(p.runs[1].text, "繳費期限115年6月30日", "繳費期限")
    p.runs[1].text = "繳費期限{{ pay_deadline }}"

    # 8. 發文日期：115年5月12日 → 發文日期：{{ issue_date }}
    p = find_para(doc, lambda t: t.startswith("發") and "發文日期" in t)
    expect(p.runs[3].text, "115年5月12日", "發文日期")
    p.runs[3].text = "{{ issue_date }}"

    # 9. 受文者：金紅視聽歌唱坊 → 受文者：{{ recipient }}
    p = find_para(doc, lambda t: t.startswith("受文者"))
    expect(p.runs[2].text, "金紅視聽歌唱坊", "受文者")
    p.runs[2].text = "{{ recipient }}"

    # 12. 授權時間（多 run + 段內換行）
    #     中華民國 115 年 01 月 01 日起至 115 年 12 月 31 日止。
    #   → 中華民國 {{ period_start }}起至 {{ period_end }}止。
    #   保留 run0-4（一、授權時間：＋換行），把日期段塞進 run5、清空其餘。
    p = find_para(doc, lambda t: "授權時間" in t)
    expect(p.runs[5].text, "中華民國", "授權時間")
    p.runs[5].text = "中華民國 {{ period_start }}起至 {{ period_end }}止。"
    for i in range(6, len(p.runs)):
        p.runs[i].text = ""

    # 13. 營業地址：台中市… → 營業地址：{{ business_address }}
    p = find_para(doc, lambda t: "營業地址" in t)
    if not p.runs[4].text.startswith("台中市"):
        raise SystemExit(f"❌ 營業地址原文不符：{p.runs[4].text!r}")
    p.runs[4].text = "{{ business_address }}"

    # 14. 申報台數： 1 台(包廂數) 應付金額： 3675 元（含稅）
    #   → 申報台數： {{ qty }} 台(包廂數) 應付金額： {{ amount }} 元（含稅）
    p = find_para(doc, lambda t: "申報台數" in t)
    expect(p.runs[5].text, "1", "申報台數")
    p.runs[5].text = "{{ qty }}"
    expect(p.runs[11].text, "3675", "應付金額")
    p.runs[11].text = "{{ amount }}"

    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out))
    print(f"✅ 已產出 jinja 模板：{out}")


if __name__ == "__main__":
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SRC
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT
    if not src.exists():
        raise SystemExit(f"❌ 找不到來源模板：{src}")
    build(src, out)
