/**
 * Frequency-driven water field used by the Effekt introduction.
 *
 * Scroll progress selects a latent architectural outline:
 * Baths/Hammams → Spas → Saunas → Pools → Hydraulic/Lighting systems.
 * Pointer velocity does the actual "drawing": it temporarily reveals the
 * selected outline as an interference contour, then lets it recede into water.
 *
 * Public pointer coordinates are normalized to the canvas (0..1) with a
 * top-left origin. The renderer never prevents pointer/touch defaults.
 */

export type WaterRendererBackend = "webgl" | "canvas2d";

export interface WaterRendererOptions {
  /** Element receiving passive pointer input. Defaults to the canvas. `null` disables it. */
  interactionTarget?: HTMLElement | Window | null;
  /** Hard device-pixel-ratio ceiling. Defaults to 1.5. */
  maxDpr?: number;
  /** DPR ceiling below 720 CSS px. Defaults to 1.25. */
  mobileMaxDpr?: number;
  /** Override the system reduced-motion preference. */
  reducedMotion?: boolean;
  /** Treat Save-Data as a request for a static field. Defaults to true. */
  respectSaveData?: boolean;
  /** Observe the canvas and stop rendering while it is outside the viewport. */
  observeVisibility?: boolean;
  /** Start the continuous field immediately when motion is allowed. */
  autoStart?: boolean;
}

export interface WaterRendererController {
  readonly backend: WaterRendererBackend;
  /**
   * Selects/morphs the latent architectural outline.
   * 0, .25, .5, .75 and 1 correspond to the five service families.
   */
  setProgress(progress: number): void;
  /**
   * Updates the normalized pointer position. When `energy` is omitted it is
   * inferred from pointer velocity. Energy is clamped to 0..1.
   */
  setPointer(x: number, y: number, energy?: number): void;
  /** Produces a strong, short-lived reveal at a normalized position. */
  pulse(x: number, y: number): void;
  /** Explicitly pauses/resumes the renderer, independently of page visibility. */
  setPaused(paused: boolean): void;
  /** Synchronizes the drawing buffer with the canvas's CSS dimensions. */
  resize(): void;
  /** Draws one frame even when continuous motion is disabled. */
  renderOnce(): void;
  /** Releases observers, event listeners, animation frames, and GPU resources. */
  destroy(): void;
}

type NetworkInformationLike = EventTarget & {
  saveData?: boolean;
};

type NavigatorWithConnection = Navigator & {
  connection?: NetworkInformationLike;
};

type PointerTarget = HTMLElement | Window;

interface WebGLState {
  gl: WebGLRenderingContext;
  program: WebGLProgram;
  vertexBuffer: WebGLBuffer;
  positionLocation: number;
  uniforms: {
    resolution: WebGLUniformLocation | null;
    time: WebGLUniformLocation | null;
    pointer: WebGLUniformLocation | null;
    pointerEnergy: WebGLUniformLocation | null;
    outlineReveal: WebGLUniformLocation | null;
    progress: WebGLUniformLocation | null;
    motion: WebGLUniformLocation | null;
  };
}

const VERTEX_SHADER = `
attribute vec2 a_position;

void main() {
  gl_Position = vec4(a_position, 0.0, 1.0);
}
`;

