# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
"""GEN PREDICTOR: P2P token-price prediction markets.

PRICE_PREDICTION: users submit a decimal price (8-decimal fixed point).
Exact matches win. If none match, predictions within the configured accuracy
threshold win. If no prediction qualifies, stakes are refundable.

PRICE_MOVEMENT: users choose exactly ABOVE_CURRENT, STABLE, or BELOW_CURRENT.
The baseline price is captured as a fixed market parameter at publication.
"""

import json
from datetime import datetime
from genlayer import *
import genlayer.gl as gl

_PRICE_PREDICTION = "PRICE_PREDICTION"
_PRICE_MOVEMENT = "PRICE_MOVEMENT"
_ABOVE = "ABOVE_CURRENT"
_STABLE = "STABLE"
_BELOW = "BELOW_CURRENT"
_ACTIVE = "ACTIVE"
_RESOLVED = "RESOLVED"
_ERROR = "RESOLUTION_ERROR"
_EXACT = "EXACT"
_ACCURACY = "ACCURACY"
_REFUND = "REFUND"
_FEE_BPS = 100
_BPS = 10_000
_SCALE = 100_000_000


@allow_storage
@dataclass
class Market:
    title: str
    symbol: str
    market_type: str
    closes_at: str
    observation_url: str
    resolution_rule: str
    reference_price_e8: u256
    stable_band_bps: u256
    fallback_accuracy_bps: u256
    status: str
    outcome: str
    winning_mode: str
    evidence_price_e8: u256
    pool_exact: u256
    pool_above: u256
    pool_stable: u256
    pool_below: u256
    total_pool: u256
    winning_pool: u256
    platform_fee: u256
    fee_accounted: bool
    analysis: str


@allow_storage
@dataclass
class Prediction:
    market_id: u32
    user: str
    choice: str
    predicted_price_e8: u256
    stake: u256


@gl.evm.contract_interface
class _Recipient:
    class View:
        pass
    class Write:
        pass


