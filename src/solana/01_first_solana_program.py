import os
import sys
import asyncio
print(sys.executable)
from dotenv import load_dotenv
from solana.rpc.async_api import AsyncClient
load_dotenv()  # 把 .env 裡面的設定讀進 Python 的環境變數。
RPC_URL = os.environ["SOLANA_RPC_URL"]
async def main():
    async with AsyncClient(RPC_URL) as client:
        # ==================================================
        # 1. 取得 finalized 狀態下最新的 Slot
        # ==================================================
        response = await client.get_slot(
            commitment="finalized"
        )
        slot = response.value
        # ==================================================
        # 2. 根據 Slot 取得 Block
        # ==================================================
        response = await client.get_block(
            slot,
            commitment="finalized",
            max_supported_transaction_version=1,
        )
        block = response.value
        # ==================================================
        # 3. 印出結果
        # ==================================================
        print("slot:", slot)
        print("has block:", block is not None)
        print(
            "transaction count:",
            len(block.transactions) if block is not None else 0
        )
        if block is not None:
            print("transaction count:", len(block.transactions))

            if block.transactions:

                first_transaction = block.transactions[0]

                print("first transaction:")
                print(first_transaction)

                print("transaction type:")
                print(type(first_transaction))
if __name__ == "__main__":
    asyncio.run(main())
