Extract structured data from each of the following product-page snippets.
Reply with a JSON array only (no prose, no code fence), one object per
snippet, each with exactly these keys:
`{"name": str, "price_usd": float|null, "in_stock": bool, "rating": float|null}`

NOTE TO RUNNERS: the real T5 run uses 50 scraped pages; the 5 snippets
below are the committed stand-in so the repo stays small and the task
stays deterministic. Swap in your own corpus for a full run — keep it
identical across models.

--- snippet 1 ---
Aurora X1 Mechanical Keyboard — $129.99. In stock, ships tomorrow.
Rated 4.6/5 (2,381 reviews).

--- snippet 2 ---
TrailBlazer 40L Hiking Pack. Price: €89 (approx. $96.50 USD).
Currently unavailable — notify me. ★★★★☆ 4.1

--- snippet 3 ---
NimbusPad Pro 11" — from $599. Select configuration to see availability.
No customer reviews yet.

--- snippet 4 ---
Cast-Iron Skillet, 12 inch. $34. IN STOCK (23 left). Rating: 4.8 out of 5.

--- snippet 5 ---
QuietFan Desk Fan v2 — was $49.99, now $39.99! Out of stock online;
check local stores. 3.9 stars.

Scoring: pass = valid JSON, all 5 objects present, prices normalized to
USD floats (null where not shown in USD terms is acceptable for snippet 3's
"from" price only if flagged consistently), stock and rating correct.
