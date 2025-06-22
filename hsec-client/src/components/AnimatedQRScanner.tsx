import React, { useRef, useEffect, useState } from 'react';
import QrScanner from 'qr-scanner';

// This is AI generated i have no idea how to do this math!!

/** ------------------------------------------------------------------
 * Utility helpers
 * ------------------------------------------------------------------*/

const rawToIp = (raw: string): string | null => {
    try {
        const decoded = atob(raw);
        return decoded.split('').map(c => c.charCodeAt(0)).join('.');
    } catch (e) {
        console.error('Failed to decode raw string:', e);
        return null;
    }
}

/** Cubic‑out easing */
const easeOutCubic = (t: number): number => 1 - Math.pow(1 - t, 3);

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

  const cx = quad.reduce((s, p) => s + p.x, 0) / 4;
  const cy = quad.reduce((s, p) => s + p.y, 0) / 4;
  const pts = [...quad].sort((a, b) => Math.atan2(a.y - cy, a.x - cx) - Math.atan2(b.y - cy, b.x - cx));

  const dist = (a: Point, b: Point): number => Math.hypot(a.x - b.x, a.y - b.y);
  const wRaw = Math.max(dist(pts[0], pts[1]), dist(pts[2], pts[3]));
  const hRaw = Math.max(dist(pts[0], pts[3]), dist(pts[1], pts[2]));

  if (wRaw === 0 || hRaw === 0) return null;
  const s = Math.round(Math.max(wRaw, hRaw));
  if (s === 0) return null;

  const dst = [
    { x: 0, y: 0 }, { x: s - 1, y: 0 },
    { x: s - 1, y: s - 1 }, { x: 0, y: s - 1 },
  ] as const;

  const A: number[][] = [];
  const B: number[] = [];
  for (let i = 0; i < 4; i++) {
    const { x: X, y: Y } = dst[i];
    const { x, y } = pts[i];
    A.push([X, Y, 1, 0, 0, 0, -x * X, -x * Y]); B.push(x);
    A.push([0, 0, 0, X, Y, 1, -y * X, -y * Y]); B.push(y);
  }
  const hVec = [...solve8x8(A, B), 1];
  const H = (r: number, c: number): number => hVec[r * 3 + c];

  const srcW = ctx.canvas.width;
  const srcH = ctx.canvas.height;
  const srcBuf = ctx.getImageData(0, 0, srcW, srcH).data;
  const out = ctx.createImageData(s, s);
  const dstBuf = out.data;

  let p = 0;
  for (let y = 0; y < s; y++) {
    for (let x = 0; x < s; x++) {
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
        dstBuf[p++] = 0; dstBuf[p++] = 0; dstBuf[p++] = 0;
        dstBuf[p++] = 255; // Opaque black for out-of-bounds
      }
    }
  }
  return out;
};

/** ------------------------------------------------------------------
 * Types
 * ------------------------------------------------------------------*/

type Point = { x: number; y: number };

interface FrozenDecodedText {
  text: string;
  style: React.CSSProperties;
}

/** ------------------------------------------------------------------
 * Component
 * ------------------------------------------------------------------*/

interface AnimatedQRScannerProps {
  onResult: (result: string) => void;
  className?: string;
  freezeOnScan?: boolean;
}

