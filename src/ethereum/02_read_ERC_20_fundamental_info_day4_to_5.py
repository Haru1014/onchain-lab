from web3 import Web3
import os
import json
with open("data/raw/ethereum/ERC-20_ABI/USDC_second_layer_erc_abi.json", "r", encoding="utf-8") as f:
    usdc_abi = json.load(f)
#等同可以call的是secon的這份api，但要配first的地址
w3 = Web3(Web3.HTTPProvider(os.environ["ETHEREUM_RPC_URL"]))
erc20_abi = [
    {
        "inputs": [],
        "name": "name",
        "outputs": [{"type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "symbol",
        "outputs": [{"type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"type": "uint8"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
    "inputs": [],
    "name": "totalSupply",
    "outputs": [{"type": "uint256"}],
    "stateMutability": "view",
    "type": "function",
},
]
#外層
token_address = Web3.to_checksum_address("0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48")
token = w3.eth.contract(address=token_address, abi= usdc_abi)#代表某個特定的智能合約
print(token.address)
print(token.functions.name().call())
print(token.functions.symbol().call())
print(token.functions.decimals().call())
print(token.functions.totalSupply().call())
print(token.functions.totalSupply())
total_supply = token.functions.totalSupply().call()
decimals = token.functions.decimals().call()
print(total_supply)
print(total_supply / 10**decimals)
#中層
token_address = Web3.to_checksum_address("0x43506849D7C04F9138D1A2050bbF3A0c054402dd")
token = w3.eth.contract(address=token_address, abi= usdc_abi)

print(token.functions.name().call())
print(token.functions.symbol().call())
print(token.functions.decimals().call())
print(token.functions.totalSupply().call())

#內層

token_address = Web3.to_checksum_address("0x800C32EaA2a6c93cF4CB51794450ED77fBfbB172")
token = w3.eth.contract(address=token_address, abi=erc20_abi)

print(token.functions.name().call())
print(token.functions.symbol().call())
print(token.functions.decimals().call())
print(token.functions.totalSupply().call())