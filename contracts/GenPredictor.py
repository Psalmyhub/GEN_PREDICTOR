# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
"""GEN PREDICTOR: admin-published, GEN-staked token price prediction markets.

Prices use 8 decimal places (price_e8 = price * 10**8).
A market resolves to ABOVE when the agreed observation is >= target_price_e8,
otherwise BELOW. The observation URL and rule are immutable after publication.
"""

import json
from datetime import datetime
from genlayer import *
import genlayer.gl as gl


_ABOVE = "ABOVE"
_BELOW = "BELOW"
_ACTIVE = "ACTIVE"
_CLOSED = "CLOSED"
_RESOLVED = "RESOLVED"
_ERROR = "RESOLUTION_ERROR"
_FEE_BPS = u256(100)
_BPS_DENOMINATOR = u256(10_000)
_PRICE_SCALE = u256(100_000_000)


@allow_storage
@dataclass
class Market:
    title: str
    symbol: str
    target_price_e8: u256
    closes_at: str
    observation_url: str
    resolution_rule: str
    status: str
    outcome: str
    evidence_price_e8: u256
    pool_above: u256
    pool_below: u256
    total_pool: u256
    platform_fee: u256
    analysis: str


@gl.evm.contract_interface
class _Recipient:
    class View:
        pass
    class Write:
        pass