const AnimatedQRScanner: React.FC<AnimatedQRScannerProps> = ({
  onResult,
  className = '',
  freezeOnScan = false,
}) => {
  const wrapRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const hudRef = useRef<HTMLCanvasElement>(null);
  const blurRef = useRef<HTMLDivElement>(null);
  const patchRef = useRef<HTMLCanvasElement | null>(null);
  const decodedTextRef = useRef<HTMLDivElement | null>(null);

  const scannerRef = useRef<QrScanner | null>(null);
  const lastResultRef = useRef<string | null>(null);
  const animFrameRef = useRef<number | null>(null);
  const cleanupTimeoutRef = useRef<number | null>(null);

  const [scanHit, setScanHit] = useState<QrScanner.ScanResult | null>(null);
  const [animating, setAnimating] = useState(false);
  const [freeze, setFreeze] = useState(false);
  const [freezePatch, setFreezePatch] = useState<{ url: string; style: React.CSSProperties } | null>(null);
  const [freezeBg, setFreezeBg] = useState<string | null>(null);
  const [frozenDecodedText, setFrozenDecodedText] = useState<FrozenDecodedText | null>(null);
  const [containerSize, setContainerSize] = useState(0);

  useEffect(() => {
    if (!videoRef.current) return;
    if (!scannerRef.current) {
      scannerRef.current = new QrScanner(
        videoRef.current,
        res => {
          if (!animating && res.data !== lastResultRef.current) {
            setScanHit(res);
            setAnimating(true);
          }
        },
        { 
          returnDetailedScanResult: true,
          highlightScanRegion: false,
          calculateScanRegion: (video: HTMLVideoElement) => {return {x: 0, y: 0, width: video.videoWidth, height: video.videoHeight, downscaledWidth: video.videoWidth, downscaledHeight: video.videoHeight}},
          preferredCamera: 'environment',
        },
      );
      
    }
    const scanner = scannerRef.current;
    if (animating || freeze) scanner.pause();
    else scanner.start();
    setTimeout(() => {
      scanner.stop();
      scanner.setCamera('environment')
      scanner.start();
    },1000);
    return () => {
      scanner.stop();
      scanner.destroy();
      scannerRef.current = null;
    };
  }, [animating, freeze]);

  useEffect(() => {
    if (!scanHit || !videoRef.current || !wrapRef.current || !hudRef.current || !animating || containerSize === 0) return;

    if (cleanupTimeoutRef.current) clearTimeout(cleanupTimeoutRef.current);
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    if (patchRef.current) patchRef.current.remove();
    if (decodedTextRef.current) decodedTextRef.current.remove();

    if (blurRef.current) blurRef.current.style.opacity = '1';

    const vw = videoRef.current.videoWidth;
    const vh = videoRef.current.videoHeight;
    const scale = Math.max(containerSize / vw, containerSize / vh);
    const offX = (containerSize - vw * scale) / 2;
    const offY = (containerSize - vh * scale) / 2;

    const { cornerPoints: rawCornerPoints } = scanHit;
    const centroidX = rawCornerPoints.reduce((s, p) => s + p.x, 0) / 4;
    const centroidY = rawCornerPoints.reduce((s, p) => s + p.y, 0) / 4;
    const sortedCornerPoints = [...rawCornerPoints].sort(
      (a, b) => Math.atan2(a.y - centroidY, a.x - centroidX) - Math.atan2(b.y - centroidY, b.x - centroidX)
    );
    const sortedDispPts = sortedCornerPoints.map<Point>(p => ({ x: p.x * scale + offX, y: p.y * scale + offY }));
    const detectedCentroidX = sortedDispPts.reduce((sum, p) => sum + p.x, 0) / 4;
    const detectedCentroidY = sortedDispPts.reduce((sum, p) => sum + p.y, 0) / 4;

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
    hudCtx.moveTo(sortedDispPts[0].x, sortedDispPts[0].y);
    sortedDispPts.slice(1).forEach(p => hudCtx.lineTo(p.x, p.y));
    hudCtx.closePath();
    hudCtx.stroke();

    const frameCanvas = document.createElement('canvas');
    frameCanvas.width = vw;
    frameCanvas.height = vh;
    frameCanvas.getContext('2d')!.drawImage(videoRef.current, 0, 0);
    const patch = grabStraightQuad(frameCanvas.getContext('2d')!, scanHit.cornerPoints as Point[]);
    if (!patch || patch.width === 0) return;

    const patchCan = document.createElement('canvas');
    patchCan.width = patch.width;
    patchCan.height = patch.height;
    patchCan.getContext('2d')!.putImageData(patch, 0, 0);
    patchCan.style.cssText = `position:absolute;top:0;left:0;transform-origin:0 0;pointer-events:none;z-index:12;border-radius:4px;box-shadow:0 0 10px rgba(0,0,0,0.4);`;
    wrapRef.current.appendChild(patchCan);
    patchRef.current = patchCan;

    const textEl = document.createElement('div');
    textEl.textContent = rawToIp(scanHit.data) || scanHit.data;
    textEl.style.cssText = `
        position: absolute; opacity: 0; display: none; z-index: 14; color: white;
        background-color: rgba(0,0,0,0.65); padding: 10px 14px; border-radius: 6px;
        font-size: 15px; text-align: center; pointer-events: none; user-select: none;
        max-width: ${Math.min(containerSize * 0.8, 350)}px; word-break: break-all;
        transform: translateX(-50%); box-shadow: 0 2px 8px rgba(0,0,0,0.3);`;
    wrapRef.current.appendChild(textEl);
    decodedTextRef.current = textEl;

    const patchSideLength = patchCan.width;
    const initialDetectedWidth = Math.hypot(sortedDispPts[1].x - sortedDispPts[0].x, sortedDispPts[1].y - sortedDispPts[0].y);
    const initialDetectedHeight = Math.hypot(sortedDispPts[3].x - sortedDispPts[0].x, sortedDispPts[3].y - sortedDispPts[0].y);
    const avgInitialDetectedSideLength = (initialDetectedWidth + initialDetectedHeight) / 2.0;
    const initialAngle = getAngle(sortedDispPts[0], sortedDispPts[1]);
    const targetSize = Math.min(containerSize * 0.7, Math.max(containerSize * 0.4, 200));
    const endScale = targetSize / patchSideLength;
    const endX = (containerSize - targetSize) / 2;
    const endY = (containerSize - targetSize) / 2;
    const startUniformScale = avgInitialDetectedSideLength / patchSideLength;
    const scaledHalfSide = startUniformScale * patchSideLength / 2;
    const cosA = Math.cos(initialAngle);
    const sinA = Math.sin(initialAngle);
    const rotatedCenterXOffset = scaledHalfSide * cosA - scaledHalfSide * sinA;
    const rotatedCenterYOffset = scaledHalfSide * sinA + scaledHalfSide * cosA;
    const initialTx = detectedCentroidX - rotatedCenterXOffset;
    const initialTy = detectedCentroidY - rotatedCenterYOffset;

    patchCan.style.transform = `translate(${initialTx}px,${initialTy}px) rotate(${initialAngle}rad) scale(${startUniformScale})`;

    const ZOOM_DURATION = 700;
    const FLOAT_DURATION = 400;
    const FLOAT_AMOUNT = -25; // Negative for up
    const TEXT_FADE_IN_START_TIME = ZOOM_DURATION; // Start fade when zoom ends
    const TEXT_FADE_IN_DURATION = 300;
    const animationStartTime = performance.now();

    const step = (now: number) => {
      const elapsed = now - animationStartTime;
      let currentPatchX = endX, currentPatchY = endY, currentScale = endScale, currentAngle = 0;
      let currentFloatOffsetY = 0, currentTextOpacity = 0;

      if (elapsed < ZOOM_DURATION) {
        const k = easeOutCubic(elapsed / ZOOM_DURATION);
        currentPatchX = initialTx + (endX - initialTx) * k;
        currentPatchY = initialTy + (endY - initialTy) * k;
        currentScale = startUniformScale + (endScale - startUniformScale) * k;
        currentAngle = initialAngle * (1 - k);
      }

      if (elapsed >= ZOOM_DURATION && elapsed < ZOOM_DURATION + FLOAT_DURATION) {
        currentFloatOffsetY = easeOutCubic((elapsed - ZOOM_DURATION) / FLOAT_DURATION) * FLOAT_AMOUNT;
      } else if (elapsed >= ZOOM_DURATION + FLOAT_DURATION) {
        currentFloatOffsetY = FLOAT_AMOUNT;
      }
      
      const finalAnimatedPatchY = currentPatchY + currentFloatOffsetY; // Y pos of patch including float

      if (patchCan) {
        patchCan.style.transform = `translate(${currentPatchX}px, ${finalAnimatedPatchY}px) rotate(${currentAngle}rad) scale(${currentScale})`;
      }

      if (elapsed >= TEXT_FADE_IN_START_TIME && elapsed < TEXT_FADE_IN_START_TIME + TEXT_FADE_IN_DURATION) {
        currentTextOpacity = easeOutCubic((elapsed - TEXT_FADE_IN_START_TIME) / TEXT_FADE_IN_DURATION);
      } else if (elapsed >= TEXT_FADE_IN_START_TIME + TEXT_FADE_IN_DURATION) {
        currentTextOpacity = 1;
      }

      if (decodedTextRef.current) {
        const patchDisplaySize = patchSideLength * currentScale;
        const textTop = finalAnimatedPatchY + patchDisplaySize + 15; // Below patch
        const textLeft = currentPatchX + patchDisplaySize / 2; // Center of patch
        decodedTextRef.current.style.opacity = `${currentTextOpacity}`;
        decodedTextRef.current.style.top = `${textTop}px`;
        decodedTextRef.current.style.left = `${textLeft}px`;
        decodedTextRef.current.style.display = currentTextOpacity > 0.01 ? 'block' : 'none';
      }

      const totalAnimTime = Math.max(ZOOM_DURATION + FLOAT_DURATION, TEXT_FADE_IN_START_TIME + TEXT_FADE_IN_DURATION);
      if (elapsed < totalAnimTime) {
        animFrameRef.current = requestAnimationFrame(step);
      } else {
        lastResultRef.current = scanHit.data;
        onResult(scanHit.data);
        if (freezeOnScan) {
          setFreeze(true);
          if (patchCan) {
            setFreezePatch({
              url: patchCan.toDataURL(),
              style: {
                position: 'absolute', top: `${endY + FLOAT_AMOUNT}px`, left: `${endX}px`,
                width: `${targetSize}px`, height: `${targetSize}px`, zIndex: 13,
                borderRadius: '4px', boxShadow: '0 0 10px rgba(0,0,0,0.4)',
              },
            });
          }
          const finalPatchTopForText = endY + FLOAT_AMOUNT;
          const finalPatchLeftForText = endX + targetSize / 2;
          setFrozenDecodedText({
            text: rawToIp(scanHit.data) || scanHit.data,
            style: {
              position: 'absolute', opacity: 1, zIndex: 14, color: 'white',
              backgroundColor: 'rgba(0,0,0,0.65)', padding: '10px 14px', borderRadius: '6px',
              fontSize: '15px', textAlign: 'center', pointerEvents: 'none', userSelect: 'none',
              maxWidth: `${Math.min(containerSize * 0.8, 350)}px`, wordBreak: 'break-all',
              boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
              top: `${finalPatchTopForText + targetSize + 15}px`,
              left: `${finalPatchLeftForText}px`,
              transform: 'translateX(-50%)',
            },
          });
          if (hudRef.current) setFreezeBg(hudRef.current.toDataURL());
          if (patchRef.current) patchRef.current.remove();
          if (decodedTextRef.current) decodedTextRef.current.remove();
          setAnimating(false);
        } else {
          if (blurRef.current) blurRef.current.style.opacity = '0';
          if (patchRef.current) patchRef.current.remove();
          if (decodedTextRef.current) decodedTextRef.current.remove();
          patchRef.current = null; decodedTextRef.current = null;
          setAnimating(false); setScanHit(null);
          cleanupTimeoutRef.current = window.setTimeout(() => { lastResultRef.current = null; }, 300);
        }
      }
    };
    animFrameRef.current = requestAnimationFrame(step);

    return () => {
      if (cleanupTimeoutRef.current) clearTimeout(cleanupTimeoutRef.current);
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      if (patchRef.current) patchRef.current.remove();
      if (decodedTextRef.current) decodedTextRef.current.remove();
      patchRef.current = null; decodedTextRef.current = null;
    };
  }, [scanHit, animating, freezeOnScan, onResult, containerSize]);

  useEffect(() => {
    if (!freeze) {
      setFreezePatch(null);
      setFreezeBg(null);
      setFrozenDecodedText(null);
      setAnimating(false);
      lastResultRef.current = null;
      if (blurRef.current) blurRef.current.style.opacity = '0';
    }
  }, [freeze]);

  useEffect(() => {
    const handleResize = () => {
      if (!wrapRef.current || !hudRef.current) return;
      const S = wrapRef.current.clientWidth;
      hudRef.current.width = S;
      hudRef.current.height = S;
      setContainerSize(S);
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return (
    <div
      ref={wrapRef}
      className={`relative overflow-hidden w-full h-full aspect-square ${className}`.trim()}
      onClick={() => { if (freeze) setFreeze(false); }}
    >
      {!freeze && (
        <video ref={videoRef} className="absolute inset-0 w-full h-full object-cover" muted playsInline />
      )}
      <canvas ref={hudRef} className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: freeze ? -1 : 1 }} />
      <div
        ref={blurRef}
        style={{
          position: 'absolute', inset: 0, zIndex: 10, pointerEvents: 'none',
          transition: 'opacity 0.3s', opacity: animating || (freeze && !freezeBg) ? 1 : 0,
          backdropFilter: 'blur(8px)', WebkitBackdropFilter: 'blur(8px)',
          background: (freeze && freezeBg) ? 'transparent' : 'rgba(0,0,0,0.1)',
        }}
      />
      {freeze && freezeBg && (
        <img src={freezeBg} alt="Frozen background" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover', zIndex: 9, filter: 'blur(8px)', pointerEvents: 'none', userSelect: 'none' }} draggable={false} />
      )}
      {freezePatch && (
        <img src={freezePatch.url} style={freezePatch.style} alt="QR patch" draggable={false} />
      )}
      {frozenDecodedText && (
        <div style={frozenDecodedText.style}>{frozenDecodedText.text}</div>
      )}
    </div>
  );
};

export default AnimatedQRScanner;