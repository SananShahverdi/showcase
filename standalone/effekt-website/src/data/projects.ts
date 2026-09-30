export type DisciplineId =
  | "baths-hammams"
  | "spa-wellness"
  | "saunas"
  | "pools"
  | "systems";

export type MediaLabel = "Site photography" | "Visualization";

export type ProjectStage =
  | "Built work"
  | "Site documentation"
  | "Work in progress"
  | "Final fit-out"
  | "Design study";

export type ProjectImage = {
  src: string;
  alt: string;
  width: number;
  height: number;
  position?: string;
  stage?: ProjectStage;
};

export type Discipline = {
  id: DisciplineId;
  order: number;
  index: string;
  navLabel: string;
  title: string;
  offerings: string[];
  introduction: string;
};

export type Project = {
  slug: string;
  clusterId: string;
  clusterConfidence: number;
  discipline: DisciplineId;
  title: string;
  category: string;
  imagery: MediaLabel;
  stage: ProjectStage;
  description: string;
  materials: string[];
  tone: "mineral" | "night" | "water" | "garden" | "amber" | "cedar";
  images: ProjectImage[];
};

export type SystemsEvidence = {
  id: string;
  clusterId: string;
  discipline: "systems";
  title: string;
  stage: "Built work" | "Work in progress" | "Final fit-out";
  imagery: "Site photography";
  description: string;
  image: ProjectImage;
};

/**
 * Canonical portfolio order.
 *
 * The offering labels describe Effekt's requested service taxonomy. Individual
 * projects below use only the narrower labels that can be supported by the
 * photographed or visualized evidence in the asset catalogue.
 */
export const disciplines: Discipline[] = [
  {
    id: "baths-hammams",
    order: 1,
    index: "01",
    navLabel: "Baths / Hammams",
    title: "Baths & Hammams",
    offerings: ["Turkish baths", "Oriental baths", "Azerbaijani baths"],
    introduction:
      "Domes, heated stone, wash basins and mosaic—bath environments shaped by water, ritual and light.",
  },
  {
    id: "spa-wellness",
    order: 2,
    index: "02",
    navLabel: "Spa / Wellness",
    title: "Spa & Wellness",
    offerings: ["Heat rooms", "Wellness centres", "Massage rooms"],
    introduction:
      "Spaces for warmth, immersion and pause, from treatment-focused interiors to indoor wellness pools.",
  },
  {
    id: "saunas",
    order: 3,
    index: "03",
    navLabel: "Saunas",
    title: "Saunas",
    offerings: ["Dry saunas", "Wet saunas", "Finnish saunas"],
    introduction:
      "Timber-lined thermal rooms composed through tiered seating, heaters, stone, glass and integrated warm light.",
  },
  {
    id: "pools",
    order: 4,
    index: "04",
    navLabel: "Pools",
    title: "Pools",
    offerings: [
      "Hot plunge",
      "Warm plunge",
      "Cold plunge",
      "Indoor pools",
      "Outdoor pools",
    ],
    introduction:
      "Indoor and outdoor pools, plunge basins, integrated spa pools, fountains and custom mosaic surfaces.",
  },
  {
    id: "systems",
    order: 5,
    index: "05",
    navLabel: "Systems",
    title: "Hydraulic & Wet-Room Lighting Systems",
    offerings: [
      "Water circulation",
      "Drainage",
      "Water features",
      "Wet-room lighting",
    ],
    introduction:
      "Selected visible outcomes of integrated water circulation, drainage, water-feature and lighting solutions.",
  },
];

/**
 * Every gallery is a single verified catalogue cluster. Images are never grouped
 * merely because their colour, material, or room type looks similar.
 */
