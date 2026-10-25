# Contract test plan — NOT YET EXECUTED

Run using the GenLayer SDK/test harness matching the pinned `py-genlayer` dependency.

1. Deployer can publish; non-admin cannot.
2. Invalid title/symbol/rule/target/source/close-time inputs reject.
3. Invalid ID/side, zero stake, closed market and post-close stake reject.
4. ABOVE/BELOW pools, individual stakes and total pool update correctly.
5. Resolution before close and repeated resolution reject.
6. Valid evidence converts to 8-decimal fixed point and compares to target.
7. Invalid, unavailable, wrong-token, malformed or time-inappropriate evidence cannot produce a payable outcome.
8. Claims are unavailable before successful resolution and to non-winners.
9. Winner can claim once; duplicate claim rejects.
10. Fee is 1% and payouts are proportional to winning-side stake.
11. Verify payout message semantics, solvency and claim accounting on the target GenLayer network.
12. Define and test refunds when the resolved side has no winning stakes before production.
