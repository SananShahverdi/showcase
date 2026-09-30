import { useEffect, useRef, useState } from "react";
import { EffektLogo } from "./components/EffektLogo";
import { LanguageSwitcher } from "./components/LanguageSwitcher";
import { ResponsiveImage } from "./components/ResponsiveImage";
import { WaterIntro } from "./components/WaterIntro";
import {
  useI18n,
  usePortfolioContent,
  type LocalizedDiscipline,
  type LocalizedProject,
} from "./i18n";

type GalleryState = {
  projectSlug: string;
  imageIndex: number;
} | null;

function useScrollProgress() {
  useEffect(() => {
    let animationFrame = 0;

    const update = () => {
      const scrollable =
        document.documentElement.scrollHeight - window.innerHeight;
      const progress = scrollable > 0 ? window.scrollY / scrollable : 0;

      document.documentElement.style.setProperty(
        "--scroll-progress",
        String(Math.min(1, Math.max(0, progress))),
      );
      animationFrame = 0;
    };

    const requestUpdate = () => {
      if (!animationFrame) {
        animationFrame = window.requestAnimationFrame(update);
      }
    };

    update();
    window.addEventListener("scroll", requestUpdate, { passive: true });
    window.addEventListener("resize", requestUpdate);

    return () => {
      window.removeEventListener("scroll", requestUpdate);
      window.removeEventListener("resize", requestUpdate);
      window.cancelAnimationFrame(animationFrame);
    };
  }, []);
}

function useScrollReveals() {
  useEffect(() => {
    const root = document.documentElement;
    const reducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    const elements = Array.from(
      document.querySelectorAll<HTMLElement>("[data-reveal]"),
    );

    root.classList.add("motion-ready");

    if (reducedMotion || !("IntersectionObserver" in window)) {
      elements.forEach((element) => element.classList.add("is-visible"));
      return () => root.classList.remove("motion-ready");
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      {
        rootMargin: "0px 0px -10% 0px",
        threshold: 0.12,
      },
    );

    elements.forEach((element) => observer.observe(element));

    return () => {
      observer.disconnect();
      root.classList.remove("motion-ready");
    };
  }, []);
}

function Manifesto() {
  const { copy, display } = useI18n();

  return (
    <section className="manifesto" aria-labelledby="manifesto-title">
      <div className="manifesto__label" data-reveal="copy">
        <p className="eyebrow">{copy.manifesto.eyebrow}</p>
        <span>{copy.manifesto.atmosphere}</span>
      </div>

      <div className="manifesto__statement" data-reveal="copy">
        <h2 id="manifesto-title">
          {copy.manifesto.statement.map((line, index) => (
            <span key={line}>
              {display(line)}
              {index < copy.manifesto.statement.length - 1 && <br />}
            </span>
          ))}
        </h2>
      </div>

      <div className="material-legend" data-reveal="copy">
        {copy.manifesto.materials.map((material) => (
          <div key={material.id}>
            <span
              className={`material-legend__swatch material-legend__swatch--${
                material.id === "timber" ? "cedar" : material.id
              }`}
            />
            <p>{material.label}</p>
            <small>{material.detail}</small>
          </div>
        ))}
      </div>
    </section>
  );
}

type ProjectChapterProps = {
  project: LocalizedProject;
  onOpen: (projectSlug: string, imageIndex: number) => void;
};

