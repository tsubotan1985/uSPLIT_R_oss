# microSPLIT-R - Design Document

## Overview

本アプリケーションは、MiniPIX TPX 3台の同時制御・連続データ取得・準リアルタイム分析を実現する PySide6 GUI アプリケーションである。マルチスレッドアーキテクチャを採用し、測定（優先度高）・分析（優先度低）・GUI表示の3系統を分離する。Pixet SDK の非スレッドセーフ制約に対応するため、全ハードウェアアクセスを `threading.Lock` で保護する。

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        GUI Main Thread                          │
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │   Measurement Tab │  │   Training Tab   │                    │
│  │  (Sensor Panels,  │  │  (Folder Select, │                    │
│  │   Plots, Log)     │  │   Progress, Eval)│                    │
│  └────────┬─────────┘  └────────┬─────────┘                    │
│           │ PySide6 signals/slots│                              │
├───────────┼─────────────────────┼──────────────────────────────┤
│  Result Queue (thread-safe)     │                              │
├───────────┼─────────────────────┼──────────────────────────────┤
│           │                     │                              │
│  ┌────────▼─────────┐  ┌───────▼──────────┐                    │
│  │ MeasurementThread │  │ AnalysisThread   │                    │
│  │ (QThread, 高優先) │  │ (QThread, 低優先)│                    │
│  │                   │  │                  │                    │
│  │ acquire_all()     │  │ Loader→Extractor │                    │
│  │ → .out files      │  │ →Classifier→Spec │                    │
│  └────────┬─────────┘  └────────▲─────────┘                    │
│           │                     │                              │
│  ┌────────▼─────────────────────┴──────────┐                    │
│  │            Hardware Layer                │                    │
│  │  PixetManager (singleton)                │                    │
│  │  MultiDeviceController (3台管理)          │                    │
│  │  DeviceController × 3 (Lock付き)          │                    │
│  └──────────────────┬──────────────────────┘                    │
│                     │                                          │
│  ┌──────────────────▼──────────────────────┐                    │
│  │              Pixet SDK                   │                    │
│  │  pypixet.pyd / pxcore.dll / minipix.dll  │                    │
│  └─────────────────────────────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
```

### スレッド優先度設計
| スレッド | 優先度 | 役割 | 実行トリガー |
|---------|--------|------|-------------|
| GUI (Main) | 通常 | 表示更新、ユーザー操作 | イベント駆動 |
| Measurement | **高** | フレーム取得、ファイル保存 | インターバルタイマー |
| Analysis | **低** | 特徴量抽出、分類、スペクトル | 未分析 .out ファイルの監視 |

**測定割り込み機構**: 分析スレッド実行中に次の測定フレーム取得タイミングが来た場合、分析処理を一時中断し測定を優先する。

## Components and Interfaces

### 1. Hardware Layer (`src/hardware/`)

#### PixetManager (`pixet_manager.py`) — Singleton
- `PixetManager.initialize()`: `pypixet.start()` を呼び出しSDK初期化。再呼び出し時は既存インスタンスを返す
- `PixetManager.shutdown()`: `pypixet.exit()` によるクリーンアップ
- `PixetManager.list_devices()`: 接続デバイス一覧の列挙

#### DeviceController (`device_controller.py`)
- 単一デバイスの制御クラス。インスタンスごとに `threading.Lock` を保持
- `connect(device_index)`: デバイスオープンと初期設定
- `load_calibration()`: `dev.deviceID()` の部分一致で `calibration/` のXMLを自動選択
- `acquire_frame()`: **Lock 取得 →** 単一フレーム取得 → 強度データ返却 → **Lock 解放**
- `get_temperature()`: チップ温度取得
- `disconnect()`: デバイスクローズ

#### MultiDeviceController (`multi_device.py`)
- 3台の `DeviceController` を集約管理
- `discover_and_match()`: デバイス列挙 → ID (`E02`/`I03`/`J03`) による自動マッピング
- `acquire_all()`: 3台の `acquire_frame()` を逐次実行（Lockは個別）
- `get_all_temperatures()`: 全センサー温度の一括取得

### 2. Acquisition Layer (`src/acquisition/`)

#### FileSaver (`file_saver.py`)
- `create_measurement_dir(base_path)`: タイムスタンプ付きルートフォルダ + `Sensor01/02/03` サブフォルダ作成
- `save_frame(data, sensor_id, frame_number)`: `.out` ファイル保存。命名: `frame_{NNNNNN}.out`
- `save_metadata(metadata)`: `metadata.json` に測定条件を記録

#### MeasurementThread (`measurement_thread.py`) — QThread
- `run()`: 設定インターバルに基づき測定サイクルをループ実行
  - **0.1秒設定**: 1秒周期で0.1秒間の測定実行 → 残り0.9秒は待機（センサー通信ラグ対策）
  - **1秒設定**: 1秒周期で1秒間の測定実行
  - **10秒設定**: 10秒周期で測定実行
- 停止シグナル受信でループ脱出
- 割り込みカウンタ: 次フレームまでに分析処理が完了しなかった場合、分析を中断し測定を実行するカウントをインクリメント
- emits: `frame_acquired(sensor_id, frame_number, counts)`, `measurement_error(sensor_id, error)`, `interval_missed(count)`

### 3. Analysis Layer (`src/analysis/`)

#### DataLoader (`data_loader.py`)
- `load_out_file(filepath)`: `.out` バイナリの256x256強度行列読み込み
- `preprocess(matrix)`: デッドピクセルマスク (値 > 11000)、エッジクリッピング

#### FeatureExtractor (`feature_extractor.py`)
- `extract_features(matrix)`: `skimage.measure.label` → `regionprops` → 14特徴量 (面積、周囲長、重心、強度統計、形状特徴等, DICAS-ML 由来)
- 返却: `list[dict]` （クラスターごとの特徴量辞書）

#### Classifier (`classifier.py`)
- `load_model(model_path)`: `.joblib` から LightGBM モデル読込
- `predict(features_list)`: 各クラスターの α/β/γ 分類 + 信頼度
- フォールバック: モデル未ロード時は簡易ルールベース分類

#### SpectrumCalculator (`spectrum.py`)
- `compute_energy_spectrum(matrix, cluster_labels)`: α/β/γ/Total 別のエネルギーヒストグラム
- クラスター総強度をエネルギー値に変換（キャリブレーション係数使用）

#### TimeSeriesAggregator (`time_series.py`)
- `accumulate(frame_results)`: フレーム別クラスターカウントの時系列蓄積
- `get_series(sensor_id)`: 指定センサーの時系列データ返却

#### AnalysisThread (`analysis_thread.py`) — QThread
- `run()`: 未分析 `.out` ファイルのポーリング監視
- 処理パイプライン: `DataLoader → FeatureExtractor → Classifier → SpectrumCalculator → TimeSeriesAggregator`
- 測定割り込みチェック: 各ステップ間で `should_yield()` を確認
- emits: `analysis_complete(frame_path, results)`, `classification_updated(sensor_id, counts)`

### 4. Training Layer (`src/training/`)

#### DataPreparer (`data_preparer.py`)
- `prepare_from_folders(alpha_dir, beta_dir, gamma_dir)`: 3フォルダから `.out` を並列読み込み、特徴量抽出、ラベル (0/1/2) 付与
- `split_train_test(features, labels)`: 層化抽出で train/test 分割

#### ModelTrainer (`model_trainer.py`)
- `train(X_train, y_train, params)`: LightGBM 分類器学習（Optuna 最適化オプション付き）
- `evaluate(model, X_test, y_test)`: Accuracy, Precision/Recall/F1 per class, Confusion Matrix

#### ModelSaver (`model_saver.py`)
- `save(model, path, metadata)`: `.joblib` + メタデータJSON保存
  - 出力: `{model_name}.joblib`, `{model_name}_metadata.json`

#### TrainingManager (`training_manager.py`)
- `run_pipeline(alpha_dir, beta_dir, gamma_dir, model_name, filter_threshold)`: 全ステップ統括
- 進捗コールバック: `progress_callback(stage, percent)`

### 5. GUI Layer (`src/gui/`)

#### MainWindow (`main_window.py`)
- QMainWindow + QTabWidget (測定タブ / 学習タブ)
- 下部共通ログパネル (`LogPanel`)
- `setup_menu_bar()`: ファイル/ヘルプメニュー

#### MeasurementControl (`measurement_control.py`)
- Start/Stop ボタン、インターバル ComboBox (0.1s / 1s / 10s)、測定時間設定、保存先 Browse
- 0.1s選択時の補足表示: 「1秒周期で0.1秒間測定（センサー通信ラグ対策）」をツールチップ表示
- 信号接続: Start → MeasurementThread 起動、Stop → 停止シグナル送出

#### SensorPanel (`sensor_panel.py`) × 3
- リアルタイム表示: α/β/γ/Total カウント、温度 (°C)、接続状態インジケータ (●緑/●赤)
- `update_counts(counts_dict)`, `update_temperature(temp)`, `update_status(connected)`

#### PlotWidget (`plot_widget.py`)
- Matplotlib FigureCanvas 埋め込み
- タブ切替: Counts Only (α/β/γ 時系列) / Spectrum (log-log 4パネル)
- 軽量アニメーション更新: `blit` 使用、全再描画回避

#### TrainingTab (`training_tab.py`)
- α/β/γ フォルダ Browse × 3
- α線フィルタ閾値入力、モデル名入力
- 「学習開始」ボタン → TrainingManager を別スレッドで実行
- 進捗バー (QProgressBar)
- 結果表示: 分類レポート (QLabel) + 混同行列/特徴量重要度 (PlotWidget タブ切替)
- 保存先フルパス表示

#### LogPanel (`log_panel.py`)
- QTextEdit (read-only) によるログ表示
- `append_log(level, message)`: タイムスタンプ付きログ追加
- レベル別色分け (INFO=白, WARNING=黄, ERROR=赤)

### 6. Config & Logger (`src/`)

#### Config (`config.py`)
- 設定保存形式: JSON（可読性優先）
- 管理項目: 最終保存先パス、デフォルトインターバル、モデルパス、GUIジオメトリ、ログレベル
- `load()`, `save()`, `get(key, default)`, `set(key, value)`

#### Logger (`logger.py`)
- デュアル出力: ファイル (`logs/app.log`) + GUIログパネル
- スレッドセーフ: `queue.Queue` + 専用ログ出力スレッド
- ログレベル: DEBUG/INFO/WARNING/ERROR

## Data Models

### FrameData
| Field | Type | Description |
|-------|------|-------------|
| `sensor_id` | str | "Sensor01" / "02" / "03" |
| `frame_number` | int | フレーム連番 (6桁ゼロ埋め) |
| `timestamp` | datetime | 取得時刻 |
| `intensity_matrix` | np.ndarray (256×256) | 生強度データ |
| `temperature` | float | チップ温度 (°C) |

### ClusterFeatures
| Field | Type | Description |
|-------|------|-------------|
| `area` | int | クラスター面積 (px) |
| `perimeter` | float | 周囲長 |
| `centroid` | (float, float) | 重心座標 |
| `intensity_max` | float | 最大強度 |
| `intensity_mean` | float | 平均強度 |
| `intensity_sum` | float | 総強度 |
| ... (計14特徴量) | | |

### ClassificationResult
| Field | Type | Description |
|-------|------|-------------|
| `sensor_id` | str | センサー識別子 |
| `frame_number` | int | フレーム番号 |
| `alpha_count` | int | α線クラスター数 |
| `beta_count` | int | β線クラスター数 |
| `gamma_count` | int | γ線クラスター数 |
| `total_count` | int | 総クラスター数 |
| `spectrum` | dict[str, np.ndarray] | α/β/γ/Total 別ヒストグラム |

### TrainingResult
| Field | Type | Description |
|-------|------|-------------|
| `model_path` | str | .joblib フルパス |
| `accuracy` | float | 全体正解率 |
| `f1_score` | float | 加重平均F1 |
| `per_class_metrics` | dict | α/β/γ 別 precision/recall/f1 |
| `confusion_matrix` | np.ndarray | 3×3 混同行列 |
| `feature_importance` | np.ndarray | 14特徴量の重要度 |

## Error Handling

| エラー種別 | 検出場所 | ハンドリング |
|-----------|---------|-------------|
| デバイス未接続 | `MultiDeviceController.discover_and_match()` | 未検出デバイスIDをGUIエリアに「未接続」表示、接続デバイスのみ測定開始 |
| デバイス切断 (実行中) | `DeviceController.acquire_frame()` | 例外キャッチ → 該当センサーのみ停止・赤表示。他センサーは継続 |
| Pixet SDK エラー | `PixetManager.initialize()` | スタートアップチェック、エラーダイアログ表示 |
| ファイルI/Oエラー | `FileSaver.save_frame()` | リトライ1回 → 失敗時はログ出力、測定継続 |
| モデル未ロード | `Classifier.predict()` | ルールベースフォールバック + ログ警告 |
| 分析メモリ不足 | `AnalysisThread.run()` | 処理キュー上限設定、古い未処理ファイルのスキップ |

## Testing Strategy

**テストフレームワーク**: pytest  
**テスト方針**: TDD (Red-Green-Refactor)

### テストレベル

| レベル | 対象 | 手法 |
|--------|------|------|
| ユニットテスト | 全モジュールの個別関数/メソッド | モック/スタブ使用。pytest fixtures で依存注入 |
| 統合テスト | データフロー (測定→I/O→分析→GUIキュー) | モックデバイス + 擬似 .out データ |
| 実機テスト | 3台 MiniPIX 接続のエンドツーエンド | 実デバイス60分間連続測定 + 分析パイプライン通し検証 |

### テストフィクスチャ

- `tests/fixtures/generate_fixtures.py`: 擬似256×256強度データ生成
  - α線: 数ピクセルの高強度クラスタ
  - β線: 中程度の広がりクラスタ
  - γ線: 1-2ピクセル低強度スポット
  - 背景ノイズ: ランダム低値 + デッドピクセル (値 > 11000)
- `tests/fixtures/train_samples/`: α/β/γ 各5ファイル以上のサンプルセット（学習パイプライン結合テスト用）

### テスト実行コマンド
```bash
pytest tests/ -v --cov=src --cov-report=term-missing
```