const FRAGMENT_SHADER = `
precision highp float;

uniform vec2 u_resolution;
uniform float u_time;
uniform vec2 u_pointer;
uniform float u_pointerEnergy;
uniform float u_outlineReveal;
uniform float u_progress;
uniform float u_motion;

#define PI 3.141592653589793

float saturate(float value) {
  return clamp(value, 0.0, 1.0);
}

float sdCircle(vec2 point, float radius) {
  return length(point) - radius;
}

float sdBox(vec2 point, vec2 halfSize) {
  vec2 delta = abs(point) - halfSize;
  return length(max(delta, 0.0)) + min(max(delta.x, delta.y), 0.0);
}

float sdRoundBox(vec2 point, vec2 halfSize, float radius) {
  vec2 delta = abs(point) - halfSize + radius;
  return min(max(delta.x, delta.y), 0.0) + length(max(delta, 0.0)) - radius;
}

float sdSegment(vec2 point, vec2 start, vec2 end) {
  vec2 segment = end - start;
  float projection = clamp(
    dot(point - start, segment) / max(dot(segment, segment), 0.00001),
    0.0,
    1.0
  );
  return length(point - start - segment * projection);
}

float sdOctagon(vec2 point, float radius) {
  const vec3 factors = vec3(
    -0.9238795325,
     0.3826834323,
     0.4142135623
  );
  point = abs(point);
  point -= 2.0 * min(dot(vec2(factors.x, factors.y), point), 0.0)
    * vec2(factors.x, factors.y);
  point -= 2.0 * min(dot(vec2(-factors.x, factors.y), point), 0.0)
    * vec2(-factors.x, factors.y);
  point -= vec2(clamp(point.x, -factors.z * radius, factors.z * radius), radius);
  return length(point) * sign(point.y);
}

// P002-derived: octagonal heated stone, pointed alcoves, and star-dome axes.
float bathOutline(vec2 point) {
  float distanceToOutline = abs(sdOctagon(point, 0.64));
  distanceToOutline = min(distanceToOutline, abs(sdOctagon(point, 0.31)));
  distanceToOutline = min(distanceToOutline, abs(sdCircle(point, 0.09)));

  distanceToOutline = min(distanceToOutline, sdSegment(point, vec2(0.31, 0.0), vec2(0.56, 0.0)));
  distanceToOutline = min(distanceToOutline, sdSegment(point, vec2(-0.31, 0.0), vec2(-0.56, 0.0)));
  distanceToOutline = min(distanceToOutline, sdSegment(point, vec2(0.0, 0.31), vec2(0.0, 0.56)));
  distanceToOutline = min(distanceToOutline, sdSegment(point, vec2(0.0, -0.31), vec2(0.0, -0.56)));
  distanceToOutline = min(distanceToOutline, sdSegment(point, vec2(0.22, 0.22), vec2(0.40, 0.40)));
  distanceToOutline = min(distanceToOutline, sdSegment(point, vec2(-0.22, 0.22), vec2(-0.40, 0.40)));
  distanceToOutline = min(distanceToOutline, sdSegment(point, vec2(0.22, -0.22), vec2(0.40, -0.40)));
  distanceToOutline = min(distanceToOutline, sdSegment(point, vec2(-0.22, -0.22), vec2(-0.40, -0.40)));

  // Four restrained chevrons abstract the pointed wall alcoves.
  distanceToOutline = min(distanceToOutline, sdSegment(point, vec2(-0.13, 0.64), vec2(0.0, 0.78)));
  distanceToOutline = min(distanceToOutline, sdSegment(point, vec2(0.0, 0.78), vec2(0.13, 0.64)));
  distanceToOutline = min(distanceToOutline, sdSegment(point, vec2(-0.13, -0.64), vec2(0.0, -0.78)));
  distanceToOutline = min(distanceToOutline, sdSegment(point, vec2(0.0, -0.78), vec2(0.13, -0.64)));
  distanceToOutline = min(distanceToOutline, sdSegment(point, vec2(0.64, -0.13), vec2(0.78, 0.0)));
  distanceToOutline = min(distanceToOutline, sdSegment(point, vec2(0.78, 0.0), vec2(0.64, 0.13)));
  distanceToOutline = min(distanceToOutline, sdSegment(point, vec2(-0.64, -0.13), vec2(-0.78, 0.0)));
  distanceToOutline = min(distanceToOutline, sdSegment(point, vec2(-0.78, 0.0), vec2(-0.64, 0.13)));

  return distanceToOutline;
}

// A thermal room perimeter, round immersion basin, and treatment-table capsule.
float spaOutline(vec2 point) {
  float distanceToOutline = abs(sdRoundBox(point, vec2(0.72, 0.48), 0.055));

  vec2 basinPoint = point + vec2(0.29, 0.035);
  distanceToOutline = min(distanceToOutline, abs(sdCircle(basinPoint, 0.255)));
  distanceToOutline = min(distanceToOutline, abs(sdCircle(basinPoint, 0.16)));

  vec2 tablePoint = point - vec2(0.31, -0.02);
  float table = abs(sdSegment(
    tablePoint,
    vec2(0.0, -0.215),
    vec2(0.0, 0.215)
  ) - 0.105);
  distanceToOutline = min(distanceToOutline, table);
  distanceToOutline = min(
    distanceToOutline,
    sdSegment(point, vec2(0.0, -0.43), vec2(0.0, 0.43))
  );

  return distanceToOutline;
}

// P001-derived: L-shaped tiered benches, timber slats, and heater enclosure.
float saunaOutline(vec2 point) {
  float distanceToOutline = abs(sdBox(point, vec2(0.72, 0.49)));
  distanceToOutline = min(
    distanceToOutline,
    abs(sdBox(point + vec2(0.0, 0.245), vec2(0.64, 0.17)))
  );
  distanceToOutline = min(
    distanceToOutline,
    abs(sdBox(point - vec2(0.505, 0.02), vec2(0.135, 0.34)))
  );

  distanceToOutline = min(distanceToOutline, sdSegment(point, vec2(-0.62, -0.19), vec2(0.62, -0.19)));
  distanceToOutline = min(distanceToOutline, sdSegment(point, vec2(-0.62, -0.09), vec2(0.62, -0.09)));
  distanceToOutline = min(distanceToOutline, sdSegment(point, vec2(-0.62, 0.01), vec2(0.62, 0.01)));
  distanceToOutline = min(distanceToOutline, sdSegment(point, vec2(-0.62, 0.11), vec2(0.62, 0.11)));
  distanceToOutline = min(distanceToOutline, sdSegment(point, vec2(0.31, -0.29), vec2(0.31, 0.28)));
  distanceToOutline = min(distanceToOutline, sdSegment(point, vec2(0.42, -0.29), vec2(0.42, 0.28)));
  distanceToOutline = min(distanceToOutline, sdSegment(point, vec2(0.53, -0.29), vec2(0.53, 0.28)));

  vec2 heaterPoint = point - vec2(0.48, 0.30);
  distanceToOutline = min(
    distanceToOutline,
    abs(sdRoundBox(heaterPoint, vec2(0.125, 0.105), 0.018))
  );
  distanceToOutline = min(distanceToOutline, abs(sdCircle(heaterPoint + vec2(-0.045, 0.0), 0.025)));
  distanceToOutline = min(distanceToOutline, abs(sdCircle(heaterPoint + vec2(0.045, 0.0), 0.025)));

  return distanceToOutline;
}

// P011/P004-derived: curved fish-scale basin and circular tiered fountain.
float poolOutline(vec2 point) {
  vec2 mainPoint = point + vec2(0.08, 0.0);
  float distanceToOutline = abs(sdRoundBox(mainPoint, vec2(0.66, 0.43), 0.18));
  distanceToOutline = min(
    distanceToOutline,
    abs(sdRoundBox(mainPoint, vec2(0.565, 0.335), 0.135))
  );

  vec2 plungePoint = point - vec2(0.43, 0.16);
  distanceToOutline = min(distanceToOutline, abs(sdCircle(plungePoint, 0.17)));
  distanceToOutline = min(distanceToOutline, abs(sdCircle(plungePoint, 0.105)));
  distanceToOutline = min(distanceToOutline, abs(sdCircle(plungePoint, 0.048)));
  distanceToOutline = min(
    distanceToOutline,
    sdSegment(point, vec2(0.29, 0.0), vec2(0.54, 0.0))
  );

  // Three shallow arcs hint at the scalloped fish-scale mosaic edge.
  distanceToOutline = min(distanceToOutline, abs(sdCircle(point - vec2(-0.44, -0.34), 0.105)));
  distanceToOutline = min(distanceToOutline, abs(sdCircle(point - vec2(-0.22, -0.34), 0.105)));
  distanceToOutline = min(distanceToOutline, abs(sdCircle(point - vec2(0.0, -0.34), 0.105)));

  return distanceToOutline;
}

// P014/P023/P031/P026-derived: fixture nodes, jets/drains, a central
// water-column gesture, and an overflow spout. This is a visual constellation,
// deliberately not a literal engineering plan.
float systemsOutline(vec2 point) {
  float distanceToOutline = abs(sdRoundBox(point, vec2(0.70, 0.48), 0.07));

  // Central water column above a circular basin/drain.
  distanceToOutline = min(distanceToOutline, sdSegment(point, vec2(-0.035, -0.19), vec2(-0.035, 0.35)));
  distanceToOutline = min(distanceToOutline, sdSegment(point, vec2(0.035, -0.19), vec2(0.035, 0.35)));
  distanceToOutline = min(distanceToOutline, abs(sdCircle(point - vec2(0.0, -0.30), 0.14)));
  distanceToOutline = min(distanceToOutline, abs(sdCircle(point - vec2(0.0, -0.30), 0.062)));

  // Fixture, jet, and drain nodes sit independently in the wet-room field.
  distanceToOutline = min(distanceToOutline, abs(sdCircle(point - vec2(-0.48, 0.23), 0.095)));
  distanceToOutline = min(distanceToOutline, abs(sdCircle(point - vec2(-0.49, -0.25), 0.072)));
  distanceToOutline = min(distanceToOutline, abs(sdCircle(point - vec2(0.47, -0.25), 0.072)));
  distanceToOutline = min(distanceToOutline, abs(sdCircle(point - vec2(0.27, 0.20), 0.048)));
  distanceToOutline = min(distanceToOutline, abs(sdCircle(point - vec2(0.40, 0.10), 0.048)));

  // Overflow spout: a small architectural bracket ending in a mouth.
  distanceToOutline = min(distanceToOutline, sdSegment(point, vec2(0.50, 0.43), vec2(0.50, 0.25)));
  distanceToOutline = min(distanceToOutline, sdSegment(point, vec2(0.50, 0.43), vec2(0.65, 0.43)));
  distanceToOutline = min(distanceToOutline, abs(sdCircle(point - vec2(0.50, 0.24), 0.035)));

  // Restrained rays abstract the wet-room lighting emitters.
  distanceToOutline = min(distanceToOutline, sdSegment(point, vec2(-0.48, 0.36), vec2(-0.48, 0.48)));
  distanceToOutline = min(distanceToOutline, sdSegment(point, vec2(-0.59, 0.32), vec2(-0.67, 0.40)));
  distanceToOutline = min(distanceToOutline, sdSegment(point, vec2(-0.37, 0.32), vec2(-0.29, 0.40)));

  return distanceToOutline;
}

float selectedOutline(vec2 point, float progress) {
  float phase = clamp(progress, 0.0, 1.0) * 4.0;

  if (phase < 1.0) {
    return mix(
      bathOutline(point),
      spaOutline(point),
      smoothstep(0.12, 0.88, phase)
    );
  }
  if (phase < 2.0) {
    return mix(
      spaOutline(point),
      saunaOutline(point),
      smoothstep(0.12, 0.88, phase - 1.0)
    );
  }
  if (phase < 3.0) {
    return mix(
      saunaOutline(point),
      poolOutline(point),
      smoothstep(0.12, 0.88, phase - 2.0)
    );
  }
  if (phase < 4.0) {
    return mix(
      poolOutline(point),
      systemsOutline(point),
      smoothstep(0.12, 0.88, phase - 3.0)
    );
  }
  return systemsOutline(point);
}

void main() {
  vec2 fragment = gl_FragCoord.xy;
  float shortSide = max(min(u_resolution.x, u_resolution.y), 1.0);
  vec2 point = (2.0 * fragment - u_resolution) / shortSide;

  vec2 pointerPixel = vec2(
    u_pointer.x * u_resolution.x,
    u_pointer.y * u_resolution.y
  );
  vec2 pointerPoint = (2.0 * pointerPixel - u_resolution) / shortSide;
  vec2 fromPointer = point - pointerPoint;
  float pointerDistance = length(fromPointer);

  float time = u_time * u_motion;
  float energy = saturate(u_pointerEnergy);
  float frequencyLift = 1.0 + energy * 1.9;
  float pointerPhase = (u_pointer.x - 0.5) * 2.4 + (u_pointer.y - 0.5) * 1.7;

  float harmonicA = sin(
    (point.x * 5.6 + point.y * 1.9) * frequencyLift
    + time * 0.72
    + pointerPhase
  );
  float harmonicB = sin(
    (point.x * -2.7 + point.y * 7.2) * (1.0 + energy * 0.8)
    - time * 0.51
    - pointerPhase * 0.7
  );
  float harmonicC = sin(
    length(point + vec2(0.22, -0.14)) * 12.0
    - time * 0.93
    + pointerPhase * 0.35
  );

  float localRipple = sin(
    pointerDistance * (21.0 + energy * 25.0)
    - time * (2.8 + energy * 2.2)
  ) * exp(-pointerDistance * 2.15) * energy;

  vec2 direction = fromPointer / max(pointerDistance, 0.025);
  vec2 warpedPoint = point;
  warpedPoint += vec2(
    harmonicA + harmonicC * 0.42,
    harmonicB - harmonicA * 0.36
  ) * (0.009 + energy * 0.006);
  warpedPoint += direction * localRipple * 0.022;

  float distanceToOutline = selectedOutline(warpedPoint, u_progress);
  float pixel = 2.0 / shortSide;
  float lineWidth = max(pixel * 2.1, 0.0034);
  float contour = 1.0 - smoothstep(lineWidth, lineWidth * 2.45, distanceToOutline);
  float halo = exp(-distanceToOutline * 16.0);

  // The outline is intentionally almost absent at rest. Pointer energy reveals
  // it locally, so the frequencies appear to draw architecture into the water.
  float localReveal = exp(-pointerDistance * pointerDistance * 1.25);
  float reveal = saturate(u_outlineReveal * (0.30 + localReveal * 0.92));
  float dormantTrace = 0.022;
  float interferenceInk = 0.68 + 0.32 * sin(
    warpedPoint.x * 18.0
    - warpedPoint.y * 15.0
    + time * 0.9
    + harmonicB
  );
  float revealedContour = contour
    * (dormantTrace + reveal * (1.0 - dormantTrace))
    * interferenceInk;
  float revealedHalo = halo * reveal * 0.18;

  float interference = (harmonicA + harmonicB + harmonicC) / 3.0;
  float fineWave = sin(
    point.x * 21.0
    + point.y * 10.0
    + harmonicB * 1.6
    + time * 0.42
  );
  float caustic = pow(saturate(0.53 + interference * 0.25 + fineWave * 0.12), 2.2);

  vec3 basalt = vec3(0.043, 0.063, 0.063);
  vec3 slate = vec3(0.114, 0.165, 0.157);
  vec3 waterline = vec3(0.102, 0.357, 0.392);
  vec3 mist = vec3(0.557, 0.792, 0.816);
  vec3 copper = vec3(0.722, 0.482, 0.294);

  vec3 color = mix(basalt, slate, saturate(0.22 + caustic * 0.62));
  color += waterline * caustic * 0.20;
  color = mix(color, mist, saturate(revealedContour * 0.94 + revealedHalo));

  float pointerSheen = exp(-pointerDistance * pointerDistance * 3.4)
    * energy
    * (0.35 + 0.65 * saturate(localRipple * 0.5 + 0.5));
  color = mix(color, copper, pointerSheen * 0.22);

  float vignette = 1.0 - smoothstep(
    0.18,
    1.55,
    length(point * vec2(0.74, 0.82))
  );
  color *= mix(0.69, 1.0, vignette);

  gl_FragColor = vec4(color, 1.0);
}
`;

