# Animal Tracker: counting prototype

The Python prototype detects animals in a gate camera or video, follows them with temporary tracker IDs, and counts crossings of a horizontal line. Downward crossings count as **out**; upward crossings count as **in**. Session totals and passage events are stored in `runs/animal_tracker.sqlite3` and shown on a local web dashboard.

## Setup (Windows PowerShell)

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Run

Start the records dashboard in one PowerShell window:

```powershell
.\venv\Scripts\python.exe dashboard.py
```

Open `http://127.0.0.1:5000` in your browser. Leave the dashboard running while the counter runs in a second PowerShell window.

Use camera 0:

```powershell
.\venv\Scripts\python.exe main.py --source 0
```

Or use a recorded video:

```powershell
.\venv\Scripts\python.exe main.py --source .\sample-video.mp4
```

Press **Q** in the preview window to stop. The first run downloads the selected YOLO weights if they are not already available. The default class index is COCO `cow` (19). To count every class detected by the selected model, pass `--animal-class -1`; for a different livestock species, use a model that detects that species and configure its class index. The dashboard refreshes automatically and shows the latest session plus its recent crossings.

## Current limits

- `TEMP-*` IDs come from video tracking and may change after occlusion, crowded crossings, or a tracker restart. They do not identify a specific animal across separate sessions.
- Direction is based on image coordinates: top-to-bottom is out, bottom-to-top is in. Mount the camera so that this matches the gate direction.
- “Still out” is the session's outgoing count minus the return count. It does not prove which individual animals remain outside.
- Permanent ear-tag recognition is not implemented yet.
