import { useEffect, useRef, useState } from "react";
import { useI18n, usePortfolioContent } from "../i18n";
import {
  createWaterRenderer,
  type WaterRendererController,
} from "../lib/waterRenderer";
import { EffektLogo } from "./EffektLogo";
import { LanguageSwitcher } from "./LanguageSwitcher";

function clamp(value: number, minimum = 0, maximum = 1) {
  return Math.min(maximum, Math.max(minimum, value));
}

function chapterFromProgress(progress: number) {
  if (progress < 0.12 || progress > 0.94) return -1;
  const serviceProgress = clamp((progress - 0.12) / 0.82);
  return Math.min(4, Math.floor(serviceProgress * 5));
}

function prefersReducedMotion() {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function storedPausePreference() {
  if (typeof window === "undefined") return false;
  try {
    return window.sessionStorage.getItem("effekt-water-paused") === "true";
  } catch {
    return false;
  }
}

export function WaterIntro() {
  const { copy, format, display } = useI18n();
  const { disciplines } = usePortfolioContent();
  const sectionRef = useRef<HTMLElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rendererRef = useRef<WaterRendererController | null>(null);
  const progressRef = useRef(0);
  const pointerIdleTimerRef = useRef<number | undefined>(undefined);
  const [activeChapter, setActiveChapter] = useState(-1);
  const [reducedMotion, setReducedMotion] = useState(prefersReducedMotion);
  const [paused, setPaused] = useState(
    () => prefersReducedMotion() || storedPausePreference(),
  );
  const activeChapterRef = useRef(-1);

  useEffect(() => {
    const section = sectionRef.current;
    if (!section) return;

    let frame = 0;

    const update = () => {
      const travel = section.offsetHeight - window.innerHeight;
      const progress =
        travel > 0
          ? clamp(-section.getBoundingClientRect().top / travel)
          : 0;
      const introFade = clamp(1 - progress / 0.13);
      const nextChapter = chapterFromProgress(progress);
      const serviceProgress = clamp((progress - 0.12) / 0.82);
      const outlineProgress = clamp((serviceProgress - 0.1) / 0.8);

      progressRef.current = outlineProgress;
      section.style.setProperty("--water-progress", String(progress));
      section.style.setProperty("--water-intro-fade", String(introFade));
      rendererRef.current?.setProgress(outlineProgress);

      if (nextChapter !== activeChapterRef.current) {
        activeChapterRef.current = nextChapter;
        setActiveChapter(nextChapter);
      }

      frame = 0;
    };

    const requestUpdate = () => {
      if (!frame) frame = window.requestAnimationFrame(update);
    };

    update();
    window.addEventListener("scroll", requestUpdate, { passive: true });
    window.addEventListener("resize", requestUpdate);

    return () => {
      window.removeEventListener("scroll", requestUpdate);
      window.removeEventListener("resize", requestUpdate);
      window.cancelAnimationFrame(frame);
    };
  }, []);

  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const handleChange = (event: MediaQueryListEvent) => {
      setReducedMotion(event.matches);
      if (event.matches) setPaused(true);
    };

    query.addEventListener("change", handleChange);
    return () => query.removeEventListener("change", handleChange);
  }, []);

  useEffect(() => {
    const section = sectionRef.current;
    const stage = stageRef.current;
    const canvas = canvasRef.current;
    if (!section || !stage || !canvas) return;

    try {
      const renderer = createWaterRenderer(canvas, {
        interactionTarget: null,
        maxDpr: 1.5,
        mobileMaxDpr: 1,
        observeVisibility: true,
        respectSaveData: true,
      });
      rendererRef.current = renderer;
      renderer.setProgress(progressRef.current);
      renderer.setPaused(paused);
      section.dataset.waterBackend = renderer.backend;
    } catch (error) {
      section.dataset.waterBackend = "css";
      console.warn("Effekt water renderer is using its CSS fallback.", error);
    }

    return () => {
      rendererRef.current?.destroy();
      rendererRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!reducedMotion) {
      try {
        window.sessionStorage.setItem("effekt-water-paused", String(paused));
      } catch {
        // Storage can be unavailable in privacy-restricted contexts.
      }
    }
    rendererRef.current?.setPaused(paused);
  }, [paused, reducedMotion]);

  useEffect(
    () => () => {
      if (pointerIdleTimerRef.current !== undefined) {
        window.clearTimeout(pointerIdleTimerRef.current);
      }
    },
    [],
  );

  const handlePointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
    if (paused) return;
    const stage = event.currentTarget;
    const bounds = stage.getBoundingClientRect();
    const x = clamp((event.clientX - bounds.left) / bounds.width);
    const y = clamp((event.clientY - bounds.top) / bounds.height);

    stage.style.setProperty("--pointer-x", `${x * 100}%`);
    stage.style.setProperty("--pointer-y", `${y * 100}%`);
    stage.style.setProperty("--pointer-energy", "1");
    rendererRef.current?.setPointer(x, y);

    if (pointerIdleTimerRef.current !== undefined) {
      window.clearTimeout(pointerIdleTimerRef.current);
    }
    pointerIdleTimerRef.current = window.setTimeout(() => {
      stage.style.setProperty("--pointer-energy", "0");
    }, 420);
  };

  const handlePointerLeave = (event: React.PointerEvent<HTMLDivElement>) => {
    if (pointerIdleTimerRef.current !== undefined) {
      window.clearTimeout(pointerIdleTimerRef.current);
    }
    event.currentTarget.style.setProperty("--pointer-energy", "0");
  };

  const handlePointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
    if (paused) return;
    const bounds = event.currentTarget.getBoundingClientRect();
    const x = clamp((event.clientX - bounds.left) / bounds.width);
    const y = clamp((event.clientY - bounds.top) / bounds.height);
    rendererRef.current?.pulse(x, y);
  };

  const togglePaused = () => {
    if (!reducedMotion) setPaused((current) => !current);
  };

  const interactionLabel =
    activeChapter >= 0
      ? format.interactionDiscipline(disciplines[activeChapter].navLabel)
      : copy.water.interactionAll;

  return (
    <section
      className="water-intro"
      ref={sectionRef}
      aria-labelledby="water-intro-title"
    >
      <div
        className="water-intro__stage"
        ref={stageRef}
        onPointerMove={handlePointerMove}
        onPointerDown={handlePointerDown}
        onPointerLeave={handlePointerLeave}
      >
        <div className="water-intro__fallback" aria-hidden="true" />
        <canvas
          className="water-intro__canvas"
          ref={canvasRef}
          aria-hidden="true"
        />

        <header className="water-header">
          <a
            className="water-header__brand"
            href="#top"
            aria-label={copy.navigation.homeAriaLabel}
          >
            <EffektLogo className="effekt-logo" />
          </a>

          <nav
            className="water-header__nav"
            aria-label={copy.navigation.primaryAriaLabel}
          >
            <a href="#portfolio">{copy.navigation.portfolio}</a>
            <a href="#about">{copy.navigation.about}</a>
            <LanguageSwitcher />
            <button
              className="water-intro__control"
              type="button"
              disabled={reducedMotion}
              onClick={togglePaused}
            >
              {reducedMotion
                ? copy.water.motionReduced
                : paused
                  ? copy.water.play
                  : copy.water.pause}
            </button>
          </nav>
        </header>

        <div className="water-intro__opening">
          <p className="eyebrow">{copy.hero.eyebrow}</p>
          <h1 id="water-intro-title">
            {display(copy.hero.titleBeforeEmphasis)}
            <em>{display(copy.hero.titleEmphasis)}</em>
            {display(copy.hero.titleAfterEmphasis)}
          </h1>
          <p className="water-intro__support">{copy.hero.support}</p>
          <div className="water-intro__actions">
            <a className="water-intro__primary-link" href="#portfolio">
              {copy.hero.explore} <span aria-hidden="true">↘</span>
            </a>
            <a className="water-intro__secondary-link" href="#about">
              {copy.hero.about}
            </a>
          </div>
        </div>

        <ol className="water-intro__chapters">
          {disciplines.map((discipline, index) => (
            <li
              className={`water-intro__chapter${
                activeChapter === index ? " is-active" : ""
              }`}
              key={discipline.id}
            >
              <span className="water-intro__chapter-index">
                {discipline.index} / {copy.water.outline}
              </span>
              <h2>{display(discipline.title)}</h2>
              <p>
                {discipline.introduction} {discipline.outline}.
              </p>
            </li>
          ))}
        </ol>

        <p className="water-intro__interaction-note" aria-hidden="true">
          {interactionLabel}
        </p>

        <div className="water-intro__progress" aria-hidden="true">
          {disciplines.map((discipline, index) => (
            <span
              className={
                index === activeChapter
                  ? "is-active"
                  : index < activeChapter
                    ? "is-past"
                    : undefined
              }
              key={discipline.id}
            />
          ))}
        </div>

        <p className="sr-only">
          {copy.water.screenReaderDescription}
        </p>
      </div>
    </section>
  );
}
