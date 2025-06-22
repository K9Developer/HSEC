import cv2
import numpy as np
import os
from PIL import Image
from typing import List, Tuple

DIFF_THRESHOLD = 22
MORPH_KERNEL = 5
MIN_BLOB_AREA_PX = 400
MAX_RELOCATE_PX = 15
SCORE_GAIN = 20000
GLITCH_MEAN_DELTA = 55
GLITCH_AREA_FRAC = 0.60
EDGE_DILATE = 2

def _pil_to_cv(img: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)

def _align_by_phase(prev_g: np.ndarray, curr_g: np.ndarray) -> Tuple[np.ndarray, Tuple[float, float]]:
    (shift_y, shift_x), _ = cv2.phaseCorrelate(
        prev_g.astype(np.float32), curr_g.astype(np.float32)
    )
    M = np.float32([[1, 0, shift_x], [0, 1, shift_y]])
    aligned = cv2.warpAffine(prev_g, M, (prev_g.shape[1], prev_g.shape[0]),
                             flags=cv2.INTER_LINEAR,
                             borderMode=cv2.BORDER_REPLICATE)
    return aligned, (shift_x, shift_y)

def _contours(mask: np.ndarray) -> List[Tuple[int, float, float, int, int, int, int]]:
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    blobs = []
    for c in cnts:
        area = int(cv2.contourArea(c))
        if area < MIN_BLOB_AREA_PX:
            continue
        x, y, w, h = cv2.boundingRect(c)
        M = cv2.moments(c)
        cx = M["m10"] / M["m00"]
        cy = M["m01"] / M["m00"]
        blobs.append((area, cx, cy, x, y, x + w, y + h))
    return blobs

def _iou_intersects(b1, b2) -> bool:
    _, _, _, x0a, y0a, x1a, y1a = b1
    _, _, _, x0b, y0b, x1b, y1b = b2
    ix0, iy0 = max(x0a, x0b), max(y0a, y0b)
    ix1, iy1 = min(x1a, x1b), min(y1a, y1b)
    return ix1 > ix0 and iy1 > iy0

def _same_blob(b1, b2) -> bool:
    _, cx1, cy1, *_ = b1
    _, cx2, cy2, *_ = b2
    return (
        abs(cx1 - cx2) <= MAX_RELOCATE_PX
        and abs(cy1 - cy2) <= MAX_RELOCATE_PX
        and _iou_intersects(b1, b2)
    )

def motion_score(prev_pil: Image.Image, curr_pil: Image.Image) -> int:
    prev = _pil_to_cv(prev_pil)
    curr = _pil_to_cv(curr_pil)
    prev_g = cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY)
    curr_g = cv2.cvtColor(curr, cv2.COLOR_BGR2GRAY)

    aligned_prev_g, (dx, dy) = _align_by_phase(prev_g, curr_g)

    diff = cv2.absdiff(curr_g, aligned_prev_g)
    _, diff_mask = cv2.threshold(diff, DIFF_THRESHOLD, 255, cv2.THRESH_BINARY)

    k = cv2.getStructuringElement(cv2.MORPH_RECT, (MORPH_KERNEL, MORPH_KERNEL))
    motion_mask = cv2.morphologyEx(diff_mask, cv2.MORPH_OPEN, k)
    motion_mask = cv2.morphologyEx(motion_mask, cv2.MORPH_CLOSE, k)

    edge_prev = cv2.Canny(aligned_prev_g, 60, 120)
    edge_curr = cv2.Canny(curr_g, 60, 120)
    edge_prev = cv2.dilate(edge_prev, None, iterations=EDGE_DILATE // 2)
    edge_curr = cv2.dilate(edge_curr, None, iterations=EDGE_DILATE // 2)

    prev_blobs = _contours(edge_prev)
    curr_blobs = _contours(edge_curr)

    new_mask = np.zeros_like(motion_mask)
    for cb in curr_blobs:
        if not any(_same_blob(cb, pb) for pb in prev_blobs):
            _, _, _, x0, y0, x1, y1 = cb
            new_mask[y0:y1, x0:x1] = motion_mask[y0:y1, x0:x1]

    new_area = int(np.count_nonzero(new_mask))
    total_px = motion_mask.size
    new_frac = new_area / total_px
    mean_delta = float(np.mean(diff))

    if mean_delta > GLITCH_MEAN_DELTA or new_frac > GLITCH_AREA_FRAC:
        score = 0
    else:
        score = int(min(100, new_frac * SCORE_GAIN))

    return score
