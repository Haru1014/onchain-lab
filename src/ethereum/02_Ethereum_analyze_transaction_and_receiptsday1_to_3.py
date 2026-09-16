import json
from pathlib import Path
# 要分析的 Ethereum Block 範圍
START_BLOCK = 25779328
END_BLOCK = 25779328+99
# 02_fetch_100_blocks_day1_to_3抓下來的原始資料位置
BLOCK_DIR = Path("data/raw/ethereum/blocks")
RECEIPT_DIR = Path("data/raw/ethereum/receipts")

# ------------------------------------------------------------
# 分析結果儲存位置
# ------------------------------------------------------------

OUTPUT_DIR = Path("data/processed/ethereum")

OUTPUT_JSON = (
    OUTPUT_DIR
    / f"block_analysis_{START_BLOCK}_to_{END_BLOCK}.json"
)
OUTPUT_CSV = (
    OUTPUT_DIR
    / f"block_analysis_{START_BLOCK}_to_{END_BLOCK}.csv"
)
# ============================================================
# 2. 基本工具函式
# ============================================================
def hex_to_int(value):
    """
    將 Ethereum JSON-RPC 常見的 hex 字串轉成 int。
    例如：
        "0x1"       -> 1
        "0x5208"    -> 21000
    如果本身已經是 int，直接回傳。
    """
    if isinstance(value, str) and value.startswith("0x"):
        return int(value, 16)
    return value
def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

# ============================================================
# 3. Block 分析
# ============================================================

def analyze_block(block_data):
    """
    分析單一 Block JSON。
    這一區只使用：
        block_xxx_original.json
    不讀取 Receipt。
    分析內容：
        1. Block number
        2. Timestamp
        3. Transaction count
        4. Gas limit
        5. Gas used
        6. Gas utilization
        7. ETH transfer count / ratio
        8. Contract call count / ratio
        9. Contract creation count / ratio
    """
    # --------------------------------------------------------
    # Original JSON-RPC Response
    # --------------------------------------------------------
    block = block_data["result"]
    print(f"Analyzing Block: {block['number']}")
    block_number = hex_to_int(block["number"])
    print(f"Analyzing Block: {block_number}")
    timestamp = hex_to_int(block["timestamp"])
    gas_limit = hex_to_int(block["gasLimit"])
    gas_used = hex_to_int(block["gasUsed"])
    # --------------------------------------------------------
    # Transaction
    # --------------------------------------------------------
    transactions = block["transactions"]
    transaction_count = len(transactions)
    # --------------------------------------------------------
    # Transaction 類型統計
    # --------------------------------------------------------

    eth_transfer_count = 0
    contract_call_count = 0
    contract_creation_count = 0
    unknown_count = 0
    for tx in transactions:
        to_address = tx.get("to")
        input_data = tx.get("input", "0x")
        # ----------------------------------------------------
        # Contract Creation
        # Ethereum Contract Creation Transaction 通常： to == None，建立合約沒有呼叫合約
        if to_address is None:
            contract_creation_count += 1
        # ----------------------------------------------------
        # 一般 ETH Transfer
        # 粗略判斷：
        # to != None
        # input == 0x
        # 代表沒有 calldata，(沒有呼叫合約的 function)，
        # 因此通常可以視為單純 ETH transfer。
        # ---------------------------------------------------
        elif input_data == "0x":
            eth_transfer_count += 1
        # ----------------------------------------------------
        # Contract Call
        # to != None
        # input != 0x
        # 通常代表呼叫 Smart Contract 的某個 function。
        # ---------------------------------------------------
        elif input_data != "0x":
            contract_call_count += 1
        else:
            unknown_count += 1

    # --------------------------------------------------------
    # 計算比例
    # --------------------------------------------------------
    if transaction_count > 0:
        eth_transfer_ratio = (eth_transfer_count / transaction_count)
        contract_call_ratio = (contract_call_count / transaction_count)
        contract_creation_ratio = (contract_creation_count / transaction_count)
        unknown_ratio = (unknown_count / transaction_count)
    else:
        eth_transfer_ratio = 0
        contract_call_ratio = 0
        contract_creation_ratio = 0
        unknown_ratio = 0
    # --------------------------------------------------------
    # Gas utilization
    # 表示 Block 的 Gas Limit 有多少比例被實際使用。
    # 例如：
    # gasUsed  = 15,000,000
    # gasLimit = 30,000,000
    # utilization = 0.5 = 50%
    # --------------------------------------------------------
    if gas_limit > 0:
        gas_utilization = gas_used / gas_limit
    else:
        gas_utilization = 0
    # --------------------------------------------------------
    # 回傳 Block 分析結果
    # --------------------------------------------------------
    return {
        "block_number": block_number,
        "timestamp": timestamp,
        # Block gas
        "gas_limit": gas_limit,
        "gas_used": gas_used,
        "gas_utilization": gas_utilization,
        # Transaction count
        "transaction_count": transaction_count,
        # Transaction classification
        "eth_transfer_count": eth_transfer_count,
        "eth_transfer_ratio": eth_transfer_ratio,
        "contract_call_count": contract_call_count,
        "contract_call_ratio": contract_call_ratio,
        "contract_creation_count": contract_creation_count,
        "contract_creation_ratio": contract_creation_ratio,
        "unknown_transaction_count": unknown_count,
        "unknown_transaction_ratio": unknown_ratio,
    }

