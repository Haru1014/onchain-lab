import json
from pathlib import Path
from decimal import Decimal


# ============================================================
# 1. 資料夾設定
# ============================================================
CHUNK_DIR = Path( r"D:\blockchain_data\ethereum\usdc_transfer\chunks")
# ============================================================
# 2. 初始化
# ============================================================
total_transfer_count = 0
total_raw_value = 0
chunk_count = 0
first_block = None
last_block = None
# 先取得所有 chunk 檔案
json_files = sorted(CHUNK_DIR.glob("chunk_*.json"))

total_chunks = len(json_files)

print(f"總共有 {total_chunks} 個 chunk")
print("開始讀取...")
print()
# ============================================================
# 3. 逐個讀取 chunk JSON
# ===========================================================
for json_file in sorted(CHUNK_DIR.glob("chunk_*.json")):
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    chunk_count += 1
    # --------------------------------------------------------
    # 這個 chunk 的基本資訊
    # --------------------------------------------------------
    chunk_index = data["chunk_index"]
    from_block = data["from_block"]
    to_block = data["to_block"]
    log_count = data["log_count"]
    logs = data["logs"]
    # --------------------------------------------------------
    # 記錄整體 block 範圍
    # --------------------------------------------------------
    if first_block is None:
        first_block = from_block
    last_block = to_block
    # --------------------------------------------------------
    # 加總 Transfer 次數
    # --------------------------------------------------------
    total_transfer_count += log_count
    # --------------------------------------------------------
    # 檢查 log_count 和實際 logs 數量是否一致
    # --------------------------------------------------------
    if log_count != len(logs):
        print(f"WARNING: {json_file.name}")
        print(f"  log_count = {log_count}")
        print(f"  len(logs)  = {len(logs)}")
    # --------------------------------------------------------
    # 加總所有 Transfer 的 raw value
    # --------------------------------------------------------
    for log in logs:
        raw_value = log["args"]["value"]
        total_raw_value += raw_value
    # ============================
    # 每 50 個 chunk 顯示一次進度
    # ============================
    if chunk_count % 10 == 0 or chunk_count == total_chunks:
        progress = chunk_count / total_chunks * 100
        print(
            f"進度: {chunk_count}/{total_chunks} "
            f"({progress:.1f}%) | "
            f"目前 block: {from_block} ~ {to_block} | "
            f"目前 Transfer 數: {total_transfer_count:,}"
        )
# ============================================================
# 4. USDC raw value → USDC
# ============================================================
total_transfer_amount = (Decimal(total_raw_value) / Decimal(10**6))
# ============================================================
# 5. 印出結果
# ============================================================
print()
print("=" * 60)
print("Alchemy USDC Transfer 統計")
print("=" * 60)

print(
    f"Chunk 數量       : {chunk_count}"
)

print(
    f"Block 範圍       : {first_block} ~ {last_block}"
)

print(
    f"Transfer 次數    : {total_transfer_count:,}"
)

print(
    f"Raw Transfer 金額: {total_raw_value:,}"
)

print(
    f"Transfer 金額    : {total_transfer_amount:,.6f} USDC"
)

print("=" * 60)