const clamp01 = (value: number): number => Math.min(1, Math.max(0, value));

const safelyNow = (): number =>
  typeof performance === "undefined" ? Date.now() : performance.now();

class EffektWaterRenderer implements WaterRendererController {
  readonly canvas: HTMLCanvasElement;
  readonly options: Required<
    Pick<
      WaterRendererOptions,
      | "maxDpr"
      | "mobileMaxDpr"
      | "respectSaveData"
      | "observeVisibility"
      | "autoStart"
    >
  > &
    Pick<WaterRendererOptions, "reducedMotion" | "interactionTarget">;

  private webgl: WebGLState | null = null;
  private context2d: CanvasRenderingContext2D | null = null;
  private currentBackend: WaterRendererBackend = "canvas2d";

  private progress = 0;
  private pointerX = 0.5;
  private pointerY = 0.5;
  private pointerEnergy = 0;
  private outlineReveal = 0;
  private lastPointerX = 0.5;
  private lastPointerY = 0.5;
  private lastPointerTime = 0;
  private elapsed = 0;
  private lastFrameTime = 0;

  private explicitlyPaused = false;
  private inViewport = true;
  private documentVisible =
    typeof document === "undefined" ? true : !document.hidden;
  private destroyed = false;
  private animationFrame = 0;

