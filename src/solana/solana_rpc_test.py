import os
import requests
import json

from dotenv import load_dotenv


# 載入 .env
load_dotenv()

# 取得 Solana RPC URL
SOLANA_RPC_URL = os.environ["SOLANA_RPC_URL"]

# 要查詢的 slot
slot = 100000000

# 要求 finalized
COMMITMENT = "finalized"


# 建立 JSON-RPC request
payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "getBlock",
    "params": [
        slot,
        {
            "commitment": COMMITMENT,
            "encoding": "json",
            "transactionDetails": "full",
            "maxSupportedTransactionVersion": 0,
            "rewards": False,
        },
    ],
}


# 送出 HTTP POST request
response = requests.post(
    SOLANA_RPC_URL,
    json=payload,
    timeout=30,
)

# 如果 HTTP 本身有錯誤，這裡會報錯
response.raise_for_status()

# 將 JSON response 轉成 Python 資料
data = response.json()

# 印出結果
print(data)
print(type(data))
print(data.keys())

# 取得真正的 block
block = data["result"]

if block is None:
    print("這個 slot 沒有 block")
else:
    print("block type:", type(block))
    print("block keys:", block.keys())

# 儲存成真正的 JSON
with open("block_100000000.json", "w", encoding="utf-8") as f:
    json.dump(
        data,
        f,
        ensure_ascii=False,
        indent=2
    )

print("JSON 檔案儲存完成")