export const projects: Project[] = [
  {
    slug: "blue-gold-hammam",
    clusterId: "P002",
    clusterConfidence: 0.95,
    discipline: "baths-hammams",
    title: "Blue & Gold Hammam",
    category: "Turkish hammam",
    imagery: "Site photography",
    stage: "Final fit-out",
    description:
      "A late-stage hammam interior organized around an octagonal veined-marble table, curved cobalt mosaic seating, pointed alcoves, and a deep blue-and-gold mosaic dome.",
    materials: [
      "Cobalt glass mosaic",
      "Veined marble",
      "Carved limestone",
      "Brass lighting",
    ],
    tone: "mineral",
    images: [
      {
        src: "/photo_16_2026-07-28_18-51-51.jpg",
        alt: "Octagonal veined-marble table facing a cobalt mosaic bench and blue-and-gold pointed alcove in a hammam.",
        width: 622,
        height: 1280,
        position: "center 46%",
      },
      {
        src: "/photo_17_2026-07-28_18-51-51.jpg",
        alt: "Symmetrical hammam view with a pointed mosaic niche, spiral columns, blue seating, and the edge of a marble table.",
        width: 622,
        height: 1280,
      },
      {
        src: "/photo_22_2026-07-28_18-51-51.jpg",
        alt: "Curved cobalt mosaic bench below an illuminated blue, white, and gold alcove framed by carved stone.",
        width: 622,
        height: 1280,
      },
      {
        src: "/photo_25_2026-07-28_18-51-51.jpg",
        alt: "Upward view of a navy and gold mosaic hammam dome surrounded by teal mosaic and carved stone bands.",
        width: 622,
        height: 1280,
      },
    ],
  },
  {
    slug: "blue-mosaic-hammam-study",
    clusterId: "P005",
    clusterConfidence: 0.98,
    discipline: "baths-hammams",
    title: "Blue Mosaic Hammam Study",
    category: "Oriental hammam study",
    imagery: "Visualization",
    stage: "Design study",
    description:
      "A coherent visualization study combining cobalt mosaic benches, carved basins, patterned arches, white marble surfaces, and a gold-accented vaulted ceiling.",
    materials: [
      "Cobalt mosaic",
      "White marble",
      "Carved basins",
      "Brass fixtures",
    ],
    tone: "water",
    images: [
      {
        src: "/photo_68_2026-07-28_18-51-51.jpg",
        alt: "Architectural visualization of a symmetrical blue mosaic hammam with curved seating, carved basins, and patterned arches.",
        width: 768,
        height: 768,
      },
      {
        src: "/photo_54_2026-07-28_18-52-08.jpg",
        alt: "Wide visualization of a blue mosaic hammam with a scalloped mural, twin marble basins, and a veined stone table.",
        width: 1240,
        height: 877,
      },
      {
        src: "/photo_55_2026-07-28_18-52-08.jpg",
        alt: "Side visualization of the same hammam with blue mosaic seating, striped marble floor, folded towels, and twin basins.",
        width: 1280,
        height: 972,
      },
    ],
  },
  {
    slug: "mosaic-wellness-room",
    clusterId: "P049",
    clusterConfidence: 0.5,
    discipline: "spa-wellness",
    title: "Mosaic Wellness Room",
    category: "Indoor wellness room",
    imagery: "Site photography",
    stage: "Site documentation",
    description:
      "A documented indoor wellness room brings together a circular sunken basin, blue mosaic seating, overflow grilles, a central fountain riser, and a marble-topped treatment surface.",
    materials: [
      "Blue glass mosaic",
      "White marble",
      "Overflow grilles",
      "Metal water fitting",
    ],
    tone: "water",
    images: [
      {
        src: "/photo_43_2026-07-28_18-52-08.jpg",
        alt: "High view of an indoor blue mosaic wellness room with a circular basin, tiled seating, overflow grilles, and a marble-topped treatment surface.",
        width: 1280,
        height: 1280,
      },
    ],
  },
  {
    slug: "illuminated-timber-sauna",
    clusterId: "P001",
    clusterConfidence: 0.95,
    discipline: "saunas",
    title: "Illuminated Timber Sauna",
    category: "Timber sauna",
    imagery: "Site photography",
    stage: "Built work",
    description:
      "A completed timber-lined sauna with tiered L-shaped seating, dark geometric inlays, a guarded heater, and warm indirect light integrated behind the benches.",
    materials: [
      "Light timber",
      "Dark timber inlay",
      "Slatted seating",
      "Integrated LED light",
    ],
    tone: "cedar",
    images: [
      {
        src: "/photo_4_2026-07-28_18-51-50.jpg",
        alt: "Front view of a timber sauna bench with a geometric dark-wood backrest and warm indirect lighting.",
        width: 1280,
        height: 960,
      },
      {
        src: "/photo_13_2026-07-28_18-51-51.jpg",
        alt: "Corner view of tiered L-shaped sauna benches with illuminated V-shaped panels, a bucket, and a wooden ladle.",
        width: 960,
        height: 1280,
      },
      {
        src: "/photo_18_2026-07-28_18-51-51.jpg",
        alt: "Detail of a light timber sauna backrest with dark geometric inlay, warm LED strips, and an angled headrest.",
        width: 1280,
        height: 720,
      },
      {
        src: "/photo_20_2026-07-28_18-51-51.jpg",
        alt: "Timber sauna corner with a slatted bench, wooden headrest, dark backrest bands, and a curved light shade.",
        width: 960,
        height: 1280,
      },
    ],
  },
  {
    slug: "pool-after-dark",
    clusterId: "P003",
    clusterConfidence: 0.98,
    discipline: "pools",
    title: "Pool After Dark",
    category: "Outdoor pool",
    imagery: "Site photography",
    stage: "Built work",
    description:
      "A rectangular outdoor pool documented by day and night, where cyan underwater light, a dark timber-toned deck, and globe lamps structure the water's reflections.",
    materials: [
      "Blue mosaic",
      "Pale coping",
      "Timber-toned deck",
      "Underwater lighting",
    ],
    tone: "night",
    images: [
      {
        src: "/photo_15_2026-07-28_18-52-07.jpg",
        alt: "Night view of a cyan-lit rectangular outdoor pool with a dark deck, globe lamps, a brick residence, and a pool pavilion.",
        width: 1280,
        height: 960,
      },
      {
        src: "/photo_16_2026-07-28_18-52-07.jpg",
        alt: "Wide nighttime view along a blue-lit rectangular pool bordered by globe lamps and a covered terrace.",
        width: 1280,
        height: 622,
      },
      {
        src: "/photo_14_2026-07-28_18-52-07.jpg",
        alt: "Daytime view of the same turquoise mosaic pool with a white border, timber-toned deck, and globe lamps.",
        width: 960,
        height: 1280,
      },
    ],
  },
  {
    slug: "fish-scale-mosaic-pool",
    clusterId: "P011",
    clusterConfidence: 0.95,
    discipline: "pools",
    title: "Fish-Scale Mosaic Pool",
    category: "Outdoor pool",
    imagery: "Site photography",
    stage: "Built work",
    description:
      "A curved outdoor pool whose blue-and-white fish-scale mosaic follows the basin geometry around planted edges, pale coping, and stainless-steel water features.",
    materials: [
      "Fish-scale mosaic",
      "Pale stone",
      "Stainless steel",
      "Planted edges",
    ],
    tone: "water",
    images: [
      {
        src: "/photo_35_2026-07-28_18-52-08.jpg",
        alt: "High view of a curved outdoor pool with turquoise fish-scale mosaic, pale coping, and cypress trees.",
        width: 1280,
        height: 960,
      },
      {
        src: "/photo_33_2026-07-28_18-51-51.jpg",
        alt: "Wide view of a fish-scale mosaic pool with a stainless ladder, stone deck, lawn, and palm trees.",
        width: 1280,
        height: 622,
      },
      {
        src: "/photo_54_2026-07-28_18-51-51.jpg",
        alt: "Curved fish-scale mosaic pool around a planted palm island with a stainless-steel cascade feature.",
        width: 1280,
        height: 960,
      },
    ],
  },
  {
    slug: "fountain-garden-pool",
    clusterId: "P004",
    clusterConfidence: 0.95,
    discipline: "pools",
    title: "Fountain Garden Pool",
    category: "Outdoor pool & fountain",
    imagery: "Site photography",
    stage: "Built work",
    description:
      "A freeform turquoise pool extends into a circular basin with a three-tier carved-stone fountain, set within pale paving, lawn, and evergreen planting.",
    materials: [
      "Turquoise mosaic",
      "Carved stone",
      "Pale paving",
      "Garden planting",
    ],
    tone: "garden",
    images: [
      {
        src: "/photo_53_2026-07-28_18-52-08.jpg",
        alt: "High view of a freeform turquoise pool with a circular basin, tiered stone fountain, pale paving, and lawn.",
        width: 1280,
        height: 960,
      },
      {
        src: "/photo_18_2026-07-28_18-52-07.jpg",
        alt: "Installation view of the same curved pool and working tiered fountain with tools and workers around the unfinished deck.",
        width: 720,
        height: 1280,
        stage: "Work in progress",
      },
    ],
  },
];