function ProjectChapter({ project, onOpen }: ProjectChapterProps) {
  const { copy, format, display } = useI18n();
  const cover = project.images[0];
  const secondaryImages = project.images.slice(1, 3);

  return (
    <article
      className="project"
      id={project.slug}
      data-tone={project.tone}
      aria-labelledby={`${project.slug}-title`}
    >
      <div className="project__stratum" aria-hidden="true" />

      <div className="project__inner">
        <header className="project__header" data-reveal="copy">
          <div>
            <p className="eyebrow">{project.category}</p>
            <p
              className="project__cluster"
              aria-label={copy.common.archiveCluster}
            >
              {project.clusterId}
            </p>
          </div>
          <p className="project__format">
            {project.imagery} · {project.stage}
          </p>
        </header>

        <button
          className="project__cover image-button"
          type="button"
          onClick={() => onOpen(project.slug, 0)}
          aria-label={format.openGallery(project.title)}
          data-reveal="image"
        >
          <ResponsiveImage
            image={cover}
            alt=""
            sizes="(max-width: 700px) calc(100vw - 2.5rem), 75vw"
            loading="lazy"
            decoding="async"
          />
          <span className="image-button__action" aria-hidden="true">
            {format.viewGallery(project.images.length)}
          </span>
        </button>

        <div className="project__details" data-reveal="copy">
          <h3 id={`${project.slug}-title`}>{display(project.title)}</h3>
          <p>{project.description}</p>
          <ul
            className="material-tags"
            aria-label={copy.common.visibleMaterials}
          >
            {project.materials.map((material) => (
              <li key={material}>{material}</li>
            ))}
          </ul>
        </div>

        {secondaryImages.length > 0 && (
          <div className="project__secondary" data-reveal="image">
            {secondaryImages.map((image, imageIndex) => (
              <button
                className="image-button image-button--secondary"
                type="button"
                key={image.src}
                onClick={() => onOpen(project.slug, imageIndex + 1)}
                aria-label={format.openImage(
                  imageIndex + 2,
                  project.title,
                )}
              >
                <ResponsiveImage
                  image={image}
                  alt=""
                  sizes="(max-width: 700px) 46vw, 38vw"
                  loading="lazy"
                  decoding="async"
                />
              </button>
            ))}
          </div>
        )}
      </div>
    </article>
  );
}

function DisciplineHeader({
  discipline,
}: {
  discipline: LocalizedDiscipline;
}) {
  const { copy, format, display } = useI18n();

  return (
    <header className="discipline__header" data-reveal="copy">
      <p className="discipline__index">{discipline.index}</p>
      <div>
        <p className="eyebrow">{copy.portfolio.disciplineEyebrow}</p>
        <h2 id={`${discipline.id}-title`}>{display(discipline.title)}</h2>
      </div>
      <div className="discipline__context">
        <p>{discipline.introduction}</p>
        <ul aria-label={format.offerings(discipline.title)}>
          {discipline.offerings.map((offering) => (
            <li key={offering}>{offering}</li>
          ))}
        </ul>
      </div>
    </header>
  );
}

function SystemsCapability() {
  const { copy, display } = useI18n();
  const { systemsEvidence } = usePortfolioContent();

  return (
    <div className="systems-capability">
      <div className="systems-capability__statement" data-reveal="copy">
        <p className="eyebrow">{copy.systemsIntro.eyebrow}</p>
        <h3>{display(copy.systemsIntro.title)}</h3>
        <p>{copy.systemsIntro.description}</p>
      </div>

      <div className="systems-grid">
        {systemsEvidence.map((record, index) => (
          <figure
            className="systems-record"
            data-feature={index === 0 ? "lead" : undefined}
            data-reveal="image"
            key={record.id}
          >
            <div className="systems-record__image">
              <ResponsiveImage
                image={record.image}
                sizes={
                  index === 0
                    ? "(max-width: 700px) calc(100vw - 2.5rem), 66vw"
                    : "(max-width: 700px) calc(100vw - 2.5rem), 34vw"
                }
                loading="lazy"
                decoding="async"
              />
            </div>
            <figcaption>
              <span>{record.clusterId}</span>
              <div>
                <h4>{record.title}</h4>
                <p>{record.description}</p>
              </div>
              <small>{record.stage}</small>
            </figcaption>
          </figure>
        ))}
      </div>
    </div>
  );
}

