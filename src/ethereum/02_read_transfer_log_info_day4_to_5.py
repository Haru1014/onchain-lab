from web3 import Web3
import json
import os
from dotenv import load_dotenv
from decimal import Decimal
from_block =  25779334
to_block = 25779328+10

# 1. 連接 Ethereum
load_dotenv()
w3 = Web3(Web3.HTTPProvider(os.getenv("ETHEREUM_RPC_URL")))
ABI_PATH = "data/raw/ethereum/ERC-20_ABI/USDC_second_layer_erc_abi.json"
with open(ABI_PATH, "r", encoding="utf-8") as f:
    erc20_abi = json.load(f)
token_address = Web3.to_checksum_address("0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48")
token = w3.eth.contract(address=token_address,abi=erc20_abi)
logs = token.events.Transfer.get_logs(from_block=from_block,to_block=to_block)

decimals = token.functions.decimals().call()
symbol = token.functions.symbol().call()
print(f"找到 {len(logs)} 筆 Transfer logs")
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
results = []
for i, log in enumerate(logs):

    from_address = log["args"]["from"]
    to_address = log["args"]["to"]
    raw_value = log["args"]["value"]
    # --------------------------------------------------------
    # 將原始整數依 decimals 正規化
    # --------------------------------------------------------
    normalized_value = (Decimal(raw_value) / (Decimal(10) ** decimals))
    # --------------------------------------------------------
    # 判斷 mint / burn / 一般 transfer
    # --------------------------------------------------------
    from_is_zero = (from_address.lower() == ZERO_ADDRESS.lower())
    to_is_zero = (to_address.lower() == ZERO_ADDRESS.lower())
    if from_is_zero:
        transfer_type = "mint"
    elif to_is_zero:
        transfer_type = "burn"
    else:
        transfer_type = "transfer"
    result = {
        "block_number": log["blockNumber"],
        "transaction_hash": log["transactionHash"].hex(),
        "from": from_address,
        "to": to_address,
        "raw_value": raw_value,
        "normalized_value": str(normalized_value),
        "symbol": symbol,
        "type": transfer_type,
    }

    results.append(result)

print()
for i, result in enumerate(results):
    print("----------------------------------------")
    print("Transfer #", i + 1)
    print("Block:", result["block_number"])
    print("Transaction:", result["transaction_hash"])
    print("From:", result["from"])
    print("To:", result["to"])
    print("Raw value:", result["raw_value"])
    print(
        "Amount:",
        result["normalized_value"],
        result["symbol"]
    )
    print("Type:", result["type"])
mint_count = 0
burn_count = 0
transfer_count = 0
for result in results:
    if result["type"] == "mint":
        mint_count += 1
    elif result["type"] == "burn":
        burn_count += 1
    elif result["type"] == "transfer":
        transfer_count += 1
print()
print("========== Transfer Type Summary ==========")
print("Mint:", mint_count)
print("Burn:", burn_count)
print("Transfer:", transfer_count)
# ============================================================
# 10. 研究上的注意事項
# ============================================================

print()
print("========== Research Note ==========")
print(
    "Transfer event 表示 ERC-20 合約記錄了一筆 token "
    "轉移事件，但不一定代表現實世界中的付款。"
)
print(
    "from / to / value 可以描述 token 的轉移，"
    "但實際商業目的仍需要結合交易與合約上下文判斷。"
)