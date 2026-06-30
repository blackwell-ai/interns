# Data dictionary

One record describes one video product review, in foundation_dataset.jsonl (one
JSON object per line), validated against schema/review.schema.json.

## product
- name: product name.
- product_id: stable slug shared by every review of the same product.
- brand: brand name.

## video
- reviewer: the reviewer.
- title: the review title.
- published_at: ISO 8601 date.
- duration_seconds, view_count: integers.
- review_type: single_review, comparison, or roundup.

## transcript
The full review transcript.

## reviewer_profile
- skin_type: free text, for example oily or combination.
- acne_prone: yes | no | unknown.
- skin_tone_depth: fair | light | medium | tan | deep | unknown.
- undertone: warm | cool | neutral | olive | unknown.
- shade_used: the shade named, verbatim.

## outcomes
- stayed_matte: yes | mostly | no | not_tested.
- wear_hours: hours it looked good, or null.
- broke_out / oxidized / would_repurchase: yes | no | not_mentioned.
- overall: positive | mixed | negative.

## is_sponsored
Boolean, flagged only on explicit evidence.

## key_quote
One verbatim line from the reviewer.