# ============================================================
# 4. Receipt 分析
# ============================================================
def analyze_receipts(receipt_data):
    """
    分析單一 Block 的 Transaction Receipts。
    這一區只使用：
        block_xxx_receipts_original.json
    不重新讀取 RPC。
    分析內容：
        1. Receipt transaction count
        2. Successful transaction count
        3. Failed transaction count
        4. Failed transaction ratio
        5. Logs = 0 count
        6. Logs = 0 ratio
        7. Total logs
        8. Average logs per transaction
    """
    # --------------------------------------------------------
    # 取得 Receipt
    # --------------------------------------------------------
    receipts = receipt_data["receipts"]
    receipt_count = len(receipts)
    # --------------------------------------------------------
    # 初始化統計
    # --------------------------------------------------------
    success_count = 0
    failed_count = 0
    logs_zero_count = 0
    total_log_count = 0
    # --------------------------------------------------------
    # 逐筆分析 Receipt
    # --------------------------------------------------------
    for receipt_rpc_response in receipts:
        # ----------------------------------------------------
        # Receipt 本身也是 JSON-RPC Response
        #
        # {
        #     "jsonrpc": "2.0",
        #     "result": {...}
        # }
        # ----------------------------------------------------
        receipt = receipt_rpc_response["result"]
        # ----------------------------------------------------
        # Transaction Status
        # 0x1 = Success
        # 0x0 = Failed
        # ----------------------------------------------------
        status = receipt.get("status")
        status = hex_to_int(status)
        if status == 1:
            success_count += 1
        elif status == 0:
            failed_count += 1
        # ----------------------------------------------------
        # Logs
        # ----------------------------------------------------
        logs = receipt.get("logs", [])
        log_count = len(logs)
        total_log_count += log_count
        # ----------------------------------------------------
        # 計算 logs == 0 的交易數
        # ----------------------------------------------------
        if log_count == 0:
            logs_zero_count += 1
    # --------------------------------------------------------
    # Failed transaction ratio
    # --------------------------------------------------------
    if receipt_count > 0:
        failed_transaction_ratio = (failed_count / receipt_count)
        logs_zero_ratio = (logs_zero_count / receipt_count)
        average_logs_per_transaction = (total_log_count / receipt_count)
    else:
        failed_transaction_ratio = 0
        logs_zero_ratio = 0
        average_logs_per_transaction = 0
    # --------------------------------------------------------
    # 回傳 Receipt 分析結果
    # --------------------------------------------------------
    return {
        "receipt_count": receipt_count,
        # Success / Failed
        "success_count": success_count,
        "failed_count": failed_count,
        "failed_transaction_ratio": failed_transaction_ratio,
        # Logs
        "logs_zero_count": logs_zero_count,
        "logs_zero_ratio": logs_zero_ratio,
        "total_log_count": total_log_count,
        "average_logs_per_transaction": average_logs_per_transaction,
    }


# ============================================================
# 5. 分析單一 Block
# ============================================================

