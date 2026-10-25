# GEN PREDICTOR

An admin-published peer-to-peer (P2P) token-price prediction market built as a GenLayer Intelligent Contract.

## Two market categories

### 1. PRICE_PREDICTION — enter an exact price
Example: “Predict the GEN price on Friday at 08:00 UTC.” Each participant submits a positive decimal price (for example, 1.11 or 0.2) and stakes GEN.

- The market resolves using the price evidence and observation time defined by the market's immutable rule.
- If one or more entries exactly match the resolved price at 8-decimal precision, only exact entries qualify.
- If there are no exact matches, entries meeting the admin-configured 95%–99% accuracy threshold qualify. The threshold means the prediction must be within 1%–5% of the actual price.
- If nobody qualifies, the contract enables refunds of each participant's stake.

### 2. PRICE_MOVEMENT — choose one of exactly three outcomes
Example: “Will GEN be above its current price, stable, or below it in 24 hours?”

- The three choices are ABOVE_CURRENT, STABLE, and BELOW_CURRENT.
- The admin must fix the baseline price at publication. Resolution compares the agreed closing observation with that baseline.
- “Stable” means the closing price is within the configured stability band around the baseline. The band is configured in basis points (100 bps = 1%).
- Only participants who chose the resolved outcome qualify. If nobody chose that outcome, the contract enables refunds.

## Common rules

- The contract deployer is the admin; only that address can publish.
- Participants stake native GEN. This is a P2P pool, not an order book or a guaranteed-price market.
- Winner payouts are proportional to each winning participant's stake, from the total pool after a 1% fee. Exact-price matches share with other exact matches; fallback winners share only when no exact match exists.
- Market rules, source URL, baseline and relevant thresholds are set at publication and cannot be changed through the contract.
- Claims are recorded to prevent duplicate claims. Fees can be withdrawn by the admin.
- Price values use 8 decimals internally: multiply the displayed price by 100,000,000 (for example, 1.11 -> 111000000).

## Resolution and finality

After the market closes, a permissionless resolver reads the configured source using GenLayer non-deterministic execution. The validator function independently retrieves evidence and checks token identity and price agreement. The result is stored only after the consensus call returns. The frontend must wait for protocol finality before showing a market as settled or a payout as claimable.

The source must provide verifiable historical observations at the specified timestamp. A generic webpage may show only a current price; that is not sufficient to resolve a past close. The current contract checks that the returned observation time is present but still needs stricter timestamp parsing/validation and source-specific integration before production.

## MVP limitations — do not use for real funds yet

- This is not audited financial software. Contract compilation, test harness execution, payout semantics, solvency and real-network finality still need verification.
- Native GEN only; ERC-20 tokens, a frontend, admin rotation and multisig are not included.
- One prediction per wallet per market is enforced in this version.
- Resolution-error markets do not currently have a finalized admin/governance recovery mechanism.
- Dust from integer rounding can remain in the contract after proportional payouts.
- Before production, test no-winner refunds, payout messages, fee withdrawal, consensus disagreements, historical price sources and the full appeal/finality lifecycle.

## Files

- contracts/GenPredictor.py: market contract
- tests/CONTRACT_TEST_PLAN.md: test checklist (not a claim of executed tests)

## References

- https://docs.genlayer.com/developers/intelligent-contracts/features/non-determinism
- https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle
- https://docs.genlayer.com/developers/intelligent-contracts/features/value-transfers
- https://docs.genlayer.com/developers/intelligent-contracts/testing
