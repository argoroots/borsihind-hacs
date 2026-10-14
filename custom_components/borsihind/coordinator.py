"""Data update coordinator for Börsihind.ee."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import API_URL, CONF_INTERVAL, CONF_MARGINAL, CONF_PLAN, DOMAIN, FETCH_INTERVAL
from .prices import process_prices, summarize

_LOGGER = logging.getLogger(__name__)

# Small delay after a slot boundary, so the new slot is already current
BOUNDARY_DELAY = timedelta(seconds=5)


class BorsihindCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch price data and refresh sensors at every slot boundary."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        self.entry = entry
        self._cached_api_data: dict[str, Any] | None = None
        self._last_fetch: datetime | None = None

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=self._until_next_slot(dt_util.utcnow()),
        )

    @property
    def plan(self) -> str:
        """Get plan value from options or data."""
        return self.entry.options.get(CONF_PLAN, self.entry.data[CONF_PLAN])

    @property
    def interval(self) -> str:
        """Get interval value from options or data."""
        return self.entry.options.get(
            CONF_INTERVAL, self.entry.data.get(CONF_INTERVAL, "15min")
        )

    @property
    def marginal(self) -> float:
        """Get marginal (cents/kWh with VAT) from options or data."""
        return self.entry.options.get(
            CONF_MARGINAL, self.entry.data.get(CONF_MARGINAL, 0)
        )

    @property
    def slot_minutes(self) -> int:
        """Length of one price slot in minutes."""
        return 60 if self.interval == "1h" else 15

    def _until_next_slot(self, now: datetime) -> timedelta:
        """Time until just after the next slot boundary (UTC, same boundaries as Tallinn)."""
        slot = timedelta(minutes=self.slot_minutes)
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        next_boundary = midnight + ((now - midnight) // slot + 1) * slot
        return next_boundary - now + BOUNDARY_DELAY

    async def _fetch(self) -> dict[str, Any]:
        """Download the v2 price file for the current plan and interval."""
        url = f"{API_URL}/v2/{self.interval}/{self.plan}.json"
        session = async_get_clientsession(self.hass)

        async with asyncio.timeout(10):
            response = await session.get(url)
            response.raise_for_status()
            return await response.json(content_type=None)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch new data when due, then recalculate prices for the current slot."""
        now = dt_util.utcnow()

        # Fetch hourly (the file is updated during the day and tomorrow's prices
        # arrive in the afternoon). Based on elapsed time, so a refresh can never be skipped.
        if self._last_fetch is None or now - self._last_fetch >= FETCH_INTERVAL:
            try:
                self._cached_api_data = await self._fetch()
                self._last_fetch = now
            except Exception as err:  # noqa: BLE001
                if self._cached_api_data is None:
                    raise UpdateFailed(f"Error fetching price data: {err}") from err
                _LOGGER.warning("Error fetching price data, using cached data: %s", err)

        # Run again just after the next slot starts
        self.update_interval = self._until_next_slot(now)

        prices = process_prices(self._cached_api_data, now, self.marginal)
        if not prices:
            # Cached data has run out; fetch again on the next update
            self._last_fetch = None
            raise UpdateFailed("No price data available for current time")

        data = summarize(prices, 60 // self.slot_minutes)
        data["last_update"] = now
        return data
