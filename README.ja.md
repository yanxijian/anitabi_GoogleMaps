# anitabi → Google My Maps

**日本語** · [English](README.md) · [简体中文](README.zh-CN.md) · [한국어](README.ko.md)

<!-- translated-from: README.md sha256:328afc1d9022 -->

[anitabi](https://www.anitabi.cn/map) の聖地巡礼マップを **KML** として書き出し、[Google My Maps](https://www.google.com/maps/d/) に読み込んで Google マップ上で眺めるためのツールです。

Python 3.8 以降の標準ライブラリだけで動きます。**`requests` のインストールは不要**です。

## 使い方

```bash
# bangumi_id を 1 つ指定（複数まとめて指定も可）
python anitabi_GoogleMaps.py 331884

# 複数の作品をまとめて書き出す
python anitabi_GoogleMaps.py 331884 4912

# 出力ファイル／出力ディレクトリを指定する
python anitabi_GoogleMaps.py 331884 -o bocchi-the-rock.kml
python anitabi_GoogleMaps.py 331884 --outdir maps

# 対話モード（id を省略すると起動。Enter か q で終了）
python anitabi_GoogleMaps.py
```

`bangumi_id` は作品ページの URL に含まれる数字です。<https://www.anitabi.cn/map> を開き、作品を検索してアドレスバーの `bangumi/<id>` を見てください。

読み込み手順：[Google My Maps](https://www.google.com/maps/d/) を開く → 新しい地図を作る → レイヤーを追加 → インポート → 生成された `.kml` を選ぶ。

## ネットワークが不安定なとき

anitabi の API は、環境によってタイムアウトしたり 403 を返したりします。スクリプトは再試行し（`--retries`、既定 2 回。`--timeout`、既定 20 秒）、それでも駄目なら**スクリプトと同じディレクトリの `{id}.json`** に切り替えます：

1. ブラウザで `https://api.anitabi.cn/bangumi/<id>/points/detail` を開く
2. スクリプトと同じディレクトリに `{id}.json` として保存する
3. `python anitabi_GoogleMaps.py <id> --offline` を実行する

注意：`--offline` で `{id}.json`（地点の配列）だけがあり作品情報がない場合、出力ファイル名は bangumi_id になります。

## 旧版からの変更点

| 問題 | 旧版 | 現在 |
| --- | --- | --- |
| 依存 | `requests` が必要 | 標準ライブラリのみ |
| 引数 | 対話入力だけ | 位置引数に加えて `-o` / `--outdir` / `--offline` / `--timeout` / `--retries` |
| タイムアウトと再試行 | なし（固まったままになることも） | 既定 20 秒のタイムアウトと指数バックオフ |
| KML の名前空間 | `http://www.opengis.net`（仕様外） | `http://www.opengis.net/kml/2.2` |
| ドキュメント名 | `<Document><name>` がない | ある |
| ファイル名 | 作品名をそのまま使用。`Re:Zero` のような題名は Windows で書き込みに失敗 | `<>:"/\|?*`、予約名、末尾のドット、長すぎる名前を除去 |
| 欠けた項目 | `item['geo']` / `item['id']` で KeyError | その地点を飛ばして数える |
| XML の安全性 | 画像 URL が未エスケープで、属性が切れたり CDATA が早く終わったりしうる | 属性のエスケープと CDATA の分割 |
| 書き込み | 直接上書き。中断すると半端なファイルが残る | `.tmp` に書いてから `os.replace` |
| 検証 | なし | XML の形と座標順をテストで担保 |

## テスト

```bash
python -m unittest discover -s tests -v
```

23 件すべてオフラインです。HTTP 呼び出しは偽実装に差し替え、KML の構造・エスケープ・座標順、ファイル名の整形、再試行と切り替え、エンドツーエンドの生成と終了コードを確認します。

## 既知の制約

- 出力するのは地点（Placemark）だけです。経路、画像のダウンロード、作品のカバー画像は含みません。
- 座標は anitabi が返す `[緯度, 経度]` を KML の `経度,緯度,0` に変換するだけで、測地系の補正はしません。
- API に公開仕様がないため、項目が欠けた地点は変換全体を止めずに飛ばします。
- Windows のコンソールでコードページが UTF-8 でない場合、65001 に切り替えを試みます。切り替えられないと非 ASCII は `?` になりますが、`UnicodeEncodeError` で変換が止まることはありません。ファイルへのリダイレクトは常に UTF-8 です。

## 作成したマップの一部

1. 冴えない彼女の育てかた - https://www.google.com/maps/d/viewer?mid=19CAvroXYoTebZ4wZ9tvg9XvoRiL6XvE&usp=sharing
2. ラブライブ！スーパースター!! - https://www.google.com/maps/d/viewer?mid=1_shPyo5kTGYvp5Q2BGH9X8e36bfrk94&usp=sharing
3. ソードアート・オンライン - https://www.google.com/maps/d/viewer?mid=1V2zw6YQYttRrdspKxNwpfAsRh4NLeys&usp=sharing
4. BanG Dream! It's MyGO!!!!!／Ave Mujica - https://www.google.com/maps/d/viewer?mid=1ty5EjnQo1LLCgDqHdhwijhZDN6ZdDlM&usp=sharing
5. 響け！ユーフォニアム - https://www.google.com/maps/d/viewer?mid=1XfU4x6KMA1FdQ2180QJ5Ua_wgYQIdTI&usp=sharing
6. 負けヒロインが多すぎる！ - https://www.google.com/maps/d/viewer?mid=1CNXd5Xkkh2Qf0QZPNG7azKCJC-aCDjE&usp=sharing
7. ぼっち・ざ・ろっく！ - https://www.google.com/maps/d/viewer?mid=13FySg0WBFmL4ptTyzw5CDndq0NWQdkc&usp=sharing

## ライセンス

MIT。[LICENSE](LICENSE) を参照してください。