class GenPredictor(gl.Contract):
    """Single-registry MVP. Contract deployer is the market administrator."""

    admin: Address
    markets: DynArray[Market]
    predictions: DynArray[Prediction]
    has_prediction: TreeMap[str, bool]
    claimed: TreeMap[str, bool]
    platform_fees: u256

    def __init__(self):
        self.admin = gl.message.sender_address
        self.platform_fees = u256(0)

    def _only_admin(self) -> None:
        if gl.message.sender_address != self.admin:
            raise gl.vm.UserError("Only the admin can publish markets.")

    def _entry_key(self, market_id: u32, user: str) -> str:
        return str(market_id) + ":" + user.lower()

    def _is_price_winner(self, market: Market, prediction: Prediction) -> bool:
        actual = int(market.evidence_price_e8)
        predicted = int(prediction.predicted_price_e8)
        if actual <= 0:
            return False
        if market.winning_mode == _EXACT:
            return predicted == actual
        if market.winning_mode == _ACCURACY:
            allowed_error_bps = _BPS - int(market.fallback_accuracy_bps)
            return abs(predicted - actual) * _BPS <= actual * allowed_error_bps
        return False

    def _is_winner(self, market: Market, prediction: Prediction) -> bool:
        if market.winning_mode == _REFUND:
            return True
        if market.market_type == _PRICE_PREDICTION:
            return self._is_price_winner(market, prediction)
        return prediction.choice == market.outcome

    @gl.public.write
    def publish_market(
        self,
        title: str,
        symbol: str,
        market_type: str,
        closes_at: str,
        observation_url: str,
        resolution_rule: str,
        reference_price_e8: u256,
        stable_band_bps: u256,
        fallback_accuracy_bps: u256,
    ) -> u32:
        self._only_admin()
        if not title.strip() or not symbol.strip():
            raise gl.vm.UserError("Title and token symbol are required.")
        if market_type not in (_PRICE_PREDICTION, _PRICE_MOVEMENT):
            raise gl.vm.UserError("Choose PRICE_PREDICTION or PRICE_MOVEMENT.")
        if not observation_url.startswith("https://"):
            raise gl.vm.UserError("Use an HTTPS price observation URL.")
        if not resolution_rule.strip():
            raise gl.vm.UserError("A fixed resolution rule is required.")
        if market_type == _PRICE_MOVEMENT:
            if reference_price_e8 == u256(0):
                raise gl.vm.UserError("Movement markets need a positive baseline price.")
            if stable_band_bps == u256(0) or stable_band_bps > u256(1000):
                raise gl.vm.UserError("Stable band must be between 1 and 1000 basis points.")
        if market_type == _PRICE_PREDICTION:
            if fallback_accuracy_bps < u256(9500) or fallback_accuracy_bps > u256(9900):
                raise gl.vm.UserError("Fallback accuracy must be between 9500 and 9900 basis points.")
        try:
            close_time = datetime.fromisoformat(closes_at.replace("Z", "+00:00"))
        except Exception:
            raise gl.vm.UserError("closes_at must be ISO-8601 with timezone.")
        if close_time.tzinfo is None or close_time <= datetime.now().astimezone():
            raise gl.vm.UserError("Closing time must be in the future and include a timezone.")

        market_id = u32(len(self.markets))
        self.markets.append(Market(
            title=title.strip(),
            symbol=symbol.strip().upper(),
            market_type=market_type,
            closes_at=closes_at,
            observation_url=observation_url,
            resolution_rule=resolution_rule.strip(),
            reference_price_e8=reference_price_e8,
            stable_band_bps=stable_band_bps,
            fallback_accuracy_bps=fallback_accuracy_bps,
            status=_ACTIVE,
            outcome="",
            winning_mode="",
            evidence_price_e8=u256(0),
            pool_exact=u256(0),
            pool_above=u256(0),
            pool_stable=u256(0),
            pool_below=u256(0),
            total_pool=u256(0),
            winning_pool=u256(0),
            platform_fee=u256(0),
            fee_accounted=False,
            analysis="",
        ))
        return market_id

    @gl.public.write.payable
    def predict(self, market_id: u32, choice: str, predicted_price_e8: u256) -> None:
        if market_id >= u32(len(self.markets)):
            raise gl.vm.UserError("Unknown market.")
        market = self.markets[market_id]
        if market.status != _ACTIVE:
            raise gl.vm.UserError("Market is not accepting predictions.")
        if datetime.now().astimezone() >= datetime.fromisoformat(market.closes_at.replace("Z", "+00:00")):
            raise gl.vm.UserError("Market closing time has passed.")
        user = str(gl.message.sender_address).lower()
        entry_key = self._entry_key(market_id, user)
        if self.has_prediction.get(entry_key, False):
            raise gl.vm.UserError("One prediction per wallet per market is allowed.")
        amount = gl.message.value
        if amount == u256(0):
            raise gl.vm.UserError("Stake a non-zero amount of GEN.")

        if market.market_type == _PRICE_PREDICTION:
            if choice != "EXACT" or predicted_price_e8 == u256(0):
                raise gl.vm.UserError("Enter a positive decimal price prediction.")
            market.pool_exact = market.pool_exact + amount
        else:
            if choice not in (_ABOVE, _STABLE, _BELOW):
                raise gl.vm.UserError("Choose ABOVE_CURRENT, STABLE, or BELOW_CURRENT.")
            if predicted_price_e8 != u256(0):
                raise gl.vm.UserError("Movement markets accept a choice, not a price.")
            if choice == _ABOVE:
                market.pool_above = market.pool_above + amount
            elif choice == _STABLE:
                market.pool_stable = market.pool_stable + amount
            else:
                market.pool_below = market.pool_below + amount

        self.has_prediction[entry_key] = True
        self.predictions.append(Prediction(
            market_id=market_id,
            user=user,
            choice=choice,
            predicted_price_e8=predicted_price_e8,
            stake=amount,
        ))
        market.total_pool = market.total_pool + amount
        self.markets[market_id] = market

    @gl.public.write
    def resolve_market(self, market_id: u32) -> None:
        if market_id >= u32(len(self.markets)):
            raise gl.vm.UserError("Unknown market.")
        market = self.markets[market_id]
        if market.status != _ACTIVE:
            raise gl.vm.UserError("Market cannot be resolved in its current state.")
        if datetime.now().astimezone() < datetime.fromisoformat(market.closes_at.replace("Z", "+00:00")):
            raise gl.vm.UserError("Market cannot resolve before close.")

        symbol, source_url, rule, close_time = (
            market.symbol, market.observation_url, market.resolution_rule, market.closes_at
        )
        market_type = market.market_type
        reference_price = int(market.reference_price_e8)
        reference_text = str(reference_price / _SCALE)

        def leader_fn() -> str:
            page = gl.nondet.web.render(source_url, mode="text", wait_after_loaded="3s") or ""
            prompt = f"""
Resolve a token price market from the evidence below. Return JSON only:
{{"valid_source": boolean, "symbol": string, "observation_time": string,
"observed_price": number, "reasoning": string}}.
Token: {symbol}. Market type: {market_type}. Required observation time: {close_time}.
Movement baseline price (if applicable): {reference_text}.
Fixed rule: {rule}. Source URL: {source_url}.
Evidence: <evidence>{page[:18000]}</evidence>
Verify token identity and a numeric price observed at the required close time.
Do not substitute a current price for a historical close-time price.
If the evidence cannot verify the token, timestamp, and price, set valid_source=false
and observed_price=0. Return observed_price as a decimal number.
"""
            return gl.nondet.exec_prompt(prompt)

        def validator_fn(proposed) -> bool:
            try:
                if isinstance(proposed, Exception):
                    return False
                candidate_raw = proposed.calldata if isinstance(proposed, gl.vm.Return) else str(proposed)
                candidate = json.loads(candidate_raw)
                independent = json.loads(leader_fn())
                if candidate.get("valid_source") is not True or independent.get("valid_source") is not True:
                    return False
                if str(candidate.get("symbol", "")).upper() != symbol.upper():
                    return False
                if str(independent.get("symbol", "")).upper() != symbol.upper():
                    return False
                candidate_time = str(candidate.get("observation_time", ""))
                independent_time = str(independent.get("observation_time", ""))
                if not candidate_time or not independent_time:
                    return False
                candidate_price = float(candidate.get("observed_price", 0))
                independent_price = float(independent.get("observed_price", 0))
                if candidate_price <= 0 or independent_price <= 0:
                    return False
                return abs(candidate_price - independent_price) / max(candidate_price, independent_price) <= 0.001
            except Exception:
                return False

        result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        try:
            data = json.loads(str(result))
            if data.get("valid_source") is not True:
                market.status, market.analysis = _ERROR, json.dumps(data)
                self.markets[market_id] = market
                return
            price_e8 = u256(int(round(float(data["observed_price"]) * _SCALE)))
            if price_e8 == u256(0):
                raise ValueError("Observed price must be positive.")
            market.evidence_price_e8 = price_e8
            if market.market_type == _PRICE_MOVEMENT:
                baseline = int(market.reference_price_e8)
                stable_delta = baseline * int(market.stable_band_bps) // _BPS
                observed = int(price_e8)
                if observed > baseline + stable_delta:
                    market.outcome = _ABOVE
                elif observed < baseline - stable_delta:
                    market.outcome = _BELOW
                else:
                    market.outcome = _STABLE
                market.winning_mode = "CHOICE"
            else:
                exact_pool = u256(0)
                fallback_pool = u256(0)
                for prediction in self.predictions:
                    if prediction.market_id != market_id:
                        continue
                    if int(prediction.predicted_price_e8) == int(price_e8):
                        exact_pool = exact_pool + prediction.stake
                    if abs(int(prediction.predicted_price_e8) - int(price_e8)) * _BPS <= int(price_e8) * (_BPS - int(market.fallback_accuracy_bps)):
                        fallback_pool = fallback_pool + prediction.stake
                if exact_pool > u256(0):
                    market.winning_mode = _EXACT
                    market.winning_pool = exact_pool
                elif fallback_pool > u256(0):
                    market.winning_mode = _ACCURACY
                    market.winning_pool = fallback_pool
                else:
                    market.winning_mode = _REFUND
                    market.winning_pool = market.total_pool
            if market.market_type == _PRICE_MOVEMENT:
                winning_pool = u256(0)
                for prediction in self.predictions:
                    if prediction.market_id == market_id and prediction.choice == market.outcome:
                        winning_pool = winning_pool + prediction.stake
                if winning_pool == u256(0):
                    market.winning_mode = _REFUND
                    market.winning_pool = market.total_pool
                else:
                    market.winning_pool = winning_pool
            market.analysis = json.dumps(data)
            market.status = _RESOLVED
        except Exception as exc:
            market.status, market.analysis = _ERROR, str(exc)
        self.markets[market_id] = market

    @gl.public.write
    def claim(self, market_id: u32) -> u256:
        if market_id >= u32(len(self.markets)):
            raise gl.vm.UserError("Unknown market.")
        market = self.markets[market_id]
        if market.status != _RESOLVED:
            raise gl.vm.UserError("Market is not resolved.")
        user = str(gl.message.sender_address).lower()
        claim_key = self._entry_key(market_id, user)
        if self.claimed.get(claim_key, False):
            raise gl.vm.UserError("Reward already claimed.")
        user_stake = u256(0)
        user_prediction = None
        for prediction in self.predictions:
            if prediction.market_id == market_id and prediction.user == user:
                user_stake = prediction.stake
                user_prediction = prediction
                break
        if user_prediction is None or user_stake == u256(0):
            raise gl.vm.UserError("No prediction found for this wallet.")
        if not self._is_winner(market, user_prediction):
            raise gl.vm.UserError("This prediction is not eligible for payout.")
        if market.winning_pool == u256(0):
            raise gl.vm.UserError("No distributable winning pool.")

        if market.winning_mode == _REFUND:
            payout = user_stake
        else:
            fee = market.total_pool * _FEE_BPS // _BPS
            payout = (market.total_pool - fee) * user_stake // market.winning_pool
            if not market.fee_accounted:
                market.platform_fee = fee
                market.fee_accounted = True
                self.platform_fees = self.platform_fees + fee
        self.claimed[claim_key] = True
        self.markets[market_id] = market
        _Recipient(Address(user)).emit_transfer(value=payout, on="finalized")
        return payout

    @gl.public.write
    def withdraw_platform_fees(self) -> u256:
        self._only_admin()
        amount = self.platform_fees
        if amount == u256(0):
            raise gl.vm.UserError("No platform fees to withdraw.")
        self.platform_fees = u256(0)
        _Recipient(Address(str(self.admin))).emit_transfer(value=amount, on="finalized")
        return amount

    @gl.public.view
    def get_market(self, market_id: u32) -> dict:
        if market_id >= u32(len(self.markets)):
            raise gl.vm.UserError("Unknown market.")
        m = self.markets[market_id]
        return {
            "id": market_id, "title": m.title, "symbol": m.symbol,
            "market_type": m.market_type, "closes_at": m.closes_at,
            "observation_url": m.observation_url, "resolution_rule": m.resolution_rule,
            "reference_price_e8": m.reference_price_e8, "stable_band_bps": m.stable_band_bps,
            "fallback_accuracy_bps": m.fallback_accuracy_bps, "status": m.status,
            "outcome": m.outcome, "winning_mode": m.winning_mode,
            "evidence_price_e8": m.evidence_price_e8, "pool_exact": m.pool_exact,
            "pool_above": m.pool_above, "pool_stable": m.pool_stable,
            "pool_below": m.pool_below, "total_pool": m.total_pool,
            "winning_pool": m.winning_pool, "platform_fee": m.platform_fee,
            "analysis": m.analysis,
        }

    @gl.public.view
    def get_market_count(self) -> u32:
        return u32(len(self.markets))

    @gl.public.view
    def get_user_prediction(self, market_id: u32, user: str) -> dict:
        for prediction in self.predictions:
            if prediction.market_id == market_id and prediction.user == user.lower():
                return {"choice": prediction.choice,
                        "predicted_price_e8": prediction.predicted_price_e8,
                        "stake": prediction.stake,
                        "claimed": self.claimed.get(self._entry_key(market_id, user), False)}
        raise gl.vm.UserError("No prediction found.")

    @gl.public.view
    def get_platform_fees(self) -> u256:
        return self.platform_fees
