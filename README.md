# Blockchain Data Collection and Analysis

本專案以 Ethereum 與 Solana 公開鏈上資料為研究對象，練習區塊鏈資料的擷取、儲存、解析與分析，並逐步建立可重現的資料處理流程。

目前專案分為 Ethereum 與 Solana 兩個部分。兩者各自具有獨立的資料擷取方式、原始資料格式與分析程式。

> 本專案以公開鏈上資料為研究材料，不執行 Mainnet 交易。研究指標與資料處理流程仍在持續驗證與調整中。

---

# 1. Project Structure

```text
onchain-lab/
├── data/
│   ├── raw/
│   │   ├── ethereum/
│   │   │   ├── blocks/
│   │   │   └── receipts/
│   │   └── solana/
│   │       └── blocks/
│   └── processed/
│       └── solana/
├── src/
│   ├── common/
│   ├── ethereum/
│   │   ├── 01_rpc_test.py
│   │   ├── 02_Ethereum_analyze_transaction_and_receiptsday1_to_3.py
│   │   ├── 02_Ethereum_undestand_day1_to_3.py
│   │   ├── 02_fetch_100_blocks_day1_to_3.py
│   │   ├── 02_read_ERC_20_fundamental_info_day4_to_5.py
│   │   ├── 02_read_transfer_log_info_day4_to_5.py
│   │   ├── 02_study_Ethereum_slice_for_analyze_number.py
│   │   └── 02_study_Ethereum_slice_for_fetch.py
│   └── solana/
│       ├── 01_first_solana_program.py
│       ├── 02_analyze_solana_slots.py
│       ├── 02_solana_fetch_slots_and_save.py
│       └── solana_rpc_test.py
├── .env
├── .gitignore
└── README.md
```

| Directory | Description |
|---|---|
| `data/raw/` | 儲存從 RPC 擷取的原始資料。 |
| `data/processed/` | 儲存整理與分析後的資料。 |
| `src/ethereum/` | Ethereum 資料擷取、學習與分析程式。 |
| `src/solana/` | Solana 資料擷取、學習與分析程式。 |
| `src/common/` | 預留給共用函式與工具。 |

`data/` 下的資料夾會由程式依照設定建立；尚未執行資料擷取時，部分資料夾可能不存在。

---

# 2. Ethereum

## 2.1 Research Overview

Ethereum 部分目前以 Ethereum 區塊、交易與交易收據（Transaction Receipt）為主要資料，並以 ERC-20 USDC Transfer Event 作為初期研究主題。

目前工作包含：

- 透過 Ethereum RPC 擷取區塊與完整交易資料。
- 取得區塊內交易對應的 Transaction Receipt。
- 讀取 ERC-20 合約基本資訊。
- 解析 ERC-20 Transfer Event Log。
- 整理交易與收據資料，供後續分析使用。

## 2.2 Data Collection

主要資料擷取程式：

```text
src/ethereum/02_fetch_100_blocks_day1_to_3.py
```

目前程式設定：

| Parameter | Value |
|---|---|
| Start block | `25779328` |
| End block | `25779427` |
| Number of blocks | `100` |
| Request timeout | `30` seconds |
| Maximum retries | `3` |
| Retry delay | `2` seconds |
| Fetch mode | `original` |

程式支援兩種擷取方式：

- `original`：透過 raw JSON-RPC request 取得資料。
- `web3`：透過 Web3.py 取得資料。

目前預設使用 `original` 模式。

主要執行流程：

1. 從環境變數讀取 Ethereum RPC URL。
2. 建立 RPC 連線並確認連線狀態。
3. 逐一取得指定範圍內的 blocks，並包含完整交易資訊。
4. 將 block 資料儲存成 JSON。
5. 從 block 資料中取得 transaction hashes。
6. 依照 transaction hash 取得對應的 receipts。
7. 將 receipts 獨立儲存成 JSON。

程式包含 request timeout、失敗重試，以及略過已存在 block 檔案的處理。

## 2.3 Raw Data Structure

Ethereum 原始資料分別儲存在 block 與 receipt 資料夾：

```text
data/raw/ethereum/
├── blocks/
│   ├── block_25779328_original.json
│   ├── block_25779329_original.json
│   └── ...
└── receipts/
    ├── block_25779328_receipts_original.json
    ├── block_25779329_receipts_original.json
    └── ...
```

| Data | Filename |
|---|---|
| Block | `block_<block_number>_original.json` |
| Receipts | `block_<block_number>_receipts_original.json` |

Block JSON 保存區塊與完整交易資訊。Receipt JSON 則依照 block number 整理該區塊內交易的 receipts。

## 2.4 Initial Research Topic: ERC-20 USDC Transfers