  private readonly resizeObserver: ResizeObserver | null;
  private readonly intersectionObserver: IntersectionObserver | null;
  private readonly motionQuery: MediaQueryList | null;
  private readonly connection: NetworkInformationLike | undefined;
  private readonly pointerTarget: PointerTarget | null;

  constructor(canvas: HTMLCanvasElement, options: WaterRendererOptions = {}) {
    this.canvas = canvas;
    this.options = {
      maxDpr: Math.max(1, options.maxDpr ?? 1.5),
      mobileMaxDpr: Math.max(1, options.mobileMaxDpr ?? 1.25),
      respectSaveData: options.respectSaveData ?? true,
      observeVisibility: options.observeVisibility ?? true,
      autoStart: options.autoStart ?? true,
      reducedMotion: options.reducedMotion,
      interactionTarget: options.interactionTarget,
    };

    this.motionQuery =
      typeof window !== "undefined" && "matchMedia" in window
        ? window.matchMedia("(prefers-reduced-motion: reduce)")
        : null;
    this.connection =
      typeof navigator === "undefined"
        ? undefined
        : (navigator as NavigatorWithConnection).connection;

    this.pointerTarget =
      options.interactionTarget === null
        ? null
        : options.interactionTarget ?? canvas;

    this.initializeContext();

    this.resizeObserver =
      typeof ResizeObserver === "undefined"
        ? null
        : new ResizeObserver(this.handleResize);
    this.resizeObserver?.observe(canvas);

    this.intersectionObserver =
      this.options.observeVisibility && typeof IntersectionObserver !== "undefined"
        ? new IntersectionObserver(this.handleIntersection, {
            rootMargin: "96px",
            threshold: 0,
          })
        : null;
    this.intersectionObserver?.observe(canvas);

    document.addEventListener("visibilitychange", this.handleVisibilityChange);
    window.addEventListener("resize", this.handleResize, { passive: true });
    this.motionQuery?.addEventListener("change", this.handleMotionPolicyChange);
    this.connection?.addEventListener("change", this.handleMotionPolicyChange);

    this.pointerTarget?.addEventListener("pointermove", this.handlePointerMove, {
      passive: true,
    });
    this.pointerTarget?.addEventListener("pointerdown", this.handlePointerDown, {
      passive: true,
    });

    canvas.addEventListener("webglcontextlost", this.handleContextLost);
    canvas.addEventListener("webglcontextrestored", this.handleContextRestored);

    this.resize();
    this.renderOnce();
    this.updateAnimationLoop();
  }

  get backend(): WaterRendererBackend {
    return this.currentBackend;
  }

  setProgress(progress: number): void {
    if (this.destroyed || !Number.isFinite(progress)) {
      return;
    }
    const nextProgress = clamp01(progress);
    if (Math.abs(nextProgress - this.progress) < 0.0001) {
      return;
    }
    this.progress = nextProgress;
    this.requestStaticFrame();
  }

