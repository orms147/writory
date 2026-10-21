import { useEffect, useRef } from 'react';
import { useFinePointer, usePrefersReducedMotion } from '../lib/media';

const INTERACTIVE = 'a,button,label,input,textarea,select,[data-press]';

/** Vầng mực theo chuột (README bàn giao mục 7, `onMove` trong source-dc/D-*.dc.html). Chỉ khi
 *  `(hover: hover) and (pointer: fine)` và không bật giảm chuyển động. */
export function InkHalo() {
  const fine = useFinePointer();
  const reduced = usePrefersReducedMotion();
  const ref = useRef<HTMLDivElement>(null);
  const enabled = fine && !reduced;

  useEffect(() => {
    if (!enabled) return;
    const halo = ref.current;
    if (!halo) return;
    let hx = 0;
    let hy = 0;
    let tx = 0;
    let ty = 0;
    let started = false;
    let raf = 0;

    const loop = () => {
      hx += (tx - hx) * 0.2;
      hy += (ty - hy) * 0.2;
      halo.style.transform = `translate3d(${hx}px, ${hy}px, 0)`;
      raf = Math.abs(tx - hx) + Math.abs(ty - hy) > 0.3 ? requestAnimationFrame(loop) : 0;
    };
    const onMove = (e: MouseEvent) => {
      tx = e.clientX;
      ty = e.clientY;
      if (!started) {
        hx = tx;
        hy = ty;
        started = true;
      }
      const t = e.target instanceof Element ? e.target : null;
      halo.dataset.on = '1';
      halo.dataset.hover = t?.closest(INTERACTIVE) ? '1' : '0';
      halo.dataset.paper = t?.closest('[data-paper]') ? '1' : '0';
      if (!raf) raf = requestAnimationFrame(loop);
    };
    const onLeave = () => {
      halo.dataset.on = '0';
    };
    window.addEventListener('mousemove', onMove, { passive: true });
    document.documentElement.addEventListener('mouseleave', onLeave);
    return () => {
      window.removeEventListener('mousemove', onMove);
      document.documentElement.removeEventListener('mouseleave', onLeave);
      if (raf) cancelAnimationFrame(raf);
    };
  }, [enabled]);

  if (!enabled) return null;
  return <div ref={ref} className="wt-halo" style={{ position: 'fixed' }} aria-hidden="true" />;
}
