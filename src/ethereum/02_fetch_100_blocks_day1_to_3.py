import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3
from web3.exceptions import TimeExhausted
import requests
# 指定要抓取的 Ethereum Block 範圍
START_BLOCK = 25779328
END_BLOCK = 25779328+99
REQUEST_TIMEOUT = 30 # 每次 RPC Request 的 timeout（秒）
MAX_RETRIES = 3 # RPC 失敗時最多重試幾次
RETRY_DELAY = 2 # 每次 retry 前等待幾秒
OUTPUT_DIR = Path("data/raw/ethereum/blocks")# 原始資料儲存位置
RECEIPT_OUTPUT_DIR = Path("data/raw/ethereum/receipts")
# "original" → 直接使用 JSON-RPC
# "web3"     → 使用 Web3.py
FETCH_MODE = "original" 

# 2. 讀取 .env
load_dotenv() # 2. 讀取 .env
ethereum_rpc = os.environ.get("ETHEREUM_RPC_URL")

if not ethereum_rpc:
    raise RuntimeError( "找不到 ETHEREUM_RPC_URL，請確認 .env 是否正確設定。")

# 3. 建立 Ethereum RPC 連線,確認是否成功連線
w3 = Web3(Web3.HTTPProvider(ethereum_rpc, request_kwargs={"timeout": REQUEST_TIMEOUT}))
if not w3.is_connected():
    raise RuntimeError("無法連接 Ethereum RPC，請確認 Alchemy RPC URL 是否正確。")
# 4. 檢查 Block 範圍
if START_BLOCK > END_BLOCK:
    raise ValueError("START_BLOCK 不可以大於 END_BLOCK。")
block_count = END_BLOCK - START_BLOCK + 1
print(f"Start block: {START_BLOCK}")
print(f"End block:   {END_BLOCK}")
print(f"Total blocks: {block_count}")

# 5. 建立輸出資料夾
OUTPUT_DIR.mkdir(parents=True,exist_ok=True)
RECEIPT_OUTPUT_DIR.mkdir(parents=True,exist_ok=True)

def fetch_block_original(block_number):
    """
    直接使用 Ethereum JSON-RPC API 取得 Block。
    不透過 Web3.py 解析 Block，
    而是直接取得 JSON-RPC Response。
    回傳：
        dict: 原始 JSON-RPC Response
    """
    # JSON-RPC Request
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getBlockByNumber",
        "params": [
            hex(block_number),
            True
        ],
        "id": 1
    }
    # Retry
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(
                f"[Original] Downloading block {block_number} "
                f"(attempt {attempt}/{MAX_RETRIES})..."
            )
            response = requests.post(ethereum_rpc,json=payload,timeout=REQUEST_TIMEOUT)
            # 檢查 HTTP 狀態碼
            response.raise_for_status()
            # 取得 JSON-RPC Response
            rpc_response = response.json()
            # 檢查 JSON-RPC 是否回傳 error
            if "error" in rpc_response:
                raise RuntimeError(f"JSON-RPC error: {rpc_response['error']}")
            return rpc_response
        except Exception as error:
            print(
                f"Failed to fetch block {block_number}: "
                f"{error}"
            )
            if attempt < MAX_RETRIES:
                print(
                    f"Retrying in {RETRY_DELAY} seconds..."
                )
                time.sleep(RETRY_DELAY)
            else:
                raise RuntimeError(
                    f"Block {block_number} 下載失敗，"
                    f"已重試 {MAX_RETRIES} 次。"
                ) from error

# 6. 將 Web3 資料轉成 JSON 可以儲存的格式

def convert_to_json_serializable(value):
    """
    將 Web3.py 回傳的資料遞迴轉換成
    JSON 可以儲存的格式。
    """
    # --------------------------------------------------------
    # bytes / HexBytes
    if isinstance(value, bytes):
        return "0x" + value.hex()
    # --------------------------------------------------------
    # Dictionary / AttributeDict
    if hasattr(value, "items"):
        return {
            str(key): convert_to_json_serializable(val)
            for key, val in value.items()
        }
    # --------------------------------------------------------
    # List / Tuple
    if isinstance(value, (list, tuple)):
        return [
            convert_to_json_serializable(item)
            for item in value
        ]
    # --------------------------------------------------------
    # 其他具有 item() 的數值型別
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    # --------------------------------------------------------
    # 已經是 JSON 可以直接處理的型別
    return value
