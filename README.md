# microSPLIT-R

[![CI](https://github.com/tsubotan1985/uSPLIT_R_oss/actions/workflows/ci.yml/badge.svg)](https://github.com/tsubotan1985/uSPLIT_R_oss/actions/workflows/ci.yml)

Windows 上で **MiniPIX TPX (Standard) 3台** を同時接続し、連続データ取得と準リアルタイム α/β/γ 分類分析を行う Python GUI アプリケーションです。

> **このリポジトリは OSS 版です。** 誰でも fork / 改変 / 再配布できます（MIT）。
> Advacam の Pixet SDK バイナリ、実機のキャリブレーション XML、社内の関連プロジェクトは
> 権利・秘匿の都合で**同梱していません**。手元で動かす場合は Pixet SDK を各自で配置してください（後述）。


## 特徴

### 測定
- **3台同時測定**: MiniPIX TPX (E02/I03/J03) を自動認識・マッチング、同一インターバルでフレーム取得
- **並列センサー取得**: `ThreadPoolExecutor(max_workers=3)` による3センサーの並列フレーム取得
- **精密インターバル制御**: 取得時間を計測し、残り時間だけ待機する正確な周期制御（0.1s / 1s / 10s）
- **ToT モード**: `PX_TPXMODE_TOT` によるエネルギー値取得
- **キャリブレーション自動読込**: `pixet_sdk/configs/MiniPIX-*.xml` からデバイスID一致で自動選択

### 分析
- **14特徴量抽出**: `skimage.measure.regionprops` 由来の14次元特徴量（面積、周囲長、重心、強度統計、形状特徴等）
- **LGBM 分類**: LightGBM 3クラス分類（α/β/γ）。モデル未ロード時はルールベースフォールバック
- **バックグラウンド分析**: `AnalysisWorker` (QThread) が分析処理を GUI スレッドから分離
- **バックグラウンドヒートマップ**: `HitmapWorker` (daemon thread) がピクセルレベルPNGを非同期生成

### 学習
- **LGBM 学習パイプライン**: `.out`/`.txt`/`.dat`/`.asc` ファイルを α/β/γ フォルダから読み込み、14特徴量 + ラベルで学習
- **Optuna ハイパーパラメータ最適化**: 12パラメータをベイズ最適化（3-fold CV × F1-macro、試行回数10〜500）
  - `max_depth`, `num_leaves`, `n_estimators`, `learning_rate`, `feature_fraction`, `subsample`
  - `reg_alpha`, `reg_lambda`, `min_child_samples`, `colsample_bytree`
- **クラス不均衡対策**: `class_weight='balanced'` により α/β/γ のサンプル数偏りを自動調整
- **α線フィルタ**: `intensity_max < 閾値` の α 線クラスタを学習データから除外可能

### 可視化
- **3センサーカウント表示**: α/β/γ/Total カウントをリアルタイム更新
- **ライブセンサー情報**: Temperature（5秒更新）、BiasSense（実測バイアス電圧）、Serial
- **時系列グラフ**: 3センサー縦積み時系列プロット（matplotlib、2秒更新）
- **ピクセルレベルヒートマップPNG**: 全ピクセルを分類色で塗り分け、統計ボックス付きで自動保存
- **分類結果CSV**: `analysis_results/time_series.csv`（フレーム別 α/β/γ カウント）

### 保存構造
```
analysis_results/
├── time_series.csv           # 全センサー統合時系列
├── Sensor01 (E02)/           # センサー別サブフォルダ
│   ├── frame_000001.png
│   ├── frame_000002.png
│   └── ...
├── Sensor02 (I03)/
└── Sensor03 (J03)/
```

## システム要件

- **OS**: Windows 10/11 64bit
- **Python**: 3.12（Pixet SDK `.pyd` ABI 互換性のため固定）
- **ハードウェア**: MiniPIX TPX (Standard) × 3台 + USB 接続
- **SDK**: Pixet SDK API 1.8.5（`pypixet.pyd`, `pxcore.dll`, `minipix.dll` 等）

## セットアップ

```bash
# 仮想環境作成
python -m venv venv

# 仮想環境有効化
venv\Scripts\activate

# 依存パッケージインストール
pip install -r requirements.txt
```

### Pixet SDK の配置

`pixet_sdk/` ディレクトリに以下のファイルを配置してください（Pixet API 1.8.5 より）:

- `pypixet.pyd` — **python312.dll と互換性のあるビルドを使用**
- `pxcore.dll`, `pxproc.dll`, `minipix.dll`
- `pixet.ini`
- `configs/MiniPIX-*.xml` — デバイス別キャリブレーションファイル（Bias電圧・DAC設定）
- `firmware/` — FPGA ファームウェア (.rbf)

## 起動方法

```bash
start_usplit.bat
```

または:

```bash
venv\Scripts\python src\main.py
```

## 使い方

### 測定タブ

1. **保存先**: デフォルト `~/uSPLIT-R/`、必要に応じて Browse
2. **インターバル**: 0.1s / 1s / 10s から選択（0.1s は1秒周期で0.1秒測定のデューティサイクル動作）
3. **モデル選択**: `(rule-based)` フォールバック or 学習済み `.joblib` → **Apply**
4. **コメント**: オプションで測定コメントを入力（`metadata.json` に保存）
5. **Start**: 3センサーの同時測定開始
6. **Stop**: 停止 → `analysis_results/time_series.csv` とヒートマップPNGを保存
7. **Clear**: グラフリセット

### 学習タブ

1. **α/β/γ フォルダ**: 各線源の `.out` / `.txt` / `.dat` / `.asc` ファイルがあるフォルダを Browse
2. **α線フィルタ閾値**: `intensity_max < 閾値` の αクラスタを除外（デフォルト 1000）
3. **モデル名**: 保存先ファイル名（例: `LGBM_20260526_1230`）
4. **Optuna 最適化**: チェックを入れると12ハイパーパラメータをベイズ最適化（試行回数10〜500）
5. **Start Training**: 学習実行 → 進捗バー表示 → Accuracy + Precision/Recall/F1 を表示
6. 保存されたモデルは測定タブのドロップダウンから選択可能（自動でコンフィグ保存）

## プロジェクト構成

```
uSPLIT_R/
├── src/
│   ├── main.py                     # エントリポイント
│   ├── config.py                   # JSON設定管理
│   ├── logger.py                   # スレッドセーフログ
│   ├── hardware/
│   │   ├── pixet_manager.py        # pypixet シングルトン（start/exit）
│   │   ├── device_controller.py    # 単一デバイス制御（Lock + ToT）
│   │   └── multi_device.py         # 3台集約（ThreadPoolExecutor並列取得）
│   ├── acquisition/
│   │   ├── file_saver.py           # フレーム保存（センサー別サブフォルダ）
│   │   └── measurement_thread.py   # 測定QThread（精密周期制御）
│   ├── analysis/
│   │   ├── data_loader.py          # .out 読込 + 前処理
│   │   ├── feature_extractor.py    # 14特徴量抽出（regionprops）
│   │   ├── classifier.py           # LGBM分類器（+ ルールベースフォールバック）
│   │   ├── analysis_thread.py      # 分析QThread
│   │   ├── spectrum.py             # エネルギースペクトル
│   │   └── time_series.py          # 時系列集計
│   ├── training/
│   │   ├── data_preparer.py        # 学習データ準備
│   │   ├── model_trainer.py        # LGBM学習 + Optuna最適化
│   │   ├── model_saver.py          # モデル保存
│   │   └── training_manager.py     # パイプライン統括
│   └── gui/
│       ├── main_window.py          # メインウィンドウ + Analysis/Hitmap/TrainingWorker
│       ├── measurement_control.py  # Start/Stop/Interval/Model選択
│       ├── sensor_panel.py         # センサー個別表示（Count/Temp/Bias/Status）
│       ├── plot_widget.py          # 時系列グラフ（matplotlib）
│       ├── training_tab.py         # 学習タブ（Optuna設定含む）
│       └── log_panel.py            # ログ表示パネル
├── tools/
│   └── check_params.py             # デバイスパラメータ診断ツール
├── tests/                          # pytest + .out フィクスチャ
├── specs/                          # 要件・設計・タスク分解
├── models/                         # 学習済みモデル (.joblib) とメタデータ
├── requirements.txt
└── start_usplit.bat
```

## 分析パイプライン詳細

### 14特徴量一覧

| # | 特徴量 | 説明 | 取得元 |
|---|--------|------|--------|
| 1 | area | クラスター面積 (px) | `regionprops.area` |
| 2 | perimeter | 周囲長 | `regionprops.perimeter` |
| 3 | centroid\_row | 重心 Y | `regionprops.centroid[0]` |
| 4 | centroid\_col | 重心 X | `regionprops.centroid[1]` |
| 5 | intensity\_max | 最大強度（ToT値） | `regionprops.intensity_max` |
| 6 | intensity\_mean | 平均強度 | `regionprops.intensity_mean` |
| 7 | intensity\_sum | 総強度（mean × area） | 計算値 |
| 8 | intensity\_std | 強度標準偏差 | `np.std(intensity_image)` |
| 9 | bbox\_height | バウンディングボックス高さ | `bbox[2] - bbox[0]` |
| 10 | bbox\_width | バウンディングボックス幅 | `bbox[3] - bbox[1]` |
| 11 | eccentricity | 離心率（0=円, 1=線分） | `regionprops.eccentricity` |
| 12 | solidity | 充填率（面積/凸面積） | `regionprops.solidity` |
| 13 | extent | 占有率（面積/バウンディングボックス面積） | `regionprops.extent` |
| 14 | orientation | 主軸角度 [-π/2, π/2] | `regionprops.orientation` |

※ DICAS-ML との互換性: 上記14特徴量は DICAS-ML で使用される特徴量の共通部分集合です。DICAS-ML で学習したモデルも microSPLIT-R で読み込んで使用できます。

### 機械学習パラメータ（Optuna 探索範囲）

| パラメータ | 探索範囲 | 説明 |
|-----------|----------|------|
| max\_depth | 3〜15 | ツリーの最大深さ |
| num\_leaves | 10〜max(10, 2^depth) | 1葉あたりの最大リーフ数 |
| n\_estimators | 100〜1000 (step=50) | ブースティングラウンド数 |
| learning\_rate | 0.01〜0.3 (log) | 学習率 |
| feature\_fraction | 0.6〜1.0 | 特徴量サブサンプリング |
| subsample | 0.6〜1.0 | データサブサンプリング |
| reg\_alpha | 0.0〜10.0 | L1正則化 |
| reg\_lambda | 0.0〜10.0 | L2正則化 |
| min\_child\_samples | 5〜100 | 葉の最小データ数 |
| colsample\_bytree | 0.6〜1.0 | 列サブサンプリング |

固定パラメータ: `objective=multiclass, num_class=3, metric=multi_logloss, boosting_type=gbdt, class_weight=balanced`

## スレッドモデル

```
┌─────────────────────────────────────────────────────────────┐
│                     GUI Main Thread                          │
│  Measurement Tab (SensorPanels / PlotWidget / LogPanel)      │
│  Training Tab (Progress / Results)                           │
│  ┌─────────────────────┐   ┌──────────────────────────────┐ │
│  │ AnalysisWorker      │   │ HitmapWorker                 │ │
│  │ (QThread)           │   │ (daemon threading.Thread)    │ │
│  │ 特徴量抽出+分類     │   │ ピクセルヒートマップPNG生成  │ │
│  └─────────┬───────────┘   └─────────────┬────────────────┘ │
│            │ Qt Signal                    │ Queue           │
├────────────┼──────────────────────────────┼─────────────────┤
│  ┌─────────▼──────────────────────────────▼──────────────┐ │
│  │          MeasurementThread (QThread, 高優先)           │ │
│  │  3ch並列取得 → フレーム保存 → データキュー送出         │ │
│  └─────────────────────────┬──────────────────────────────┘ │
│  ┌─────────────────────────▼──────────────────────────────┐ │
│  │             Hardware Layer                              │ │
│  │  MultiDeviceController (ThreadPoolExecutor 3 workers)  │ │
│  │  DeviceController × 3 (threading.Lock 保護)            │ │
│  │  PixetManager (singleton, pypixetラッパー)              │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

- **測定最優先**: 分析・PNG生成はバックグラウンドスレッドで非同期実行
- **スレッドセーフ**: 全ハードウェアアクセスを `threading.Lock` で保護
- **デーモンスレッド**: HitmapWorker は daemon=True でウィンドウ終了時に自動終了

## 設定ファイル（config.json）

`%APPDATA%\microSPLIT-R\config.json` に保存されます。GUI から変えられる項目以外は直接編集してください。

| キー | 既定値 | 内容 |
|---|---|---|
| `save_dir` | `~/uSPLIT-R` | 測定データの保存先（GUI の Save to と連動） |
| `interval` | `1.0` | 取得インターバル（秒） |
| `model_path` | `""` | 起動時に自動で読み込む学習済みモデル |
| `alpha_filter_threshold` | `1000` | 学習時、`intensity_max` がこれ未満の α クラスタを除外 |
| `dead_pixel_threshold` | `11000` | この値を超えるピクセルをデッドピクセルとして 0 にする |
| `edge_margin_px` | `2` | 端から何ピクセルを捨てるか |
| `rule_based` | 下記 | モデル未使用時のルールベース分類の閾値 |

```json
"rule_based": {
  "alpha_max_intensity": 5000,
  "alpha_max_area": 5,
  "beta_min_area": 5,
  "beta_min_intensity": 2000
}
```

学習済みモデルは読み込み時に**特徴量セットの互換性を検査**します。現行の 14 特徴量と違うモデルは
`ModelFeatureMismatch` となり、GUI には「モデル非互換」の警告が出て適用されません。

## テスト

```bash
pytest tests/ -v
```

## 同梱しないもの（各自で用意）

| 必要なもの | 理由 |
|---|---|
| `pixet_sdk/`（`pypixet.pyd`, `pxcore.dll`, `minipix.dll`, `pixet.ini`, `firmware/`） | Advacam の配布物。再配布不可のため |
| `pixet_sdk/configs/MiniPIX-*.xml`（デバイス別 Bias/DAC キャリブ） | 実機シリアルに紐づく設定。自分の検出器のものを使う |
| 測定データ（`.out` の実測ログ、`analysis_results/`） | サイズと秘匿の都合 |

`tests/fixtures/*.out` には動作確認用の小さなサンプルだけを入れています。

## 同梱モデルについて

`models/` には参考用の学習済み LightGBM モデルが2件入っています（メタデータ JSON 付き）。

- `LGBM_20260120_142338.joblib` — 14特徴量（`area_bbox`, `fractal_dimension` など DICAS-ML 系の特徴量セット）で学習。**現在の `feature_extractor.py` が出力する14特徴量とは名前が一致しない**ため、読み込み時に `ModelFeatureMismatch` となり GUI から適用できません（互換性検査を入れたので黙って誤推論することはありません）。
- `LGBM20260526tentativeusplit.joblib` — 現行の特徴量セットで学習した暫定モデル。精度 0.91 だが β の precision 0.38 と弱い。

モデルを読み込む前に `models/*_metadata.json` の `selected_features` と
`src/analysis/feature_extractor.py` の出力順が一致しているか確認してください。

## コントリビュート

Issue / Pull Request を歓迎します。まずは Issue を立てて方針をすり合わせてください。
校正データや実測ログは各自の環境に依存するので、共有が必要な場合は**匿名化した最小サンプル**でお願いします。

## ライセンス

MIT（`LICENSE` 参照）。ただし次のものは MIT の対象外です。

- Advacam の Pixet SDK / pypixet（各自のライセンスに従う）
- 論文等で公開している測定データ（別途の条件があればそれに従う）

MiniPIX / Pixet / Advacam は Advacam s.r.o. の商標または製品名です。本リポジトリは Advacam 非公式のツールです。

