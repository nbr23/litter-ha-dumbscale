# Litter Home-Assistant DumbScale

A Home Assistant custom integration that tracks (better) which cat used the litter box based on weight readings from the Litter-Robot 4's SmartScale.

![Litter Home-Assistant DumbScale Dashboard][1]

## Installation

1. Copy the `custom_components/litter_ha_dumbscale` folder to your Home Assistant's `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings** > **Devices & Services**
2. Click **Add Integration**
3. Search for "Cat Weight Tracker"
4. Select your litter box weight sensor entity
5. Set minimum/maximum weight thresholds (to filter out invalid readings)
6. Add each cat with their current weight

## Entities Created

| Entity | Type | Description |
|--------|------|-------------|
| `number.litter_ha_dumbscale_{cat}_weight` | Number | Current weight for each cat (editable) |
| `sensor.litter_ha_dumbscale_{cat}_visit_count` | Sensor | Total litter box visits per cat |
| `sensor.litter_ha_dumbscale_{cat}_last_visit` | Sensor | Timestamp of last visit per cat |
| `sensor.litter_ha_dumbscale_last_cat` | Sensor | Last cat to use the box (format: "Name (X.X lb)") |

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
