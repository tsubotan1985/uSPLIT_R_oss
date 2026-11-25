# microSPLIT-R - Task List

## Implementation Tasks

- [x] 0. **Phase 0: プロジェクトセットアップ**
    - [x] 0.1. Python 3.12 仮想環境の構築と依存パッケージのインストール
        - *Goal*: 再現可能な開発環境を確立する
        - *Details*: `python -m venv venv` で仮想環境作成後、`requirements.txt` から全依存をインストール。`lightgbm` は Windows ビルド済みwheel (`--only-binary=lightgbm`) を使用。`scikit-image` バージョンは `measure.label` / `regionprops` 互換のため 0.22〜0.25 に固定
        - *Requirements*: 非機能要件（Python 3.12 互換性）
    - [x] 0.2. Pixet SDK の配置
        - *Goal*: MiniPIX ハードウェア通信の基盤を整える
        - *Details*: `pixet_sdk/` に `pypixet.pyd`, `pxcore.dll`, `pxproc.dll`, `minipix.dll`, `pixet.ini`, `configs/`, `firmware/`, VC++ ランタイム DLL を配置。`pixet.ini` の `[hwlibs]` に `minipix.dll` が登録されていることを確認
        - *Requirements*: コア機能1（マルチデバイス制御）
    - [x] 0.3. ディレクトリ構造の構築
        - *Goal*: モジュール分割に沿ったソースコード配置を確立する
        - *Details*: `src/`, `tests/` および下位モジュール (`hardware/`, `acquisition/`, `analysis/`, `training/`, `gui/`) に `__init__.py` を作成
        - *Requirements*: 設計書アーキテクチャ構成
    - [x] 0.4. .gitignore と VS Code 設定
        - *Goal*: バージョン管理と開発効率の向上
        - *Details*: `.gitignore` に `venv/`, `pixet_sdk/`, `__pycache__/`, `.pytest_cache/` 等を追加。`.vscode/settings.json` でインタープリタパスを設定、`.vscode/launch.json` で `src/main.py` のデバッグ起動を設定
        - *Requirements*: 開発ワークフロー基盤

- [x] 1. **Phase 1: 設定・ログ基盤 (TDD)**
    - [x] 1.1. アプリ設定管理 (`src/config.py`)
        - *Goal*: JSON ベースの設定管理機構を実装する
        - *Details*: `load()` / `save()` / `get(key, default)` / `set(key, value)` の4メソッド。管理項目: 最終保存先パス、デフォルトインターバル、モデルパス、GUIジオメトリ、ログレベル
        - *Requirements*: コア機能2（連続データ取得の設定要素）
    - [x] 1.2. Config のテスト実装 (`tests/test_config.py`)
        - *Goal*: 設定のロード/セーブ/デフォルト値が正しく動作することを検証する
        - *Details*: 存在しないファイルからのデフォルト値読込、保存→再読込の整合性、欠落キーへのフォールバックテスト
        - *Requirements*: 受入基準（テストカバレッジ）
    - [x] 1.3. スレッドセーフなログシステム (`src/logger.py`)
        - *Goal*: ファイルと GUI の両方に安全にログ出力できる基盤を提供する
        - *Details*: `queue.Queue` + 専用ログ出力スレッドによるスレッドセーフ設計。レベル別色分け (DEBUG/INFO/WARNING/ERROR)。回転ファイル出力 (`logs/app.log`)
        - *Requirements*: 非機能要件（スレッド安全性）、コア機能4（GUIログパネル）