class GenPredictor(gl.Contract):
    """Single-registry MVP. Admin is the deployer; only admin can publish."""

    admin: Address
    markets: DynArray[Market]
    stakes: TreeMap[str, u256]
    claimed: TreeMap[str, bool]
    platform_fees: u256

    def __init__(self):
        self.admin = gl.message.sender_address
        self.platform_fees = u256(0)

    def _only_admin(self) -> None:
        if gl.message.sender_address != self.admin:
            raise gl.vm.UserError("Only the admin can publish markets.")

    def _stake_key(self, market_id: u32, user: str, side: str) -> str:
        return str(market_id) + ":" + user.lower() + ":" + side

    def _claim_key(self, market_id: u32, user: str) -> str:
        return str(market_id) + ":" + user.lower()

    @gl.public.write
    def publish_market(
        self,
        title: str,
        symbol: str,
        target_price_e8: u256,
        closes_at: str,
        observation_url: str,
        resolution_rule: str,
    ) -> u32:
        self._only_admin()
        if not title.strip() or not symbol.strip():
            raise gl.vm.UserError("Title and token symbol are required.")
        if target_price_e8 == u256(0):
            raise gl.vm.UserError("Target price must be greater than zero.")
        if not observation_url.startswith("https://"):
            raise gl.vm.UserError("Use an HTTPS price observation URL.")
        if not resolution_rule.strip():
            raise gl.vm.UserError("Resolution rule is required.")
        try:
            close_time = datetime.fromisoformat(closes_at.replace("Z", "+00:00"))
        except Exception:
            raise gl.vm.UserError("closes_at must be ISO-8601 with timezone.")
        if close_time.tzinfo is None:
            raise gl.vm.UserError("closes_at must include a timezone.")
        if close_time <= datetime.now().astimezone():
            raise gl.vm.UserError("Closing time must be in the future.")

        market_id = u32(len(self.markets))
        self.markets.append(Market(
            title=title.strip(),
            symbol=symbol.strip().upper(),
            target_price_e8=target_price_e8,
            closes_at=closes_at,
            observation_url=observation_url,
            resolution_rule=resolution_rule.strip(),
            status=_ACTIVE,
            outcome="",
            evidence_price_e8=u256(0),
            pool_above=u256(0),
            pool_below=u256(0),
            total_pool=u256(0),
            platform_fee=u256(0),
            analysis="",
        ))
        return market_id

    @gl.public.write.payable
    def predict(self, market_id: u32, side: str) -> None:
        if market_id >= u32(len(self.markets)):
            raise gl.vm.UserError("Unknown market.")
        if side not in (_ABOVE, _BELOW):
            raise gl.vm.UserError("Side must be ABOVE or BELOW.")
        market = self.markets[market_id]
        if market.status != _ACTIVE:
            raise gl.vm.UserError("Market is not accepting predictions.")
        if datetime.now().astimezone() >= datetime.fromisoformat(
            market.closes_at.replace("Z", "+00:00")
        ):
            raise gl.vm.UserError("Market closing time has passed.")
        amount = gl.message.value
        if amount == u256(0):
            raise gl.vm.UserError("Send a non-zero amount of GEN.")
        user = str(gl.message.sender_address).lower()
        key = self._stake_key(market_id, user, side)
        self.stakes[key] = self.stakes.get(key, u256(0)) + amount
        if side == _ABOVE:
            market.pool_above = market.pool_above + amount
        else:
            market.pool_below = market.pool_below + amount
        market.total_pool = market.total_pool + amount
        self.markets[market_id] = market

    @gl.public.write
    def resolve_market(self, market_id: u32) -> None:
        if market_id >= u32(len(self.markets)):
            raise gl.vm.UserError("Unknown market.")
        market = self.markets[market_id]
        if market.status not in (_ACTIVE, _CLOSED):
            raise gl.vm.UserError("Market cannot be resolved in its current state.")
        if datetime.now().astimezone() < datetime.fromisoformat(
            market.closes_at.replace("Z", "+00:00")
        ):
            raise gl.vm.UserError("Market cannot resolve before its close time.")

        title = market.title
        symbol = market.symbol
        target = int(market.target_price_e8)
        target_text = str(target / int(_PRICE_SCALE))
        source_url = market.observation_url
        rule = market.resolution_rule
        close_time = market.closes_at

        def leader_fn() -> str:
            page = gl.nondet.web.render(
                source_url, mode="text", wait_after_loaded="3s"
            ) or ""
            prompt = f"""
Resolve a token price prediction market using ONLY the source evidence below.
Return JSON only with keys: valid_source (boolean), symbol (string),
observation_time (ISO-8601 string), observed_price (decimal number),
reasoning (string).
Market: {title}
Token symbol: {symbol}
Target price: {target_text}
Required observation time: the market close time {close_time}
Rule: {rule}
Source URL: {source_url}
Page evidence:
<evidence>{page[:18000]}</evidence>
Requirements:
- Confirm the source is relevant to the named token and provides a numeric price.
- Use a price observation at the close time, or the nearest observation only if the
  rule explicitly permits it. Do not substitute the current price for a historical
  close-time price.
- If source/time/token cannot be verified, set valid_source=false and observed_price=0.
- observed_price must be a decimal number, not a formatted currency string.
"""
            return gl.nondet.exec_prompt(prompt)

        def validator_fn(proposed) -> bool:
            if isinstance(proposed, Exception):
                return False
            try:
                data = json.loads(str(proposed))
                if data.get("valid_source") is not True:
                    return False
                if str(data.get("symbol", "")).upper() != symbol.upper():
                    return False
                price = float(data.get("observed_price", 0))
                return price > 0 and price < 1e18 and bool(data.get("observation_time"))
            except Exception:
                return False

        result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        try:
            data = json.loads(str(result))
            if data.get("valid_source") is not True:
                market.status = _ERROR
                market.analysis = json.dumps(data)
                self.markets[market_id] = market
                return
            price_e8 = u256(int(round(float(data["observed_price"]) * int(_PRICE_SCALE))))
            market.evidence_price_e8 = price_e8
            market.outcome = _ABOVE if price_e8 >= market.target_price_e8 else _BELOW
            market.analysis = json.dumps(data)
            market.status = _RESOLVED
        except Exception:
            market.status = _ERROR
            market.analysis = str(result)
        self.markets[market_id] = market

    @gl.public.write
    def claim(self, market_id: u32) -> u256:
        if market_id >= u32(len(self.markets)):
            raise gl.vm.UserError("Unknown market.")
        market = self.markets[market_id]
        if market.status != _RESOLVED:
            raise gl.vm.UserError("Market is not resolved.")
        user = str(gl.message.sender_address).lower()
        claim_key = self._claim_key(market_id, user)
        if self.claimed.get(claim_key, False):
            raise gl.vm.UserError("Reward already claimed.")
        winning_side = market.outcome
        winning_stake = self.stakes.get(
            self._stake_key(market_id, user, winning_side), u256(0)
        )
        if winning_stake == u256(0):
            raise gl.vm.UserError("No winning stake for this account.")
        total_winning = market.pool_above if winning_side == _ABOVE else market.pool_below
        fee = market.total_pool * _FEE_BPS // _BPS_DENOMINATOR
        distributable = market.total_pool - fee
        payout = distributable * winning_stake // total_winning
        self.claimed[claim_key] = True
        market.platform_fee = fee
        self.platform_fees = self.platform_fees + fee
        self.markets[market_id] = market
        _Recipient(Address(user)).emit_transfer(value=payout)
        return payout

    @gl.public.view
    def get_market(self, market_id: u32) -> dict:
        if market_id >= u32(len(self.markets)):
            raise gl.vm.UserError("Unknown market.")
        m = self.markets[market_id]
        return {
            "id": market_id,
            "title": m.title,
            "symbol": m.symbol,
            "target_price_e8": m.target_price_e8,
            "closes_at": m.closes_at,
            "observation_url": m.observation_url,
            "resolution_rule": m.resolution_rule,
            "status": m.status,
            "outcome": m.outcome,
            "evidence_price_e8": m.evidence_price_e8,
            "pool_above": m.pool_above,
            "pool_below": m.pool_below,
            "total_pool": m.total_pool,
            "platform_fee": m.platform_fee,
            "analysis": m.analysis,
        }

    @gl.public.view
    def get_market_count(self) -> u32:
        return u32(len(self.markets))

    @gl.public.view
    def get_user_stake(self, market_id: u32, user: str, side: str) -> u256:
        return self.stakes.get(self._stake_key(market_id, user, side), u256(0))

    @gl.public.view
    def get_platform_fees(self) -> u256:
        return self.platform_fees
