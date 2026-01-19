# Börsihind.ee - Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Home Assistant integration for Estonian electricity exchange prices (Nord Pool) with network fees and taxes included.

## About

This integration fetches real-time electricity prices from [Börsihind.ee](https://borsihind.ee) and displays them as sensors in Home Assistant. Perfect for automating energy-intensive devices to run during cheaper hours and tracking your energy costs on the Energy Dashboard.

## Features

- **Real-time electricity prices** with all components (spot price, transmission, taxes, provider margin)
- **Price statistics** (current, average, minimum, maximum)
- **Energy Dashboard integration** for automatic cost calculations
- **Multiple network packages** supported (V1, V2, V4, V5)
- **Flexible update intervals** (15-minute or 1-hour data)
- **Configurable provider marginal** to match your electricity contract
- **Automation-ready** with detailed price attributes and forecasts

## Installation

### HACS (Recommended)

1. Open **HACS** in Home Assistant
2. Go to **Integrations**
3. Click the **three dots** in the top right corner
4. Select **Custom repositories**
5. Add this repository:
   - **URL**: `https://github.com/argoroots/borsihind-hacks`
   - **Category**: `Integration`
6. Click **Add**
7. Search for **"Börsihind.ee"** in HACS
8. Click **Download**
9. **Restart Home Assistant**

### Manual Installation

1. Download or clone this repository
2. Copy the `custom_components/borsihind` folder to your Home Assistant's `custom_components` directory
3. The path should be: `config/custom_components/borsihind/`
4. Restart Home Assistant

## Configuration

### Initial Setup

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for **"Börsihind.ee"**
4. Configure:
   - **Network Package**: Select your network area (V1, V2, V4, or V5)
   - **Data Interval**: Choose 15 minutes or 1 hour
   - **Provider Marginal**: Enter your provider's margin in cents (0-100)

### Changing Settings

You can modify the network package, interval, and marginal at any time:
1. Go to **Settings** → **Devices & Services**
2. Find the **Börsihind.ee** integration
3. Click **Configure**

## Sensors

The integration creates 7 sensors:

| Sensor | Description | Unit |
|--------|-------------|------|
| **Current Price** | Real-time electricity cost with all fees | €/kWh |
| **Average Price** | Average of all future prices | €/kWh |
| **Minimum Price** | Lowest upcoming price | €/kWh |
| **Maximum Price** | Highest upcoming price | €/kWh |
| **Network Package** | Configured network plan | - |
| **Data Interval** | Update frequency setting | - |
| **Provider Marginal** | Provider markup cost | €/kWh |

### Current Price Attributes

The Current Price sensor includes detailed attributes:
- `time` - Timestamp of current price
- `electricity_price` - Nord Pool spot price
- `transmission` - Network transmission fee
- `renewable_tax` - Renewable energy surcharge
- `supply_security` - Supply security fee
- `excise` - Electricity excise tax
- `marginal` - Provider markup
- `prices` - Array of next 24 price periods for automation

## Energy Dashboard Integration

To track your electricity costs automatically:

1. Go to **Settings** → **Dashboards** → **Energy**
2. Under **Electricity grid** → **Consumption**, add your energy meter
3. Select **"Use an entity with the current price"**
4. Choose the **Current Price** sensor (`sensor.borsihind_ee_*_current_price`)

Home Assistant will now calculate your actual energy costs based on real-time prices!

## Automation Examples

### Notify when price is below average

```yaml
automation:
  - alias: "Low electricity price notification"
    trigger:
      - platform: template
        value_template: >
          {{ states('sensor.borsihind_ee_vork_1_current_price') | float <
             states('sensor.borsihind_ee_vork_1_average_price') | float }}
    action:
      - service: notify.notify
        data:
          message: "Electricity price dropped below average! Good time for heavy loads."
```

### Run water heater during minimum price

```yaml
automation:
  - alias: "Smart water heater - cheapest hour"
    trigger:
      - platform: time_pattern
        minutes: "/15"
    condition:
      - condition: template
        value_template: >
          {{ states('sensor.borsihind_ee_vork_1_current_price') | float ==
             states('sensor.borsihind_ee_vork_1_minimum_price') | float }}
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.water_heater
```

### Turn off heating when price is too high

```yaml
automation:
  - alias: "Reduce heating during expensive hours"
    trigger:
      - platform: numeric_state
        entity_id: sensor.borsihind_ee_vork_1_current_price
        above: 0.15  # 15 cents per kWh
    action:
      - service: climate.set_temperature
        target:
          entity_id: climate.living_room
        data:
          temperature: 19
```

## Technical Details

- **Data source**: Börsihind.ee S3 bucket (`borsihind.s3.eu-central-1.amazonaws.com`)
- **Update frequency**: Every 15 minutes
- **IoT class**: Cloud polling
- **Price includes**: All taxes and fees, 24% VAT included
- **Future prices**: Up to 24 periods ahead (depending on available data)

### Price Components

All prices in €/kWh include:

1. **Electricity price** - Nord Pool spot price (variable)
2. **Transmission** - Network fee (varies by package and time)
3. **Renewable tax** - 1.04 c/kWh
4. **Supply security** - 0.94 c/kWh  
5. **Excise tax** - 0.26 c/kWh
6. **Marginal** - Your provider's markup (configurable)

### Network Packages

- **V1 (Võrk 1)** - Network area 1
- **V2 (Võrk 2)** - Network area 2
- **V4 (Võrk 4)** - Network area 4
- **V5 (Võrk 5)** - Network area 5

## Support

For issues, questions, or feature requests:
- **GitHub Issues**: [borsihind-hacks/issues](https://github.com/argoroots/borsihind-hacks/issues)
- **Email**: argo@roots.ee

## Credits

- Data provided by **Nord Pool** via [Börsihind.ee](https://borsihind.ee)
- Integration developed by [@argoroots](https://github.com/argoroots)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

