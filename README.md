# GEN PREDICTOR

Admin-published token price prediction markets on GenLayer.

## MVP
- Contract deployer is admin; only admin can publish.
- Market metadata fixes token symbol, target, close time, HTTPS observation URL and resolution rule.
- Users stake native GEN on ABOVE or BELOW.
- After close, GenLayer non-deterministic execution reads evidence and validates the structured result.
- Successful resolution enables proportional winner claims with a 1% fee.
- Price uses 8 decimals: multiply the human price by 100,000,000 (e.g. $3,500.25 = `350025000000`).

## Safety and limitations
This is an un-audited MVP, not production-ready financial software. A general webpage may not reliably provide a historical price at the exact close time; configure a verifiable historical source and exact rule. Invalid evidence disables claims via RESOLUTION_ERROR. The no-winning-side case currently has no refund path. Native GEN only; ERC-20 staking, admin rotation, multisig and frontend are not included. Validate contract compilation, transfer-message behavior, solvency, and GenLayer protocol finality before using real funds. Frontends must wait for protocol finality, not merely initial acceptance or an EVM receipt.

## Files
- `contracts/GenPredictor.py`: contract
- `tests/CONTRACT_TEST_PLAN.md`: validation checklist

## References
- https://docs.genlayer.com/developers/intelligent-contracts/features/non-determinism
- https://docs.genlayer.com/developers/intelligent-contracts/features/value-transfers
- https://docs.genlayer.com/understand-genlayer-protocol/core-concepts/transactions/transaction-execution
