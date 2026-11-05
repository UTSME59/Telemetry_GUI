# UTS Motorsports Telemetry Dashboard

Python/PySide6 desktop application containing Stages 1–5 of the telemetry pipeline.

## Included stages

1. GUI framework and page navigation
2. Automatic USB/serial device detection
3. USART frame reception and validation
4. Lookup-table-driven CAN signal decoding
5. Thread-safe live telemetry signal cache with bounded history and stale-state detection

## Dashboard pages

- Main Overview
- High Voltage
- Low Voltage
- Faults
- USART Frames

The VCU and Vehicle Dynamics dashboard pages have been removed. Their telemetry
signals can still be decoded and cached if they remain useful elsewhere in the
application.

## Main Overview

- Pack voltage
- SOC
- Vehicle state (0 = GLV on / neutral, 1 = precharge, 2 = ready to drive, 3 = fault)
- Accumulator high temperature
- Motor temperature
- Motor controller temperature
- High/low cell voltage history on one graph
- All three temperatures on one graph
- Telemetry link status inside the receiver section

## High Voltage

- S_AUX + and S_AUX -
- Pack SOC
- DCL and CCL
- Accumulator, motor, and motor-controller temperatures
- High/low cell voltage history
- Pack voltage history
- Fan speed

## Low Voltage

- Vehicle state
- GLV battery voltage
- PDM current

## Critical IMD fault

When the decoded `IMD Fault` signal changes to an active/non-zero state, the
application opens a separate critical warning window. The warning is available
regardless of which dashboard page is currently selected.

The lookup table contains disabled placeholders for newly requested signals whose
real CAN IDs and byte mappings have not yet been supplied. Add the real mapping in
`telemetry_dashboard/data/telemetry_lookup_table.csv` and change `enabled` to
`true` for those rows.

## Run on Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

Configuration is stored in `app_config.json`. Signal definitions are stored in
`telemetry_dashboard/data/telemetry_lookup_table.csv`. Runtime logs are written
to `logs/telemetry_dashboard.log`.
