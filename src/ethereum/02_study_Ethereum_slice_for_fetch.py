#from builtins import dict
from web3 import Web3
from dotenv import load_dotenv
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelta, timezone
import os
import json
import time
import sys

print("Python 執行檔：")
print(sys.executable)
print()
print("Python 版本：")
print(sys.version)
print()
print("是否使用虛擬環境：")
print(sys.prefix != sys.base_prefix)
# ============================================================
# 1. 基本設定
# ============================================================

# 研究日期
START_DATE = "2026-07-01"
END_DATE = "2026-07-01"
# 如果你想直接指定 block number，可以填數字
# 例如：
# START_BLOCK = 23000000
# END_BLOCK = 23010000
# 如果使用日期自動找 block，就維持 None
START_BLOCK =None
END_BLOCK = None
# 大量 USDC raw data 放在 D 槽
USDC_OUTPUT_DIR = Path(r"D:\blockchain_data\ethereum\usdc_transfer")
# 每個 chunk 的 raw logs
CHUNK_DIR = USDC_OUTPUT_DIR / "chunks"
# 每個 chunk 的執行狀況
RUN_CONDITION_DIR = USDC_OUTPUT_DIR / "run_conditions"
# checkpoint
CHECKPOINT_PATH = USDC_OUTPUT_DIR / "checkpoint.json"
# 每次 eth_getLogs 最多查多少個 block
# 可以依 RPC provider 的限制調整
CHUNK_SIZE = 10
# RPC request retry 設定
MAX_RETRIES = 3
RETRY_DELAY = 2
# USDC Ethereum Mainnet Contract
#USDC_ADDRESS = "0xA0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
# USDC decimals
USDC_DECIMALS = 6

# ============================================================
# 2. 載入 RPC
# ============================================================
load_dotenv()
RPC_URL = os.getenv("ETHEREUM_RPC_URL")
if not RPC_URL:
    raise ValueError("找不到 ETHEREUM_RPC_URL，請確認 .env 是否設定。")
w3 = Web3(Web3.HTTPProvider(RPC_URL))
ABI_PATH = "data/raw/ethereum/ERC-20_ABI/USDC_second_layer_erc_abi.json"
with open(ABI_PATH, "r", encoding="utf-8") as f:
    erc20_abi = json.load(f)
USDC_ADDRESS  = Web3.to_checksum_address("0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48")
token = w3.eth.contract(address=USDC_ADDRESS,abi=erc20_abi)
# ============================================================
# 3. 基本檢查
# ============================================================
if not w3.is_connected():
    raise ConnectionError("無法連接 Ethereum RPC。")
print("Connected to Ethereum RPC")
print(f"Latest block: {w3.eth.block_number}")
# 將 USDC address 轉成 checksum address
# ERC-20 Transfer event
# Transfer(address,address,uint256)

print()
print(f"USDC contract: {USDC_ADDRESS}")

# ============================================================
# 4. RPC retry wrapper
# ============================================================
def make_json_serializable(data):
    """
    將 Web3 回傳的資料轉換成可以被 json.dump()
    儲存的 Python 資料型態。
    Web3 的 log 裡面可能會出現：
    - AttributeDict
    - HexBytes
    - bytes
    等 JSON 不認識的型態。
    這個函式會遞迴處理整個資料結構。
    """
    # --------------------------------------------------------
    # 如果是 dictionary
    if hasattr(data, "items"):#這個東西有沒有 .items() 這個功能？

        return {
            str(key): make_json_serializable(value)
            for key, value in data.items()
        }

    # 如果是 list 或 tuple
    # --------------------------------------------------------
    elif isinstance(data, (list, tuple)):
        return [
            make_json_serializable(item)
            for item in data
        ]
    # --------------------------------------------------------
    # 如果是 bytes
    # 例如：
    # HexBytes("0x1234...")
    # 轉成：
    # "0x1234..."
    # --------------------------------------------------------
    elif isinstance(data, bytes):
        return "0x" + data.hex()#如果 Web3 回傳的資料是「位元組資料」，就把它轉成一般字串，方便存進 JSON。
    # --------------------------------------------------------
    # 其他一般 Python 型態
    # -------------------------------------------------------
    else:
        return data

