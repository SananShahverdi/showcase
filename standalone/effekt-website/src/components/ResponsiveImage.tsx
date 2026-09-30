import type {
  CSSProperties,
  ImgHTMLAttributes,
} from "react";
import type { ProjectImage } from "../data/projects";

const DERIVATIVE_WIDTHS = [480, 768, 1280] as const;

type ImageLoading = ImgHTMLAttributes<HTMLImageElement>["loading"];
type ImageDecoding = ImgHTMLAttributes<HTMLImageElement>["decoding"];
type ImageFetchPriority =
  ImgHTMLAttributes<HTMLImageElement>["fetchPriority"];

export type ResponsiveImageProps = {
  image: Pick<
    ProjectImage,
    "src" | "alt" | "width" | "height" | "position"
  >;
  alt?: string;
  sizes?: string;
  loading?: ImageLoading;
  decoding?: ImageDecoding;
  fetchPriority?: ImageFetchPriority;
  className?: string;
  style?: CSSProperties;
};

function sourceStem(src: string): string {
  const path = src.split(/[?#]/, 1)[0] ?? src;
  const filename = path.slice(path.lastIndexOf("/") + 1);

  return filename.replace(/\.[^.]+$/, "");
}

function supportedWidths(sourceWidth: number): number[] {
  const exactWidth = Math.max(1, Math.round(sourceWidth));

  return [
    ...new Set([
      ...DERIVATIVE_WIDTHS.filter((width) => width <= exactWidth),
      exactWidth,
    ]),
  ].sort((left, right) => left - right);
}

function derivativeSrcSet(
  stem: string,
  widths: readonly number[],
  format: "avif" | "webp",
): string {
  return widths
    .map(
      (width) =>
        `/optimized/${stem}-w${width}.${format} ${width}w`,
    )
    .join(", ");
}

export function ResponsiveImage({
  image,
  alt,
  sizes,
  loading,
  decoding,
  fetchPriority,
  className,
  style,
}: ResponsiveImageProps) {
  const stem = sourceStem(image.src);
  const widths = supportedWidths(image.width);
  const imageStyle = image.position
    ? { objectPosition: image.position, ...style }
    : style;

  return (
    <picture style={{ display: "contents" }}>
      <source
        type="image/avif"
        srcSet={derivativeSrcSet(stem, widths, "avif")}
        sizes={sizes}
      />
      <source
        type="image/webp"
        srcSet={derivativeSrcSet(stem, widths, "webp")}
        sizes={sizes}
      />
      <img
        src={image.src}
        alt={alt ?? image.alt}
        width={image.width}
        height={image.height}
        sizes={sizes}
        loading={loading}
        decoding={decoding}
        fetchPriority={fetchPriority}
        className={className}
        style={imageStyle}
      />
    </picture>
  );
}
