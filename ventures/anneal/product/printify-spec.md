# Printify build sheet

This is the exact spec to enter into Printify (by hand at setup, or via the Printify API once I have the token). Print on demand pushes the finished products into Shopify and generates the variants, so this, not a Shopify CSV, is the real build artifact.

Confirm live base costs at build time and pick the print provider with the lowest base for each blank. Bases below are 2026 estimates.

## AN-TEE-01, the curve tee

- Blank: Bella+Canvas 3001 (unisex jersey tee). Fallback: Comfort Colors 1717 for a heavier hand.
- Colors to enable: Bone (natural) and Graphite (dark grey or vintage black, pick the closest stocked shade).
- Sizes to enable: XS, S, M, L, XL, 2XL, 3XL.
- Print placement:
  - Back, full: `designs/heat-hold-cool.svg`, centered, top of print area ~7.5cm below the collar, max width of the provider's back print area.
  - Front, chest: `designs/chest-mark.svg`, left chest, ~9cm wide.
- Ink: water-based / soft-hand DTG. On Bone use Graphite ink, on Graphite use Bone ink.
- Retail price: $42. Compare-at: leave blank, we do not fake discounts.
- Shopify title: Anneal Curve Tee
- Description: pull from `store/copy.md` AN-TEE-01 block.

## AN-TEE-02, the heavyweight blank tee

- Blank: Comfort Colors 1717 (garment-dyed heavyweight). Fallback: Stanley Stella Creator 2.0 if leaning organic.
- Colors: Bone (ivory or sand) and Steel (a grey-blue if stocked, else heather slate).
- Sizes: XS to 3XL.
- Print placement: front chest only, `designs/chest-mark.svg`, left chest ~9cm. No back print, this is the quiet one.
- Retail price: $46.
- Shopify title: Anneal Heavyweight Tee
- Description: write a two-line variant in brand voice, lead with the 1717's heavier garment-dyed hand.

## AN-HOOD-01, the hoodie

- Blank: Gildan 18500 (heavy blend hoodie). Premium fallback: Stanley Stella Cruiser 2.0.
- Colors: Graphite and Bone.
- Sizes: XS to 3XL.
- Print placement:
  - Front chest: `designs/chest-mark.svg`, centered chest or left chest, ~12cm.
  - Left sleeve: the monospace "MADE BY A MACHINE" caption, vertical down the sleeve, ~2cm tall.
- Retail price: $84.
- Shopify title: Anneal Hoodie
- Description: pull from `store/copy.md` AN-HOOD-01 block.

## Shared settings

- Product category in Shopify: Apparel & Accessories > Clothing.
- Tags: anneal, made-on-order, drop-01.
- Profit check: after entering retail, Printify shows your margin per variant. Confirm every variant clears the $15 contribution floor from `ops/financials.md`. The 3XL upcharge on some blanks can dip margin, raise the 2XL/3XL price by the upcharge if so.
- Mockups: use Printify's flat-lay mockups at launch, replace with real sample photos once samples arrive (see `marketing/launch-plan.md` phase 0).