def save_chunk_json(logs,chunk_index,from_block,to_block):
    """
    將一個 chunk 的 USDC Transfer logs
    立即儲存成一個 JSON。
    例如：
    chunk_000001.json
    chunk_000002.json
    chunk_000003.json
    每一個 JSON 對應一個 block range。
    """
    # 建立資料夾
    CHUNK_DIR.mkdir(parents=True,exist_ok=True)
    # JSON 檔案名稱
    output_path = (CHUNK_DIR/ f"chunk_{chunk_index:06d}.json")
    # 將 Web3 logs 轉成 JSON-compatible format
    serializable_logs = make_json_serializable(logs)
    # 建立這個 chunk 的資料-
    chunk_data = {
        "chunk_index": chunk_index,
        "from_block": from_block,
        "to_block": to_block,
        "log_count": len(logs),
        "logs": serializable_logs
    }
    # --------------------------------------------------------
    # 寫入 JSON
    # --------------------------------------------------------
    with open(output_path,"w",encoding="utf-8") as f:
        json.dump(chunk_data,f,ensure_ascii=False,indent=2)
    print(
        f"    Saved raw chunk: "
        f"{output_path}"
    )
    return output_path
# 4. 讀取 checkpoint
# ============================================================

def load_checkpoint():
    """
    讀取 checkpoint.json。
    如果 checkpoint 不存在：
        回傳 None
    如果存在：
        回傳 checkpoint dictionary
    """
    if not CHECKPOINT_PATH.exists():
        return None
    with open(CHECKPOINT_PATH,"r",encoding="utf-8") as f:
        checkpoint = json.load(f)
    return checkpoint
def save_checkpoint(chunk_index,from_block,to_block):
    """
    儲存最後一個成功完成的 chunk。
    注意：
    checkpoint 只有在 raw JSON 成功儲存之後才會更新。
    """
    USDC_OUTPUT_DIR.mkdir(parents=True,exist_ok=True)
    checkpoint = {
        "last_completed_chunk": chunk_index,
        "last_completed_from_block": from_block,
        "last_completed_to_block": to_block
    }
    with open( CHECKPOINT_PATH,"w",encoding="utf-8") as f:
        json.dump(checkpoint,f,ensure_ascii=False,indent=2)
    print(
        f"    Checkpoint updated: "
        f"chunk {chunk_index}"
    )

def get_next_run_number(chunk_index):
    """
    找出指定 chunk 下一次執行應該使用的 run number。
    例如已經有：
        chunk_000003_run_001.json
        chunk_000003_run_002.json
    下一次就會使用：
        run_003
    """
    RUN_CONDITION_DIR.mkdir(parents=True,exist_ok=True)
    # 找出這個 chunk 已經存在的 run condition
    existing_files = list(
        RUN_CONDITION_DIR.glob(
            f"chunk_{chunk_index:06d}_run_*.json"
        )
    )
    # 如果完全沒有紀錄
    if not existing_files:
        return 1
    # --------------------------------------------------------
    # 找出最大的 run number
    # --------------------------------------------------------
    run_numbers = []
    for file_path in existing_files:
        # 例如：
        # chunk_000003_run_002.json
        filename = file_path.stem
        # split:
        # ["chunk", "000003", "run", "002"]
        parts = filename.split("_")
        if len(parts) >= 4:
            try:
                run_number = int(parts[-1])
                run_numbers.append(
                    run_number
                )
            except ValueError:
                pass
    # 如果找不到有效的 run number
    if not run_numbers:
        return 1
    return max(run_numbers) + 1

def save_run_condition(chunk_index,run_number,from_block,to_block,status,elapsed_seconds,log_count,retry_count,error_type=None,error_message=None):
    """
    儲存一次 chunk 執行的詳細紀錄。每個 chunk 的執行時間、log 數量、重試次數與錯誤類型。
    例如：
    chunk_000003_run_001.json
    chunk_000003_run_002.json
    如果第一次失敗、第二次成功，
    兩次紀錄都會保留。
    """
    RUN_CONDITION_DIR.mkdir(parents=True,exist_ok=True)
    output_path = (
        RUN_CONDITION_DIR
        / (
            f"chunk_{chunk_index:06d}"
            f"_run_{run_number:03d}.json"
        )
    )
    run_condition = {
        "chunk_index": chunk_index,
        "run_number": run_number,
        "from_block": from_block,
        "to_block": to_block,
        "status": status,
        "elapsed_seconds": round(elapsed_seconds,3),
        "log_count": log_count,
        "retry_count": retry_count,
        "error_type": error_type,
        "error_message": error_message
    }
    with open(output_path,"w",encoding="utf-8") as f:
        json.dump(run_condition,f,ensure_ascii=False,indent=2)
    print(
        f"    Saved run condition: "
        f"{output_path}"
    )
