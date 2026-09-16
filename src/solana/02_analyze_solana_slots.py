import json
from pathlib import Path
from collections import defaultdict
import pandas as pd
START_SLOT = 100000000
END_SLOT = 100000999
RAW_DATA_DIR = Path("data/raw/solana/blocks")
OUTPUT_DIR = Path("data/processed/solana")


def load_block(slot):
    """
    讀取指定 slot 的原始 JSON。

    如果該 slot 沒有 block，
    JSON 內容預期為 null，
    此時回傳 None。
    """

    input_file = RAW_DATA_DIR / f"slot_{slot}_original.json"

    if not input_file.exists():
        print(f"    File not found: {input_file}")
        return None

    with open(input_file, "r", encoding="utf-8") as f:
        block = json.load(f)

    return block


# ============================================================
# 3. 判斷 transaction version
# ============================================================

def get_transaction_version(transaction):
    """
    判斷 transaction 是 legacy 還是 versioned。

    Solana transaction 一般可以是：

    legacy
    0

    這裡回傳：
        "legacy"
        "versioned"
    """

    version = transaction.get("version")

    if version is None or version == "legacy":
        return "legacy"

    return "versioned"


# ============================================================
# 4. 取得 Program ID
# ============================================================

def get_program_id_from_instruction(instruction, account_keys):
    """
    從一個 instruction 找出 Program ID。

    instruction.programIdIndex
    指向 message.accountKeys 中的某一個位置。
    """

    program_id_index = instruction.get("programIdIndex")

    if program_id_index is None:
        return None

    if program_id_index >= len(account_keys):
        return None

    return account_keys[program_id_index]


# ============================================================
# 5. 分析單一 block
# ============================================================

def analyze_block(slot, block, transaction_rows, program_stats):
    """
    分析一個 block。

    回傳：
        slot_summary
    """

    # --------------------------------------------------------
    # 沒有 block
    # --------------------------------------------------------

    if block is None:
        return {
            "slot_num": slot,
            "has_block": False,
            "transaction_count": 0,
            "success_count": 0,
            "failed_count": 0,
            "legacy_count": 0,
            "versioned_count": 0,
            "versioned_ratio": 0.0,
        }

    # --------------------------------------------------------
    # 取得 transactions
    # --------------------------------------------------------

    transactions = block.get("transactions", [])

    transaction_count = len(transactions)

    success_count = 0
    failed_count = 0

    legacy_count = 0
    versioned_count = 0

    # ========================================================
    # 分析每一筆 transaction
    # ========================================================

    for tx_index, tx_data in enumerate(transactions):

        transaction = tx_data.get("transaction", {})
        meta = tx_data.get("meta")

        # ----------------------------------------------------
        # Transaction version
        # ----------------------------------------------------

        tx_version = get_transaction_version(transaction)

        if tx_version == "legacy":
            legacy_count += 1
        else:
            versioned_count += 1

        # ----------------------------------------------------
        # Success / Failed
        # ----------------------------------------------------

        if meta is None:
            failed_count += 1
            success = False

        else:
            error = meta.get("err")

            if error is None:
                success_count += 1
                success = True
            else:
                failed_count += 1
                success = False

        # ----------------------------------------------------
        # Fee
        # ----------------------------------------------------

        fee_lamports = None
        fee_sol = None

        if meta is not None:
            fee_lamports = meta.get("fee")

            if fee_lamports is not None:
                fee_sol = fee_lamports / 1_000_000_000

        # ----------------------------------------------------
        # Signature
        # ----------------------------------------------------

        signatures = transaction.get("signatures", [])

        if len(signatures) > 0:
            signature = signatures[0]
        else:
            signature = None

        # ----------------------------------------------------
        # Message
        # ----------------------------------------------------

        message = transaction.get("message", {})

        account_keys = message.get("accountKeys", [])

        # ----------------------------------------------------
        # Outer instructions
        # ----------------------------------------------------

        outer_program_ids = []

        instructions = message.get("instructions", [])

        for instruction in instructions:

            program_id = get_program_id_from_instruction(
                instruction,
                account_keys
            )

            if program_id is not None:

                outer_program_ids.append(program_id)

                program_stats[program_id]["call_count"] += 1
                program_stats[program_id]["outer_count"] += 1

        # ----------------------------------------------------
        # Inner instructions
        # ----------------------------------------------------

        inner_program_ids = []

        if meta is not None:

            inner_instructions = meta.get(
                "innerInstructions",
                []
            )

            for inner_group in inner_instructions:

                inner_list = inner_group.get(
                    "instructions",
                    []
                )

                for instruction in inner_list:

                    program_id = get_program_id_from_instruction(
                        instruction,
                        account_keys
                    )

                    if program_id is not None:

                        inner_program_ids.append(program_id)

                        program_stats[program_id]["call_count"] += 1
                        program_stats[program_id]["inner_count"] += 1

        # ----------------------------------------------------
        # 計算這筆 transaction 呼叫過哪些不同 Program
        # ----------------------------------------------------

        unique_program_ids = set(
            outer_program_ids + inner_program_ids
        )

        for program_id in unique_program_ids:
            program_stats[program_id]["tx_count"] += 1

        # ----------------------------------------------------
        # 儲存 Transaction-level 資料
        # ----------------------------------------------------

        transaction_rows.append({
            "slot_num": slot,
            "transaction_index": tx_index,
            "signature": signature,
            "success": success,
            "fee_lamports": fee_lamports,
            "fee_sol": fee_sol,
            "transaction_version": tx_version,
            "outer_program_ids": json.dumps(
                outer_program_ids,
                ensure_ascii=False
            ),
            "inner_program_ids": json.dumps(
                inner_program_ids,
                ensure_ascii=False
            ),
        })

    # ========================================================
    # Versioned ratio
    # ========================================================

    if transaction_count > 0:
        versioned_ratio = versioned_count / transaction_count
    else:
        versioned_ratio = 0.0

    # ========================================================
    # 回傳 Block-level summary
    # ========================================================

    return {
        "slot_num": slot,
        "has_block": True,
        "transaction_count": transaction_count,
        "success_count": success_count,
        "failed_count": failed_count,
        "legacy_count": legacy_count,
        "versioned_count": versioned_count,
        "versioned_ratio": versioned_ratio,
    }


