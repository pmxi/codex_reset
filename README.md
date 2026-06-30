`codex_reset_info.py` prints [Codex](https://openai.com/codex/) subscription usage and rate limit reset details.

This is a simple, dependency-free Python script. Here's how to use it:

```sh
python3 codex_reset_info.py
```

## Setup

Download the live script from GitHub and run it:

```sh
curl -fsSLO https://raw.githubusercontent.com/pmxi/codex_reset/main/codex_reset_info.py
python3 codex_reset_info.py
```

This script was created because the [Codex team now issues "banked resets"](https://x.com/OpenAI/status/2065225362544726371) that can be used to reset 5-hour and 7-day limits anytime, but they expire and their expiry date is not displayed anywhere. This script shows that.

Note: This will read your Codex `auth.json` file and calls the Codex backend using those credentials.