- [x] 2. **Phase 2: ハードウェア制御層 (TDD + Sequential Thinking)**
    - [x] 2.1. Pixet SDK シングルトン管理 (`src/hardware/pixet_manager.py`)
        - *Goal*: `pypixet.start/exit` のライフサイクルを一元管理する
        - *Details*: シングルトンパターンで実装。`initialize()` で初回のみ `pypixet.start()` を呼び出し。`shutdown()` で `pypixet.exit()`。`list_devices()` で接続デバイス列挙
        - *Requirements*: コア機能1（マルチデバイス制御）
    - [x] 2.2. 単一デバイス制御 (`src/hardware/device_controller.py`)
        - *Goal*: 1台の MiniPIX の初期化・取得・キャリブレーションをスレッドセーフに制御する
        - *Details*: **必ず `threading.Lock` を実装**。`connect()`, `load_calibration()` (デバイスID部分一致でXML自動選択), `acquire_frame()`, `get_temperature()`, `disconnect()`。Lock取得→ハードウェア操作→Lock解放の一貫したパターン
        - *Requirements*: コア機能1、非機能要件（スレッド安全性）
        - *Sequential Thinking*: マルチスレッド競合リスクの論理展開後に実装
    - [x] 2.3. 3台同時制御 (`src/hardware/multi_device.py`)
        - *Goal*: 3台の DeviceController を集約し、デバイス発見と自動マッチングを行う
        - *Details*: `discover_and_match()` でデバイスID (`E02`/`I03`/`J03`) による自動マッピング。`acquire_all()` で3台逐次取得（Lockは個別）。未接続デバイスはスキップし接続済みのみ処理
        - *Requirements*: コア機能1、受入基準（3台同時認識、キャリブレーション自動選択）
    - [x] 2.4. ハードウェア層のテスト実装
        - *Goal*: モックデバイスを用いた初期化・エラーハンドリングのテスト
        - *Details*: モック `pypixet` を用いた PixetManager テスト、未接続エラー時の例外テスト、デバイスIDマッチングのユニットテスト
        - *Requirements*: 受入基準（デバイス未接続時のエラーハンドリング、テストカバレッジ）

- [x] 3. **Phase 3: データ取得モジュール (TDD)**
    - [x] 3.1. ファイル保存機構 (`src/acquisition/file_saver.py`)
        - *Goal*: タイムスタンプ付きフォルダ構造と .out ファイルの命名規則を実装する
        - *Details*: `create_measurement_dir(base_path)` で `{タイムスタンプ}/Sensor01/02/03/` を作成。`save_frame()` で `frame_{NNNNNN}.out` を保存。`save_metadata()` で `metadata.json` 出力。I/Oエラー時はリトライ1回→ログ出力
        - *Requirements*: コア機能2、受入基準（ファイル命名規則）
    - [x] 3.2. 測定スレッド (`src/acquisition/measurement_thread.py`)
        - *Goal*: QThread ベースでインターバル測定ループを実装する
        - *Details*: `run()` でインターバルタイマーに基づく `acquire_all()` + `save_frame()` ループ。0.1秒設定時は1秒周期のうち0.1秒間測定・0.9秒待機。停止シグナル受信で安全に終了。emits: `frame_acquired`, `measurement_error`, `interval_missed`
        - *Requirements*: コア機能2、非機能要件（パフォーマンス: 0.1秒デューティサイクル）
    - [x] 3.3. スレッド割り込みテスト
        - *Goal*: 測定中停止シグナル・次フレーム割り込みが正常機能することを検証する
        - *Details*: 擬似デバイス + QThread の結合テスト。停止シグナルの応答時間測定、インターバル逸脱時のカウント検証
        - *Requirements*: 受入基準（測定割り込み機構）

- [x] 4. **Phase 4: 分析モジュール (TDD + Fetch 推奨)**
    - [x] 4.1. .out データ読み込みと前処理 (`src/analysis/data_loader.py`)
        - *Goal*: .out バイナリから 256×256 強度行列を読み込み、デッドピクセルとエッジクリッピングを適用する
        - *Details*: バイナリパース (ヘッダ + 強度データ)。デッドピクセル: 値 > 11000 をマスク。エッジクリッピング: 周辺ピクセルの閾値処理
        - *Requirements*: コア機能3（準リアルタイム分析）
    - [x] 4.2. 14特徴量抽出 (`src/analysis/feature_extractor.py`)
        - *Goal*: `skimage.measure.label` + `regionprops` で DICAS-ML 由来の14特徴量を抽出する
        - *Details*: 連結成分ラベリング → 各クラスターの area, perimeter, centroid, intensity_max/mean/sum, 形状特徴等。返却: `list[dict]`
        - *Requirements*: コア機能3
    - [x] 4.3. LightGBM 分類器 (`src/analysis/classifier.py`)
        - *Goal*: 学習済みモデルで α/β/γ 線分類を実行する
        - *Details*: `load_model()` で `.joblib` 読込。`predict()` で各クラスターの分類 + 信頼度。モデル未ロード時は簡易ルールベースにフォールバック
        - *Requirements*: コア機能3, 5
    - [x] 4.4. スペクトルと時系列集計 (`src/analysis/spectrum.py` & `time_series.py`)
        - *Goal*: エネルギースペクトルヒストグラムとフレーム別クラスターカウントの時系列を生成する
        - *Details*: α/β/γ/Total 別のヒストグラム + クラスター総強度のエネルギー換算。時系列: フレーム別クラスターカウントの累積蓄積
        - *Requirements*: コア機能3, 4
    - [x] 4.5. 分析スレッド (`src/analysis/analysis_thread.py`)
        - *Goal*: QThread ベースで未分析ファイルを監視し、処理結果をGUI向けキューに送信する
        - *Details*: `run()` で未分析 `.out` のポーリング監視。パイプライン: `DataLoader→FeatureExtractor→Classifier→SpectrumCalculator→TimeSeriesAggregator`。各ステップ間で測定割り込みの `should_yield()` チェック。emits: `analysis_complete`, `classification_updated`
        - *Requirements*: コア機能3、受入基準（測定優先割り込み）、非機能要件（ファイルI/O競合防止）

