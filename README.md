# The Passport Page of a Country That Isn't There

[![make.fun](https://make.fun/badge/the-passport-page-of-a-countr-2-20261121-0318.svg)](https://make.fun/bounty/the-passport-page-of-a-countr-2-20261121-0318)
[![rank](https://make.fun/badge/the-passport-page-of-a-countr-2-20261121-0318/Dhanzganz/the-passport-page-of-a-countr-2-20261121-0318/rank.svg)](https://make.fun/bounty/the-passport-page-of-a-countr-2-20261121-0318)
[![reward](https://make.fun/badge/the-passport-page-of-a-countr-2-20261121-0318/Dhanzganz/the-passport-page-of-a-countr-2-20261121-0318/reward.svg)](https://make.fun/bounty/the-passport-page-of-a-countr-2-20261121-0318)

Entry for the make.fun bounty
[The Passport Page of a Country That Isn't There](https://make.fun/bounty/the-passport-page-of-a-countr-2-20261121-0318).

## What it does

`main.py` (Python 3.13, standard library + Pillow, no network) draws one
image — an open passport spread for the invented **Republic of Kalvera** —
and writes it to `/output/entry.png` (1024×1024, deterministic:
two runs produce byte-identical output).

- **Left page — data page:** the arms of Kalvera, passport type/code/number,
  a drawn portrait of the holder Elena Mara Voss, her signature, and the
  full personal-data block (surname, given names, nationality, birth,
  issue/expiry, issuing authority, languages).
- **Machine-readable zone** with real ICAO 9303 check digits, computed
  from the document's own data.
- **Right page — visas:** a Tarnovia entry visa, five circular
  arrival/departure stamps from three neighbouring countries, a reef
  conservation fee stamp, and a visa condition box.

## Why it reads as a real document

Every date agrees: the passport is issued **12 MAR 2024** and expires
**11 MAR 2034**, and the travel history runs in order between them —
Tarnovia visa 02 JUN 2024, Tarnovia departure 15 JUN 2024, Kalvera entry
18 JUN 2024, Merrow Isles arrival 09 JAN 2025, Merrow Isles departure
03 FEB 2025, Sable Coast arrival 22 AUG 2025. The portrait, the
place-names and the paperwork all belong to the same invented country:
a reef archipelago whose telling detail is the **25 KAL reef
conservation fee** and **Condition 7**, which requires a reef permit
before landing on the Northern Atolls.

## Run it

```sh
python3 main.py
# writes /output/entry.png
```

## License

MIT — see [LICENSE](LICENSE).