/**
 * Cross-project capability evidence. These images intentionally remain separate
 * records so that unrelated technical details are not presented as one project.
 */
export const systemsEvidence: SystemsEvidence[] = [
  {
    id: "underwater-lighting",
    clusterId: "P014",
    discipline: "systems",
    title: "Underwater Lighting",
    stage: "Work in progress",
    imagery: "Site photography",
    description:
      "Submerged fixtures and cyan illumination documented in an indoor pool hall during final fit-out.",
    image: {
      src: "/photo_13_2026-07-28_18-52-07.jpg",
      alt: "Indoor pool hall during fit-out with visible underwater light fixtures, overflow grilles, a ladder, and glass walls.",
      width: 1280,
      height: 960,
    },
  },
  {
    id: "pool-fittings-drainage",
    clusterId: "P023",
    discipline: "systems",
    title: "Pool Fittings & Drainage",
    stage: "Work in progress",
    imagery: "Site photography",
    description:
      "Visible wall jets, bottom-drain fittings, coping, and deck protection recorded before the pool was filled.",
    image: {
      src: "/photo_6_2026-07-28_18-52-07.jpg",
      alt: "Empty blue mosaic indoor pool during fit-out with visible wall jets, bottom drains, coping, and a wrapped water feature.",
      width: 1280,
      height: 720,
    },
  },
  {
    id: "water-column-feature",
    clusterId: "P031",
    discipline: "systems",
    title: "Water-Column Feature",
    stage: "Work in progress",
    imagery: "Site photography",
    description:
      "A suspended stainless-steel column delivers a central water cascade into a circular indoor basin.",
    image: {
      src: "/photo_28_2026-07-28_18-51-51.jpg",
      alt: "Circular indoor basin during fit-out beneath a glass dome, with a stainless-steel water column cascading at its centre.",
      width: 622,
      height: 1280,
    },
  },
  {
    id: "overflow-water-feature",
    clusterId: "P026",
    discipline: "systems",
    title: "Overflow & Water Feature",
    stage: "Built work",
    imagery: "Site photography",
    description:
      "A perimeter overflow channel and stainless-steel waterfall spout integrated at the edge of an outdoor pool.",
    image: {
      src: "/photo_10_2026-07-28_18-52-07.jpg",
      alt: "Oval outdoor pool with a perimeter overflow channel, pale stone coping, and a stainless-steel waterfall spout.",
      width: 1280,
      height: 960,
    },
  },
];

export const craftImages: ProjectImage[] = [
  {
    src: "/photo_24_2026-07-28_18-51-51.jpg",
    alt: "A floral mosaic pattern being assembled across the floor of an empty pool.",
    width: 1280,
    height: 622,
  },
  {
    src: "/photo_2_2026-07-28_18-52-07.jpg",
    alt: "Close view of a blue dolphin mosaic panel laid out by hand on a workshop floor.",
    width: 768,
    height: 1024,
  },
];
