// Hand-rolled animated speedometer ("accelerometer") gauge — shared by the
// report cards and the breakdown modal so both animate identically. No external
// chart library. Returns the SVG plus an animate() that sweeps the needle + arc
// and counts the number up; call animate() on a fresh frame each time you want
// it to re-play.

import { mosTier } from "./api";

export function speedometer(
  value: number | null,
  opts: { size?: number; className?: string } = {},
): { svg: SVGSVGElement; animate: () => void } {
  const v = value === null ? 0 : Math.max(0, Math.min(100, value));
  const size = opts.size ?? 220;
  const color = mosTier(value).color;
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", "0 0 200 128");
  svg.setAttribute("width", String(size));
  svg.setAttribute("class", "spdo" + (opts.className ? ` ${opts.className}` : ""));

  const ARC = "M 18,108 A 90,90 0 0 1 182,108"; // ~180° arc, length ≈ 282.7
  const LEN = 282.7;
  const strokeW = size < 130 ? "16" : "13";

  const track = document.createElementNS(ns, "path");
  track.setAttribute("d", ARC);
  track.setAttribute("fill", "none");
  track.setAttribute("stroke", "rgba(255,255,255,.08)");
  track.setAttribute("stroke-width", strokeW);
  track.setAttribute("stroke-linecap", "round");
  svg.appendChild(track);

  const fill = document.createElementNS(ns, "path");
  fill.setAttribute("d", ARC);
  fill.setAttribute("fill", "none");
  fill.setAttribute("stroke", color);
  fill.setAttribute("stroke-width", strokeW);
  fill.setAttribute("stroke-linecap", "round");
  fill.setAttribute("stroke-dasharray", String(LEN));
  fill.setAttribute("stroke-dashoffset", String(LEN));
  svg.appendChild(fill);

  const needle = document.createElementNS(ns, "line");
  needle.setAttribute("x1", "100");
  needle.setAttribute("y1", "108");
  needle.setAttribute("x2", "100");
  needle.setAttribute("y2", "40");
  needle.setAttribute("stroke", color);
  needle.setAttribute("stroke-width", "3.5");
  needle.setAttribute("stroke-linecap", "round");
  needle.style.transformOrigin = "100px 108px";
  needle.style.transform = "rotate(-90deg)";
  svg.appendChild(needle);

  const hub = document.createElementNS(ns, "circle");
  hub.setAttribute("cx", "100");
  hub.setAttribute("cy", "108");
  hub.setAttribute("r", "6");
  hub.setAttribute("fill", color);
  svg.appendChild(hub);

  const label = document.createElementNS(ns, "text");
  label.setAttribute("x", "100");
  label.setAttribute("y", "99");
  label.setAttribute("text-anchor", "middle");
  label.setAttribute("class", "spdo-num");
  label.textContent = "0";
  svg.appendChild(label);

  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const animate = () => {
    const targetDeg = (v / 100) * 180 - 90;
    const targetOff = LEN * (1 - v / 100);
    if (reduce) {
      needle.style.transform = `rotate(${targetDeg}deg)`;
      fill.setAttribute("stroke-dashoffset", String(targetOff));
      label.textContent = value === null ? "—" : String(Math.round(v));
      return;
    }
    // reset then animate, so repeated opens re-play
    needle.style.transition = "none";
    fill.style.transition = "none";
    needle.style.transform = "rotate(-90deg)";
    fill.setAttribute("stroke-dashoffset", String(LEN));
    requestAnimationFrame(() => {
      needle.style.transition = "transform 1.15s cubic-bezier(.2,.75,.2,1)";
      fill.style.transition = "stroke-dashoffset 1.15s cubic-bezier(.2,.75,.2,1)";
      needle.style.transform = `rotate(${targetDeg}deg)`;
      fill.setAttribute("stroke-dashoffset", String(targetOff));
    });
    if (value === null) {
      label.textContent = "—";
      return;
    }
    let n = 0;
    const step = Math.max(1, Math.round(v / 42));
    const timer = setInterval(() => {
      n += step;
      if (n >= v) {
        n = Math.round(v);
        clearInterval(timer);
      }
      label.textContent = String(n);
    }, 26);
  };

  return { svg, animate };
}
