`codex_reset_info.py` prints [Codex](https://openai.com/codex/) subscription usage and rate limit reset details.

This is a simple, dependency-free Python script. Here's how to use it:

```sh
# download the script
curl -fsSLO https://raw.githubusercontent.com/pmxi/codex_reset/main/codex_reset_info.py
# run it
python3 codex_reset_info.py
```

Codex now offers ["banked resets"](https://x.com/OpenAI/status/2065225362544726371) that let you reset 5-hour and 7-day limits on demand, but those resets expire and Codex does not show their expiration dates. This script displays those reset-credit details.

Note: This reads your Codex `auth.json` file and calls the Codex backend using those credentials.

## Example

```
$ ./codex_reset_info.py
Codex usage
Checked: 2026-06-30 12:39:57 AM EDT

Account
Email: paras...@gmail.com
Name: Paras Mittal
Account ID: fb735652-b434-46d6-8488-f128a725b208
Plan: Plus

Limit status
Allowed: true
Limit reached: false

Usage windows
5h limit
  Used: 8%
  Remaining: 92%
  Window seconds: 18000
  Resets in: 4h 14m
  Resets at: 2026-06-30 4:54:33 AM EDT

Weekly limit
  Used: 1%
  Remaining: 99%
  Window seconds: 604800
  Resets in: 6d 23h
  Resets at: 2026-07-06 11:54:33 PM EDT

Reset credits
Available count: 3

Credit 1
  ID: RateLimitResetCredit_6fa20b24afc48191ace728208e063113
  Title: Full reset (Weekly + 5 hr)
  Type: codex_rate_limits
  Status: available
  Granted at: 2026-06-11 11:56:08 PM EDT
  Expires at: 2026-07-11 11:56:08 PM EDT

Credit 2
  ID: RateLimitResetCredit_1505699669f48191b7ebfdab6ea1fb55
  Title: Full reset (Weekly + 5 hr)
  Type: codex_rate_limits
  Status: available
  Granted at: 2026-06-17 8:34:17 PM EDT
  Expires at: 2026-07-17 8:34:17 PM EDT

Credit 3
  ID: RateLimitResetCredit_33d55797fa2c8191ba6f1290148732c1
  Title: Full reset (Weekly + 5 hr)
  Type: codex_rate_limits
  Status: available
  Granted at: 2026-06-26 8:09:46 PM EDT
  Expires at: 2026-07-26 8:09:46 PM EDT
```
