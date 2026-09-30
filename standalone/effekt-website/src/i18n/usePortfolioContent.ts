import { useMemo } from "react";
import {
  craftImages,
  disciplines,
  projects,
  systemsEvidence,
} from "../data/projects";
import { useI18n } from "./I18nProvider";
import type {
  LocalizedDiscipline,
  LocalizedPortfolioContent,
  LocalizedProject,
  LocalizedProjectImage,
  LocalizedSystemsEvidence,
  ProjectSlug,
  SystemRecordId,
} from "./types";

export function usePortfolioContent(): LocalizedPortfolioContent {
  const { copy } = useI18n();

  return useMemo(() => {
    const localizedDisciplines: LocalizedDiscipline[] = disciplines.map(
      (discipline) => {
        const translation = copy.disciplines[discipline.id];

        return {
          ...discipline,
          ...translation,
          offerings: [...translation.offerings],
        };
      },
    );

    const localizedProjects: LocalizedProject[] = projects.map((project) => {
      const translation = copy.projects[project.slug as ProjectSlug];
      const images: LocalizedProjectImage[] = project.images.map(
        (image, index) => ({
          ...image,
          alt: translation?.imageAlts[index] ?? image.alt,
          stage: image.stage ? copy.common.stages[image.stage] : undefined,
        }),
      );

      return {
        ...project,
        title: translation?.title ?? project.title,
        category: translation?.category ?? project.category,
        imagery: copy.common.mediaLabels[project.imagery],
        stage: copy.common.stages[project.stage],
        description: translation?.description ?? project.description,
        materials: translation
          ? [...translation.materials]
          : [...project.materials],
        images,
      };
    });

    const localizedSystemsEvidence: LocalizedSystemsEvidence[] =
      systemsEvidence.map((record) => {
        const translation = copy.systems[record.id as SystemRecordId];

        return {
          ...record,
          title: translation?.title ?? record.title,
          stage: copy.common.stages[record.stage],
          imagery: copy.common.mediaLabels[record.imagery],
          description: translation?.description ?? record.description,
          image: {
            ...record.image,
            alt: translation?.imageAlt ?? record.image.alt,
            stage: record.image.stage
              ? copy.common.stages[record.image.stage]
              : undefined,
          },
        };
      });

    const localizedCraftImages: LocalizedProjectImage[] = craftImages.map(
      (image, index) => ({
        ...image,
        alt: copy.craft.imageAlts[index] ?? image.alt,
        stage: image.stage ? copy.common.stages[image.stage] : undefined,
      }),
    );

    return {
      disciplines: localizedDisciplines,
      projects: localizedProjects,
      systemsEvidence: localizedSystemsEvidence,
      craftImages: localizedCraftImages,
    };
  }, [copy]);
}

