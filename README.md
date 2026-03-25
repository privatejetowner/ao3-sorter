# AO3 Sorter

Generates static HTML reading pages for AO3 tags, sorted by kudos/hits ratio.

## Files

- `ao3_sorter.py`: fetches works for a tag and writes `ao3_sorted_<tag>.html`
- `gen_tags.py`: scans generated HTML files and builds `tags.json`
- `index.html`: landing page that reads `tags.json`
- `update.bat`: local publish helper for batch updates
- `update.local.example.bat`: local-only override template for tags and output path

## Setup

1. Install Python 3.10+.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a local config file:

```bash
copy ao3_config.example.json ao3_config.json
```

4. Edit `ao3_config.json` and paste your AO3 cookie string into `cookie_string`.

You can also keep your tag URLs in the same config file:

```json
{
  "cookie_string": "your cookie",
  "request_delay": 1.0,
  "max_retries": 5,
  "fetch_concurrency": 3,
  "output_dir": "C:\\Users\\your-name\\Desktop\\sidework\\ao3",
  "tag_inputs": [
    "https://archiveofourown.org/tags/Mu%20Zhicheng*s*Wang%20Lujie/works",
    "https://archiveofourown.org/tags/%E6%A1%82%E7%91%9E"
  ]
}
```

You can also configure the script with environment variables:

- `AO3_COOKIE_STRING`
- `AO3_REQUEST_DELAY`
- `AO3_MAX_RETRIES`
- `AO3_FETCH_CONCURRENCY`
- `AO3_CONFIG_PATH`

Environment variables override values from `ao3_config.json`.

## Usage

Generate one tag page:

```bash
python ao3_sorter.py "tag name"
```

Generate one tag page from the first configured URL in `ao3_config.json`:

```bash
python ao3_sorter.py
```

Generate into a specific output directory:

```bash
python ao3_sorter.py "tag name" "C:\path\to\output"
```

Rebuild `tags.json` for the current directory:

```bash
python gen_tags.py
```

Batch update and publish with tags passed on the command line:

```bash
update.bat "桂瑞" "奇文"
```

Batch update and publish all configured URLs from `ao3_config.json`:

```bash
update.bat
```

Or create a local preset:

```bash
copy update.local.example.bat update.local.bat
```

Then edit `update.local.bat` and run:

```bash
update.bat
```

## Notes

- `ao3_config.json` is ignored by git on purpose because it contains private cookies.
- `update.local.bat` is ignored by git so you can keep machine-specific paths and tag presets locally.
- If AO3 is behind Cloudflare, your cookie string may need `cf_clearance` and related cookies.
- Generated HTML files are project output and can stay versioned if you publish them with GitHub Pages.
- `fetch_concurrency` defaults to `3`; if AO3 starts rate-limiting you, reduce it to `1` or `2`.
- You can put either plain tag names or full AO3 tag URLs into `tag_inputs`; `/works` URLs are supported.