- [x] 5. **Phase 4.5: 学習モジュール (TDD)**
    - [x] 5.1. データ準備 (`src/training/data_preparer.py`)
        - *Goal*: α/β/γ フォルダから .out を並列読込し、特徴量抽出とラベル付与を行う
        - *Details*: 3フォルダから全 .out を列挙 → 並列で DataLoader + FeatureExtractor → ラベル (α=0, β=1, γ=2) 付与 → 層化抽出で train/test 分割。α線フィルタ閾値 (intensity_max < 閾値 → 除外)
        - *Requirements*: コア機能5
    - [x] 5.2. モデル学習と評価 (`src/training/model_trainer.py` & `evaluation.py`)
        - *Goal*: LightGBM 分類器の学習、Optuna 最適化、混同行列生成
        - *Details*: `train()`: LGBM学習。Optuna 利用不可時はデフォルトパラメータにフォールバック。`evaluate()`: Accuracy, Precision/Recall/F1 per class, 混同行列3×3
        - *Requirements*: コア機能5
    - [x] 5.3. モデル保存とパイプライン統括 (`src/training/model_saver.py` & `training_manager.py`)
        - *Goal*: 学習済みモデルとメタデータを保存し、全パイプラインを統括する
        - *Details*: `save()`: `.joblib` + `_metadata.json` 出力。`TrainingManager.run_pipeline()`: データ準備→学習→評価→保存の一括実行 + 進捗コールバック
        - *Requirements*: コア機能5、コア機能4（GUI学習タブ）

- [x] 6. **Phase 5: GUI 実装 (PySide6)**
    - [x] 6.1. メインウィンドウとタブ構成 (`src/gui/main_window.py`)
        - *Goal*: QTabWidget（測定タブ/学習タブ）+ 共通ログパネルの基本レイアウトを実装する
        - *Details*: QMainWindow ベース。メニューバー（ファイル/ヘルプ）。下部に LogPanel を固定配置。QTabWidget で測定タブと学習タブを切り替え
        - *Requirements*: コア機能4
    - [x] 6.2. 測定制御とセンサーパネル (`src/gui/measurement_control.py` & `sensor_panel.py`)
        - *Goal*: 測定操作インターフェースとセンサー別リアルタイム表示を提供する
        - *Details*: MeasurementControl: Start/Stop/Interval ComboBox（0.1s/1s/10s、0.1s選択時ツールチップ表示）/保存先Browse。SensorPanel×3: α/β/γ/Total カウント、温度 (°C)、接続状態インジケータ (●緑/●赤)
        - *Requirements*: コア機能4（測定タブ）
    - [x] 6.3. プロットウィジェット (`src/gui/plot_widget.py`)
        - *Goal*: Matplotlib 埋め込みで時系列プロットとエネルギースペクトルを表示する
        - *Details*: FigureCanvas 埋め込み。タブ切替: Counts Only (α/β/γ 時系列) / Spectrum (log-log 4パネル: α/β/γ/Total)。`blit` 使用の軽量アニメーション更新
        - *Requirements*: コア機能4（可視化）
    - [x] 6.4. 学習タブ (`src/gui/training_tab.py`)
        - *Goal*: 学習用設定・進捗表示・評価結果表示の UI を提供する
        - *Details*: α/β/γ フォルダ Browse×3、α線フィルタ閾値入力、モデル名入力、「学習開始」ボタン→TrainingManager 別スレッド実行、QProgressBar 進捗、分類レポート (QLabel)、混同行列/特徴量重要度を PlotWidget タブ切替で表示
        - *Requirements*: コア機能4（学習タブ）, 5
    - [x] 6.5. ログパネル (`src/gui/log_panel.py`)
        - *Goal*: リアルタイムログ出力を GUI 上で提供する
        - *Details*: QTextEdit (read-only)。Logger のキューから信号経由でログ受信。レベル別色分け (INFO=白, WARNING=黄, ERROR=赤)。タイムスタンプ付き
        - *Requirements*: コア機能4（共通ログパネル）

