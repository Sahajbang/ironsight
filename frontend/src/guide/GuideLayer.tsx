/* The AI Guide pointer and its delivery vehicle.
 *
 * The pointer is ONE persistent element for the whole session. Its position is a pair of
 * springs, which is what lets the same object do two different jobs without ever popping
 * out of existence:
 *
 *   companion mode — no walkthrough running, so the springs chase the operator's real
 *   cursor at an offset. It trails slightly behind, like something riding along with you
 *   rather than something stuck to the mouse.
 *
 *   guiding mode — a walkthrough is running, so the springs chase the current target. The
 *   pointer physically travels there, waits while the operator acts, then travels to the
 *   next control. It never disappears between steps.
 *
 * The loader only appears when the guide is switched on: it drives in, tips the pointer out
 * and leaves. A machine parked permanently on screen would be the distraction we were asked
 * to avoid, and re-running the delivery on every step would get old fast.
 */
import { AnimatePresence, motion, useMotionValue, useSpring } from "framer-motion";
import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { Icon } from "../design";
import { useGuide } from "../state/store";
import { LoaderVehicle } from "./LoaderVehicle";
import "./guide.css";

const LOADER_W = 132;
const COMPANION_OFFSET = { x: 26, y: 24 };

interface Rect {
  left: number;
  top: number;
  width: number;
  height: number;
  bottom: number;
  right: number;
}

const findTarget = (id: string | null | undefined) =>
  id ? document.querySelector<HTMLElement>(`[data-guide-id="${id}"]`) : null;

function rectOf(el: HTMLElement): Rect {
  const r = el.getBoundingClientRect();
  return { left: r.left, top: r.top, width: r.width, height: r.height, bottom: r.bottom, right: r.right };
}

