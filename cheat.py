"""
Aviassembly Save Editor
Modifies money, scrap, and advanced scrap in .plane save files.

File format (binary, little-endian, BinaryWriter):
  int32   version = 17
  float32 playtime
  int32   gameMode
  [GameModeData: 4 bools + int32]
  [PlaneStorage: variable size]
  float32 money          <- found dynamically
  bool    creativeMode
  [FogOfWar: int32 N_partitions + N*8 + int32 N_airports + N*8]
  int32   scrap          <- found dynamically (researchPoints)
  int32   advScrap       <- found dynamically (advancedResearchPoints)
  int32   N_parts
  [N_parts strings: unlocked part names starting with "Body"]
  ...
"""

import struct
import shutil
import os
import argparse
from pathlib import Path

SAVE_DIR = Path(os.environ["APPDATA"]).parent / "LocalLow/Aviassembly/Aviassembly/SaveGames"

BODY_PATTERN = bytes([0x00, 0x04, 0x42, 0x6F, 0x64, 0x79])  # Write("Body") = null-check + len(4) + "Body"


def find_offsets(data: bytes) -> dict:
    """
    Dynamically locate money, scrap, and advanced scrap offsets by:
    1. Finding ResearchManager via the Write("Body") pattern
    2. Scanning backward through FogOfWar to locate MoneyManager
    """
    n = len(data)

    # Step 1: find all Write("Body") candidates that look like ResearchManager
    body_positions = []
    for i in range(n - len(BODY_PATTERN)):
        if data[i:i+len(BODY_PATTERN)] == BODY_PATTERN:
            if i < 12:
                continue
            count = struct.unpack_from("<i", data, i - 4)[0]
            scrap = struct.unpack_from("<i", data, i - 8)[0]
            adv   = struct.unpack_from("<i", data, i - 12)[0]
            if 10 <= count <= 200 and 0 <= scrap <= 100000 and 0 <= adv <= 100000:
                body_positions.append(i)

    if not body_positions:
        raise RuntimeError("Could not locate ResearchManager in the save file.")

    # Pick the earliest valid position
    body_offset = body_positions[0]
    scrap_offset = body_offset - 12
    adv_offset   = scrap_offset + 4

    # Step 2: scan backward to find money offset via FogOfWar structure.
    # ResearchManager starts at scrap_offset.
    # FogOfWar ends just before it.
    # We try every candidate money position and verify FogOfWar fits exactly.
    money_offset = None
    search_start = max(20, scrap_offset - 5000)

    for p in range(search_start, scrap_offset - 8):
        money_candidate = struct.unpack_from("<f", data, p)[0]
        if not (0 <= money_candidate <= 1_000_000):
            continue
        bool_byte = data[p + 4]
        if bool_byte > 1:
            continue
        fog_start = p + 5
        if fog_start + 4 >= scrap_offset:
            continue
        part_count = struct.unpack_from("<i", data, fog_start)[0]
        if not (0 <= part_count <= 2000):
            continue
        airports_off = fog_start + 4 + part_count * 8
        if airports_off + 4 > scrap_offset:
            continue
        airport_count = struct.unpack_from("<i", data, airports_off)[0]
        if not (0 <= airport_count <= 500):
            continue
        research_start = airports_off + 4 + airport_count * 8
        if research_start == scrap_offset:
            money_offset = p
            break

    if money_offset is None:
        raise RuntimeError(
            "Could not locate MoneyManager. "
            "Try saving in-game and running the script again."
        )

    return {
        "money": money_offset,
        "scrap": scrap_offset,
        "adv_scrap": adv_offset,
    }


def list_saves():
    saves = sorted(SAVE_DIR.glob("*.plane"))
    if not saves:
        print("No save files found.")
        return []
    for i, s in enumerate(saves):
        try:
            data = s.read_bytes()
            offs = find_offsets(data)
            money = struct.unpack_from("<f", data, offs["money"])[0]
            scrap = struct.unpack_from("<i", data, offs["scrap"])[0]
            adv   = struct.unpack_from("<i", data, offs["adv_scrap"])[0]
            print(f"  [{i}] {s.name:<25} | money={money:>10.0f}  scrap={scrap:>8}  adv_scrap={adv:>8}")
        except RuntimeError as e:
            print(f"  [{i}] {s.name:<25} | ERROR: {e}")
    return saves


def edit_save(save_path: Path, money=None, scrap=None, advanced_scrap=None):
    data = bytearray(save_path.read_bytes())
    offs = find_offsets(bytes(data))

    backup = save_path.with_suffix(".plane.bak")
    if not backup.exists():
        shutil.copy2(save_path, backup)
        print(f"Backup created: {backup.name}")

    if money is not None:
        struct.pack_into("<f", data, offs["money"], float(money))
        print(f"  money     -> {money}")
    if scrap is not None:
        struct.pack_into("<i", data, offs["scrap"], int(scrap))
        print(f"  scrap     -> {scrap}")
    if advanced_scrap is not None:
        struct.pack_into("<i", data, offs["adv_scrap"], int(advanced_scrap))
        print(f"  adv_scrap -> {advanced_scrap}")

    save_path.write_bytes(data)
    print(f"Saved: {save_path.name}")


def main():
    parser = argparse.ArgumentParser(
        description="Aviassembly Save Editor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cheat.py                          # list saves and current values
  python cheat.py --money 999999           # set money on AutoSave 0
  python cheat.py --money 50000 --scrap 500 --advanced-scrap 200
  python cheat.py --save 1 --money 99999  # target slot 1
        """,
    )
    parser.add_argument("--money", type=float)
    parser.add_argument("--scrap", type=int)
    parser.add_argument("--advanced-scrap", type=int, dest="advanced_scrap")
    parser.add_argument("--save", type=int, default=0, help="Save slot index (default: 0)")

    args = parser.parse_args()

    print(f"\nSave directory: {SAVE_DIR}\n")
    saves = list_saves()

    if not saves:
        return

    if args.money is None and args.scrap is None and args.advanced_scrap is None:
        print("\nNothing to do. Use --money, --scrap, or --advanced-scrap.")
        return

    if args.save >= len(saves):
        print(f"Error: index {args.save} is out of range ({len(saves)} save(s) found).")
        return

    target = saves[args.save]
    print(f"\nEditing: {target.name}")
    edit_save(target, money=args.money, scrap=args.scrap, advanced_scrap=args.advanced_scrap)

    print("\n=== Values after edit ===")
    list_saves()


if __name__ == "__main__":
    main()
