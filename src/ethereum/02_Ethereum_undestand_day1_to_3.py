# 匯入 os 模組
# 用來讀取環境變數，例如我們放在 .env 裡面的 ETHEREUM_RPC_URL
import os
# 從 python-dotenv 匯入 load_dotenv
# 用來讀取專案根目錄下的 .env 檔案
from dotenv import load_dotenv
# 從 web3 套件匯入 Web3
# Web3.py 可以讓 Python 比較方便地與 Ethereum 節點溝通
from web3 import Web3

# 讀取 .env 檔案
# 執行後，.env 裡面的 ETHEREUM_RPC_URL
# 就可以透過 os.environ 取得
load_dotenv()

# 建立一個 Web3 物件，並告訴它：
# 「我要透過 HTTP 連線到這個 Ethereum RPC」
# os.environ["ETHEREUM_RPC_URL"]
#     ↓
# 取得 .env 裡面的 Alchemy RPC URL
#
# Web3.HTTPProvider(...)
#     ↓
# 建立 HTTP 連線入口
#
# Web3(...)
#     ↓
# 建立可以操作 Ethereum 的 Web3 物件
w3 = Web3(Web3.HTTPProvider(os.environ["ETHEREUM_RPC_URL"]))
if not w3.is_connected():
    raise RuntimeError("無法連接 Ethereum RPC")

# 取得目前 Ethereum 最新的 Block Number
#
# w3.eth
#     ↓
# Ethereum 相關功能
#
# w3.eth.block_number
#     ↓
# 向 Ethereum 詢問：
# 「目前最新的 Block Number 是多少？」
#
# 例如可能得到：
# 25779328
latest = w3.eth.block_number
# 根據剛剛取得的 Block Number，
# 把這個 Block 的完整資料抓回來
# latest
#     ↓
# 要查詢的 Block Number
#
# full_transactions=True
#     ↓
# 除了 Block 本身的資料之外，
# 也把這個 Block 裡面的 Transaction 詳細資料一起抓回來
block = w3.eth.get_block(latest, full_transactions=True)
# latest 就是剛剛從 Ethereum 得到的最新 Block Number
print("block number:", latest)


# 印出 Block Hash
#
# block["hash"]
#     ↓
# 從 Block 資料中取得 Block Hash
#
# .hex()
#     ↓
# 把原本的資料格式轉成我們比較常看到的
# 0x...... 十六進位字串
print("block hash:", block["hash"])
print("block hash:", block["hash"].hex())


# 計算這個 Block 裡面有幾筆 Transaction
#
# block["transactions"]
#     ↓
# 取得這個 Block 裡面的所有 Transaction
#
# len(...)
#     ↓
# 計算有幾個
print("transaction count:", len(block["transactions"]))


# 印出這個 Block 的 Gas Used
#
# block["gasUsed"]
#     ↓
# 從 Block 資料中取得 Gas Used
#
# 它代表這個 Block 中的交易實際消耗了多少 Gas
print("gas used:", block["gasUsed"])

print("end")