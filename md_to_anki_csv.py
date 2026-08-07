#!/usr/bin/env python3
"""JLPT文法問題のMarkdownをANKIインポート用CSVに変換するスクリプト。

data/jlpt-n1-grammar-test/chapter-6.md と同形式のMarkdownを読み込み、
Cloze(穴埋め)形式のCSVを出力する。

CSVフィールド（ヘッダ行なし・Text, Back Extra, Tags の3列）:
  - Text: 問題文（「（　　　）」を {{c1::正解}} に置換）+ 選択肢
  - Back Extra: 常に空文字列
  - Tags: 固定タグ「N1文法」+ 文法項目（～を除いた部分）
    文法項目は各問題の「- **[タグ: ～〇〇]**」行から取得する。
    タグ行がない場合は見出し「【～〇〇】」からのフォールバック（旧形式）。

使い方:
  python3 md_to_anki_csv.py data/jlpt-n1-grammar-test/chapter-6.md
  python3 md_to_anki_csv.py chapter-6.md chapter-8.md -o all.csv

出力先を -o で指定しない場合は、入力ファイルと同じ場所に .csv を作る。
"""

import argparse
import re
import sys
import unicodedata
from pathlib import Path

FIXED_TAG = "N1文法"

# 「## 【～〇〇】」「#### 【～〇〇】」などの見出し
RE_HEADING = re.compile(r"^#{2,4}\s*【(.+?)】\s*$")
# 「**1 問題文**」の行
RE_QUESTION = re.compile(r"^\*\*(\d+)[\s　]+(.+?)\*\*\s*$")
# 「- a 選択肢」「- 1 選択肢」の行（記号は英字・数字、全角半角どちらも可）
RE_CHOICE = re.compile(r"^-\s+([0-9a-z０-９ａ-ｚ])\s+(.+?)\s*$")
# 「- **[正解: c]**」の行
RE_ANSWER = re.compile(r"^-\s+\*\*\[正解:\s*(.+?)\]\*\*\s*$")
# 「- **[タグ: ～が早いか]**」の行
RE_TAG = re.compile(r"^-\s+\*\*\[タグ:\s*(.+?)\]\*\*\s*$")
# 問題文中の空欄「（　　　）」（全角・半角スペース混在も許容）
RE_BLANK = re.compile(r"（[\s　]*）")


def warn(msg: str) -> None:
    print(f"警告: {msg}", file=sys.stderr)


def normalize_key(raw: str) -> str:
    """選択肢の記号や正解を照合用に正規化する（全角→半角など）。"""
    return unicodedata.normalize("NFKC", raw.strip())


def normalize_tag(raw: str) -> str:
    """「～が早いか」→「が早いか」、「～や・～や否や」→「や・や否や」のように整形する。"""
    return re.sub(r"[～\s　]", "", raw)


def parse_markdown(path: Path) -> list[tuple[str, str]]:
    """Markdownを解析して (Text, Tags) のリストを返す。"""
    rows: list[tuple[str, str]] = []
    grammar_tag: str | None = None  # 見出し由来のフォールバック用タグ（旧形式）
    question: str | None = None
    question_line = 0
    choices: dict[str, str] = {}
    answer_key: str | None = None
    question_tag: str | None = None

    def flush() -> None:
        """溜めている1問分をCSV行にして rows に追加する。"""
        nonlocal question, choices, answer_key, question_tag
        if question is None:
            return
        if answer_key is None:
            warn(f"{path.name}:{question_line} 正解行がないためスキップ")
        elif answer_key not in choices:
            warn(
                f"{path.name}:{question_line} 正解「{answer_key}」が"
                f"選択肢にないためスキップ: {question[:20]}…"
            )
        elif not RE_BLANK.search(question):
            warn(f"{path.name}:{question_line} 空欄（　　　）がないためスキップ")
        else:
            cloze = RE_BLANK.sub(
                "{{c1::" + choices[answer_key] + "}}", question, count=1
            )
            text = cloze + "<br><br>" + "<br>".join(choices.values())
            tag = question_tag or grammar_tag
            if tag:
                tags = f"{FIXED_TAG} {tag}"
            else:
                warn(f"{path.name}:{question_line} 文法項目が不明のためタグは{FIXED_TAG}のみ")
                tags = FIXED_TAG
            rows.append((text, tags))
        question = None
        choices = {}
        answer_key = None
        question_tag = None

    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.rstrip()

        m = RE_HEADING.match(line)
        if m:
            flush()
            heading = m.group(1).strip()
            if heading.startswith("～") and len(heading) > 1:
                grammar_tag = normalize_tag(heading)
            else:
                # 「【総合問題 1〜5】」や「【～】」など文法項目でない見出しは
                # タグにせず、直前のタグを引きずらないようにクリアする
                grammar_tag = None
            continue

        m = RE_QUESTION.match(line)
        if m:
            flush()
            question = m.group(2).strip()
            question_line = lineno
            continue

        m = RE_ANSWER.match(line)
        if m:
            if question is None:
                warn(f"{path.name}:{lineno} 問題文のない正解行を無視")
            else:
                answer_key = normalize_key(m.group(1))
            continue

        m = RE_TAG.match(line)
        if m:
            if question is None:
                warn(f"{path.name}:{lineno} 問題文のないタグ行を無視")
            else:
                question_tag = normalize_tag(m.group(1))
            continue

        m = RE_CHOICE.match(line)
        if m:
            choices[normalize_key(m.group(1))] = m.group(2)

    flush()
    return rows


def write_csv(rows: list[tuple[str, str]], out_path: Path) -> None:
    """ANKIインポート用CSVを書き出す（Textのみ引用符で囲む）。

    フィールドは Text, Back Extra, Tags の3列。Back Extra は常に空。
    ヘッダ行はANKIインポート時にデータとして取り込まれてしまうため出力しない。
    """
    with out_path.open("w", encoding="utf-8", newline="\n") as f:
        for text, tags in rows:
            f.write('"' + text.replace('"', '""') + '",,' + tags + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="JLPT文法問題のMarkdownをANKIインポート用CSVに変換する"
    )
    parser.add_argument("inputs", nargs="+", type=Path, help="入力Markdownファイル")
    parser.add_argument(
        "-o", "--output", type=Path,
        help="出力CSVファイル（省略時は入力ごとに同名の.csvを作成、指定時は全入力を1ファイルにまとめる）",
    )
    args = parser.parse_args()

    if args.output:
        all_rows = []
        for path in args.inputs:
            rows = parse_markdown(path)
            print(f"{path.name}: {len(rows)}問")
            all_rows.extend(rows)
        write_csv(all_rows, args.output)
        print(f"{args.output}: 計{len(all_rows)}問を書き出しました")
    else:
        for path in args.inputs:
            rows = parse_markdown(path)
            out_path = path.with_suffix(".csv")
            write_csv(rows, out_path)
            print(f"{out_path}: {len(rows)}問を書き出しました")


if __name__ == "__main__":
    main()
