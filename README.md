# Animal Tracker

Animal Tracker is a local prototype for counting animals passing through a gate. It reads a live camera or video file, detects and tracks objects with Ultralytics YOLO, records each tracked object's crossing of a horizontal line, and displays session totals and recent events on a local Flask dashboard.

The project is intended for supervised counting experiments. Track IDs are temporary and counts can be affected by camera placement, occlusion, missed detections, or tracker ID changes.

## Features

- Live camera and prerecorded video input.
- YOLO object detection with persistent ByteTrack IDs.
- Configurable target class and horizontal counting line.
- Counts top-to-bottom crossings as **out** and bottom-to-top crossings as **in**.
- SQLite storage for sessions and crossing events.
- Dashboard that refreshes every three seconds and shows the newest session's totals and latest 100 crossings.

## Requirements

- Windows, macOS, or Linux with Python 3.10 or newer (recommended).
- A camera for live capture, or a readable video file.
- Dependencies in `requirements.txt` (Ultralytics, OpenCV, Flask). YOLO inference may run on CPU; compatible hardware can improve throughput.

The repository contains a `yolo11n.pt` weights file, but `.pt` files are ignored by Git. If it is absent, Ultralytics will try to obtain the requested weights when the model is loaded. The first run can therefore require network access.

## Installation

From the project directory, create and activate a virtual environment, then install dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, run the environment's interpreter directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

For macOS or Linux, use `python3 -m venv .venv`, activate with `source .venv/bin/activate`, and then install requirements with `python -m pip install -r requirements.txt`.

## Run the application

Run the dashboard and counter in separate terminals from the project directory. Start the dashboard:

```powershell
python dashboard.py
```

Then open [http://127.0.0.1:5000](http://127.0.0.1:5000). The dashboard can start before or after a counter session; it reports the most recently created session.

Start the counter in another terminal, using camera index `0`:

```powershell
python main.py --source 0
```

Or process a video file:

```powershell
python main.py --source .\sample-video.mp4
```

The preview draws detections, temporary track IDs, the counting line, and running totals. Press **Q** in the preview window to stop. When a video ends or the counter exits, it closes the session and saves its events. Use `--no-display` to run without a preview window (for example, on a headless host); this mode ends when the source ends or the process is interrupted.

## Counter options

| Option | Default | Description |
| --- | --- | --- |
| `--source` | `0` | Camera index (as a numeric string) or video path. |
| `--model` | `yolo11n.pt` | Ultralytics model weights. The selected model must recognize the class you want to count. |
| `--tracker` | `bytetrack.yaml` | Ultralytics tracker configuration. |
| `--animal-class` | `19` | Class index to count; `19` is `cow` in the standard COCO class list. Use `-1` to count every detected class. |
| `--line-position` | `0.5` | Horizontal line position as a fraction of frame height, from `0` (top) to `1` (bottom). |
| `--no-display` | off | Disable the OpenCV preview window. |

Examples:

```powershell
python main.py --source 1 --line-position 0.62
python main.py --source .\yard.mp4 --model .\custom-livestock.pt --animal-class 0
python main.py --source 0 --no-display
```

Use the class indices for the model you selected. The default class index is specific to the standard COCO label mapping; a custom livestock model may use different indices. To find available command options, run `python main.py --help`.

## Counting behavior and setup guidance

Each frame is passed to `model.track(..., persist=True)`. For each tracked detection matching the configured class, the application compares the bounding-box center to the horizontal line. A change from above the line to below it records an **out** event; below to above records an **in** event. Remaining on the same side does not create repeated counts, while crossing back can count again.

Mount the camera so the line spans the gate and animals cross it in the intended direction. The line is based on image coordinates, not physical direction. A low, crowded, or obstructed view can reduce detection and tracking quality. Tune the line position and validate results against observed passages before relying on counts.

The displayed **Still out** total is `max(0, out - in)` for the session. It is a net count, not a list of individual animals believed to be outside.

## Dashboard and API

- `GET /` serves the dashboard page.
- `GET /api/state` returns a JSON snapshot containing the latest session, its `out`, `in`, and `still_out` totals, and up to 100 newest crossing events.

The Flask server binds to `127.0.0.1:5000`, so it is accessible only from the same machine by default. The page requests the state every three seconds.

## Data storage

SQLite data is stored at `runs/animal_tracker.sqlite3`, relative to the process's current working directory. The directory and tables are created automatically. `runs/` is ignored by Git, so session data is local runtime data and is not committed with the source.

The database has two tables:

- `sessions`: session ID, start timestamp, and optional end timestamp.
- `crossings`: event ID, session ID, local ISO-8601 timestamp, temporary track ID (such as `TEMP-7`), and direction (`out` or `in`).

The dashboard queries the newest session by ID. Existing sessions are retained; starting a new one does not erase earlier records. Back up the SQLite file if the records need to be preserved.

## Project layout

```text
AnimalTracker/
├── dashboard.py       # Flask page and JSON API
├── main.py            # Video capture, YOLO tracking, crossing detection
├── storage.py         # SQLite schema and persistence helpers
├── templates/
│   └── index.html     # Dashboard UI
├── requirements.txt  # Python dependencies
└── runs/              # Created at runtime; SQLite database is ignored by Git
```

## Known limitations

- `TEMP-*` identifiers are tracker IDs, not permanent identities; they can change after occlusion, crowded crossings, or a tracker reset.
- A lost or duplicated track can cause a missed or duplicate crossing. There is no manual correction or event review interface.
- The counter only evaluates the configured class (or all classes with `-1`) and does not identify ear tags or individual animals.
- The dashboard shows the newest session only; it does not provide historical session selection or exports.
- No authentication is configured. The dashboard is bound to localhost by default and should not be exposed to an untrusted network without adding appropriate access controls.

## Troubleshooting

- **Camera or video fails to open:** check the camera index, file path, camera permissions, and whether another application is using the device.
- **No animals are counted:** verify the model supports the chosen class index, that detections have track IDs, and that animals' bounding-box centers cross the line.
- **Counts have the wrong direction:** move the camera or treat top-to-bottom as out and bottom-to-top as in; direction is not inferred from the real-world gate.
- **Dashboard shows no session:** run the counter at least once and confirm both processes are using the project directory, since the SQLite path is relative.
- **Weights cannot load:** ensure the configured weights file exists, or allow Ultralytics to download the default weights on first use.
