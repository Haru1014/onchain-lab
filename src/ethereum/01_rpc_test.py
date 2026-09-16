import os
from dotenv import load_dotenv

load_dotenv()

ethereum_rpc = os.environ["ETHEREUM_RPC_URL"]
#solana_rpc = os.environ["SOLANA_RPC_URL"]
print("Ethereum RPC URL exists:", bool(ethereum_rpc))