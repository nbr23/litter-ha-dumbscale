# Litter Home-Assistant DumbScale

A Home Assistant custom integration that tracks (better) which cat used the litter box based on weight readings from the Litter-Robot 4's SmartScale. Relies on data collected by the [litter-robot integration](https://www.home-assistant.io/integrations/litterrobot/)

![Litter Home-Assistant DumbScale Dashboard][1]

## Installation

1. Copy the `custom_components/litter_ha_dumbscale` folder to your Home Assistant's `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings** > **Devices & Services**
2. Click **Add Integration**
3. Search for "Cat Weight Tracker"
4. Select one or more weight sensor entities
5. Set minimum/maximum weight thresholds (to filter out invalid readings)
6. Set the anomaly threshold (readings that differ from all known cat weights by more than this are rejected — default 1.0 lb)
7. Add each cat with their current weight

## Entities Created

| Entity | Type | Description |
|--------|------|-------------|
| `number.litter_ha_dumbscale_{cat}_weight` | Number | Raw last measured weight per cat (editable) |
| `sensor.litter_ha_dumbscale_{cat}_ema_weight` | Sensor | Smoothed weight per cat (exponential moving average) |
| `sensor.litter_ha_dumbscale_{cat}_visit_count` | Sensor | Total litter box visits per cat |
| `sensor.litter_ha_dumbscale_{cat}_last_visit` | Sensor | Timestamp of last visit per cat |
| `sensor.litter_ha_dumbscale_last_cat` | Sensor | Last cat to use the box (format: "Name (X.X lb)") |
| `binary_sensor.litter_ha_dumbscale_anomaly` | Binary Sensor | On when the last reading was rejected as an anomaly |

## How It Works

On each weight reading the integration:

1. Compares the reading against each cat's smoothed (EMA) weight to find the closest match
2. Rejects the reading if it differs from every cat's EMA by more than the anomaly threshold — fires a persistent notification and a `litter_ha_dumbscale_anomaly` event so you can build automations around it
3. On a valid match, updates the cat's raw weight and nudges their EMA weight toward the new reading (alpha=0.3), so a single bad reading that slips through can only shift the reference weight by 30%

## Resetting

To reset the integration and start fresh:

1. Go to **Settings** > **Devices & Services**
2. Find "Cat Weight Tracker"
3. Click the three dots and select "Delete"
4. Re-add the integration

## Dashboard Generator

A Python script is included to generate a dashboard for your cats.

### Quick Start

1. Copy `cats.sample.json` to `cats.json` and edit with your cat names and entity IDs
2. Run the generator:

```bash
uv run --script generate_dashboard.py --config cats.json -o my_dashboard.yaml
```

3. Import the generated YAML into Home Assistant:
   - Go to **Settings** > **Dashboards** > **Add Dashboard**
   - Choose "Take control" and paste the raw YAML config

### Config File Format

```json
{
  "weight_sensor_entity": "sensor.litter_robot_pet_weight",
  "litter_level_entity": "sensor.litter_robot_litter_level",
  "waste_drawer_entity": "sensor.litter_robot_waste_drawer",
  "vacuum_entity": "vacuum.litter_robot",
  "cats": ["Cat 1", "Cat 2"]
}
```

[1]:docs/ha-dashboard.png
