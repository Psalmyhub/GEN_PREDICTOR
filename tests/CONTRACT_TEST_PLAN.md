# GEN PREDICTOR contract test plan — NOT YET EXECUTED

Use the GenLayer Testing Suite (genlayer-test) and the pinned py-genlayer dependency. Direct Mode supports mocked web/LLM responses; use Studio Mode for integration and consensus checks.

## Admin and market creation
1. Deployer can publish; non-admin publishing reverts.
2. Reject unknown market type, blank title/symbol/rule, non-HTTPS source and malformed, timezone-free or past close time.
3. Reject a movement market with zero baseline or an out-of-range stability band.
4. Reject a price-prediction market with fallback accuracy outside 95%–99%.

## Entries and pools
5. Reject unknown market, inactive/closed market, zero stake and duplicate wallet prediction.
6. PRICE_PREDICTION accepts a positive fixed-point decimal price and rejects zero/invalid price or non-EXACT choice.
7. PRICE_MOVEMENT accepts exactly ABOVE_CURRENT, STABLE or BELOW_CURRENT and rejects price inputs or any other choice.
8. Confirm each choice pool, total pool and stored user prediction/stake are correct.

## Resolution and winner policy
9. Resolution before close, repeated resolution and unknown market reject.
10. Valid historical source evidence returns correct token, observation time and price; malformed, unavailable, wrong-token and wrong-time evidence cannot resolve normally.
11. PRICE_PREDICTION: exact matches qualify first; fallback accuracy winners qualify only if exact-match pool is empty.
12. Test 95%, 96%, 97%, 98% and 99% thresholds at boundary values using fixed-point arithmetic.
13. If no exact or fallback prediction qualifies, every participant can refund their own stake and no fee is charged.
14. PRICE_MOVEMENT resolves to exactly one of ABOVE_CURRENT, STABLE or BELOW_CURRENT based on immutable baseline and stability band.
15. Only entries choosing the resolved movement outcome qualify; if that side has no stakes, all entries can refund.

## Claims, fees, and finality
16. Non-winners cannot claim, winners/refunders can claim once, duplicate claims reject.
17. Winning payouts are proportional to stake; exact winners take precedence over near-price predictions.
18. A 1% fee is accounted once for payout markets; refunds do not charge a fee.
19. Verify admin-only fee withdrawal and payout message behavior on the intended network.
20. Verify contract solvency, rounding dust, validator disagreement, and that UI waits for protocol finality.

These are required tests, not tests that have already passed.