def call_with_retry(func,*args,**kwargs):
    """
    執行 RPC request。
    如果失敗：
        會重新嘗試
    MAX_RETRIES：
        最大嘗試次數
    RETRY_DELAY：
        每次 retry 前等待幾秒
    回傳：
        result
        retry_count
    retry_count 的意思是：
        「失敗後重新嘗試了幾次」
    例如：
        第一次成功
        retry_count = 0
        第一次失敗
        第二次成功
        retry_count = 1
        第一次失敗
        第二次失敗
        第三次成功
        retry_count = 2
    """
    last_error = None
    retry_count = 0
    for attempt in range(1,MAX_RETRIES + 1):
        try:
            result = func(*args,**kwargs)#這個 * 就是在說：把 args 裡面的東西拆開，分別當成函式參數。
            return (result,retry_count)
        except Exception as e:
            last_error = e
            print(
                f"    RPC request failed "
                f"(attempt "
                f"{attempt}/{MAX_RETRIES})"
            )
            print(f"    Error: {e}")
            # ------------------------------------------------
            # 如果還可以 retry
            # ------------------------------------------------
            if attempt < MAX_RETRIES:
                retry_count += 1
                time.sleep(RETRY_DELAY)
    # --------------------------------------------------------
    # 所有 attempt 都失敗
    # --------------------------------------------------------
    raise last_error
# ============================================================
# 5. 取得 block timestamp
# ============================================================
def get_block_timestamp(block_number):
    """
    取得指定 block 的 timestamp。
    """
    block, retry_count = call_with_retry(w3.eth.get_block, block_number)
    return int(block["timestamp"])
# ============================================================
# 6. 找到「第一個 timestamp >= target_timestamp」的 block
# ============================================================
def find_first_block_at_or_after(target_timestamp,latest_block=None):
    """
    使用 binary search 找到：
    第一個 timestamp >= target_timestamp 的 block。
    例如：
    target = 2026-07-01 00:00:00 UTC
    找到：
    block X timestamp >= target
    """
    if latest_block is None:
        latest_block = w3.eth.block_number
    latest_timestamp = get_block_timestamp(latest_block)
    if latest_timestamp < target_timestamp:
        raise ValueError("目前 Ethereum 最新 block 還沒有到指定日期。")
    low = 0
    high = latest_block
    while low < high:
        mid = (low + high) // 2
        mid_timestamp = get_block_timestamp(mid)
        if mid_timestamp >= target_timestamp:
            high = mid
        else:
            low = mid + 1
    return low


# ============================================================
# 7. 日期轉 timestamp
# ============================================================

def date_to_timestamp(date_string):
    """
    將 YYYY-MM-DD 轉成 UTC 00:00:00 timestamp。
    """
    dt = datetime.strptime(date_string,"%Y-%m-%d")
    dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())
# ============================================================
# 8. 根據日期取得 block range
# ============================================================

def get_block_range_from_dates(start_date,end_date):
    """
    將：
    START_DATE
    END_DATE
    轉成 Ethereum block range。
    日期以 UTC calendar day 定義。
    """
    start_timestamp = date_to_timestamp(start_date)
    # END_DATE 的「隔天 00:00」
    end_dt = datetime.strptime(end_date,"%Y-%m-%d")
    end_dt = end_dt.replace(tzinfo=timezone.utc)
    next_day = end_dt + timedelta(days=1)
    end_exclusive_timestamp = int(next_day.timestamp())
    print()
    print("Finding block range...")
    print(f"Start date: {start_date} 00:00:00 UTC")
    print(f"End date:   {end_date} 23:59:59 UTC")
    latest_block = w3.eth.block_number
    start_block = find_first_block_at_or_after( start_timestamp,latest_block)#找第一個符合這個時間的 Block
    first_block_after_end = find_first_block_at_or_after(end_exclusive_timestamp,latest_block)
    end_block = first_block_after_end - 1#要到隔天的00:00
    return start_block, end_block

# ============================================================
# 9. 分批取得 USDC Transfer logs
# ============================================================

