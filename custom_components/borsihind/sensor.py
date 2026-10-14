"""Sensor platform for Börsihind.ee."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CURRENCY_EURO, UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_PLAN, DOMAIN, PLANS
from .coordinator import BorsihindCoordinator
from .prices import CHEAPEST_HOURS

PRICE_UNIT = f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}"


def to_euros(cents: float) -> float:
    """Convert cents/kWh to EUR/kWh for sensor states."""
    return round(cents / 100, 5)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Börsihind.ee sensor entities."""
    coordinator: BorsihindCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            BorsihindCurrentPriceSensor(coordinator, entry),
            BorsihindStatisticSensor(coordinator, entry, "average", "Average Price"),
            BorsihindStatisticSensor(coordinator, entry, "min", "Minimum Price"),
            BorsihindStatisticSensor(coordinator, entry, "max", "Maximum Price"),
            *(BorsihindCheapestSensor(coordinator, entry, hours) for hours in CHEAPEST_HOURS),
            BorsihindPlanSensor(coordinator, entry),
            BorsihindIntervalSensor(coordinator, entry),
            BorsihindMarginalSensor(coordinator, entry),
        ]
    )


class BorsihindSensorBase(CoordinatorEntity[BorsihindCoordinator], SensorEntity):
    """Base class for Börsihind.ee sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BorsihindCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        plan = entry.options.get(CONF_PLAN, entry.data.get(CONF_PLAN))
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"Börsihind.ee {PLANS.get(plan, plan)}",
            "manufacturer": "Börsihind.ee",
            "model": PLANS.get(plan, plan),
        }


class BorsihindCurrentPriceSensor(BorsihindSensorBase):
    """Sensor for the current electricity price, all fees, VAT and marginal included."""

    _attr_name = "Current Price"
    _attr_icon = "mdi:cash"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PRICE_UNIT
    # The forecast list is large and changes every slot; keep it out of the database
    _unrecorded_attributes = frozenset({"prices"})

    def __init__(
        self,
        coordinator: BorsihindCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_current_price"

    @property
    def native_value(self) -> float | None:
        """Return the current price."""
        if self.coordinator.data:
            return to_euros(self.coordinator.data["current"]["total"])
        return None

    @property
    def extra_state_attributes(self) -> dict:
        """Return price components and the forecast."""
        if not self.coordinator.data:
            return {}

        current = self.coordinator.data["current"]
        return {
            "time": current["time"],
            "start": current["start"].isoformat(),
            "end": current["end"].isoformat(),
            "electricity_price": to_euros(current["electricity"]),
            "transmission": to_euros(current["transmission"]),
            "renewable_tax": to_euros(current["renewable"]),
            "supply_security": to_euros(current["supply_security"]),
            "excise": to_euros(current["excise"]),
            "marginal": to_euros(self.coordinator.marginal),
            "prices": [
                {
                    "time": p["time"],
                    "start": p["start"].isoformat(),
                    "end": p["end"].isoformat(),
                    "price": to_euros(p["total"]),
                }
                for p in self.coordinator.data["prices"]
            ],
        }


class BorsihindStatisticSensor(BorsihindSensorBase):
    """Average, minimum or maximum of the remaining prices."""

    _attr_icon = "mdi:cash"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PRICE_UNIT

    def __init__(
        self,
        coordinator: BorsihindCoordinator,
        entry: ConfigEntry,
        key: str,
        name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._key = key
        self._attr_name = name
        # Unique IDs match the earlier per-statistic sensor classes
        self._attr_unique_id = f"{entry.entry_id}_{key}_price"

    @property
    def native_value(self) -> float | None:
        """Return the statistic."""
        if self.coordinator.data:
            return to_euros(self.coordinator.data[self._key])
        return None


class BorsihindCheapestSensor(BorsihindSensorBase):
    """Start time of the cheapest window of N hours, VAT and marginal included."""

    _attr_icon = "mdi:clock-start"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self,
        coordinator: BorsihindCoordinator,
        entry: ConfigEntry,
        hours: int,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._hours = hours
        self._attr_name = f"Cheapest {hours}h"
        self._attr_unique_id = f"{entry.entry_id}_cheapest_{hours}h"

    @property
    def _window(self) -> dict | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data["cheapest"].get(self._hours)

    @property
    def native_value(self) -> datetime | None:
        """Return the window start, or unknown when there is not enough data."""
        window = self._window
        return window["start"] if window else None

    @property
    def extra_state_attributes(self) -> dict:
        """Return the window end and average price."""
        window = self._window
        if not window:
            return {}

        return {
            "end": window["end"].isoformat(),
            "average_price": to_euros(window["average"]),
            "hours": self._hours,
        }


class BorsihindPlanSensor(BorsihindSensorBase):
    """Sensor for network package configuration."""

    _attr_name = "Network Package"
    _attr_icon = "mdi:package-variant"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: BorsihindCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_plan"

    @property
    def native_value(self) -> str | None:
        """Return the network package."""
        plan = self.coordinator.plan
        return PLANS.get(plan, plan) if plan else None


class BorsihindIntervalSensor(BorsihindSensorBase):
    """Sensor for data interval configuration."""

    _attr_name = "Data Interval"
    _attr_icon = "mdi:clock-outline"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: BorsihindCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_interval"

    @property
    def native_value(self) -> str | None:
        """Return the data interval."""
        return self.coordinator.interval


class BorsihindMarginalSensor(BorsihindSensorBase):
    """Sensor for provider marginal configuration (with VAT)."""

    _attr_name = "Provider Marginal"
    _attr_icon = "mdi:cash"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PRICE_UNIT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: BorsihindCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_marginal"

    @property
    def native_value(self) -> float | None:
        """Return the provider marginal."""
        return to_euros(self.coordinator.marginal)
