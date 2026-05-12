# aviassembly-tools

A save editor for [Aviassembly](https://store.steampowered.com/app/2660460/Aviassembly/). Set your money, scrap, and advanced scrap to whatever you want without touching the game.

## What it edits

| Field | Type | Description |
|---|---|---|
| Money | float | The coins shown in the top-right HUD |
| Scrap | int | Research points used to unlock parts |
| Advanced Scrap | int | The second (rarer) research currency |

## Requirements

- Python 3.x
- Aviassembly installed (save files are auto-detected from `AppData\LocalLow`)

## Usage

Close the game before running the script. Open it again after.

```
# See current values across all your saves
python cheat.py

# Give yourself money
python cheat.py --money 999999

# Give yourself scrap and advanced scrap
python cheat.py --scrap 500 --advanced-scrap 200

# All three at once
python cheat.py --money 999999 --scrap 999 --advanced-scrap 999

# Target a specific save slot (0-indexed, default is 0)
python cheat.py --save 1 --money 50000
```

A `.bak` backup of the original save is created automatically the first time you modify a file. It won't be overwritten on subsequent runs, so you always have a way back.

## How it works

The `.plane` save files are raw binary (Unity's `BinaryWriter`). Money and scrap aren't at fixed offsets — they shift depending on how many plane parts you have and how much of the map you've explored.

The script finds them dynamically every time:

1. Scans for the `ResearchManager` block by locating the part name list (starts with `"Body"`)
2. Parses the `FogOfWar` block that sits right before it (explored map partitions + discovered airports)
3. Lands on `MoneyManager` which is right before `FogOfWar`

This means it still works correctly after you redesign your plane or explore new areas.

## Notes

- The game has a built-in money cheat: hold **C + Enter** in-game for 100k money, and **R + Enter** to unlock all parts in the research tree. This script is mainly useful for scrap since there's no in-game cheat for it.
- Only tested on the desktop (non-Steam) version. Should work on Steam too since save files are local.
- Don't modify the save while the game is running — it autosaves and will overwrite your changes.
