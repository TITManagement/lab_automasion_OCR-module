# PaddleOCR セキュリティ/オフライン運用ガイド

<!-- README_LEVEL: L3 -->

| 項目 | 内容 |
| --- | --- |
| 文書ID | `LABOCR-SECURITY-OFFLINE-README` |
| 作成日 | `2026-05-03` |
| 作成者 | `Tinoue` |
| 最終更新日 | `2026-05-03` |
| 最終更新者 | `Codex` |
| 版数 | `v1.0` |
| 状態 | `運用中` |

## 概要

対象: [../../vendor/PaddleOCR](../../vendor/PaddleOCR/)

- 取得したソースの版固定
- Python依存の固定化
- SBOMと脆弱性レポートの定期出力
- 閉鎖ネットワーク搬入用のwheelhouse作成

## 使い方

1. [scripts/01_record_source_baseline.sh](scripts/01_record_source_baseline.sh) を実行
2. [scripts/02_export_lock_and_reports.sh](scripts/02_export_lock_and_reports.sh) を実行
3. [scripts/03_build_wheelhouse.sh](scripts/03_build_wheelhouse.sh) を実行

## 依存

- [../../vendor/PaddleOCR](../../vendor/PaddleOCR/) のローカルクローン
- `pip-audit`
- CycloneDX SBOM 出力に必要な Python パッケージ
- 閉鎖ネットワーク搬入用 wheelhouse を作成できる Python 仮想環境

## 出力物

- [reports/source_baseline.txt](reports/source_baseline.txt)
- [reports/requirements.lock.txt](reports/requirements.lock.txt)
- [reports/sbom.cdx.json](reports/sbom.cdx.json)
- [reports/pip_audit.txt](reports/pip_audit.txt)
- [reports/wheelhouse](reports/wheelhouse/)