目前初期研究使用 Ethereum 上的 USDC 合約，觀察 ERC-20 Transfer Event。

| Parameter | Value |
|---|---|
| Blockchain | Ethereum |
| Token | USDC |
| Contract address | `0xA0b86991c6218b36c1d19d4a2e9eb0cE3606eB48` |
| Observation period | 2026-07-01 to 2026-07-31 |

相關程式：

| Script | Purpose |
|---|---|
| `02_read_ERC_20_fundamental_info_day4_to_5.py` | 讀取 ERC-20 合約基本資訊。 |
| `02_read_transfer_log_info_day4_to_5.py` | 學習與讀取 Transfer Event Log。 |
| `02_Ethereum_analyze_transaction_and_receiptsday1_to_3.py` | Transaction 與 Receipt 相關分析。 |
| `02_Ethereum_undestand_day1_to_3.py` | Ethereum 資料結構與相關概念的學習程式。 |
| `02_study_Ethereum_slice_for_analyze_number.py` | Ethereum 資料分析切片相關實驗。 |
| `02_study_Ethereum_slice_for_fetch.py` | Ethereum 資料擷取切片相關實驗。 |

以上用途依照目前檔名與已檢視程式整理；其他程式的詳細輸入、輸出與分析定義，仍應以程式內容及後續驗證為準。

---

# 3. Solana

## 3.1 Research Overview

Solana 部分目前以 Slot 對應的 Block 資料為主要研究材料，透過 RPC 取得 block 及其 transactions，再進行不同層級的資料分析。

目前分析分為三個層級：

- **Slot-level：** 觀察每個 slot 是否有 block，以及 block 中的交易數量與交易狀態。
- **Transaction-level：** 整理每筆交易的 signature、fee、transaction version 與 Program 呼叫資訊。
- **Program-level：** 統計不同 Program 被呼叫的次數，以及涉及的交易數量。

## 3.2 Data Collection

主要資料擷取程式：

```text
src/solana/02_solana_fetch_slots_and_save.py
```

目前程式設定：

| Parameter | Value |
|---|---|
| Start slot | `443900000` |
| End slot | `443900999` |
| Number of slots | `1,000` |
| Maximum supported transaction version | `0` |

主要執行流程：

1. 從環境變數讀取 Solana RPC URL。
2. 建立 Solana RPC client。
3. 逐一查詢指定範圍內的 slots。
4. 取得 block 資料。
5. 將每個 slot 的回傳 block 儲存成獨立 JSON 檔案。
6. 若遇到錯誤，印出該 slot 的錯誤訊息並繼續處理後續 slot。

## 3.3 Raw Data Structure

Solana 原始 block 資料儲存在：

```text
data/raw/solana/blocks/
```

檔案命名方式：

```text
slot_<slot_number>_original.json
```

例如：

```text
data/raw/solana/blocks/
├── slot_443900000_original.json
├── slot_443900001_original.json
├── slot_443900002_original.json
└── ...
```

每個 JSON 檔案對應一個 slot 的 block 資料。若查詢結果沒有 block，程式會將該結果儲存為 JSON `null`。

## 3.4 Data Analysis

主要分析程式：

```text
src/solana/02_analyze_solana_slots.py
```

分析程式讀取本地原始 JSON 檔案，並產生 Slot-level、Transaction-level 與 Program-level 三種分析結果。

### A. Slot-level Analysis

| Field | Description |
|---|---|
| `slot_num` | Slot number。 |
| `has_block` | 該 slot 是否有 block。 |
| `transaction_count` | 該 block 中的 transaction 數量。 |
| `success_count` | 成功交易數量。 |
| `failed_count` | 失敗交易數量。 |
| `legacy_count` | Legacy transaction 數量。 |
| `versioned_count` | Versioned transaction 數量。 |
| `versioned_ratio` | Versioned transaction 數量占總交易數的比例。 |

目前程式中的計算方式：

```text
versioned_ratio = versioned_count / transaction_count
```

當 `transaction_count` 為 0 時，`versioned_ratio` 設為 0。

### B. Transaction-level Analysis

| Field | Description |
|---|---|
| `slot_num` | Transaction 所屬的 slot。 |
| `transaction_index` | Transaction 在 block 中的索引位置。 |
| `signature` | Transaction signature。 |
| `success` | Transaction 成功狀態。 |
| `fee_lamports` | Transaction fee，以 lamports 表示。 |
| `fee_sol` | Transaction fee，換算為 SOL。 |
| `transaction_version` | Transaction version 類型。 |
| `outer_program_ids` | Outer instructions 中的 Program IDs。 |
| `inner_program_ids` | Inner instructions 中的 Program IDs。 |

