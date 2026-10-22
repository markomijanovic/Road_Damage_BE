"""The prototype expects GPS samples at 30 samples/second."""
import json
import math
from fastapi import HTTPException


def read_positions(path):
    try:
        with open(path) as stream:
            samples = json.load(stream)["dynamicMetadata"]
        if not isinstance(samples, list) or not samples:
            raise ValueError("Missing GPS samples")
        positions = [(float(s["latitude"]), float(s["longitude"])) for s in samples]
        if any(not math.isfinite(lat) or not math.isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180 for lat, lon in positions):
            raise ValueError("Invalid coordinates")
        return positions
    except (ValueError, KeyError, TypeError, UnicodeError, OverflowError) as exc:
        raise HTTPException(422, "Metadata must contain non-empty dynamicMetadata with valid coordinates") from exc


def position_at_frame(positions, frame, video_fps):
    # Short metadata retains its last known position instead of indexing past EOF.
    return positions[min(int(frame * 30 / video_fps), len(positions) - 1)]
