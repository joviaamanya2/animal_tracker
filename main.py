"""Count animals crossing a gate line in a video or camera feed.

Temporary tracker IDs are valid only while the tracker can follow an animal.
They are not permanent animal identities.
"""

from __future__ import annotations

import argparse

import cv2
from ultralytics import YOLO

from storage import end_session, record_crossing, start_session


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="0", help="Camera index (0) or video file path")
    parser.add_argument("--model", default="yolo11n.pt", help="Ultralytics YOLO model weights")
    parser.add_argument("--tracker", default="bytetrack.yaml", help="Ultralytics tracker config")
    parser.add_argument("--animal-class", type=int, default=19,
                        help="YOLO class index to count (COCO cow=19); use -1 for all detected classes")
    parser.add_argument("--line-position", type=float, default=0.5,
                        help="Horizontal counting line as a fraction of frame height (0 to 1)")
    parser.add_argument("--no-display", action="store_true", help="Run without an OpenCV preview window")
    args = parser.parse_args()
    if not 0 <= args.line_position <= 1:
        parser.error("--line-position must be between 0 and 1")
    if args.animal_class < -1:
        parser.error("--animal-class must be -1 or a valid class index")
    return args


def open_source(source: str) -> cv2.VideoCapture:
    value: int | str = int(source) if source.isdecimal() else source
    capture = cv2.VideoCapture(value)
    if not capture.isOpened():
        raise RuntimeError(f"Could not open video source: {source}")
    return capture


def main() -> None:
    args = parse_args()
    model = YOLO(args.model)
    capture = open_source(args.source)
    session_id = start_session()

    # Each track's last observed side of the gate line prevents repeated counts
    # while it remains on the same side. A genuine recrossing counts again.
    last_side: dict[int, int] = {}
    outbound = 0
    inbound = 0
    line_y: int | None = None
    print(f"Counting session {session_id} started. Press Q in the preview window to stop.")
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break

            height, width = frame.shape[:2]
            line_y = int(height * args.line_position)
            result = model.track(frame, persist=True, tracker=args.tracker, verbose=False)[0]
            boxes = result.boxes

            if boxes is not None and boxes.id is not None:
                ids = boxes.id.int().cpu().tolist()
                coords = boxes.xyxy.int().cpu().tolist()
                classes = boxes.cls.int().cpu().tolist()

                for track_id, (x1, y1, x2, y2), class_id in zip(ids, coords, classes):
                    if args.animal_class != -1 and class_id != args.animal_class:
                        continue

                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2
                    side = -1 if center_y < line_y else 1
                    old_side = last_side.get(track_id)

                    color = (80, 220, 80)
                    if old_side is not None and side != old_side:
                        # With a horizontal line: downward is outbound and upward is inbound.
                        direction = "out" if old_side == -1 and side == 1 else "in"
                        if direction == "out":
                            outbound += 1
                        else:
                            inbound += 1
                        record_crossing(session_id, f"TEMP-{track_id}", direction)
                        color = (0, 180, 255)

                    last_side[track_id] = side
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(frame, f"TEMP-{track_id}", (x1, max(20, y1 - 8)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            cv2.line(frame, (0, line_y), (width, line_y), (255, 180, 0), 2)
            still_out = max(0, outbound - inbound)
            cv2.putText(frame, f"Out: {outbound}  Returned: {inbound}  Still out: {still_out}",
                        (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)

            if not args.no_display:
                cv2.imshow("Animal gate counter", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
    finally:
        capture.release()
        cv2.destroyAllWindows()
        end_session(session_id)

    print(f"Finished. Out: {outbound}; returned: {inbound}; still out: {max(0, outbound - inbound)}")
    print("Passage events saved to runs/animal_tracker.sqlite3")


if __name__ == "__main__":
    main()