SOL 與 lamports 的換算：

```text
1 SOL = 1,000,000,000 lamports
```

### C. Program-level Analysis

| Field | Description |
|---|---|
| `program_id` | Program 的識別碼。 |
| `call_count` | Program 被呼叫的總次數。 |
| `outer_count` | Program 在 outer instructions 中被呼叫的次數。 |
| `inner_count` | Program 在 inner instructions 中被呼叫的次數。 |
| `tx_count` | 呼叫過該 Program 的不重複 transaction 數量。 |

`call_count` 與 `tx_count` 的計算單位不同：

- `call_count` 計算 instruction 層級的呼叫次數。
- `tx_count` 計算 transaction 層級的不重複交易數量。

因此，同一筆 transaction 即使多次呼叫相同 Program，`call_count` 仍會增加多次，但 `tx_count` 只計算一次。

## 3.5 Processed Data Outputs

分析結果儲存在：

```text
data/processed/solana/
```

目前會產生三份 CSV：

| Output file | Content |
|---|---|
| `slot_summary_<START_SLOT>_<END_SLOT>.csv` | Slot-level summary。 |
| `transaction_details_<START_SLOT>_<END_SLOT>.csv` | Transaction-level details。 |
| `program_id_stats_<START_SLOT>_<END_SLOT>.csv` | Program-level statistics。 |

---

# 4. Environment Setup

## 4.1 Python Environment

目前開發環境使用 Python 3.11.9。

在專案根目錄建立虛擬環境：

```powershell
python -m venv .venv
```

啟動虛擬環境：

```powershell
.\.venv\Scripts\Activate.ps1
```

確認 Python 執行路徑與版本：

```powershell
python --version
python -c "import sys; print(sys.executable)"
```

若專案根目錄已有 `requirements.txt`，可使用以下指令安裝套件：

```powershell
pip install -r requirements.txt
```

> `requirements.txt` 的內容與套件版本仍需整理及驗證。目前不應將尚未確認的套件清單視為最終環境規格。

## 4.2 Environment Variables

在專案根目錄建立 `.env`：

```env
ETHEREUM_RPC_URL=your_ethereum_rpc_url
SOLANA_RPC_URL=your_solana_rpc_url
```

將 placeholder 替換成可用的 RPC endpoint。

程式會透過 `python-dotenv` 載入環境變數。請勿將 `.env`、RPC API keys 或其他敏感資訊提交到 GitHub。

---

# 5. Reproducibility and Research Records

為了讓資料擷取與分析可以重現，每次研究應記錄以下資訊：

- 使用的 blockchain network。
- RPC 資料來源。
- Block number 或 slot 範圍。
- 資料擷取日期。
- 使用的程式與程式版本。
- 資料格式與儲存位置。
- 擷取失敗、缺漏資料及重試情況。
- 分析指標的計算方式與排除條件。

原始資料與分析結果應分開保存。分析時盡量使用已儲存的原始資料，避免每次分析都重新向 RPC 擷取資料。

---

# 6. Current Progress and Future Work

## Ethereum

- [x] 建立 Ethereum RPC 連線與資料擷取程式。
- [x] 擷取指定範圍的 blocks 與 transaction receipts。
- [x] 開始探索 ERC-20 合約資訊與 Transfer Event Log。
- [ ] 完整驗證 block 與 receipt 的資料完整性。
- [ ] 與 Dune 等外部資料來源交叉比對。
- [ ] 明確定義研究問題、指標公式與資料排除條件。

## Solana

- [x] 建立 Solana RPC block 擷取程式。
- [x] 將 slot 對應的 block 資料儲存為 JSON。
- [x] 建立 Slot-level、Transaction-level 與 Program-level 分析程式。
- [ ] 確認擷取與分析使用的 slot 範圍一致。
- [ ] 驗證原始 JSON 結構與 transaction version 判斷。
- [ ] 確認 Address Lookup Tables（ALT）及 loaded addresses 的處理方式。
- [ ] 區分沒有 block、原始檔案缺失及資料擷取失敗。
- [ ] 明確定義研究指標與資料排除條件。

## Project-wide

- [ ] 整理並固定必要套件及版本。
- [ ] 在乾淨環境中驗證完整執行流程。
- [ ] 加強資料完整性檢查與錯誤紀錄。
- [ ] 確保程式、資料說明與研究日誌內容一致。
- [ ] 建立可重現的研究實驗流程。

---

# 7. Notes

本 Repository 仍處於研究與開發階段。現有程式代表目前已實作的資料擷取與分析流程，不代表所有資料欄位、統計指標及分析結果都已完成驗證。

在正式使用分析結果前，仍須確認資料完整性、欄位定義、計算公式及排除規則。