import QrScanner from 'qr-scanner';
import React, { useEffect, useRef, useState } from 'react';
// This is AI generated i have no idea how to do this math!!

/** ------------------------------------------------------------------
 * Utility helpers
 * ------------------------------------------------------------------*/

/** Cubic‑out easing */
const easeOutCubic = (t: number): number => 1 - Math.pow(1 - t, 3);

/** Corner‑sorted bounding‑box */
const getBoundingBox = (pts: Point[]): BoundingBox => {
  const xs = pts.map(p => p.x);
  const ys = pts.map(p => p.y);
  return {
    minX: Math.min(...xs),
    minY: Math.min(...ys),
    maxX: Math.max(...xs),
    maxY: Math.max(...ys),
    get width() { return this.maxX - this.minX; },
    get height() { return this.maxY - this.minY; },
  } as BoundingBox;
};

const getAngle = (p0: Point, p1: Point): number => Math.atan2(p1.y - p0.y, p1.x - p0.x);

/** 8×8 Gauss–Jordan solver (used by perspective transform) */
const solve8x8 = (A: number[][], b: number[]): number[] => {
  for (let i = 0; i < 8; i++) {
    let max = i;
    for (let k = i + 1; k < 8; k++) {
      if (Math.abs(A[k][i]) > Math.abs(A[max][i])) max = k;
    }
    [A[i], A[max]] = [A[max], A[i]];
    [b[i], b[max]] = [b[max], b[i]];

    const piv = A[i][i];
    for (let j = i; j < 8; j++) A[i][j] /= piv;
    b[i] /= piv;

    for (let k = 0; k < 8; k++) {
      if (k === i) continue;
      const f = A[k][i];
      for (let j = i; j < 8; j++) A[k][j] -= f * A[i][j];
      b[k] -= f * b[i];
    }
  }
  return b;
};

/** Perspective‑correct extraction of the QR patch */
const grabStraightQuad = (
  ctx: CanvasRenderingContext2D,
  quad: Point[],
): ImageData | null => {
  if (!ctx || quad.length !== 4 || ctx.canvas.width === 0 || ctx.canvas.height === 0) return null;

  // ── Sort points clockwise around centroid ───────────────────────────
  const cx = quad.reduce((s, p) => s + p.x, 0) / 4;
  const cy = quad.reduce((s, p) => s + p.y, 0) / 4;
  const pts = [...quad].sort((a, b) => Math.atan2(a.y - cy, a.x - cx) - Math.atan2(b.y - cy, b.x - cx));

  const dist = (a: Point, b: Point): number => Math.hypot(a.x - b.x, a.y - b.y);
  const w = Math.round(Math.max(dist(pts[0], pts[1]), dist(pts[2], pts[3])));
  const h = Math.round(Math.max(dist(pts[0], pts[3]), dist(pts[1], pts[2])));

  const dst = [
    { x: 0, y: 0 },
    { x: w - 1, y: 0 },
    { x: w - 1, y: h - 1 },
    { x: 0, y: h - 1 },
  ] as const;

  // ── Build linear system for homography ──────────────────────────────
  const A: number[][] = [];
  const B: number[] = [];
  for (let i = 0; i < 4; i++) {
    const { x: X, y: Y } = dst[i];
    const { x, y } = pts[i];
    A.push([X, Y, 1, 0, 0, 0, -x * X, -x * Y]);
    B.push(x);
    A.push([0, 0, 0, X, Y, 1, -y * X, -y * Y]);
    B.push(y);
  }
  const hVec = [...solve8x8(A, B), 1];
  const H = (r: number, c: number): number => hVec[r * 3 + c];

  // ── Resample pixels ─────────────────────────────────────────────────
  const srcW = ctx.canvas.width;
  const srcH = ctx.canvas.height;
  const srcBuf = ctx.getImageData(0, 0, srcW, srcH).data;
  const out = ctx.createImageData(w, h);
  const dstBuf = out.data;

  let p = 0;
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const u = H(0, 0) * x + H(0, 1) * y + H(0, 2);
      const v = H(1, 0) * x + H(1, 1) * y + H(1, 2);
      const w_ = H(2, 0) * x + H(2, 1) * y + H(2, 2);
      const sx = Math.round(u / w_);
      const sy = Math.round(v / w_);
      if (sx >= 0 && sx < srcW && sy >= 0 && sy < srcH) {
        const sp = (sy * srcW + sx) << 2;
        dstBuf[p++] = srcBuf[sp];
        dstBuf[p++] = srcBuf[sp + 1];
        dstBuf[p++] = srcBuf[sp + 2];
        dstBuf[p++] = srcBuf[sp + 3];
      } else {
        dstBuf[p++] = dstBuf[p++] = dstBuf[p++] = 0;
        dstBuf[p++] = 255;
      }
    }
  }
  return out;
};

