# FAQ content and FAQPage schema

> **At a glance**
> | | |
> |---|---|
> | **Priority** | P3 |
> | **Template** | a new `/faq` page (optionally per-product FAQ blocks) |
> | **Add to** | on-page FAQ content plus one `FAQPage` JSON-LD block |
> | **You fill in** | return policy text, retail partner list, claims check |
> | **Authority** | the Authority section at the end of this file |

Prepared by Blackwell Enterprises, June 25, 2026.

Your site has no on-page FAQ and no `FAQPage` schema. This is content plus markup,
so it does two jobs: the answers are quotable text that AI engines lift directly into
responses, and the questions match the question-shaped searches people actually run
("what helps with dark spots," "is Good Molecules cruelty-free").

One honest note on scope. Google restricted `FAQPage` rich results in 2023 to
well-known government and health sites, so this markup will not produce the old
expandable FAQ snippet in Google for a brand site. Its value now is for the AI
engines (ChatGPT, Claude, Perplexity, Gemini) that read `FAQPage` blocks to find
clean question and answer pairs, and for the on-page content itself, which is
genuinely useful to shoppers and to crawlers reading the page. We recommend it for
that reason, not for a Google rich result.

---

## Where to put it

Two good options, not mutually exclusive:

- A dedicated `/faq` page with the full set and one `FAQPage` block. Simplest to
  ship.
- A short, product-relevant FAQ block on each product page (for example the three
  questions most relevant to that product), each with its own `FAQPage` block.

Start with the dedicated page. The product-level FAQs are a later enhancement.

---

## First FAQ set

Keyed to real skincare query patterns, answered from your catalog and `llms.txt`.
Answers are written to be quotable in full. The return-policy answer needs your
input.

1. What does Good Molecules recommend for dark spots and hyperpigmentation?
   The Discoloration Correcting Serum is the targeted product for dark spots and
   uniform tone, paired with the Brightening and Dark Spots Bar for daily cleansing.
   Use a daily sunscreen alongside them, since sun exposure drives discoloration.

2. What helps with acne and breakouts?
   Good Molecules Pimple Patches for active spots, and salicylic acid products for
   ongoing congestion. The Niacinamide Serum helps with the look of pores and post
   acne marks.

3. Which niacinamide product should I choose?
   The 10% Niacinamide Serum targets pores, tone, and texture. The Niacinamide
   Brightening Toner delivers a lighter daily dose in your routine. The 5%
   Niacinamide Serum with Ectoin is the gentler option for reactive skin.

4. Is Good Molecules cruelty-free and vegan?
   Yes. Every Good Molecules product is vegan and Leaping Bunny certified
   cruelty-free, and formulated without fragrance.

5. Is Good Molecules good for sensitive skin?
   The line is fragrance-free, which suits sensitive skin. For actives like retinol,
   start with the gentler formulations and introduce them slowly.

6. How is Good Molecules so affordable?
   Good Molecules prices clinically-studied active ingredients honestly, with single
   products from $6. The formulas focus on proven actives without the markup of
   luxury packaging or fragrance.

7. How much does shipping cost and how long does it take?
   Standard US shipping is free on orders $35 and over, and $5 on orders under $35,
   arriving in 3 to 5 business days. Expedited shipping is available, free on orders
   $100 and over.

8. What is Good Molecules' return policy?
   [YOU SUPPLY: return window in days, the process, and whether return shipping is
   free.]

9. Where can I buy Good Molecules?
   Directly at goodmolecules.com, and through [YOU SUPPLY: list your retail partners,
   for example Beautylish, Ulta, Target].

10. What is the difference between the 12ml and 30ml Niacinamide Serum?
    Same formula, two sizes. The 12ml is the trial size and the 30ml is the full
    size. Both are the 10% niacinamide serum.

---

## FAQPage markup

Add this as a `<script type="application/ld+json">` block on the FAQ page. One
`Question` per FAQ, each with an `acceptedAnswer`. The answer text should match the
visible on-page answer word for word, which is a Google requirement and good practice
generally.

```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "What does Good Molecules recommend for dark spots and hyperpigmentation?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "The Discoloration Correcting Serum is the targeted product for dark spots and uniform tone, paired with the Brightening and Dark Spots Bar for daily cleansing. Use a daily sunscreen alongside them, since sun exposure drives discoloration."
      }
    },
    {
      "@type": "Question",
      "name": "Is Good Molecules cruelty-free and vegan?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Yes. Every Good Molecules product is vegan and Leaping Bunny certified cruelty-free, and formulated without fragrance."
      }
    }
    // repeat one Question object per FAQ above
  ]
}
```

---

## Authority

- schema.org FAQPage type, https://schema.org/FAQPage.
- Google Search Central FAQ structured data,
  https://developers.google.com/search/docs/appearance/structured-data/faqpage.
  This page also documents the 2023 restriction on FAQ rich results, which is why we
  position this for AI engine quotability rather than a Google rich result.

---

## Data your team fills in

1. Your return policy text for FAQ 8.
2. Your list of retail partners for FAQ 9.
3. A check of answers 1 through 6 by whoever owns product claims, so the wording
   matches how you describe the products.