def analyze_single_block(block_number):
    """
    分析指定 Block。
    會同時讀取：
        blocks/
            block_xxx_original.json
        receipts/
            block_xxx_receipts_original.json
    但兩個資料來源會分開分析，
    最後再合併成同一筆結果。
    """
    # --------------------------------------------------------
    # Block JSON 路徑
    # --------------------------------------------------------
    block_path = (
        BLOCK_DIR /
        f"block_{block_number}_original.json"
    )
    # --------------------------------------------------------
    # Receipt JSON 路徑
    # --------------------------------------------------------
    receipt_path = (
        RECEIPT_DIR /
        f"block_{block_number}_receipts_original.json"
    )
    # --------------------------------------------------------
    # 檢查 Block 是否存在
    # --------------------------------------------------------
    if not block_path.exists():
        print(
            f"[Skip] Block {block_number} "
            f"file not found."
        )
        return None
    # --------------------------------------------------------
    # 檢查 Receipt 是否存在
    # --------------------------------------------------------
    if not receipt_path.exists():
        print(
            f"[Skip] Receipt for block {block_number} "
            f"not found."
        )
        return None
    print()
    print("========================================")
    print(f"Analyzing Block {block_number}")
    print("========================================")
    # ========================================================
    # A. 從 Block JSON 分析
    # ========================================================
    print("[1/2] Analyzing Block data...")
    block_data = load_json(block_path)
    block_analysis = analyze_block(block_data)
    # ========================================================
    # B. 從 Receipt JSON 分析
    # ========================================================
    print("[2/2] Analyzing Receipt data...")
    receipt_data = load_json(receipt_path)
    receipt_analysis = analyze_receipts(receipt_data)
    # ========================================================
    # C. 檢查 Transaction 數量是否一致
    # ========================================================
    block_transaction_count = (block_analysis["transaction_count"])
    receipt_transaction_count = (receipt_analysis["receipt_count"])
    if block_transaction_count != receipt_transaction_count:
        print(
            "WARNING:"
            f" Block transaction count = "
            f"{block_transaction_count},"
            f" Receipt count = "
            f"{receipt_transaction_count}"
        )
    # ========================================================
    # D. 合併分析結果
    # ========================================================
    #把 block_analysis 和 receipt_analysis 裡面的所有 key-value 拿出來，合併成一個新的 dictionary。
    result = {
        **block_analysis,
        **receipt_analysis,
    }
    return result

# ============================================================
# 6. 分析所有 Block
# ============================================================
def analyze_blocks():
    """
    分析 START_BLOCK ~ END_BLOCK。
    """
    print("========================================")
    print("Ethereum Block Analysis")
    print("========================================")
    print(f"Start block: {START_BLOCK}")
    print(f"End block:   {END_BLOCK}")
    print(
        f"Total blocks: "
        f"{END_BLOCK - START_BLOCK + 1}"
    )
    results = []
    # --------------------------------------------------------
    # 逐一分析 Block
    # --------------------------------------------------------
    for block_number in range(START_BLOCK,END_BLOCK + 1):
        result = analyze_single_block(block_number)
        if result is not None:
            results.append(result)
    return results
# ============================================================
# 7. 儲存 JSON
# ============================================================
def save_json(results):
    """
    將分析結果儲存成 JSON。
    """
    OUTPUT_DIR.mkdir(parents=True,exist_ok=True)
    with open(OUTPUT_JSON,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            results,
            f,
            ensure_ascii=False,
            indent=2
        )

    print()
    print(
        f"Saved JSON analysis to: "
        f"{OUTPUT_JSON}"
    )


# ============================================================
# 8. 儲存 CSV
# ============================================================

def save_csv(results):
    """
    將分析結果儲存成 CSV。
    不使用 pandas，
    避免 analyze 階段需要額外依賴。
    """
    import csv
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    if not results:
        print("No results to save.")
        return

    fieldnames = list(results[0].keys())

    with open(
        OUTPUT_CSV,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(results)

    print(
        f"Saved CSV analysis to: "
        f"{OUTPUT_CSV}"
    )


# ============================================================
# 9. 主程式
# ============================================================

if __name__ == "__main__":

    # --------------------------------------------------------
    # 開始分析
    # --------------------------------------------------------
    results = analyze_blocks()
    # --------------------------------------------------------
    # 儲存分析結果
    # --------------------------------------------------------
    save_json(results)
    save_csv(results)
    # --------------------------------------------------------
    # 完成
    # --------------------------------------------------------

    print()
    print("========================================")
    print("Analysis completed.")
    print(f"Blocks analyzed: {len(results)}")
    print(f"JSON output: {OUTPUT_JSON}")
    print(f"CSV output:  {OUTPUT_CSV}")
    print("========================================")