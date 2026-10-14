# Börsihind.ee - Home Assistant Integration

Home Assistant integration for Estonian electricity exchange prices (Nord Pool) with network fees, taxes and 24% VAT included.

Full documentation, sensors and automation examples: https://github.com/argoroots/borsihind-hacs

## Sensors

- **Current Price** - current price (€/kWh) with all fees, VAT and your provider marginal. Attributes include the price components and all upcoming prices.
- **Average / Minimum / Maximum Price** - statistics of the upcoming prices
- **Cheapest 1h … 4h** - start of the cheapest 1–4 hour window, with `end` and `average_price` attributes
- **Network Package**, **Data Interval**, **Provider Marginal** - configuration

The provider marginal is entered in cents/kWh, including VAT.

## Support

- GitHub: https://github.com/argoroots/borsihind-hacs/issues
- Email: argo@roots.ee

Data provided by Nord Pool via [Börsihind.ee](https://borsihind.ee).