function Portfolio({
  onOpen,
}: {
  onOpen: (projectSlug: string, imageIndex: number) => void;
}) {
  const { copy, display } = useI18n();
  const { disciplines, projects } = usePortfolioContent();

  return (
    <section className="work portfolio" id="portfolio" aria-labelledby="work-title">
      <div className="work__intro">
        <p className="eyebrow" data-reveal="copy">
          {copy.portfolio.eyebrow}
        </p>
        <h2 id="work-title" data-reveal="copy">
          {display(copy.portfolio.title)}
        </h2>
        <p data-reveal="copy">{copy.portfolio.introduction}</p>
      </div>

      <nav
        className="discipline-index"
        aria-label={copy.portfolio.disciplinesAriaLabel}
      >
        <ol>
          {disciplines.map((discipline) => (
            <li key={discipline.id}>
              <a href={`#${discipline.id}`}>
                <span>{discipline.index}</span>
                {discipline.navLabel}
              </a>
            </li>
          ))}
        </ol>
      </nav>

      <div className="discipline-list">
        {disciplines.map((discipline) => {
          const disciplineProjects = projects.filter(
            (project) => project.discipline === discipline.id,
          );

          return (
            <section
              className="discipline"
              id={discipline.id}
              aria-labelledby={`${discipline.id}-title`}
              key={discipline.id}
            >
              <DisciplineHeader discipline={discipline} />

              {discipline.id === "systems" ? (
                <SystemsCapability />
              ) : (
                <div className="project-list">
                  {disciplineProjects.map((project) => (
                    <ProjectChapter
                      project={project}
                      onOpen={onOpen}
                      key={project.slug}
                    />
                  ))}
                </div>
              )}
            </section>
          );
        })}
      </div>
    </section>
  );
}

function CraftInterlude() {
  const { copy, display } = useI18n();
  const { craftImages } = usePortfolioContent();

  return (
    <section className="craft" aria-labelledby="craft-title">
      <div className="craft__wide" data-reveal="image">
        <ResponsiveImage
          image={craftImages[0]}
          sizes="(max-width: 700px) calc(100vw - 2.5rem), 75vw"
          loading="lazy"
          decoding="async"
        />
      </div>

      <div className="craft__copy" data-reveal="copy">
        <p className="eyebrow">{copy.craft.eyebrow}</p>
        <h2 id="craft-title">{display(copy.craft.title)}</h2>
        <p>{copy.craft.description}</p>
      </div>

      <figure className="craft__detail" data-reveal="image">
        <ResponsiveImage
          image={craftImages[1]}
          sizes="(max-width: 700px) 72vw, 34vw"
          loading="lazy"
          decoding="async"
        />
        <figcaption>{copy.craft.caption}</figcaption>
      </figure>
    </section>
  );
}

function About() {
  const { copy, display } = useI18n();

  return (
    <section className="about" id="about" aria-labelledby="about-title">
      <p className="eyebrow" data-reveal="copy">
        {copy.about.eyebrow}
      </p>
      <div className="about__grid">
        <h2 id="about-title" data-reveal="copy">
          {display(copy.about.titleLineOne)}
          <br />
          {display(copy.about.titleLineTwo)}
        </h2>
        <div className="about__body" data-reveal="copy">
          <p>{copy.about.paragraphOne}</p>
          <p>{copy.about.paragraphTwo}</p>
        </div>
      </div>
    </section>
  );
}

function SiteFooter() {
  const { copy, format } = useI18n();

  return (
    <footer className="site-footer">
      <a
        className="site-footer__brand"
        href="#top"
        aria-label={copy.navigation.backToTopAriaLabel}
      >
        <EffektLogo />
      </a>
      <p>
        {copy.footer.statementLineOne}
        <br />
        {copy.footer.statementLineTwo}
      </p>
      <nav aria-label={copy.navigation.footerAriaLabel}>
        <a href="#portfolio">{copy.navigation.portfolio}</a>
        <a href="#about">{copy.navigation.about}</a>
        <a href="#top">{copy.navigation.backToTop}</a>
        <LanguageSwitcher />
      </nav>
      <small>{format.copyright(new Date().getFullYear())}</small>
    </footer>
  );
}

type GalleryDialogProps = {
  gallery: GalleryState;
  setGallery: React.Dispatch<React.SetStateAction<GalleryState>>;
};

