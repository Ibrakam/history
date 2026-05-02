import { useEffect, useRef } from "react";

import { VISUAL_MODES } from "../theme";
import type {
  ArtifactCard,
  ImageSlot,
  LessonLayout,
  LessonSection,
  MediaAsset,
  PersonCard,
  VisualMode,
} from "../types";

type Props = {
  title: string;
  heroSubtitle: string;
  visualMode: VisualMode;
  layout: LessonLayout | null;
  lessonHtml?: string;
  renderMode?: "preview" | "public";
  onEditSlot?: (slotId: string) => void;
};

function useScrollReveal(enabled: boolean) {
  const containerRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!enabled || !containerRef.current) return;

    const targets = containerRef.current.querySelectorAll(".scroll-reveal");
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
            observer.unobserve(entry.target);
          }
        }
      },
      { threshold: 0.12 },
    );

    for (const target of targets) {
      observer.observe(target);
    }

    return () => observer.disconnect();
  }, [enabled]);

  return containerRef;
}

function assetCaption(asset: MediaAsset | null | undefined) {
  if (!asset || asset.provider === "demo") {
    return "";
  }
  return asset.title;
}

function MediaFigure({
  asset,
  className,
  caption,
  slotId,
  onEdit,
}: {
  asset: MediaAsset | null | undefined;
  className?: string;
  caption?: string;
  slotId?: string | null;
  onEdit?: (slotId: string) => void;
}) {
  const editable = Boolean(onEdit && slotId);
  return (
    <figure className={`${className ?? "media-figure"}${editable ? " media-editable" : ""}`}>
      {asset ? (
        <img src={asset.imageUrl} alt={asset.alt || asset.title} />
      ) : (
        <div className="media-placeholder">Исторический визуал</div>
      )}
      {editable ? (
        <button
          type="button"
          className="media-edit-button"
          onClick={(event) => {
            event.stopPropagation();
            event.preventDefault();
            if (slotId && onEdit) onEdit(slotId);
          }}
        >
          <span aria-hidden="true">⤓</span> Сменить фото
        </button>
      ) : null}
      {caption ? <figcaption className="media-caption">{caption}</figcaption> : null}
    </figure>
  );
}

function SectionIntro({ label, section }: { label: string; section: LessonSection }) {
  return (
    <div className="section-copy">
      <span className="section-kicker">{label}</span>
      <h2>{section.title}</h2>
      {section.lead ? <p className="section-lead">{section.lead}</p> : null}
    </div>
  );
}

function SectionNarrative({
  section,
  slot,
  revealClass = "",
  onEditSlot,
}: {
  section: LessonSection;
  slot: ImageSlot | undefined;
  revealClass?: string;
  onEditSlot?: (slotId: string) => void;
}) {
  const asset = slot?.selectedAsset;
  return (
    <section className={`visual-section narrative-section${revealClass}`}>
      <div className="section-shell section-shell-split">
        <div className="section-story">
          <SectionIntro label="Контекст" section={section} />
          <div className="rich-text">
            {section.body.map((paragraph, index) => (
              <p key={`${section.id}-${index}`}>{paragraph}</p>
            ))}
          </div>
        </div>

        <div className="section-stage">
          <MediaFigure
            asset={asset}
            className="section-image narrative-image"
            caption={assetCaption(asset)}
            slotId={slot?.slotId}
            onEdit={onEditSlot}
          />
          <div className="section-side-note">
            <span>Визуальный фрагмент</span>
            <strong>{asset?.title || section.title}</strong>
          </div>
        </div>
      </div>
    </section>
  );
}