# ============================================================
# 6. 主程式
# ============================================================

def main():

    print("=" * 60)
    print("Solana Slot Analysis")
    print("=" * 60)

    print(f"START_SLOT: {START_SLOT}")
    print(f"END_SLOT:   {END_SLOT}")
    print()

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # 儲存分析結果
    # --------------------------------------------------------

    slot_rows = []
    transaction_rows = []

    program_stats = defaultdict(
        lambda: {
            "call_count": 0,
            "outer_count": 0,
            "inner_count": 0,
            "tx_count": 0,
        }
    )

    # ========================================================
    # 逐個 slot 分析
    # ========================================================

    total_slots = END_SLOT - START_SLOT + 1

    for index, slot in enumerate(
        range(START_SLOT, END_SLOT + 1),
        start=1
    ):

        print(
            f"[{index}/{total_slots}] "
            f"Analyzing slot {slot}..."
        )

        block = load_block(slot)

        slot_summary = analyze_block(
            slot,
            block,
            transaction_rows,
            program_stats
        )

        slot_rows.append(slot_summary)

        if block is None:
            print("    No block")
        else:
            print(
                f"    Transactions: "
                f"{slot_summary['transaction_count']}"
            )

    # ========================================================
    # DataFrame
    # ========================================================

    slot_df = pd.DataFrame(slot_rows)

    transaction_df = pd.DataFrame(
        transaction_rows
    )

    program_rows = []

    for program_id, stats in program_stats.items():

        program_rows.append({
            "program_id": program_id,
            "call_count": stats["call_count"],
            "outer_count": stats["outer_count"],
            "inner_count": stats["inner_count"],
            "tx_count": stats["tx_count"],
        })

    program_df = pd.DataFrame(program_rows)

    # --------------------------------------------------------
    # Program ID 按呼叫次數排序
    # --------------------------------------------------------

    if not program_df.empty:

        program_df = program_df.sort_values(
            "call_count",
            ascending=False
        )

    # ========================================================
    # 輸出 CSV
    # ========================================================

    slot_output = (
        OUTPUT_DIR
        / f"slot_summary_{START_SLOT}_{END_SLOT}.csv"
    )

    transaction_output = (
        OUTPUT_DIR
        / f"transaction_details_{START_SLOT}_{END_SLOT}.csv"
    )

    program_output = (
        OUTPUT_DIR
        / f"program_id_stats_{START_SLOT}_{END_SLOT}.csv"
    )

    slot_df.to_csv(
        slot_output,
        index=False,
        encoding="utf-8-sig"
    )

    transaction_df.to_csv(
        transaction_output,
        index=False,
        encoding="utf-8-sig"
    )

    program_df.to_csv(
        program_output,
        index=False,
        encoding="utf-8-sig"
    )

    # ========================================================
    # 結果摘要
    # ========================================================

    print()
    print("=" * 60)
    print("Analysis finished")
    print("=" * 60)

    print(f"Slot summary:")
    print(f"    {slot_output}")

    print(f"Transaction details:")
    print(f"    {transaction_output}")

    print(f"Program ID statistics:")
    print(f"    {program_output}")

    print()

    # --------------------------------------------------------
    # 整體統計
    # --------------------------------------------------------

    total_blocks = int(
        slot_df["has_block"].sum()
    )

    total_transactions = int(
        slot_df["transaction_count"].sum()
    )

    total_success = int(
        slot_df["success_count"].sum()
    )

    total_failed = int(
        slot_df["failed_count"].sum()
    )

    print("Overall statistics")
    print(f"    Total slots:        {total_slots}")
    print(f"    Slots with block:   {total_blocks}")
    print(f"    Total transactions:  {total_transactions}")
    print(f"    Successful tx:       {total_success}")
    print(f"    Failed tx:           {total_failed}")


# ============================================================
# 7. 執行
# ============================================================

if __name__ == "__main__":
    main()