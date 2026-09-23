/* The AI Guide pointer and its delivery vehicle.
 *
 * Flow per highlight step: the loader drives in along the bottom of the target, raises its
 * boom, tips the cursor out into place, then drives off. The vehicle leaving matters — a
 * machine parked permanently on screen would be exactly the distraction the operator asked
 * us to avoid, so it only appears for the moment of handoff.
 *
 * Nothing here blocks the UI: there is no modal backdrop, Escape always exits, and the
 * dismiss button is always reachable (PRD §23 — guidance must never trap the operator).
 */
import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { Icon } from "../design";
import { useGuide } from "../state/store";
import { LoaderVehicle } from "./LoaderVehicle";
import "./guide.css";

const LOADER_W = 132;
const LOADER_H = 76;

interface Geometry {
  rect: DOMRect;
  loaderX: number;
  loaderY: number;
  pointerX: number;
  pointerY: number;
  tipX: number;
  tipY: number;
  tooltipAbove: boolean;
}

function findTarget(id: string | null): HTMLElement | null {
  if (!id) return null;
  return document.querySelector<HTMLElement>(`[data-guide-id="${id}"]`);
}

function measure(el: HTMLElement): Geometry {
  const rect = el.getBoundingClientRect();
  const groundY = Math.min(rect.bottom + 14, window.innerHeight - 24);
  const parkX = Math.max(12, Math.min(rect.left - 108, window.innerWidth - LOADER_W - 12));
  return {
    rect,
    loaderX: parkX,
    loaderY: groundY - LOADER_H,
    // where the cursor comes to rest: just inside the element, like a real pointer aimed at it
    pointerX: rect.left + Math.min(rect.width * 0.32, 44),
    pointerY: rect.top + rect.height / 2,
    // bucket tip once the boom is raised
    tipX: parkX + 124,
    tipY: groundY - LOADER_H + 2,
    tooltipAbove: rect.bottom + 150 > window.innerHeight,
  };
}

