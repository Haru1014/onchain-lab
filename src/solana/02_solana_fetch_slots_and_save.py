import os
import json
from pathlib import Path
from dotenv import load_dotenv
from solana.rpc.api import Client
# ============================================================
# 1. 基本設定
# ============================================================
load_dotenv()
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL")
START_SLOT = 443900000
END_SLOT = 443900000+999
OUTPUT_DIR = Path("data/raw/solana/blocks")#your path
client = Client(SOLANA_RPC_URL)
for slot in range(START_SLOT, END_SLOT + 1):
    print(
        f"[{slot - START_SLOT + 1}/"
        f"{END_SLOT - START_SLOT + 1}] "
        f"Fetching slot {slot}..."
    )
    try:
        block = client.get_block(slot,max_supported_transaction_version=0,).value
        '''
        因為.value
        有 block → block 裡面就是 block 資料
        沒有 block → block 是 None
        '''
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

print()
print("Finished.")