  setPointer(x: number, y: number, energy?: number): void {
    if (
      this.destroyed ||
      !Number.isFinite(x) ||
      !Number.isFinite(y) ||
      (energy !== undefined && !Number.isFinite(energy))
    ) {
      return;
    }

    const nextX = clamp01(x);
    const nextY = clamp01(y);
    const now = safelyNow();
    const elapsedSeconds =
      this.lastPointerTime > 0
        ? Math.max((now - this.lastPointerTime) / 1000, 1 / 240)
        : 1 / 60;
    const distance = Math.hypot(
      nextX - this.lastPointerX,
      nextY - this.lastPointerY,
    );
    const inferredEnergy =
      this.lastPointerTime === 0
        ? 0.2
        : clamp01((distance / elapsedSeconds) * 0.18);
    const nextEnergy = clamp01(energy ?? Math.max(0.11, inferredEnergy));

    this.pointerX = nextX;
    this.pointerY = nextY;
    this.lastPointerX = nextX;
    this.lastPointerY = nextY;
    this.lastPointerTime = now;
    this.pointerEnergy = Math.max(this.pointerEnergy, nextEnergy);
    this.outlineReveal = Math.max(
      this.outlineReveal,
      clamp01(0.08 + nextEnergy * 0.92),
    );

    this.requestStaticFrame();
    this.updateAnimationLoop();
  }

  pulse(x: number, y: number): void {
    if (this.destroyed) {
      return;
    }
    this.setPointer(x, y, 1);
    this.pointerEnergy = 1;
    this.outlineReveal = 1;
    this.requestStaticFrame();
    this.updateAnimationLoop();
  }

  setPaused(paused: boolean): void {
    if (this.destroyed || paused === this.explicitlyPaused) {
      return;
    }
    this.explicitlyPaused = paused;
    if (paused) {
      this.cancelAnimationFrame();
    } else {
      this.renderOnce();
      this.updateAnimationLoop();
    }
  }

  resize(): void {
    if (this.destroyed) {
      return;
    }

    const bounds = this.canvas.getBoundingClientRect();
    const cssWidth = Math.max(1, Math.round(bounds.width || this.canvas.clientWidth));
    const cssHeight = Math.max(
      1,
      Math.round(bounds.height || this.canvas.clientHeight),
    );
    const dprLimit =
      cssWidth < 720 ? this.options.mobileMaxDpr : this.options.maxDpr;
    const dpr = Math.min(window.devicePixelRatio || 1, dprLimit);
    const width = Math.max(1, Math.round(cssWidth * dpr));
    const height = Math.max(1, Math.round(cssHeight * dpr));

    if (this.canvas.width !== width || this.canvas.height !== height) {
      this.canvas.width = width;
      this.canvas.height = height;
      this.webgl?.gl.viewport(0, 0, width, height);
    }

    this.requestStaticFrame();
  }

  renderOnce(): void {
    if (this.destroyed) {
      return;
    }
    this.drawFrame();
  }

  destroy(): void {
    if (this.destroyed) {
      return;
    }
    this.destroyed = true;
    this.cancelAnimationFrame();

    this.resizeObserver?.disconnect();
    this.intersectionObserver?.disconnect();
    document.removeEventListener("visibilitychange", this.handleVisibilityChange);
    window.removeEventListener("resize", this.handleResize);
    this.motionQuery?.removeEventListener("change", this.handleMotionPolicyChange);
    this.connection?.removeEventListener("change", this.handleMotionPolicyChange);

    this.pointerTarget?.removeEventListener("pointermove", this.handlePointerMove);
    this.pointerTarget?.removeEventListener("pointerdown", this.handlePointerDown);
    this.canvas.removeEventListener("webglcontextlost", this.handleContextLost);
    this.canvas.removeEventListener(
      "webglcontextrestored",
      this.handleContextRestored,
    );

    this.releaseWebGLResources();
    this.context2d = null;
  }

  private initializeContext(): void {
    const gl = this.canvas.getContext("webgl", {
      alpha: false,
      antialias: false,
      depth: false,
      stencil: false,
      powerPreference: "high-performance",
      premultipliedAlpha: false,
      preserveDrawingBuffer: false,
    });

    if (gl) {
      try {
        this.webgl = this.createWebGLState(gl);
        this.currentBackend = "webgl";
        return;
      } catch (error) {
        // A second, lower-precision compilation is attempted by createWebGLState.
        // If a driver still rejects it, keep the page functional and quiet.
        console.warn("Effekt water shader could not initialize.", error);
      }
    }

    // If WebGL was unavailable (the common fallback path), the canvas can
    // provide a regular 2D context. Shader compilation failures after a WebGL
    // context is acquired are extremely rare and may leave 2D unavailable.
    this.context2d = this.canvas.getContext("2d", { alpha: false });
    this.currentBackend = "canvas2d";
  }