def fetch_usdc_transfer_logs(start_block,end_block):
    """
    使用 eth_getLogs 分批取得 USDC Transfer events。
    特點：
    1. 每個 chunk 抓完立即儲存
    2. 不把所有 logs 放在 all_logs
    3. 每個 chunk 都有 run condition
    4. 成功後更新 checkpoint
    5. 程式中斷後可以繼續
    """
    # --------------------------------------------------------
    # 計算總 block 數
    # --------------------------------------------------------
    total_blocks = (end_block- start_block+ 1)
    # --------------------------------------------------------
    # 計算總 chunk 數
    # --------------------------------------------------------
    total_chunks = (total_blocks+ CHUNK_SIZE- 1) // CHUNK_SIZE
    print()
    print("Fetching USDC Transfer logs...")
    print(
        f"Block range: "
        f"{start_block:,} -> "
        f"{end_block:,}"
    )
    print(
        f"Total blocks: "
        f"{total_blocks:,}"
    )
    print(
        f"Chunk size: "
        f"{CHUNK_SIZE:,}"
    )
    print(
        f"Total chunks: "
        f"{total_chunks:,}"
    )
    print()
    # ========================================================
    # 讀取 checkpoint
    # ========================================================
    checkpoint = load_checkpoint()
    if checkpoint is None:
        # ----------------------------------------------------
        # 第一次執行
        # ----------------------------------------------------
        current_start = start_block
        print("No checkpoint found.")
        print(
            f"Starting from block "
            f"{current_start:,}"
        )
    else:
        # ----------------------------------------------------
        # 已經有 checkpoint
        # ----------------------------------------------------
        last_completed_to_block = (checkpoint["last_completed_to_block"])
        current_start = (last_completed_to_block+ 1)
        print("Checkpoint found.")
        print(
            f"Last completed block: "
            f"{last_completed_to_block:,}"
        )
        print(
            f"Resuming from block: "
            f"{current_start:,}"
        )
    print()
    # ========================================================
    # 開始逐 chunk 抓資料
    # ========================================================
    while current_start <= end_block:
        # 計算這個 chunk 的結束 block
        current_end = min(current_start+ CHUNK_SIZE- 1, end_block)
        # 根據 block range 計算 chunk index
        # 這裡用 start_block 當基準。
        chunk_index = ((current_start - start_block) // CHUNK_SIZE) + 1
        # ----------------------------------------------------
        # 找出這個 chunk 的 run number
        run_number = (get_next_run_number(chunk_index))
        print(
            f"[Chunk {chunk_index}/{total_chunks}] "
            f"blocks "
            f"{current_start:,} -> "
            f"{current_end:,}"
        )
        print(
            f"    Run number: "
            f"{run_number}"
        )
        # 開始計時
        start_time = time.time()
        # 預設值
        logs = []
        retry_count = 0
        # ====================================================
        # RPC request
        # ====================================================
        try:
            logs, retry_count = call_with_retry(
                token.events.Transfer.get_logs,
                from_block=current_start,
                to_block=current_end
            )
            elapsed_seconds = (time.time()- start_time)

            print(
                f"    Logs found: "
                f"{len(logs):,}"
            )
            print(
                f"    Elapsed time: "
                f"{elapsed_seconds:.3f} sec"
            )
            print(
                f"    Retry count: "
                f"{retry_count}"
            )
            # 先儲存 raw chunk
            chunk_path = save_chunk_json(
                logs=logs,
                chunk_index=chunk_index,
                from_block=current_start,
                to_block=current_end
            )
            # 確認 raw chunk 真的存在
            if not chunk_path.exists():
                raise RuntimeError("Chunk JSON file was not created.")
            # Raw data 儲存成功
            # 現在才可以更新 checkpoint
            save_checkpoint(
                chunk_index=chunk_index,
                from_block=current_start,
                to_block=current_end
            )
            # 儲存 run condition
            save_run_condition(
                chunk_index=chunk_index,
                run_number=run_number,
                from_block=current_start,
                to_block=current_end,
                status="success",
                elapsed_seconds=elapsed_seconds,
                log_count=len(logs),
                retry_count=retry_count,
                error_type=None,
                error_message=None
            )
            print("    Status: SUCCESS")
            print()
            # ------------------------------------------------
            # 進入下一個 chunk
            # ------------------------------------------------
            current_start = (current_end+ 1)
        # ====================================================
        # Chunk 失敗
        # ====================================================
        except Exception as e:
            elapsed_seconds = (time.time() - start_time)
            print()
            print( "    Status: FAILED")
            print(
                f"    Error type: "
                f"{type(e).__name__}"
            )
            print(
                f"    Error: {e}"
            )
            print(
                f"    Retry count: "
                f"{retry_count}"
            )
            # =================================================
            # 記錄這次失敗
            # 注意：
            # 這裡「不更新 checkpoint」
            # =================================================
            save_run_condition(
                chunk_index=chunk_index,
                run_number=run_number,
                from_block=current_start,
                to_block=current_end,
                status="failed",
                elapsed_seconds=elapsed_seconds,
                log_count=0,
                retry_count=retry_count,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            print()

            # ------------------------------------------------
            # 停止程式
            #
            # 下次重新執行時，
            # checkpoint 仍然停在上一個成功 chunk。
            # ------------------------------------------------
            raise
    print(
        "All chunks completed successfully."
    )
# ============================================================
# 10. 將 raw log 轉成可以 JSON 儲存的格式
# ============================================================
def decode_transfer_log(log):
    """
    將 Web3.py 已經 decode 的 Transfer event
    轉換成普通 dictionary。
    """
    args = log["args"]
    from_address = args["from"]
    to_address = args["to"]
    # 保留原始鏈上數值為 int
    value = int(args["value"])
    # 使用 Decimal，不使用 float
    amount_usdc = (
        Decimal(value)
        / Decimal(10 ** USDC_DECIMALS)
    )
    block_number = int(log["blockNumber"])
    block_timestamp = get_block_timestamp(block_number)
    return {
        "block_number":block_number,
        "block_timestamp":block_timestamp,
        "transaction_hash": (log["transactionHash"].hex()),
        "transaction_index": int(log["transactionIndex"]),
        "log_index": int(log["logIndex"]),
        "contract_address": (log["address"]),
        "from_address": from_address,
        "to_address": to_address,
        # 原始鏈上 value
        "value": value,
        # USDC 實際數量
        # Decimal → string
        # 方便 JSON 儲存，Python 的 Decimal 很適合計算，但 JSON 原生沒有 Decimal 這個資料型別。
        "amount_usdc": str(amount_usdc),
    }


# ============================================================
# 12. Main
# ============================================================
def main():
    # --------------------------------------------------------
    # A. 決定 block range
    # --------------------------------------------------------
    has_date_range = ( START_DATE is not None and END_DATE is not None )
    has_block_range = ( START_BLOCK is not None and END_BLOCK is not None )
    # 日期只指定一邊也不允許 
    if ( (START_DATE is None) != (END_DATE is None) ): 
        raise ValueError( "START_DATE 和 END_DATE 必須同時指定或同時為 None。" )
    # Block 只指定一邊也不允許
    if ( (START_BLOCK is None) != (END_BLOCK is None) ): 
        raise ValueError( "START_BLOCK 和 END_BLOCK 必須同時指定或同時為 None。" )
    date_start_block = None 
    date_end_block = None
    if has_date_range: 
        date_start_block, date_end_block = ( get_block_range_from_dates( START_DATE, END_DATE ) ) 
        print() 
        print("Block range from date:")
        print( f"{date_start_block:,} -> " f"{date_end_block:,}" )
    if has_date_range and has_block_range: 
        start_block = max( START_BLOCK, date_start_block ) 
        end_block = min( END_BLOCK, date_end_block ) 
        print() 
        print( "Using intersection of " "date range and manual block range." ) 
    elif has_date_range: # 只有日期 
        start_block = date_start_block 
        end_block = date_end_block 
        print() 
        print( "Using block range derived " "from date range." ) 
    else: # 只有手動 
        start_block = START_BLOCK 
        end_block = END_BLOCK 
        print() 
        print( "Using manually specified " "block range." )
    if start_block > end_block: raise ValueError( "Start block 必須小於或等於 end block。")
    # -------------------------------------------------------
    # B. 顯示 block range
    # --------------------------------------------------------
    print()
    print("=" * 60)
    print("Research range")
    print("=" * 60)
    print(f"Start date : {START_DATE}")
    print(f"End date   : {END_DATE}")
    print(f"Start block: {start_block:,}")
    print(f"End block  : {end_block:,}")
    print("=" * 60)
    # --------------------------------------------------------
    # C. 抓取 logs
    # --------------------------------------------------------

    fetch_usdc_transfer_logs(
        start_block,
        end_block
    )


# ============================================================
# Entry point
# ============================================================
if __name__ == "__main__":
    main()