function GalleryDialog({ gallery, setGallery }: GalleryDialogProps) {
  const { copy, display } = useI18n();
  const { projects } = usePortfolioContent();
  const dialogRef = useRef<HTMLDialogElement>(null);
  const currentProject = gallery
    ? projects.find((project) => project.slug === gallery.projectSlug)
    : null;
  const currentImage =
    gallery && currentProject ? currentProject.images[gallery.imageIndex] : null;
  const isGalleryOpen = gallery !== null;

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (isGalleryOpen && !dialog.open) {
      dialog.showModal();
      document.body.classList.add("dialog-open");
    } else if (!isGalleryOpen && dialog.open) {
      dialog.close();
    }

    return () => document.body.classList.remove("dialog-open");
  }, [isGalleryOpen]);

  useEffect(() => {
    if (!gallery || !currentProject || currentProject.images.length < 2) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      event.preventDefault();
      const direction = event.key === "ArrowRight" ? 1 : -1;

      setGallery((current) => {
        if (!current) return current;
        const project = projects.find(
          (candidate) => candidate.slug === current.projectSlug,
        );
        if (!project) return null;

        return {
          ...current,
          imageIndex:
            (current.imageIndex + direction + project.images.length) %
            project.images.length,
        };
      });
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [gallery, currentProject, setGallery]);

  const move = (direction: number) => {
    setGallery((current) => {
      if (!current) return current;
      const project = projects.find(
        (candidate) => candidate.slug === current.projectSlug,
      );
      if (!project) return null;

      return {
        ...current,
        imageIndex:
          (current.imageIndex + direction + project.images.length) %
          project.images.length,
      };
    });
  };

  return (
    <dialog
      className="gallery-dialog"
      ref={dialogRef}
      aria-labelledby="gallery-title"
      onClose={() => {
        document.body.classList.remove("dialog-open");
        setGallery(null);
      }}
      onCancel={() => setGallery(null)}
      onClick={(event) => {
        if (event.target === event.currentTarget) setGallery(null);
      }}
    >
      {gallery && currentProject && currentImage && (
        <div className="gallery-dialog__inner">
          <header className="gallery-dialog__header">
            <div>
              <p>
                {currentProject.category} ·{" "}
                {currentImage.stage ?? currentProject.stage}
              </p>
              <h2 id="gallery-title">{display(currentProject.title)}</h2>
            </div>
            <button
              className="gallery-dialog__close"
              type="button"
              onClick={() => setGallery(null)}
            >
              {copy.gallery.close}
              <span aria-hidden="true">×</span>
            </button>
          </header>

          <div className="gallery-dialog__stage">
            <ResponsiveImage
              key={currentImage.src}
              image={currentImage}
              sizes="100vw"
              decoding="async"
            />
          </div>

          <footer className="gallery-dialog__footer">
            <p className="gallery-dialog__counter" aria-live="polite">
              {gallery.imageIndex + 1} / {currentProject.images.length}
              <span>{currentProject.imagery}</span>
            </p>
            {currentProject.images.length > 1 && (
              <div className="gallery-dialog__controls">
                <button type="button" onClick={() => move(-1)}>
                  ← {copy.gallery.previous}
                </button>
                <button type="button" onClick={() => move(1)}>
                  {copy.gallery.next} →
                </button>
              </div>
            )}
          </footer>
        </div>
      )}
    </dialog>
  );
}

function WaterlineMeter() {
  const { copy } = useI18n();

  return (
    <div className="waterline-meter" aria-hidden="true">
      <span className="waterline-meter__track">
        <span className="waterline-meter__fill" />
      </span>
      <span className="waterline-meter__label">{copy.common.waterHeat}</span>
    </div>
  );
}

export default function App() {
  const { copy } = useI18n();
  const [gallery, setGallery] = useState<GalleryState>(null);

  useScrollProgress();
  useScrollReveals();

  return (
    <>
      <a className="skip-link" href="#main">
        {copy.a11y.skipWaterIntro}
      </a>
      <div id="top" />
      <WaterIntro />
      <main id="main" tabIndex={-1}>
        <Manifesto />
        <Portfolio
          onOpen={(projectSlug, imageIndex) =>
            setGallery({ projectSlug, imageIndex })
          }
        />
        <CraftInterlude />
        <About />
      </main>
      <SiteFooter />
      <WaterlineMeter />
      <GalleryDialog gallery={gallery} setGallery={setGallery} />
    </>
  );
}
