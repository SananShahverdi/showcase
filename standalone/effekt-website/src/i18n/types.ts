import type {
  Discipline,
  DisciplineId,
  Project,
  ProjectImage,
  SystemsEvidence,
} from "../data/projects";

export const SUPPORTED_LOCALES = ["en", "az", "ru"] as const;

export type Locale = (typeof SUPPORTED_LOCALES)[number];

export type ProjectSlug =
  | "blue-gold-hammam"
  | "blue-mosaic-hammam-study"
  | "mosaic-wellness-room"
  | "illuminated-timber-sauna"
  | "pool-after-dark"
  | "fish-scale-mosaic-pool"
  | "fountain-garden-pool";

export type SystemRecordId =
  | "underwater-lighting"
  | "pool-fittings-drainage"
  | "water-column-feature"
  | "overflow-water-feature";

export type MaterialLegendId = "water" | "mosaic" | "stone" | "timber";

export type LocalizedDisciplineCopy = {
  navLabel: string;
  title: string;
  offerings: readonly string[];
  introduction: string;
  outline: string;
};

export type LocalizedProjectCopy = {
  title: string;
  category: string;
  description: string;
  materials: readonly string[];
  imageAlts: readonly string[];
};

export type LocalizedSystemCopy = {
  title: string;
  description: string;
  imageAlt: string;
};

export type TranslationDictionary = {
  meta: {
    title: string;
    description: string;
  };
  localeSwitcher: {
    label: string;
    ariaLabel: string;
  };
  navigation: {
    primaryAriaLabel: string;
    footerAriaLabel: string;
    portfolio: string;
    about: string;
    backToTop: string;
    homeAriaLabel: string;
    backToTopAriaLabel: string;
  };
  hero: {
    eyebrow: string;
    titleBeforeEmphasis: string;
    titleEmphasis: string;
    titleAfterEmphasis: string;
    support: string;
    explore: string;
    about: string;
  };
  water: {
    outline: string;
    motionReduced: string;
    play: string;
    pause: string;
    interactionAll: string;
    interactionDiscipline: string;
    screenReaderDescription: string;
  };
  manifesto: {
    eyebrow: string;
    atmosphere: string;
    statement: readonly [string, string, string];
    materials: readonly {
      id: MaterialLegendId;
      label: string;
      detail: string;
    }[];
  };
  portfolio: {
    eyebrow: string;
    title: string;
    introduction: string;
    disciplinesAriaLabel: string;
    disciplineEyebrow: string;
  };
  systemsIntro: {
    eyebrow: string;
    title: string;
    description: string;
  };
  craft: {
    eyebrow: string;
    title: string;
    description: string;
    caption: string;
    imageAlts: readonly [string, string];
  };
  about: {
    eyebrow: string;
    titleLineOne: string;
    titleLineTwo: string;
    paragraphOne: string;
    paragraphTwo: string;
  };
  footer: {
    statementLineOne: string;
    statementLineTwo: string;
    copyright: string;
  };
  gallery: {
    close: string;
    previous: string;
    next: string;
    viewGallery: string;
  };
  common: {
    archiveCluster: string;
    visibleMaterials: string;
    waterHeat: string;
    mediaLabels: {
      "Site photography": string;
      Visualization: string;
    };
    stages: {
      "Built work": string;
      "Site documentation": string;
      "Work in progress": string;
      "Final fit-out": string;
      "Design study": string;
    };
  };
  a11y: {
    skipWaterIntro: string;
    openGallery: string;
    openImage: string;
    offerings: string;
  };
  disciplines: Record<DisciplineId, LocalizedDisciplineCopy>;
  projects: Record<ProjectSlug, LocalizedProjectCopy>;
  systems: Record<SystemRecordId, LocalizedSystemCopy>;
};

export type I18nFormatters = {
  openGallery: (title: string) => string;
  openImage: (index: number, title: string) => string;
  offerings: (title: string) => string;
  interactionDiscipline: (label: string) => string;
  viewGallery: (count: number) => string;
  copyright: (year: number) => string;
};

export type LocalizedProjectImage = Omit<ProjectImage, "stage"> & {
  stage?: string;
};

export type LocalizedDiscipline = Omit<
  Discipline,
  "navLabel" | "title" | "offerings" | "introduction"
> & {
  navLabel: string;
  title: string;
  offerings: readonly string[];
  introduction: string;
  outline: string;
};

export type LocalizedProject = Omit<
  Project,
  "title" | "category" | "imagery" | "stage" | "description" | "materials" | "images"
> & {
  title: string;
  category: string;
  imagery: string;
  stage: string;
  description: string;
  materials: readonly string[];
  images: LocalizedProjectImage[];
};

export type LocalizedSystemsEvidence = Omit<
  SystemsEvidence,
  "title" | "stage" | "imagery" | "description" | "image"
> & {
  title: string;
  stage: string;
  imagery: string;
  description: string;
  image: LocalizedProjectImage;
};

export type LocalizedPortfolioContent = {
  disciplines: LocalizedDiscipline[];
  projects: LocalizedProject[];
  systemsEvidence: LocalizedSystemsEvidence[];
  craftImages: LocalizedProjectImage[];
};
