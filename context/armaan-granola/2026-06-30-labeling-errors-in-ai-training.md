# Labeling errors in AI training

- Date: 2026-06-30
- Granola document id: 6db2fca8-210b-4504-844b-42c2874e699d
- Created at: 2026-06-30T11:08:00-07:00
- Attendees: Armaan Priyadarshan (armaanp4423@gmail.com)
- Content source: enhanced notes (AI summary panel) via Granola MCP
- Transcript: not available via MCP

---

## Notes

### Armaan’s Product and the Core Data Problem

- Building a brand-to-neutral-reviewer network for AI-powered consumer product discovery
  - Aggregates video reviews, turns them into retrievable data at inference time
  - Essentially RAG for product quality and social sentiment
- Key question: how to make this data high-quality and useful for training

### Label Noise: Why It Matters

- Labeling errors are endemic: human bias, human error, or AI-generated noise
- Problem scales down with data volume: large, diverse datasets are naturally more resilient
- Becomes critical with small or skewed datasets, common in niche domains
- Still relevant for LLM alignment (RLHF, DPO) and agent training, not just classical ML

### Two Approaches to Noisy Data

- **Approach 1: Pre-filtering (two-stage)**
  - Clean the dataset first (human curators or AI-based tools), then train on selected data
  - Industry standard for high-stakes use cases; often a hybrid of human + automated review
- **Approach 2: Training-time robustness (professor’s research focus)**
  - System uses internal signals (loss functions, gradients) to identify and down-weight noisy samples
  - No separate cleaning pipeline needed; more cost-effective
  - Works well for traditional deep learning with factorization models
  - Sample reweighting methods tend to work better for LLMs

### Practical Guidance

- No universal solution: method effectiveness is system-dependent
- Adding more diverse data is the quickest way to reduce noise sensitivity
- Recommended path: assess noise level, data size, and system type, then experiment with established methods
- Professor’s team currently investigating label noise on DPO and RLHF for LLM alignment, directly relevant

### Post-Call Notes

- Meeting assessed as not very useful (“badly useless”)
- Earlier call today was much more promising: an e-commerce agency that manages brands
  - Liked the audit; offered to connect with ~10 other brands
  - Next step: deliver a one-pager for the couple of brands they provided

### Next Steps

- **Send label noise papers and resources** (Professor)

  Covering factorization models, sample reweighting, and LLM alignment robustness techniques.

- **Review papers and follow up with specific questions** (Armaan)

  Assess which robustness techniques apply to the product discovery data pipeline.

- **Deliver one-pager for the e-commerce agency brands**

  Agency offered to connect with ~10 more brands after seeing the audit; one-pager is the next move.
