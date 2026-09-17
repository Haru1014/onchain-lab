import os
import sys
print(sys.executable)
from dotenv import load_dotenv
from solana.rpc.api import Client#solana 0.40.1不行
load_dotenv()#把 .env 裡面的設定讀進 Python 的環境變數。

client = Client(os.environ["SOLANA_RPC_URL"])
#一個可以向這個 Solana RPC 發送請求的 Client。
slot = client.get_slot(commitment="finalized").value#找一個 finalized 狀態下的最新 slot
# get_slot()->向 Solana RPC 詢問目前的 slot，我要 finalized 狀態的 slot。
#同一條 canonical chain 上，一個 slot 對應一個 canonical block。
'''
0.32版本的參數是
(self, slot: int,
 encoding: str = 'json',
 max_supported_transaction_version: int = None)
block = client.get_block(
    slot,
    commitment="finalized",
    max_supported_transaction_version=0,
).value
'''
block = response = client.get_block(
    slot,
    max_supported_transaction_version=0,
).value
'''
因為.value
有 block → block 裡面就是 block 資料
沒有 block → block 是 None
'''
print("slot:", slot)
print("has block:", block is not None)
print("transaction count:", len(block.transactions) if block else 0)