function SectionTimeline({
  section,
  slot,
  revealClass = "",
  onEditSlot,
}: {
  section: LessonSection;
  slot: ImageSlot | undefined;
  revealClass?: string;
  onEditSlot?: (slotId: string) => void;
}) {
  const asset = slot?.selectedAsset;
  return (
    <section className={`visual-section timeline-section${revealClass}`}>
      <SectionIntro label="Хронология" section={section} />
      <div className="timeline-layout">
        <MediaFigure
          asset={asset}
          className="timeline-figure"
          caption={assetCaption(asset)}
          slotId={slot?.slotId}
          onEdit={onEditSlot}
        />
        <div className="timeline-grid">
          {section.timelineItems.map((item) => (
            <article key={`${section.id}-${item.year}-${item.title}`} className="timeline-card">
              <div className="timeline-marker" />
              <div className="timeline-year">{item.year}</div>
              <h3>{item.title}</h3>
              <p>{item.description}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function PersonTile({
  card,
  slot,
  onEditSlot,
}: {
  card: PersonCard;
  slot: ImageSlot | undefined;
  onEditSlot?: (slotId: string) => void;
}) {
  const asset = slot?.selectedAsset;
  return (
    <article className="entity-card person-card">
      <MediaFigure
        asset={asset}
        className="entity-figure"
        caption={assetCaption(asset)}
        slotId={slot?.slotId}
        onEdit={onEditSlot}
      />
      <div className="entity-copy">
        <span>{card.role}</span>
        <h3>{card.name}</h3>
        <p>{card.summary}</p>
      </div>
    </article>
  );
}

function ArtifactTile({
  card,
  slot,
  onEditSlot,
}: {
  card: ArtifactCard;
  slot: ImageSlot | undefined;
  onEditSlot?: (slotId: string) => void;
}) {
  const asset = slot?.selectedAsset;
  return (
    <article className="artifact-card">
      <MediaFigure
        asset={asset}
        className="artifact-figure"
        caption={assetCaption(asset)}
        slotId={slot?.slotId}
        onEdit={onEditSlot}
      />
      <div className="entity-copy">
        <span>Экспонат эпохи</span>
        <h3>{card.title}</h3>
        <p>{card.summary}</p>
      </div>
    </article>
  );
}

export function LessonRenderer({
  title,
  heroSubtitle,
  visualMode,
  layout,
  lessonHtml,
  renderMode = "public",
  onEditSlot,
}: Props) {
  const themeMeta = VISUAL_MODES[visualMode];
  const isPublic = renderMode === "public";
  const containerRef = useScrollReveal(isPublic);
  const reveal = isPublic ? " scroll-reveal" : "";
  const editor = renderMode === "preview" ? onEditSlot : undefined;

  if (!layout) {
    return (
      <article className={`lesson-renderer lesson-renderer-${renderMode} visual-mode-${visualMode}`}>
        <header className="visual-hero visual-hero-legacy">
          <div className="hero-content-shell">
            <div className="hero-meta-row">
              <span className="eyebrow">История</span>
              <div className="hero-mode-pill">{themeMeta.name}</div>
            </div>
            <div className="hero-story-grid">
              <div className="hero-main-copy">
                <h1>{title}</h1>
                <p className="hero-subtitle">{heroSubtitle}</p>
              </div>
              <aside className="hero-side-card">
                <p className="hero-intro">{themeMeta.deck}</p>
                <div className="hero-side-meta">
                  <span>Режим</span>
                  <strong>{themeMeta.description}</strong>
                </div>
              </aside>
            </div>
          </div>
        </header>
        <div className="lesson-storyboard">
          <div className="legacy-lesson-content" dangerouslySetInnerHTML={{ __html: lessonHtml ?? "" }} />
        </div>
      </article>
    );
  }

  const slotList = layout.imageSlots;
  const slotsWithAsset = slotList.filter((slot) => slot.selectedAsset);

  const fallbackSlot = (fallbackIndex = 0): ImageSlot | undefined => {
    if (slotsWithAsset.length) {
      return slotsWithAsset[Math.abs(fallbackIndex) % slotsWithAsset.length];
    }
    return slotList[Math.abs(fallbackIndex) % Math.max(slotList.length, 1)];
  };

  const resolveSlot = (
    slotId?: string | null,
    role?: string,
    fallbackIndex = 0,
  ): ImageSlot | undefined => {
    if (slotId) {
      const direct = slotList.find((slot) => slot.slotId === slotId);
      if (direct?.selectedAsset) return direct;
    }
    if (role) {
      const roleSlot = slotList.find((slot) => slot.role === role && slot.selectedAsset);
      if (roleSlot) return roleSlot;
    }
    if (slotId) {
      const direct = slotList.find((slot) => slot.slotId === slotId);
      if (direct) return direct;
    }
    return fallbackSlot(fallbackIndex);
  };

  const heroSlot = resolveSlot(layout.hero.slotId, "hero", 0);
  const heroAsset = heroSlot?.selectedAsset;

  return (
    <article ref={containerRef} className={`lesson-renderer lesson-renderer-${renderMode} visual-mode-${visualMode}`}>
      <header className="visual-hero">
        <div className="hero-content-shell">
          <div className="hero-meta-row">
            <span className="eyebrow">{layout.hero.eyebrow}</span>
            <div className="hero-mode-pill">{themeMeta.name}</div>
          </div>

          <div className="hero-story-grid">
            <div className="hero-main-copy">
              <h1>{title}</h1>
              <p className="hero-subtitle">{heroSubtitle}</p>
              <p className="hero-intro hero-intro-main">{layout.hero.intro}</p>
            </div>

            <div className="hero-visual-column">
              <MediaFigure
                asset={heroAsset}
                className="hero-figure"
                caption={assetCaption(heroAsset)}
                slotId={heroSlot?.slotId}
                onEdit={editor}
              />
              <aside className="hero-side-card">
                <div className="hero-side-meta">
                  <span>Подход</span>
                  <strong>{themeMeta.deck}</strong>
                </div>
              </aside>
            </div>
          </div>
        </div>
      </header>

      <div className="lesson-storyboard">
        {layout.sections
          .filter((section) => section.visible)
          .map((section, index) => {
            if (section.blockType === "narrative") {
              return (
                <SectionNarrative
                  key={section.id}
                  section={section}
                  slot={resolveSlot(section.slotId, index % 2 === 0 ? "section" : "artifact", index + 1)}
                  revealClass={reveal}
                  onEditSlot={editor}
                />
              );
            }

            if (section.blockType === "timeline") {
              return (
                <SectionTimeline
                  key={section.id}
                  section={section}
                  slot={resolveSlot(section.slotId, "timeline", index + 1)}
                  revealClass={reveal}
                  onEditSlot={editor}
                />
              );
            }

            if (section.blockType === "person_card_grid") {
              return (
                <section key={section.id} className={`visual-section grid-section person-grid-section${reveal}`}>
                  <SectionIntro label="Персоны" section={section} />
                  <div className="entity-grid">
                    {section.personCards.map((card, cardIndex) => (
                      <PersonTile
                        key={`${section.id}-${card.name}`}
                        card={card}
                        slot={resolveSlot(card.slotId, "person", cardIndex + index + 1)}
                        onEditSlot={editor}
                      />
                    ))}
                  </div>
                </section>
              );
            }

            if (section.blockType === "artifact_gallery") {
              return (
                <section key={section.id} className={`visual-section gallery-section${reveal}`}>
                  <SectionIntro label="Артефакты" section={section} />
                  <div className="artifact-grid">
                    {section.artifactCards.map((card, cardIndex) => (
                      <ArtifactTile
                        key={`${section.id}-${card.title}`}
                        card={card}
                        slot={resolveSlot(card.slotId, "artifact", cardIndex + index + 1)}
                        onEditSlot={editor}
                      />
                    ))}
                  </div>
                </section>
              );
            }

            const quoteSlot = resolveSlot(section.slotId, "quote", index + 1);
            const quoteAsset = quoteSlot?.selectedAsset;
            return (
              <section key={section.id} className={`visual-section quote-section${reveal}`}>
                <div className="quote-panel">
                  <span className="section-kicker">Источник настроения</span>
                  <h2>{section.title}</h2>
                  {section.quoteText ? <blockquote>{section.quoteText}</blockquote> : null}
                  {section.quoteCaption ? <p className="quote-caption">{section.quoteCaption}</p> : null}
                </div>
                <MediaFigure
                  asset={quoteAsset}
                  className="section-image quote-image"
                  caption={assetCaption(quoteAsset)}
                  slotId={quoteSlot?.slotId}
                  onEdit={editor}
                />
              </section>
            );
          })}
      </div>
    </article>
  );
}
