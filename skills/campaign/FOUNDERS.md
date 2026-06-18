# Founders and the CC convention

Reference for the campaign skill: who the cofounders are and how the CC list is
built on every outbound campaign send.

## Roster

| Key | Name | Send address |
|------|------|--------------|
| samarjit | Samarjit | samarjit.deshmukh.29@dartmouth.edu |
| armaan | Armaan | armaan.priyadarshan.29@dartmouth.edu |
| ethan | Ethan | ethanpzhou@berkeley.edu |
| shamit | Shamit | shamitd@stanford.edu |

## CC convention

Every campaign send CCs the cofounders who are not the sender. The sender is
left out of their own CC list. So the CC value is always the other three
addresses from the roster above.

Per sender:

| Sender | `--cc` value |
|--------|--------------|
| Samarjit | armaan.priyadarshan.29@dartmouth.edu,ethanpzhou@berkeley.edu,shamitd@stanford.edu |
| Armaan | samarjit.deshmukh.29@dartmouth.edu,ethanpzhou@berkeley.edu,shamitd@stanford.edu |
| Ethan | samarjit.deshmukh.29@dartmouth.edu,armaan.priyadarshan.29@dartmouth.edu,shamitd@stanford.edu |
| Shamit | samarjit.deshmukh.29@dartmouth.edu,armaan.priyadarshan.29@dartmouth.edu,ethanpzhou@berkeley.edu |

Pass the matching value to `run.py --cc`.

## Source

Pulled from the existing outreach skills, where the same roster and CC list are
already hardcoded:

- `skills/autonomous-outreach/campaign.sh` (account key to address switch)
- `skills/autonomous-outreach/send_fast.py` (address to first-name map)
- `skills/autonomous-outreach/send_batch.py` and `skills/handle-replies/handle_replies.py`
  (the `CC = "..."` convention of CCing the other founders)
