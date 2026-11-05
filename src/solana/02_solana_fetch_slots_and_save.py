import os
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv
#from solana.rpc.api import Client
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Finalized
# ============================================================
# 1. 基本設定
# ============================================================
load_dotenv()
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL")
START_SLOT = 443900000
END_SLOT = 443900000+1
OUTPUT_DIR = Path("data/raw/solana/blocks")#your path
COMMITMENT = Finalized
MAX_SUPPORTED_TRANSACTION_VERSION = 0
# 同時最多執行幾個 RPC 請求
MAX_CONCURRENT_REQUESTS = 5
if not SOLANA_RPC_URL:
    raise ValueError("SOLANA_RPC_URL not found in .env")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
'''
        因為.value
        有 block → block 裡面就是 block 資料
        沒有 block → block 是 None
'''
# ============================================================
# 2. 下載單一 Slot
# ============================================================

async def fetch_single_slot(client, slot, semaphore):

    OUTPUT_FILE = OUTPUT_DIR / f"slot_{slot}_original.json"

    # ==================================================
    # 1. 建立輸出資料夾
    # ==================================================
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ==================================================
    # 2. 根據 Slot 取得 Block
    # ==================================================
    async with semaphore:
        try:
            response = await client.get_block(slot,commitment="finalized",max_supported_transaction_version=1,)
            block = response.value
            # ==================================================
            # 3. 判斷是否有 Block
            # ==================================================
            if block is None:
                result = {
                    "slot": slot,
                    "status": "no_block",
                    "block": None
                }
                status = "no_block"
            else:
                block_dict = json.loads(block.to_json())
                result = {
                    "slot": slot,
                    "status": "success",
                    "block": block_dict
                }

                status = "success"

            # ==================================================
            # 4. 儲存 JSON
            # ==================================================
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(result,f,ensure_ascii=False,indent=2)
            return slot, status

        except Exception as e:

            # ==================================================
            # 5. 發生錯誤時記錄錯誤
            # ==================================================
            result = {
                "slot": slot,
                "status": "fetch_error",
                "error": str(e)
            }

            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    result,
                    f,
                    ensure_ascii=False,
                    indent=2
                )

            return slot, "fetch_error"


# ============================================================
# 3. 非同步主程式
# ============================================================
async def main():
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)#這代表最多允許MAX_CONCURRENT_REQUESTS個任務同時進入 RPC 請求區域。
    # 記錄各種結果數量
    status_count = {
        "success": 0,
        "no_block": 0,
        "fetch_error": 0,
        "already_exists": 0
    }
    total_slots = END_SLOT - START_SLOT + 1
    # --------------------------------------------------------
    # 3-1. 建立 AsyncClient
    # --------------------------------------------------------
    async with AsyncClient(SOLANA_RPC_URL,commitment=COMMITMENT,timeout=30) as client:
        print("Checking available block slots...")
        # 先確認哪些 Slot 實際有 Block
        # 因為 Solana RPC 本身有提供一個專門的 API：getBlocks，可以直接查詢指定 Slot 範圍內，哪些 Slot 實際存在 Block。
        produced_slots = set((await client.get_blocks(START_SLOT,END_SLOT)).value)
        print(f"Total slots: {total_slots}")
        print(f"Slots with blocks: {len(produced_slots)}")
        print(f"Slots without blocks: {total_slots - len(produced_slots)}")
        # ----------------------------------------------------
        # 3-2. 建立下載任務
        # ----------------------------------------------------
        tasks = []
        for slot in range(START_SLOT, END_SLOT + 1):
            # 沒有 Block 的 Slot 不需要呼叫 get_block
            if slot not in produced_slots:
                OUTPUT_FILE = OUTPUT_DIR / f"slot_{slot}_original.json"
                result = {
                    "slot": slot,
                    "commitment": "finalized",
                    "max_supported_transaction_version":
                        MAX_SUPPORTED_TRANSACTION_VERSION,
                    "status": "no_block",
                    "block": None
                }
                # 若已存在新版資料，就不重複寫入
                if OUTPUT_FILE.exists():
                    try:
                        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                            old_data = json.load(f)
                        if old_data.get("status") == "no_block":
                            status_count["already_exists"] += 1
                            continue

                    except (json.JSONDecodeError, OSError):
                        pass

                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    json.dump(result,f,ensure_ascii=False,indent=2)
                status_count["no_block"] += 1
            else:
                tasks.append(fetch_single_slot(client,slot,semaphore))
        # ----------------------------------------------------
        # 3-3. 同時執行多個下載任務
        # ----------------------------------------------------
        print("\nStarting asynchronous fetching...\n")
        completed = 0
        for task in asyncio.as_completed(tasks):
            slot, status = await task
            status_count[status] += 1
            completed += 1
            print(
                f"[{completed}/{len(tasks)}] "
                f"Slot {slot}: {status}"
            )
    # --------------------------------------------------------
    # 3-4. 最後統計
    # --------------------------------------------------------
    print("\n========== Fetch Summary ==========")
    print(f"Total slots: {total_slots}")
    print(f"Successfully fetched: {status_count['success']}")
    print(f"No block: {status_count['no_block']}")
    print(f"Fetch errors: {status_count['fetch_error']}")
    print(f"Already exists: {status_count['already_exists']}")
    print("\nFinished!")
# ============================================================
# 4. 執行程式
# ============================================================
if __name__ == "__main__":
    asyncio.run(main())








'''
client = Client(SOLANA_RPC_URL)
for slot in range(START_SLOT, END_SLOT + 1):
    print(
        f"[{slot - START_SLOT + 1}/"
        f"{END_SLOT - START_SLOT + 1}] "
        f"Fetching slot {slot}..."
    )
    try:
        block = client.get_block(slot,max_supported_transaction_version=0,).value
        OUTPUT_DIR.mkdir(parents=True,exist_ok=True)
        OUTPUT_FILE = (OUTPUT_DIR/ f"slot_{slot}_original.json")
        with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
            json.dump(
                block,
                f,
                ensure_ascii=False,
                indent=2,
                default=str
            )
        if block is None:
            print("No block")
        else:
            print(f"Saved: {OUTPUT_FILE}")
    except Exception as e:
        print(f"    ERROR at slot {slot}: {e}")
'''
print()
print("Finished.")