  private createWebGLState(gl: WebGLRenderingContext): WebGLState {
    let program: WebGLProgram;
    try {
      program = this.linkProgram(gl, VERTEX_SHADER, FRAGMENT_SHADER);
    } catch (highPrecisionError) {
      const mediumPrecisionShader = FRAGMENT_SHADER.replace(
        "precision highp float;",
        "precision mediump float;",
      );
      try {
        program = this.linkProgram(gl, VERTEX_SHADER, mediumPrecisionShader);
      } catch {
        throw highPrecisionError;
      }
    }

    const vertexBuffer = gl.createBuffer();
    if (!vertexBuffer) {
      gl.deleteProgram(program);
      throw new Error("Unable to allocate the water-field vertex buffer.");
    }

    const positionLocation = gl.getAttribLocation(program, "a_position");
    if (positionLocation < 0) {
      gl.deleteBuffer(vertexBuffer);
      gl.deleteProgram(program);
      throw new Error("Water-field position attribute was optimized away.");
    }

    gl.bindBuffer(gl.ARRAY_BUFFER, vertexBuffer);
    gl.bufferData(
      gl.ARRAY_BUFFER,
      new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]),
      gl.STATIC_DRAW,
    );
    gl.clearColor(0.043, 0.063, 0.063, 1);

    return {
      gl,
      program,
      vertexBuffer,
      positionLocation,
      uniforms: {
        resolution: gl.getUniformLocation(program, "u_resolution"),
        time: gl.getUniformLocation(program, "u_time"),
        pointer: gl.getUniformLocation(program, "u_pointer"),
        pointerEnergy: gl.getUniformLocation(program, "u_pointerEnergy"),
        outlineReveal: gl.getUniformLocation(program, "u_outlineReveal"),
        progress: gl.getUniformLocation(program, "u_progress"),
        motion: gl.getUniformLocation(program, "u_motion"),
      },
    };
  }

  private compileShader(
    gl: WebGLRenderingContext,
    type: number,
    source: string,
  ): WebGLShader {
    const shader = gl.createShader(type);
    if (!shader) {
      throw new Error("Unable to allocate a water-field shader.");
    }

    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      const message =
        gl.getShaderInfoLog(shader) ?? "Unknown water-field shader error.";
      gl.deleteShader(shader);
      throw new Error(message);
    }
    return shader;
  }

  private linkProgram(
    gl: WebGLRenderingContext,
    vertexSource: string,
    fragmentSource: string,
  ): WebGLProgram {
    const vertexShader = this.compileShader(gl, gl.VERTEX_SHADER, vertexSource);
    const fragmentShader = this.compileShader(
      gl,
      gl.FRAGMENT_SHADER,
      fragmentSource,
    );
    const program = gl.createProgram();
    if (!program) {
      gl.deleteShader(vertexShader);
      gl.deleteShader(fragmentShader);
      throw new Error("Unable to allocate the water-field shader program.");
    }

    gl.attachShader(program, vertexShader);
    gl.attachShader(program, fragmentShader);
    gl.linkProgram(program);
    gl.deleteShader(vertexShader);
    gl.deleteShader(fragmentShader);

    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      const message =
        gl.getProgramInfoLog(program) ?? "Unknown water-field link error.";
      gl.deleteProgram(program);
      throw new Error(message);
    }
    return program;
  }

  private drawFrame(): void {
    if (this.canvas.width <= 0 || this.canvas.height <= 0) {
      return;
    }

    if (this.webgl) {
      this.drawWebGL();
    } else if (this.context2d) {
      this.drawCanvas2D();
    }
  }

  private drawWebGL(): void {
    const state = this.webgl;
    if (!state || state.gl.isContextLost()) {
      return;
    }

    const { gl, program, vertexBuffer, positionLocation, uniforms } = state;
    gl.viewport(0, 0, this.canvas.width, this.canvas.height);
    gl.useProgram(program);
    gl.bindBuffer(gl.ARRAY_BUFFER, vertexBuffer);
    gl.enableVertexAttribArray(positionLocation);
    gl.vertexAttribPointer(positionLocation, 2, gl.FLOAT, false, 0, 0);
    gl.uniform2f(uniforms.resolution, this.canvas.width, this.canvas.height);
    gl.uniform1f(uniforms.time, this.elapsed);
    // Convert the public top-left origin to WebGL's bottom-left origin.
    gl.uniform2f(uniforms.pointer, this.pointerX, 1 - this.pointerY);
    gl.uniform1f(uniforms.pointerEnergy, this.pointerEnergy);
    gl.uniform1f(uniforms.outlineReveal, this.outlineReveal);
    gl.uniform1f(uniforms.progress, this.progress);
    gl.uniform1f(uniforms.motion, this.motionConstrained ? 0 : 1);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  }

  private drawCanvas2D(): void {
    const context = this.context2d;
    if (!context) {
      return;
    }

    const width = this.canvas.width;
    const height = this.canvas.height;
    const shortSide = Math.min(width, height);
    const time = this.motionConstrained ? 0 : this.elapsed;
    const energy = this.pointerEnergy;

    const gradient = context.createLinearGradient(0, 0, width, height);
    gradient.addColorStop(0, "#0b1010");
    gradient.addColorStop(0.52, "#172421");
    gradient.addColorStop(1, "#0b1010");
    context.fillStyle = gradient;
    context.fillRect(0, 0, width, height);

    context.save();
    context.globalAlpha = 0.15;
    context.strokeStyle = "#2a7279";
    context.lineWidth = Math.max(1, shortSide * 0.0013);

    const waveCount = 18;
    const amplitude = shortSide * (0.011 + energy * 0.012);
    const frequency = 0.012 + energy * 0.011;
    for (let wave = 0; wave < waveCount; wave += 1) {
      const baseY = (height * (wave + 0.5)) / waveCount;
      context.beginPath();
      for (let x = 0; x <= width + 8; x += 8) {
        const pointerDelta = Math.hypot(
          (x / width - this.pointerX) * 1.3,
          baseY / height - this.pointerY,
        );
        const localWave =
          Math.sin(pointerDelta * (24 + energy * 26) - time * 2.6) *
          Math.exp(-pointerDelta * 2.2) *
          energy *
          amplitude;
        const y =
          baseY +
          Math.sin(x * frequency + wave * 0.72 + time * 0.8) * amplitude +
          Math.sin(x * 0.004 - wave * 0.51 - time * 0.47) * amplitude * 0.55 +
          localWave;
        if (x === 0) {
          context.moveTo(x, y);
        } else {
          context.lineTo(x, y);
        }
      }
      context.stroke();
    }
    context.restore();

    const phase = clamp01(this.progress) * 4;
    const currentIndex = Math.min(4, Math.floor(phase));
    const nextIndex = Math.min(4, currentIndex + 1);
    const rawBlend = phase - Math.floor(phase);
    const blend = rawBlend * rawBlend * (3 - 2 * rawBlend);

    const pointerPixelX = this.pointerX * width;
    const pointerPixelY = this.pointerY * height;
    const centerDistance = Math.hypot(
      (pointerPixelX - width / 2) / shortSide,
      (pointerPixelY - height / 2) / shortSide,
    );
    const localReveal = Math.exp(-centerDistance * centerDistance * 1.25);
    const reveal = clamp01(this.outlineReveal * (0.3 + localReveal * 0.92));
    const opacity = 0.018 + reveal * 0.86;

    context.save();
    context.translate(width / 2, height / 2);
    context.scale(shortSide * 0.42, shortSide * 0.42);
    context.lineCap = "round";
    context.lineJoin = "round";
    context.lineWidth = 0.009;
    context.shadowBlur = 0.055;
    context.shadowColor = "rgba(142, 202, 208, 0.55)";

    this.drawFallbackOutline(context, currentIndex, opacity * (1 - blend));
    if (nextIndex !== currentIndex) {
      this.drawFallbackOutline(context, nextIndex, opacity * blend);
    }
    context.restore();
  }

  private drawFallbackOutline(
    context: CanvasRenderingContext2D,
    index: number,
    opacity: number,
  ): void {
    context.save();
    context.globalAlpha = opacity;
    context.strokeStyle = "#8ecad0";

    switch (index) {
      case 0:
        this.drawBathFallback(context);
        break;
      case 1:
        this.drawSpaFallback(context);
        break;
      case 2:
        this.drawSaunaFallback(context);
        break;
      case 3:
        this.drawPoolFallback(context);
        break;
      default:
        this.drawSystemsFallback(context);
        break;
    }
    context.restore();
  }

  private drawBathFallback(context: CanvasRenderingContext2D): void {
    const radius = 1.42;
    context.beginPath();
    for (let side = 0; side < 8; side += 1) {
      const angle = PI_2 * (side / 8) + Math.PI / 8;
      const x = Math.cos(angle) * radius;
      const y = Math.sin(angle) * radius;
      if (side === 0) context.moveTo(x, y);
      else context.lineTo(x, y);
    }
    context.closePath();
    context.stroke();

    context.beginPath();
    for (let side = 0; side < 8; side += 1) {
      const angle = PI_2 * (side / 8) + Math.PI / 8;
      const x = Math.cos(angle) * 0.68;
      const y = Math.sin(angle) * 0.68;
      if (side === 0) context.moveTo(x, y);
      else context.lineTo(x, y);
    }
    context.closePath();
    context.stroke();
    context.beginPath();
    context.arc(0, 0, 0.2, 0, PI_2);
    context.stroke();

    context.beginPath();
    context.moveTo(0.68, 0);
    context.lineTo(1.26, 0);
    context.moveTo(-0.68, 0);
    context.lineTo(-1.26, 0);
    context.moveTo(0, 0.68);
    context.lineTo(0, 1.26);
    context.moveTo(0, -0.68);
    context.lineTo(0, -1.26);
    context.moveTo(0.48, 0.48);
    context.lineTo(0.9, 0.9);
    context.moveTo(-0.48, 0.48);
    context.lineTo(-0.9, 0.9);
    context.moveTo(0.48, -0.48);
    context.lineTo(0.9, -0.9);
    context.moveTo(-0.48, -0.48);
    context.lineTo(-0.9, -0.9);
    context.moveTo(-0.28, -1.42);
    context.lineTo(0, -1.72);
    context.lineTo(0.28, -1.42);
    context.moveTo(-0.28, 1.42);
    context.lineTo(0, 1.72);
    context.lineTo(0.28, 1.42);
    context.stroke();
  }

  private drawSpaFallback(context: CanvasRenderingContext2D): void {
    context.strokeRect(-1.52, -1.02, 3.04, 2.04);
    context.beginPath();
    context.arc(-0.62, 0.08, 0.56, 0, PI_2);
    context.stroke();
    context.beginPath();
    context.arc(-0.62, 0.08, 0.34, 0, PI_2);
    context.stroke();

    context.beginPath();
    context.roundRect(0.46, -0.72, 0.48, 1.44, 0.24);
    context.stroke();
    context.beginPath();
    context.moveTo(0, -0.9);
    context.lineTo(0, 0.9);
    context.stroke();
  }

  private drawSaunaFallback(context: CanvasRenderingContext2D): void {
    context.strokeRect(-1.52, -1.04, 3.04, 2.08);
    context.strokeRect(-1.34, -0.88, 2.68, 0.7);
    context.strokeRect(0.78, -0.62, 0.56, 1.34);
    context.beginPath();
    for (let row = 0; row < 4; row += 1) {
      const y = -0.4 + row * 0.22;
      context.moveTo(-1.3, y);
      context.lineTo(1.3, y);
    }
    for (let column = 0; column < 3; column += 1) {
      const x = 0.7 + column * 0.24;
      context.moveTo(x, -0.58);
      context.lineTo(x, 0.6);
    }
    context.stroke();
    context.strokeRect(0.86, 0.38, 0.44, 0.4);
  }

  private drawPoolFallback(context: CanvasRenderingContext2D): void {
    context.beginPath();
    context.roundRect(-1.5, -0.9, 2.75, 1.8, 0.4);
    context.stroke();
    context.beginPath();
    context.roundRect(-1.3, -0.7, 2.35, 1.4, 0.3);
    context.stroke();
    context.beginPath();
    context.arc(0.98, 0.34, 0.36, 0, PI_2);
    context.stroke();
    context.beginPath();
    context.arc(0.98, 0.34, 0.22, 0, PI_2);
    context.stroke();
    context.beginPath();
    context.arc(0.98, 0.34, 0.1, 0, PI_2);
    context.stroke();

    for (const x of [-0.98, -0.52, -0.06]) {
      context.beginPath();
      context.arc(x, -0.72, 0.22, 0, PI_2);
      context.stroke();
    }
  }

  private drawSystemsFallback(context: CanvasRenderingContext2D): void {
    context.beginPath();
    context.roundRect(-1.5, -1.02, 3, 2.04, 0.14);
    context.stroke();

    // Central water column and basin.
    context.beginPath();
    context.moveTo(-0.08, -0.38);
    context.lineTo(-0.08, 0.74);
    context.moveTo(0.08, -0.38);
    context.lineTo(0.08, 0.74);
    context.stroke();
    context.beginPath();
    context.arc(0, -0.64, 0.3, 0, PI_2);
    context.stroke();
    context.beginPath();
    context.arc(0, -0.64, 0.13, 0, PI_2);
    context.stroke();

    for (const [x, y] of [
      [-1.02, 0.5],
      [-1.04, -0.52],
      [1.0, -0.52],
      [0.56, 0.42],
      [0.86, 0.2],
    ] as Array<[number, number]>) {
      context.beginPath();
      context.arc(x, y, 0.14, 0, PI_2);
      context.stroke();
    }

    // Overflow spout and lighting rays.
    context.beginPath();
    context.moveTo(1.06, 0.92);
    context.lineTo(1.06, 0.5);
    context.moveTo(1.06, 0.92);
    context.lineTo(1.38, 0.92);
    context.moveTo(-1.02, 0.76);
    context.lineTo(-1.02, 1.02);
    context.moveTo(-1.25, 0.7);
    context.lineTo(-1.43, 0.88);
    context.moveTo(-0.79, 0.7);
    context.lineTo(-0.61, 0.88);
    context.stroke();
  }

  private releaseWebGLResources(): void {
    if (!this.webgl) {
      return;
    }
    const { gl, program, vertexBuffer } = this.webgl;
    if (!gl.isContextLost()) {
      gl.deleteBuffer(vertexBuffer);
      gl.deleteProgram(program);
    }
    this.webgl = null;
  }

  private get motionConstrained(): boolean {
    const reducedMotion =
      this.options.reducedMotion ?? this.motionQuery?.matches ?? false;
    const saveData =
      this.options.respectSaveData && this.connection?.saveData === true;
    return reducedMotion || saveData;
  }

  private get shouldAnimate(): boolean {
    return (
      !this.destroyed &&
      this.options.autoStart &&
      !this.explicitlyPaused &&
      this.inViewport &&
      this.documentVisible &&
      !this.motionConstrained
    );
  }

  private requestStaticFrame(): void {
    if (this.destroyed || !this.inViewport || !this.documentVisible) {
      return;
    }
    if (this.motionConstrained || this.explicitlyPaused) {
      this.renderOnce();
    }
  }

  private updateAnimationLoop(): void {
    if (!this.shouldAnimate) {
      this.cancelAnimationFrame();
      return;
    }
    if (this.animationFrame === 0) {
      this.lastFrameTime = safelyNow();
      this.animationFrame = requestAnimationFrame(this.tick);
    }
  }

  private cancelAnimationFrame(): void {
    if (this.animationFrame !== 0) {
      cancelAnimationFrame(this.animationFrame);
      this.animationFrame = 0;
    }
    this.lastFrameTime = 0;
  }

  private readonly tick = (now: number): void => {
    this.animationFrame = 0;
    if (!this.shouldAnimate) {
      return;
    }

    const targetRate = this.canvas.clientWidth < 720 ? 30 : 60;
    const minimumFrameInterval = 1000 / targetRate;
    const sinceLastFrame = now - (this.lastFrameTime || now);
    if (sinceLastFrame < minimumFrameInterval - 1) {
      this.animationFrame = requestAnimationFrame(this.tick);
      return;
    }

    const delta = Math.min(
      Math.max(sinceLastFrame / 1000, 0),
      0.05,
    );
    this.lastFrameTime = now;
    this.elapsed += delta;
    this.pointerEnergy *= Math.exp(-delta * 2.9);
    this.outlineReveal *= Math.exp(-delta * 1.65);

    if (this.pointerEnergy < 0.001) this.pointerEnergy = 0;
    if (this.outlineReveal < 0.001) this.outlineReveal = 0;

    this.drawFrame();
    this.animationFrame = requestAnimationFrame(this.tick);
  };

  private readonly handleResize = (): void => {
    this.resize();
  };

  private readonly handleIntersection = (
    entries: IntersectionObserverEntry[],
  ): void => {
    const entry = entries[entries.length - 1];
    if (!entry) {
      return;
    }
    this.inViewport = entry.isIntersecting;
    if (this.inViewport) {
      this.resize();
      this.renderOnce();
      this.updateAnimationLoop();
    } else {
      this.cancelAnimationFrame();
    }
  };

  private readonly handleVisibilityChange = (): void => {
    this.documentVisible = !document.hidden;
    if (this.documentVisible) {
      this.renderOnce();
      this.updateAnimationLoop();
    } else {
      this.cancelAnimationFrame();
    }
  };

  private readonly handleMotionPolicyChange = (): void => {
    this.renderOnce();
    this.updateAnimationLoop();
  };

  private readonly handlePointerMove = (event: Event): void => {
    if (!(event instanceof PointerEvent)) {
      return;
    }
    const bounds = this.canvas.getBoundingClientRect();
    if (bounds.width <= 0 || bounds.height <= 0) {
      return;
    }
    this.setPointer(
      (event.clientX - bounds.left) / bounds.width,
      (event.clientY - bounds.top) / bounds.height,
    );
  };

  private readonly handlePointerDown = (event: Event): void => {
    if (!(event instanceof PointerEvent)) {
      return;
    }
    const bounds = this.canvas.getBoundingClientRect();
    if (bounds.width <= 0 || bounds.height <= 0) {
      return;
    }
    this.pulse(
      (event.clientX - bounds.left) / bounds.width,
      (event.clientY - bounds.top) / bounds.height,
    );
  };

  private readonly handleContextLost = (event: Event): void => {
    event.preventDefault();
    this.cancelAnimationFrame();
  };

  private readonly handleContextRestored = (): void => {
    if (this.destroyed) {
      return;
    }
    this.releaseWebGLResources();
    const gl = this.canvas.getContext("webgl");
    if (gl) {
      try {
        this.webgl = this.createWebGLState(gl);
        this.currentBackend = "webgl";
      } catch (error) {
        console.warn("Effekt water shader could not be restored.", error);
      }
    }
    this.resize();
    this.renderOnce();
    this.updateAnimationLoop();
  };
}

const PI_2 = Math.PI * 2;

export function createWaterRenderer(
  canvas: HTMLCanvasElement,
  options: WaterRendererOptions = {},
): WaterRendererController {
  return new EffektWaterRenderer(canvas, options);
}