/** ------------------------------------------------------------------
 * Types
 * ------------------------------------------------------------------*/

type Point = { x: number; y: number };
interface BoundingBox { minX: number; minY: number; maxX: number; maxY: number; width: number; height: number; }



/** ------------------------------------------------------------------
 * Component
 * ------------------------------------------------------------------*/

interface AnimatedQRScannerProps {
  onResult: (result: string) => void;
  className?: string;
  /** If true, pause camera and leave enlarged QR on screen after a scan */
  freezeOnScan?: boolean;
}

const AnimatedQRScanner: React.FC<AnimatedQRScannerProps> = ({
  onResult,
  className = '',
  freezeOnScan = false,
}) => {
  /** ── DOM refs ─────────────────────────────────────────────────────*/
  const wrapRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const hudRef = useRef<HTMLCanvasElement>(null);
  const blurRef = useRef<HTMLDivElement>(null);
  const patchRef = useRef<HTMLCanvasElement | null>(null);

  /** ── Runtime refs/state ───────────────────────────────────────────*/
  const scannerRef = useRef<QrScanner | null>(null);
  const lastResultRef = useRef<string | null>(null);
  const animFrameRef = useRef<number | null>(null);
  const cleanupTimeoutRef = useRef<number | null>(null);

  const [scanHit, setScanHit] = useState<QrScanner.ScanResult | null>(null);
  const [animating, setAnimating] = useState(false);
  const [freeze, setFreeze] = useState(false);
  const [freezePatch, setFreezePatch] = useState<{
    url: string;
    style: React.CSSProperties;
  } | null>(null);
  const [freezeBg, setFreezeBg] = useState<string | null>(null);

  /** ----------------------------------------------------------------
   * Boot / teardown the camera & scanner
   * ----------------------------------------------------------------*/
  useEffect(() => {
    if (!videoRef.current) return;

    // Lazily create scanner once we have a <video>
    if (!scannerRef.current) {
      scannerRef.current = new QrScanner(
        videoRef.current,
        res => {
          if (!animating && res.data !== lastResultRef.current) {
            setScanHit(res);
            setAnimating(true);
          }
        },
        { returnDetailedScanResult: true, highlightScanRegion: false },
      );
    }

    const scanner = scannerRef.current;
    if (animating || freeze) scanner.pause();
    else scanner.start();

    return () => {
      scanner.stop();
      scanner.destroy();
      scannerRef.current = null;
    };
  }, [animating, freeze]);

  /** ----------------------------------------------------------------
   * Animation when a code is found
   * ----------------------------------------------------------------*/
  useEffect(() => {
    if (!scanHit || !videoRef.current || !wrapRef.current || !hudRef.current || !animating) return;

    // ── Cancel any previous animation/cleanup
    if (cleanupTimeoutRef.current) clearTimeout(cleanupTimeoutRef.current);
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    if (patchRef.current) patchRef.current.remove();

    // ── Activate blur overlay
    if (blurRef.current) blurRef.current.style.opacity = '1';

    const containerSize = wrapRef.current.clientWidth; // square wrapper
    const vw = videoRef.current.videoWidth;
    const vh = videoRef.current.videoHeight;
    const scale = Math.max(containerSize / vw, containerSize / vh);
    const dispW = vw * scale;
    const dispH = vh * scale;
    const offX = (containerSize - dispW) / 2;
    const offY = (containerSize - dispH) / 2;

    // Coordinates of QR corners within displayed video
    const dispPts = scanHit.cornerPoints.map<Point>(p => ({
      x: p.x * scale + offX,
      y: p.y * scale + offY,
    }));

    /** ── HUD ───────────────────────────────────────────────────────*/
    const hudCtx = hudRef.current.getContext('2d', { willReadFrequently: true })!;
    hudRef.current.width = containerSize;
    hudRef.current.height = containerSize;

    hudCtx.clearRect(0, 0, containerSize, containerSize);
    hudCtx.save();
    hudCtx.translate(offX, offY);
    hudCtx.scale(scale, scale);
    hudCtx.drawImage(videoRef.current, 0, 0);
    hudCtx.restore();

    hudCtx.strokeStyle = 'rgba(0, 255, 0, 0.7)';
    hudCtx.lineWidth = 4;
    hudCtx.beginPath();
    hudCtx.moveTo(dispPts[0].x, dispPts[0].y);
    dispPts.slice(1).forEach(p => hudCtx.lineTo(p.x, p.y));
    hudCtx.closePath();
    hudCtx.stroke();

    /** ── Extract perspective‑correct patch ────────────────────────*/
    const frameCanvas = document.createElement('canvas');
    frameCanvas.width = vw;
    frameCanvas.height = vh;
    frameCanvas.getContext('2d')!.drawImage(videoRef.current, 0, 0);

    const patch = grabStraightQuad(frameCanvas.getContext('2d')!, scanHit.cornerPoints as Point[]);
    if (!patch || patch.width === 0 || patch.height === 0) return;

    const patchCan = document.createElement('canvas');
    patchCan.width = patch.width;
    patchCan.height = patch.height;
    patchCan.getContext('2d')!.putImageData(patch, 0, 0);

    patchCan.style.cssText = `position:absolute;top:0;left:0;transform-origin:0 0;pointer-events:none;z-index:12;border-radius:4px;box-shadow:0 0 10px rgba(0,0,0,0.4);`;
    wrapRef.current.appendChild(patchCan);
    patchRef.current = patchCan;

    // ── Prepare animation keyframes ────────────────────────────────
    const bbox = getBoundingBox(dispPts);
    const initialW = Math.hypot(dispPts[1].x - dispPts[0].x, dispPts[1].y - dispPts[0].y);
    const initialH = Math.hypot(dispPts[3].x - dispPts[0].x, dispPts[3].y - dispPts[0].y);
    const initialAngle = getAngle(dispPts[0], dispPts[1]);

    const targetSize = Math.min(containerSize * 0.7, Math.max(containerSize * 0.4, 200));
    const endScale = targetSize / Math.max(patchCan.width, patchCan.height);
    const endX = (containerSize - patchCan.width * endScale) / 2;
    const endY = (containerSize - patchCan.height * endScale) / 2;

    // Place at starting pose
    patchCan.style.transform = `translate(${bbox.minX}px,${bbox.minY}px) rotate(${initialAngle}rad) scale(${initialW / patchCan.width},${initialH / patchCan.height})`;

    /** ── Animate with rAF ─────────────────────────────────────────*/
    const DURATION = 800;
    const startTime = performance.now();

    const step = (now: number): void => {
      const t = Math.min(1, (now - startTime) / DURATION);
      const k = easeOutCubic(t);

      const curX = bbox.minX + (endX - bbox.minX) * k;
      const curY = bbox.minY + (endY - bbox.minY) * k;
      const curScaleX = (initialW / patchCan.width) + (endScale - initialW / patchCan.width) * k;
      const curScaleY = (initialH / patchCan.height) + (endScale - initialH / patchCan.height) * k;
      const curAngle = initialAngle * (1 - k);

      patchCan.style.transform = `translate(${curX}px,${curY}px) rotate(${curAngle}rad) scale(${curScaleX},${curScaleY})`;

      if (t < 1) {
        animFrameRef.current = requestAnimationFrame(step);
      } else {
        // ── Animation finished ────────────────────────────────────
        lastResultRef.current = scanHit.data;
        onResult(scanHit.data);

        if (freezeOnScan) {
          // Persist enlarged patch & blurred background
          setFreezePatch({
            url: patchCan.toDataURL(),
            style: {
              position: 'absolute',
              top: `${endY}px`,
              left: `${endX}px`,
              width: `${patchCan.width * endScale}px`,
              height: `${patchCan.height * endScale}px`,
              zIndex: 13,
              borderRadius: 4,
              boxShadow: '0 0 10px rgba(0,0,0,0.4)',
              pointerEvents: 'none',
              objectFit: 'contain',
              background: 'white',
            },
          });

          const bgCanvas = document.createElement('canvas');
          bgCanvas.width = containerSize;
          bgCanvas.height = containerSize;
          bgCanvas.getContext('2d')!.drawImage(videoRef.current, 0, 0, containerSize, containerSize);
          setFreezeBg(bgCanvas.toDataURL());
          setFreeze(true);
        } else {
          patchCan.remove();
          if (blurRef.current) blurRef.current.style.opacity = '0';
          cleanupTimeoutRef.current = window.setTimeout(() => setAnimating(false), 300);
        }
      }
    };

    animFrameRef.current = requestAnimationFrame(step);

    /** ── Cleanup on effect re‑run/unmount ───────────────────────*/
    return () => {
      if (cleanupTimeoutRef.current) clearTimeout(cleanupTimeoutRef.current);
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      if (patchRef.current) patchRef.current.remove();
    };
  }, [scanHit, animating, freezeOnScan, onResult]);

  /** ----------------------------------------------------------------
   * Reset state when exiting freeze mode
   * ----------------------------------------------------------------*/
  useEffect(() => {
    if (!freeze) {
      setFreezePatch(null);
      setFreezeBg(null);
      setAnimating(false);
    }
  }, [freeze]);

  /** ----------------------------------------------------------------
   * Keep HUD canvas square and responsive
   * ----------------------------------------------------------------*/
  useEffect(() => {
    const handleResize = (): void => {
      if (!wrapRef.current || !hudRef.current) return;
      const S = wrapRef.current.clientWidth;
      hudRef.current.width = S;
      hudRef.current.height = S;
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  /** ----------------------------------------------------------------
   * JSX
   * ----------------------------------------------------------------*/
  return (
    <div
      ref={wrapRef}
      className={`relative overflow-hidden w-full h-full aspect-square ${className}`.trim()}
    >
      {!freeze && (
        <video
          ref={videoRef}
          className="absolute inset-0 w-full h-full object-cover"
          muted
          playsInline
        />
      )}

      <canvas
        ref={hudRef}
        className="absolute inset-0 w-full h-full pointer-events-none"
      />

      {/* Blur overlay */}
      <div
        ref={blurRef}
        style={{
          position: 'absolute',
          inset: 0,
          zIndex: 10,
          pointerEvents: 'none',
          transition: 'opacity 0.3s',
          opacity: animating || freeze ? 1 : 0,
          backdropFilter: 'blur(8px)',
          WebkitBackdropFilter: 'blur(8px)',
        }}
      />

      {/* Frozen blurred background */}
      {freeze && freezeBg && (
        <img
          src={freezeBg}
          alt="Frozen background"
          style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover', zIndex: 9, filter: 'blur(8px)', pointerEvents: 'none', userSelect: 'none' }}
          draggable={false}
        />
      )}

      {/* Frozen QR patch */}
      {freezePatch && (
        <img src={freezePatch.url} style={freezePatch.style} alt="QR patch" draggable={false} />
      )}
    </div>
  );
};

export default AnimatedQRScanner;