export function GuideLayer() {
  const { plan, stepIndex, phase, enabled, setPhase, advance, stop } = useGuide();
  const navigate = useNavigate();
  const location = useLocation();
  const [geo, setGeo] = useState<Geometry | null>(null);
  const [boom, setBoom] = useState(0);
  const [driving, setDriving] = useState(false);
  const [leaving, setLeaving] = useState(false);
  const timers = useRef<number[]>([]);

  const step = plan[stepIndex];

  const clearTimers = () => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
  };
  const after = (ms: number, fn: () => void) => {
    timers.current.push(window.setTimeout(fn, ms));
  };

  /* Run the current step. */
  useEffect(() => {
    if (!enabled || !step) return;
    clearTimers();

    if (step.action === "navigate") {
      if (step.route && step.route !== "*" && step.route !== location.pathname) navigate(step.route);
      after(step.route && step.route !== location.pathname ? 420 : 60, advance);
      return clearTimers;
    }

    if (step.action === "scroll") {
      findTarget(step.target)?.scrollIntoView({ behavior: "smooth", block: "center" });
      after(520, advance);
      return clearTimers;
    }

    // highlight / explain / tooltip — the delivery beat
    const el = findTarget(step.target);
    if (!el) {
      after(80, advance); // target not on this screen; skip rather than stall
      return clearTimers;
    }

    const g = measure(el);
    setGeo(g);
    setLeaving(false);
    setBoom(0);
    setDriving(true);
    setPhase("delivering", step.message);

    after(1150, () => setDriving(false)); // arrived
    after(1250, () => setBoom(-24)); // raise boom
    after(1850, () => setBoom(-14)); // tip the bucket, cursor rolls out
    after(2500, () => {
      setPhase("waiting", step.message);
      setBoom(0);
      setDriving(true);
      setLeaving(true); // drive off — the pointer stays, the machine does not
    });

    return clearTimers;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, stepIndex, plan.length]);

  /* Keep the highlight glued to the element while the page scrolls or resizes. */
  useEffect(() => {
    if (phase !== "waiting" || !step?.target) return;
    const sync = () => {
      const el = findTarget(step.target);
      if (el) setGeo(measure(el));
    };
    window.addEventListener("scroll", sync, true);
    window.addEventListener("resize", sync);
    return () => {
      window.removeEventListener("scroll", sync, true);
      window.removeEventListener("resize", sync);
    };
  }, [phase, step?.target]);

  /* Escape always gets the operator out. */
  useEffect(() => {
    if (phase === "idle") return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && stop();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [phase, stop]);

  /* Acting on the highlighted control itself is the natural way to continue. */
  useEffect(() => {
    if (phase !== "waiting" || !step?.target) return;
    const el = findTarget(step.target);
    if (!el) return;
    const onClick = () => advance();
    el.addEventListener("click", onClick);
    return () => el.removeEventListener("click", onClick);
  }, [phase, step?.target, advance]);

  useEffect(() => clearTimers, []);

  const active = enabled && phase !== "idle" && !!geo;
  const showVehicle = enabled && phase === "delivering" && !!geo;
  const showPointer = active && (phase === "waiting" || (phase === "delivering" && boom === -14));
  const interactiveTotal = plan.filter((s) => s.waitForUser).length;
  const interactiveIndex = plan.slice(0, stepIndex + 1).filter((s) => s.waitForUser).length;

  return (
    <div className="guide-layer" aria-live="polite">
      {/* highlight ring */}
      <AnimatePresence>
        {active && geo && (
          <motion.div
            key="ring"
            className="guide-ring"
            initial={{ opacity: 0, scale: 1.08 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 1.05 }}
            transition={{ duration: 0.28 }}
            style={{
              left: geo.rect.left - 8,
              top: geo.rect.top - 8,
              width: geo.rect.width + 16,
              height: geo.rect.height + 16,
            }}
          />
        )}
      </AnimatePresence>

      {/* loader driving in, delivering, driving out */}
      <AnimatePresence>
        {showVehicle && geo && (
          <motion.div
            key="loader"
            className="guide-loader"
            initial={{ x: -LOADER_W - 40, y: geo.loaderY, opacity: 0 }}
            animate={{
              x: leaving ? window.innerWidth + 80 : geo.loaderX,
              y: geo.loaderY,
              opacity: 1,
            }}
            exit={{ opacity: 0 }}
            transition={{
              x: { duration: leaving ? 1.0 : 1.15, ease: leaving ? "easeIn" : "easeOut" },
              opacity: { duration: 0.2 },
            }}
          >
            <motion.div
              animate={driving ? { y: [0, -1.2, 0] } : { y: 0 }}
              transition={driving ? { repeat: Infinity, duration: 0.32 } : { duration: 0.2 }}
            >
              <LoaderVehicle boomAngle={boom} driving={driving} bucketLoaded={boom > -10} size={LOADER_W} />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* the pointer itself — tipped out of the bucket, then parked on the target */}
      <AnimatePresence>
        {showPointer && geo && (
          <motion.div
            key="pointer"
            className="guide-pointer"
            initial={{ x: geo.tipX, y: geo.tipY, opacity: 0, rotate: -35, scale: 0.8 }}
            animate={{
              x: geo.pointerX,
              y: geo.pointerY,
              opacity: 1,
              rotate: 0,
              scale: 1,
            }}
            exit={{ opacity: 0, scale: 0.7 }}
            transition={{ type: "spring", stiffness: 140, damping: 13, mass: 0.8 }}
          >
            <motion.div
              animate={{ y: [0, -5, 0] }}
              transition={{ repeat: Infinity, duration: 1.6, ease: "easeInOut" }}
            >
              <svg width="30" height="34" viewBox="0 0 30 34" fill="none">
                <path
                  d="M4 2.2 24.6 15.4 15.6 17.2 20.1 27.4 16 29.4 11.4 19.2 4.6 25.2Z"
                  fill="var(--accent)"
                  stroke="#23262b"
                  strokeWidth="1.6"
                  strokeLinejoin="round"
                />
              </svg>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* instruction */}
      <AnimatePresence>
        {phase === "waiting" && geo && step && (
          <motion.div
            key="tip"
            className="guide-tip"
            initial={{ opacity: 0, y: geo.tooltipAbove ? 8 : -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.24 }}
            style={{
              left: Math.max(12, Math.min(geo.rect.left, window.innerWidth - 332)),
              top: geo.tooltipAbove ? undefined : geo.rect.bottom + 18,
              bottom: geo.tooltipAbove ? window.innerHeight - geo.rect.top + 18 : undefined,
            }}
          >
            <div className="guide-tip__head">
              <span className="guide-tip__badge">
                <Icon name="target" size={13} />
                AI Guide
              </span>
              <button className="guide-tip__close" onClick={stop} aria-label="Dismiss guide">
                <Icon name="close" size={15} />
              </button>
            </div>
            <p className="guide-tip__text">{step.message || "This is the control you need."}</p>
            <div className="guide-tip__foot">
              {/* Count only the beats the operator actually acts on. Navigate and scroll are
                  internal plumbing — showing "step 3 of 3" for a single instruction reads as
                  if they missed two steps. */}
              <span className="guide-tip__step">
                {interactiveTotal > 1 ? `Step ${interactiveIndex} of ${interactiveTotal}` : "AI guide"}
              </span>
              <button className="guide-tip__next" onClick={advance}>
                {stepIndex + 1 >= plan.length ? "Done" : "Next"}
                <Icon name="chevronRight" size={14} />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