export function GuideLayer() {
  const { enabled, plan, stepIndex, advance, stop } = useGuide();
  const navigate = useNavigate();
  const location = useLocation();

  const [delivering, setDelivering] = useState(false);
  const [pointerAlive, setPointerAlive] = useState(false);
  const [loaderX, setLoaderX] = useState(-LOADER_W - 40);
  const [boom, setBoom] = useState(0);
  const [driving, setDriving] = useState(false);
  const [target, setTarget] = useState<Rect | null>(null);

  const timers = useRef<number[]>([]);
  const clearTimers = () => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
  };
  const after = useCallback((ms: number, fn: () => void) => {
    timers.current.push(window.setTimeout(fn, ms));
  }, []);

  const step = plan[stepIndex];
  const guiding = enabled && !!step && step.action !== "navigate" && step.action !== "scroll";

  /* ---- the pointer's position: two springs, fed either by the mouse or by a target ---- */
  const px = useMotionValue(typeof window !== "undefined" ? window.innerWidth / 2 : 0);
  const py = useMotionValue(typeof window !== "undefined" ? window.innerHeight / 2 : 0);
  const sx = useSpring(px, { stiffness: 110, damping: 17, mass: 0.75 });
  const sy = useSpring(py, { stiffness: 110, damping: 17, mass: 0.75 });

  /* Companion mode: trail the operator's cursor. */
  useEffect(() => {
    if (!enabled || !pointerAlive || guiding) return;
    const onMove = (e: MouseEvent) => {
      px.set(e.clientX + COMPANION_OFFSET.x);
      py.set(e.clientY + COMPANION_OFFSET.y);
    };
    window.addEventListener("mousemove", onMove);
    return () => window.removeEventListener("mousemove", onMove);
  }, [enabled, pointerAlive, guiding, px, py]);

  /* Guiding mode: park on the current target. */
  useEffect(() => {
    if (!guiding || !target) return;
    px.set(target.left + Math.min(target.width * 0.3, 42));
    py.set(target.top + target.height / 2);
  }, [guiding, target, px, py]);

  /* ---- delivery: only when the switch is turned on ---- */
  useEffect(() => {
    clearTimers();
    if (!enabled) {
      setPointerAlive(false);
      setDelivering(false);
      return;
    }
    if (pointerAlive) return;

    const parkX = Math.max(24, window.innerWidth / 2 - LOADER_W);
    setLoaderX(-LOADER_W - 40);
    setDelivering(true);
    setDriving(true);
    setBoom(0);
    after(30, () => setLoaderX(parkX));
    after(1200, () => setDriving(false));
    after(1300, () => setBoom(-24));
    after(1850, () => {
      // pointer tips out of the bucket into the middle of the view, then takes over
      px.jump(parkX + 118);
      py.jump(window.innerHeight / 2);
      setPointerAlive(true);
      setBoom(-12);
    });
    after(2400, () => {
      setBoom(0);
      setDriving(true);
      setLoaderX(window.innerWidth + 120);
    });
    after(3500, () => setDelivering(false));
    return clearTimers;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled]);

  /* ---- run the plan: navigate and scroll auto-advance, highlight waits ---- */
  useEffect(() => {
    if (!enabled || !step) return;
    if (step.action === "navigate") {
      const needsMove = step.route && step.route !== "*" && step.route !== location.pathname;
      if (needsMove) navigate(step.route!);
      const id = window.setTimeout(advance, needsMove ? 420 : 60);
      return () => clearTimeout(id);
    }
    if (step.action === "scroll") {
      findTarget(step.target)?.scrollIntoView({ behavior: "smooth", block: "center" });
      const id = window.setTimeout(advance, 480);
      return () => clearTimeout(id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, stepIndex, plan.length]);

  /* Track the current target. Polled, because a step often points at something that only
     exists after the previous step was acted on — the incident form appears only once the
     operator has pressed the button the step before it highlighted. */
  useEffect(() => {
    if (!guiding) {
      setTarget(null);
      return;
    }
    const sync = () => {
      const el = findTarget(step?.target);
      setTarget(el ? rectOf(el) : null);
    };
    sync();
    const poll = window.setInterval(sync, 220);
    window.addEventListener("scroll", sync, true);
    window.addEventListener("resize", sync);
    return () => {
      clearInterval(poll);
      window.removeEventListener("scroll", sync, true);
      window.removeEventListener("resize", sync);
    };
  }, [guiding, step?.target]);

  /* Acting on the highlighted control is the natural way to move on. */
  useEffect(() => {
    if (!guiding || !step?.target) return;
    const el = findTarget(step.target);
    if (!el) return;
    const onClick = () => window.setTimeout(advance, 260);
    el.addEventListener("click", onClick);
    return () => el.removeEventListener("click", onClick);
  }, [guiding, step?.target, target, advance]);

  /* Escape always gets the operator out of a walkthrough. */
  useEffect(() => {
    if (!guiding) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && stop();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [guiding, stop]);

  useEffect(() => clearTimers, []);

  const totalSteps = plan.filter((s) => s.waitForUser).length;
  const currentStep = plan.slice(0, stepIndex + 1).filter((s) => s.waitForUser).length;
  const waitingForTarget = guiding && !target;
  const tipAbove = target ? target.bottom + 170 > window.innerHeight : false;

  return (
    <div className="guide-layer" aria-live="polite">
      {/* highlight ring */}
      <AnimatePresence>
        {guiding && target && (
          <motion.div
            key="ring"
            className="guide-ring"
            initial={{ opacity: 0, scale: 1.08 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 1.05 }}
            transition={{ duration: 0.26 }}
            style={{
              left: target.left - 8,
              top: target.top - 8,
              width: target.width + 16,
              height: target.height + 16,
            }}
          />
        )}
      </AnimatePresence>

      {/* the loader — on arrival only */}
      <AnimatePresence>
        {delivering && (
          <motion.div
            key="loader"
            className="guide-loader"
            initial={{ opacity: 0 }}
            animate={{ x: loaderX, y: window.innerHeight / 2 + 34, opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ x: { duration: 1.15, ease: driving ? "easeOut" : "easeIn" }, opacity: { duration: 0.25 } }}
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

      {/* the pointer — one element, alive for as long as the guide is on */}
      <AnimatePresence>
        {enabled && pointerAlive && (
          <motion.div
            key="pointer"
            className="guide-pointer"
            style={{ x: sx, y: sy }}
            initial={{ opacity: 0, scale: 0.6 }}
            animate={{ opacity: 1, scale: guiding ? 1 : 0.82 }}
            exit={{ opacity: 0, scale: 0.5 }}
            transition={{ duration: 0.3 }}
          >
            <motion.div
              animate={guiding ? { y: [0, -5, 0] } : { y: 0 }}
              transition={guiding ? { repeat: Infinity, duration: 1.6, ease: "easeInOut" } : { duration: 0.2 }}
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

      {/* instruction card */}
      <AnimatePresence>
        {guiding && step && (
          <motion.div
            key="tip"
            className="guide-tip"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 6 }}
            transition={{ duration: 0.22 }}
            style={
              target
                ? {
                    left: Math.max(12, Math.min(target.left, window.innerWidth - 344)),
                    top: tipAbove ? undefined : target.bottom + 18,
                    bottom: tipAbove ? window.innerHeight - target.top + 18 : undefined,
                  }
                : { left: 24, bottom: 24 }
            }
          >
            <div className="guide-tip__head">
              <span className="guide-tip__badge">
                <Icon name="target" size={13} />
                AI Guide
              </span>
              <button className="guide-tip__close" onClick={stop} aria-label="Exit walkthrough">
                <Icon name="close" size={15} />
              </button>
            </div>

            <p className="guide-tip__text">
              {waitingForTarget
                ? "Waiting for that control to appear — carry on with the step above."
                : step.message || "This is the control you need."}
            </p>

            {totalSteps > 1 && (
              <div className="guide-tip__dots" aria-hidden>
                {Array.from({ length: totalSteps }).map((_, i) => (
                  <span key={i} className="guide-tip__dot" data-done={i < currentStep - 1} data-now={i === currentStep - 1} />
                ))}
              </div>
            )}

            <div className="guide-tip__foot">
              <span className="guide-tip__step">
                {totalSteps > 1 ? `Step ${currentStep} of ${totalSteps}` : "AI guide"}
              </span>
              <button className="guide-tip__next" onClick={advance}>
                {currentStep >= totalSteps ? "Done" : "Next"}
                <Icon name="chevronRight" size={14} />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