- [x] 7. **Phase 6: 統合・最適化**
    - [x] 7.1. エントリポイント実装 (`src/main.py`)
        - *Goal*: アプリケーション起動のエントリポイントを完成させる
        - *Details*: QApplication 初期化、PixetManager 起動、Config 読み込み、MainWindow 表示、シャットダウン時のクリーンアップ（PixetManager.shutdown, Config.save）
        - *Requirements*: 全コア機能の統合
    - [x] 7.2. データフロー結合テスト
        - *Goal*: 測定 → I/O → 分析 → GUIキュー の一連の動作を検証する
        - *Details*: モックデバイス + 擬似 .out データを用いたエンドツーエンドテスト。結果キュー経由で GUI 表示まで到達することを確認
        - *Requirements*: 受入基準（全データフロー）
    - [x] 7.3. パフォーマンスチューニング
        - *Goal*: 実効インターバルの計測と最適化
        - *Details*: 各インターバル設定での実効周期を計測。分析スレッドの処理時間分布をプロファイリング。0.1秒デューティサイクルの実効性検証
        - *Requirements*: 非機能要件（パフォーマンス）
    - [x] 7.4. 耐障害性の最終確認
        - *Goal*: デバイス切断・I/Oエラー等の異常系ハンドリングを確認する
        - *Details*: デバイス切断シミュレーション、ディスクフル状態の模擬、SDK起動失敗のテスト
        - *Requirements*: 非機能要件（耐障害性）
    - [x] 7.5. **実デバイス接続試験** ★
        - *Goal*: 3台の実 MiniPIX TPX を接続し、全機能のエンドツーエンド検証を実施する
        - *Details*:
          1. 3台全センサーの認識・IDマッチング・キャリブレーション自動ロードを確認
          2. インターバル 1秒で60分間の連続測定を実行し、.out 保存・ファイル命名規則を検証
          3. インターバル 0.1秒（デューティサイクル動作）の安定性を確認
          4. 分析パイプライン（特徴量抽出→分類→スペクトル）が全センサーで正常動作することを確認
          5. GUI のリアルタイムカウント表示・温度表示・時系列プロットが更新されることを確認
          6. 測定中に1台のUSBを抜き差しし、他2台の測定継続と再接続時の復帰を確認
          7. 学習タブでα/β/γ実データを使ったLGBM学習パイプラインの通し検証
        - *Requirements*: 全受入基準の最終確認

## Task Dependencies

```
Phase 0 (セットアップ)
    │
    ▼
Phase 1 (設定・ログ基盤)
    │
    ▼
Phase 2 (ハードウェア制御層)
    │
    ├──────────────────────┐
    ▼                      ▼
Phase 3 (データ取得)    Phase 4 (分析モジュール)
    │                      │
    └────────┬─────────────┘
             ▼
    Phase 4.5 (学習モジュール)
             │
             ▼
    Phase 5 (GUI 実装)
             │
             ▼
    Phase 6 (統合・最適化) ── 7.5 実デバイス試験 ★
```

- Phase 0 → Phase 1: 基盤がなければ後続の実装不可
- Phase 1 → Phase 2: ハードウェア層はログ出力に依存
- Phase 2 → Phase 3, 4: ハードウェア層をモックすることで Phase 3 と Phase 4 は並行開発可能
- Phase 3, 4 → Phase 4.5: 学習モジュールは分析モジュールに依存
- Phase 4.5 → Phase 5: GUI は全バックエンド機能の統合先
- Phase 5 → Phase 6.1〜6.4: エントリポイント・結合テスト・最適化・耐障害性
- Phase 6.1〜6.4 → Phase 6.5 (7.5): **実デバイス試験は全Phase完了後に実施**

## Estimated Timeline

| Phase | 内容 | 目安時間 |
|-------|------|----------|
| Phase 0 | プロジェクトセットアップ | 2h |
| Phase 1 | 設定・ログ基盤 | 3h |
| Phase 2 | ハードウェア制御層 | 6h |
| Phase 3 | データ取得モジュール | 4h |
| Phase 4 | 分析モジュール | 8h |
| Phase 4.5 | 学習モジュール | 6h |
| Phase 5 | GUI 実装 | 8h |
| Phase 6.1〜6.4 | 統合・最適化 | 5h |
| Phase 6.5 (7.5) | 実デバイス接続試験 ★ | 3h |
| **合計** | | **45h** |
