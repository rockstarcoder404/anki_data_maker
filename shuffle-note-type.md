# 選択肢シャッフル用ノートタイプの設定手順

`sample-shuffle.csv` をインポートして動作確認するための Anki 側の設定。

## 1. ノートタイプを作る

1. ツール → ノートタイプを管理 → 追加
2. 「複製: 穴埋め」(Clone: Cloze)を選び、名前を **穴埋め（選択肢シャッフル）** にする
3. 作ったノートタイプを選択 → フィールド → 追加 で **Choices** フィールドを追加する
   - フィールド順は「Text, Back Extra, Choices」の順になっていること

## 2. カードテンプレートを書き換える

ノートタイプ管理 → 穴埋め（選択肢シャッフル） → カード で以下を貼り付ける。

### 表面のテンプレート

```html
{{cloze:Text}}

<br><br>
<div id="opts"></div>
<script>
(function () {
  var opts = `{{Choices}}`.split("|");
  var order = opts.map(function (_, i) { return i; });
  for (var i = order.length - 1; i > 0; i--) {
    var j = Math.floor(Math.random() * (i + 1));
    var t = order[i]; order[i] = order[j]; order[j] = t;
  }
  try {
    sessionStorage.setItem("ankiChoiceOrder", JSON.stringify(order));
  } catch (e) {}
  document.getElementById("opts").innerHTML =
    order.map(function (i) { return opts[i]; }).join("<br>");
})();
</script>
```

### 裏面のテンプレート

```html
{{cloze:Text}}

<br><br>
<div id="opts"></div>
<script>
(function () {
  var opts = `{{Choices}}`.split("|");
  var order = null;
  try {
    order = JSON.parse(sessionStorage.getItem("ankiChoiceOrder"));
  } catch (e) {}
  if (!order || order.length !== opts.length) {
    order = opts.map(function (_, i) { return i; });
  }
  document.getElementById("opts").innerHTML =
    order.map(function (i) { return opts[i]; }).join("<br>");
})();
</script>

<br>
{{Back Extra}}
```

仕組み:

- 表面を表示するたびに Fisher–Yates でシャッフルし、並び順を `sessionStorage` に保存する
- 裏面は保存された並び順を読むので、**表と裏で選択肢の順番が一致する**
- 次のレビューでは表面が再度シャッフルするので、毎回順番が変わる

## 3. CSV をインポートする

1. ファイル → 読み込む で `sample-shuffle.csv` を選ぶ
2. ノートタイプ: **穴埋め（選択肢シャッフル）**、インポート先デッキを選ぶ
3. フィールドの対応を確認する(CSV の列順):
   - 1列目 → Text
   - 2列目 → Back Extra(空)
   - 3列目 → Choices
   - 4列目 → タグ(ファイル先頭の `#tags column:4` で自動設定されるはず)

## 4. 動作確認のポイント

- 学習画面で同じカードを何度か表示し(プレビューでも可)、選択肢の順番が毎回変わること
- 表面で表示された順番と裏面の順番が同じであること
- 裏面で `言わんばかり` が青字(cloze の解答)で表示されること

> 補足: テンプレート内の JavaScript は Anki 公式には「サポート外」ですが、
> PC 版・AnkiDroid・AnkiMobile のいずれでも動作する広く使われている手法です。
> 万一 `sessionStorage` が使えない環境でも、裏面は元の順番で表示されるだけで
> エラーにはなりません。
