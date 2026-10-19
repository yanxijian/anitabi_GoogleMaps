# anitabi → Google My Maps

**English** · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

Export the pilgrimage maps from [anitabi](https://www.anitabi.cn/map) as **KML**, then import that file into [Google My Maps](https://www.google.com/maps/d/) to browse it on Google Maps.

Standard library only (Python 3.8+) — **there is no `requests` to install**.

## Usage

```bash
# one bangumi_id (you can pass several)
python anitabi_GoogleMaps.py 331884

# export several titles at once
python anitabi_GoogleMaps.py 331884 4912

# pick the output file / directory
python anitabi_GoogleMaps.py 331884 -o bocchi-the-rock.kml
python anitabi_GoogleMaps.py 331884 --outdir maps

# interactive mode (no id given; press Enter or type q to quit)
python anitabi_GoogleMaps.py
```

`bangumi_id` is the number in a title page URL: open <https://www.anitabi.cn/map>, search for the title, and take the `bangumi/<id>` segment from the address bar.

To import: open [Google My Maps](https://www.google.com/maps/d/) → create a new map → add a layer → import → choose the generated `.kml`.

## When the network is unreliable

The anitabi API times out or answers 403 on some networks. The script retries (`--retries`, default 2; `--timeout`, default 20 s) and then falls back to a **`{id}.json` placed next to the script**:

1. open `https://api.anitabi.cn/bangumi/<id>/points/detail` in a browser
2. save it as `{id}.json` next to the script
3. run `python anitabi_GoogleMaps.py <id> --offline`

Note: with `--offline` and only a `{id}.json` (the array of points) and no title information, the output file name falls back to the bangumi_id.

## What changed from the old version

| Problem | Before | Now |
| --- | --- | --- |
| Dependency | needed `requests` | standard library only |
| Arguments | interactive input only | positional ids plus `-o` / `--outdir` / `--offline` / `--timeout` / `--retries` |
| Timeout and retry | none (could hang forever) | 20 s timeout plus exponential backoff |
| KML namespace | `http://www.opengis.net` (not the spec) | `http://www.opengis.net/kml/2.2` |
| Document title | no `<Document><name>` | present |
| File name | used the title verbatim; a title like `Re:Zero` failed to write on Windows | strips `<>:"/\|?*`, reserved names, trailing dots and over-long names |
| Missing fields | `item['geo']` / `item['id']` raised KeyError | the point is skipped and counted |
| XML safety | image URL unescaped, could break the attribute or end the CDATA early | attribute escaping plus CDATA splitting |
| Writing | overwrote in place, an interrupt left half a file | writes `.tmp` then `os.replace` |
| Verification | none | XML shape and coordinate order are covered by tests |

## Tests

```bash
python -m unittest discover -s tests -v
```

23 cases, all offline: the HTTP layer is replaced by a fake, covering KML structure, escaping, coordinate order, file-name sanitising, retry and fallback, end-to-end output and exit codes.

## Known limits

- Only Placemarks are exported: no routes, no image downloads, no cover art.
- Coordinates are converted from anitabi's `[latitude, longitude]` into KML's `longitude,latitude,0`; no datum correction is applied.
- The API has no public documentation, so a point with missing fields is skipped instead of aborting the whole conversion.
- On Windows consoles whose code page is not UTF-8 the script switches to 65001; if that fails, non-ASCII output turns into `?` but never raises `UnicodeEncodeError` and aborts the conversion. Output redirected to a file is always UTF-8.

## A few maps I made

1. Saekano: How to Raise a Boring Girlfriend - https://www.google.com/maps/d/viewer?mid=19CAvroXYoTebZ4wZ9tvg9XvoRiL6XvE&usp=sharing
2. Love Live! Superstar!! - https://www.google.com/maps/d/viewer?mid=1_shPyo5kTGYvp5Q2BGH9X8e36bfrk94&usp=sharing
3. Sword Art Online - https://www.google.com/maps/d/viewer?mid=1V2zw6YQYttRrdspKxNwpfAsRh4NLeys&usp=sharing
4. BanG Dream! It's MyGO!!!!! & Ave Mujica - https://www.google.com/maps/d/viewer?mid=1ty5EjnQo1LLCgDqHdhwijhZDN6ZdDlM&usp=sharing
5. Sound! Euphonium - https://www.google.com/maps/d/viewer?mid=1XfU4x6KMA1FdQ2180QJ5Ua_wgYQIdTI&usp=sharing
6. Too Many Losing Heroines! - https://www.google.com/maps/d/viewer?mid=1CNXd5Xkkh2Qf0QZPNG7azKCJC-aCDjE&usp=sharing
7. Bocchi the Rock! - https://www.google.com/maps/d/viewer?mid=13FySg0WBFmL4ptTyzw5CDndq0NWQdkc&usp=sharing

## License

MIT, see [LICENSE](LICENSE).
