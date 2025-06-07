# Video Chapter Trimmer

[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

動画のチャプター情報を基に、CMなどの不要な部分を除外して動画を再構成するコマンドラインツールです。

## 特徴

- 📺 チャプターファイルから`--`で始まるセグメント（CM等）を自動除外
- ⚡ ストリームコピーによる高速処理（再エンコードなし）
- 📱 iOS互換性のための最適化
- 🛠️ 詳細なエラーハンドリングとログ出力
- 🧪 ドライラン機能で実行前に動作確認可能

## 必要条件

- Python 3.7以上
- ffmpeg（システムにインストール済みであること）

### ffmpegのインストール

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg

# Windows (Chocolatey)
choco install ffmpeg
```

## インストール

### pipを使用したインストール

```bash
pip install video-chapter-trimmer
```

### ソースからのインストール

```bash
git clone https://github.com/yourusername/video-chapter-trimmer.git
cd video-chapter-trimmer
pip install -e .
```

### 開発環境のセットアップ

```bash
# 開発用依存関係のインストール
pip install -e ".[dev]"

# pre-commitフックのセットアップ
pre-commit install
```

## 使用方法

### 基本的な使用方法

```bash
video-chapter-trimmer chapters.txt input_video.mp4
```

### オプション

```bash
# 出力ファイル名を指定
video-chapter-trimmer chapters.txt input.mp4 -o output.mp4

# 一時ファイルを保持
video-chapter-trimmer chapters.txt input.mp4 --keep-temp

# ドライラン（実際には実行しない）
video-chapter-trimmer chapters.txt input.mp4 --dry-run

# 詳細なログを表示
video-chapter-trimmer chapters.txt input.mp4 --verbose

# 静かなモード
video-chapter-trimmer chapters.txt input.mp4 --quiet
```

### チャプターファイルの形式

チャプターファイルは以下の形式で記述します：

```
0:00:05.151 Opening
0:01:05.822 --CM
0:02:36.160 MC
0:02:40.830 Opening Title
0:26:25.064 --CM
0:28:25.179 偉人の言葉
0:28:45.152 --CM
```

`--`で始まる行は除外対象として扱われます。

## プロジェクト構成

```
video-chapter-trimmer/
├── src/
│   └── video_chapter_trimmer/
│       ├── __init__.py
│       ├── cli.py          # メインCLIスクリプト
│       ├── parser.py       # チャプターファイルパーサー
│       ├── processor.py    # 動画処理
│       └── utils.py        # ユーティリティ関数
├── tests/
│   ├── __init__.py
│   ├── test_parser.py
│   ├── test_processor.py
│   └── test_cli.py
├── setup.py
├── setup.cfg
├── pyproject.toml
├── README.md
├── LICENSE
├── CHANGELOG.md
├── .gitignore
├── .pre-commit-config.yaml
└── requirements-dev.txt
```

## 開発

### テストの実行

```bash
# すべてのテストを実行
pytest

# カバレッジ付きでテスト
pytest --cov=video_chapter_trimmer

# 特定のテストファイルを実行
pytest tests/test_parser.py
```

### コードフォーマット

```bash
# Blackでフォーマット
black src/ tests/

# flake8でリント
flake8 src/ tests/

# mypyで型チェック
mypy src/
```

### リリース手順

1. バージョン番号を更新（`setup.py`, `__version__`）
2. CHANGELOGを更新
3. コミットしてタグを作成
   ```bash
   git commit -am "Release version X.Y.Z"
   git tag vX.Y.Z
   git push origin main --tags
   ```

## トラブルシューティング

### ffmpegが見つからない

```
RuntimeError: ffmpeg not found. Please install ffmpeg.
```

→ ffmpegをシステムにインストールしてください（上記の「必要条件」参照）

### チャプターファイルのフォーマットエラー

```
ValueError: Invalid line format: ...
```

→ チャプターファイルの形式を確認してください。各行は `HH:MM:SS.mmm タイトル` の形式である必要があります。

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は[LICENSE](LICENSE)ファイルを参照してください。

## 貢献

プルリクエストを歓迎します！大きな変更を行う場合は、まずissueを開いて変更内容について議論してください。

1. プロジェクトをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/AmazingFeature`)
3. 変更をコミット (`git commit -m 'Add some AmazingFeature'`)
4. ブランチにプッシュ (`git push origin feature/AmazingFeature`)
5. プルリクエストを開く

## 作者

Your Name - [@yourtwitter](https://twitter.com/yourtwitter)

プロジェクトリンク: [https://github.com/yourusername/video-chapter-trimmer](https://github.com/yourusername/video-chapter-trimmer)