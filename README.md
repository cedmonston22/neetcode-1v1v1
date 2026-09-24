# NeetCode 1v1v1

A local coding race for 2–3 people on the same Wi-Fi. Everyone gets the same NeetCode problem. The first player to pass every test wins. If the clock runs out, whoever passed the most tests wins, and a tie goes to whoever got there first.

- **Problem pool:** 44 Easy and Medium problems across Arrays & Hashing, Two Pointers, Sliding Window, Stack, Binary Search, Linked List and Trees. You filter by topic and difficulty in the lobby.
- **Match length:** anyone in the lobby can set it from 1 to 10 minutes. The default is 5.
- **Languages:** Python only.
- **Run** checks your code against the visible examples. **Submit** checks it against every test (examples plus about 25 generated ones) and updates your lane for everyone.
- **Opponents' code** stays hidden during the match; you only see their progress bars. Everyone's solutions are shown side by side at the end.
- **Slow solutions fail.** 33 of the 44 problems end with large tests at LeetCode's maximum input sizes. The other 11 have small limits on LeetCode, so a faster solution wouldn't show up in the timing. Every problem has a time limit of 4x the NeetCode reference solution's runtime, never less than 2.5 seconds. Brute-force O(n²) solutions time out on those tests, so they can't reach a full pass. Two Sum's large test goes past LeetCode's limit (50,000 numbers instead of 10,000), because brute force still finishes in time at 10,000.
- **Ties:** if two people submit correct answers close together, the earlier Submit click wins, not whichever finished grading first.

## Play

```bash
python -m server
```

The server prints a link like `http://192.168.1.23:8000`. Open it, create a room, and send the room link to your roommates.

The first time, Windows will ask whether Python can accept connections. Allow it on private networks. If your roommates still can't connect, add an inbound firewall rule for TCP port 8000.

The editor (Monaco) loads from a CDN, so each player needs internet access. Without it, the page falls back to a plain text box.

### Settings

| Variable | Default | What it does |
|---|---|---|
| `NCV_PORT` | `8000` | Port to serve on |
| `NCV_MATCH_SECONDS` | `300` | Default match length for new rooms, in seconds |
| `NCV_COUNTDOWN_SECONDS` | `3` | Countdown before a match starts |

## Tests

```bash
python -m pytest -q
```

## How the problem data was built

This was a one-time process, and the output is committed in `data/`.

1. `scraper/neetcode_list.py` lists the problem slugs by topic. Class-design problems and problems with unusual input formats are left out for now.
2. `python scraper/scrape.py` pulls each problem's description, starter code, parameter types and examples from LeetCode into `data/raw_problems.json`. Premium problems are skipped.
3. `python scraper/fetch_solutions.py` downloads NeetCode's MIT-licensed Python solutions into `scraper/solutions/`.
4. `python scraper/build_tests.py` runs the generators in `scraper/generators/` through each reference solution to get expected outputs, then writes `data/problems.json`.