# 7. 抓取單一 Block
def fetch_block(block_number):
    """
    使用 Web3.py 取得 Block。
    Web3.py 會幫我們處理 JSON-RPC Request，
    並將 Response 解析成 Python 資料。
    回傳：
        AttributeDict: Web3.py 解析後的 Block
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(
                f"Downloading block {block_number} "
                f"(attempt {attempt}/{MAX_RETRIES})..."
            )
            block = w3.eth.get_block(
                block_number,
                full_transactions=True
            )
            return block
        except Exception as error:
            print(
                f"Failed to fetch block {block_number}: "
                f"{error}"
            )
            if attempt < MAX_RETRIES:
                print(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                raise RuntimeError(
                    f"無法取得 Block {block_number}，"
                    f"已重試 {MAX_RETRIES} 次。") from error

def fetch_transaction_receipt_original(tx_hash):
    """
    直接使用 Ethereum JSON-RPC API
    取得指定 Transaction 的 Receipt。
    回傳：
        dict: 原始 JSON-RPC Response
    """
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getTransactionReceipt",
        "params": [tx_hash],
        "id": 1
    }
    # Retry
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(
                f"[Original] Downloading receipt "
                f"{tx_hash} "
                f"(attempt {attempt}/{MAX_RETRIES})..."
            )
            response = requests.post(ethereum_rpc,json=payload,timeout=REQUEST_TIMEOUT)
            # 檢查 HTTP 狀態碼
            response.raise_for_status()
            # 取得 JSON-RPC Response
            rpc_response = response.json()
            # 檢查 JSON-RPC 是否回傳 error
            if "error" in rpc_response:
                raise RuntimeError(f"JSON-RPC error: {rpc_response['error']}")
            # Receipt 不存在
            if rpc_response.get("result") is None:raise RuntimeError(
                    f"找不到 Transaction Receipt: {tx_hash}")
            return rpc_response
        except Exception as error:
            print(
                f"Failed to fetch receipt "
                f"{tx_hash}: {error}"
            )
            if attempt < MAX_RETRIES:
                print(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                raise RuntimeError(
                    f"Transaction Receipt {tx_hash} "
                    f"下載失敗，"
                    f"已重試 {MAX_RETRIES} 次。"
                ) from error
def get_transaction_hashes_from_block(block_path):
    """
    從已下載的 Block JSON 中，
    取得所有 Transaction Hash。
    參數：
        block_path: Block JSON 檔案路徑
    回傳：
        list[str]: Transaction Hash 列表
    """
    with open(block_path,"r",encoding="utf-8") as f:
        block_data = json.load(f)
    # Original JSON-RPC Response
    block = block_data["result"]
    transactions = block["transactions"]
    transaction_hashes = []
    for tx in transactions:
        transaction_hashes.append(tx["hash"])
    return transaction_hashes
def fetch_block_receipts(block_path):
    """
    根據已下載的 Block JSON，
    取得該 Block 中所有 Transaction 的 Receipt。
    Receipt 會以原始 JSON-RPC Response 格式保存。
    """
    block_filename = block_path.stem
    # block_25779328_original
    block_number = block_filename.split("_")[1]
    # --------------------------------------------------------
    # Receipt 輸出檔案
    # -------------------------------------------------------
    receipt_output_path = (
        RECEIPT_OUTPUT_DIR
        / f"block_{block_number}_receipts_original.json"
    )
    # --------------------------------------------------------
    # 如果已經抓過，就跳過
    # --------------------------------------------------------
    if receipt_output_path.exists():
        print(
            f"Receipts for block {block_number} "
            f"already exist. Skip."
        )
        return
    # --------------------------------------------------------
    # 從已下載的 Block 取得 Transaction Hash
    # --------------------------------------------------------

    transaction_hashes = (get_transaction_hashes_from_block(block_path))

    print(
        f"Block {block_number} contains "
        f"{len(transaction_hashes)} transactions."
    )

    # --------------------------------------------------------
    # 建立 Receipt 結果
    # --------------------------------------------------------
    receipts = []

    for index, tx_hash in enumerate(transaction_hashes,start=1):
        print(
            f"[{index}/{len(transaction_hashes)}] "
            f"Fetching receipt..."
        )
        receipt = fetch_transaction_receipt_original(tx_hash)
        receipts.append(receipt)
    # --------------------------------------------------------
    # 建立要儲存的資料
    # --------------------------------------------------------
    data_to_save = {
        "block_number": int(block_number),
        "transaction_count": len(transaction_hashes),
        "receipts": receipts
    }
    # --------------------------------------------------------
    # 儲存 JSON
    # --------------------------------------------------------
    with open(
        receipt_output_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data_to_save,
            f,
            ensure_ascii=False,
            indent=2
        )
    print(
        f"Saved receipts for block {block_number} "
        f"to {receipt_output_path}"
    )



# ============================================================
# 8. 逐一下載 Block
# ============================================================

for block_number in range(START_BLOCK,END_BLOCK + 1):
    # 根據 FETCH_MODE 決定檔名
    if FETCH_MODE == "original":
        output_path = (OUTPUT_DIR /f"block_{block_number}_original.json")
    elif FETCH_MODE == "web3":
        output_path = (OUTPUT_DIR /f"block_{block_number}.json")
    else:
        raise ValueError("FETCH_MODE 必須是 'original' 或 'web3'。")
    # --------------------------------------------------------
    # 如果已經下載過，就跳過
    # --------------------------------------------------------
    if output_path.exists():
        print(
            f"Block {block_number} already exists. Skip."
        )
        continue

    # --------------------------------------------------------
    # Original JSON-RPC
    # --------------------------------------------------------
    if FETCH_MODE == "original":
        rpc_response = fetch_block_original(block_number)
        data_to_save = rpc_response
    else:

        block = fetch_block(block_number)
        data_to_save = convert_to_json_serializable(block)

    # --------------------------------------------------------
    # 儲存 JSON
    # --------------------------------------------------------

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as f:
         json.dump(
            data_to_save,
            f,
            ensure_ascii=False,
            indent=2
        )

    print(
        f"Saved block {block_number} "
        f"to {output_path}"
    )

    print()



print("====================================")
print("Block download completed.")
print(f"Blocks: {START_BLOCK} ~ {END_BLOCK}")
print(f"Output: {OUTPUT_DIR}")
print("====================================")

# ============================================================
# 9. 逐一下載receipts
# ============================================================
print()
print("====================================")
print("Fetching transaction receipts...")
print("====================================")

for block_number in range(START_BLOCK, END_BLOCK + 1):

    if FETCH_MODE == "original":
        block_path = (OUTPUT_DIR /f"block_{block_number}_original.json")
    elif FETCH_MODE == "web3":
        block_path = (
            OUTPUT_DIR /
            f"block_{block_number}.json"
        )

    else:
        raise ValueError(
            "FETCH_MODE 必須是 'original' 或 'web3'。"
)
    if not block_path.exists():
        print(f"Block {block_number} not found. Skip.")
        continue
    fetch_block_receipts(block_path)