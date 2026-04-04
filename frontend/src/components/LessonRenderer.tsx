import { VISUAL_MODES } from "../theme";
import type { ArtifactCard, LessonLayout, LessonSection, MediaAsset, PersonCard, VisualMode } from "../types";

type Props = {
  title: string;
  heroSubtitle: string;
  visualMode: VisualMode;
  layout: LessonLayout | null;
  lessonHtml?: string;
  renderMode?: "preview" | "public";
};

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
}: {
  asset: MediaAsset | null | undefined;
  className?: string;
  caption?: string;
}) {
  return (
    <figure className={className ?? "media-figure"}>
      {asset ? (
        <img src={asset.imageUrl} alt={asset.alt || asset.title} />
      ) : (
        <div className="media-placeholder">Исторический визуал</div>
      )}
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
  asset,
}: {
  section: LessonSection;
  asset: MediaAsset | null | undefined;
}) {
  return (
    <section className="visual-section narrative-section">
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
          <MediaFigure asset={asset} className="section-image narrative-image" caption={assetCaption(asset)} />
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
  asset,
}: {
  section: LessonSection;
  asset: MediaAsset | null | undefined;
}) {
  return (
    <section className="visual-section timeline-section">
      <SectionIntro label="Хронология" section={section} />
      <div className="timeline-layout">
        <MediaFigure asset={asset} className="timeline-figure" caption={assetCaption(asset)} />
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
  asset,
}: {
  card: PersonCard;
  asset: MediaAsset | null | undefined;
}) {
  return (
    <article className="entity-card person-card">
      <MediaFigure asset={asset} className="entity-figure" caption={assetCaption(asset)} />
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
  asset,
}: {
  card: ArtifactCard;
  asset: MediaAsset | null | undefined;
}) {
  return (
    <article className="artifact-card">
      <MediaFigure asset={asset} className="artifact-figure" caption={assetCaption(asset)} />
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
}: Props) {
  const themeMeta = VISUAL_MODES[visualMode];

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

  const slotMap = new Map(layout.imageSlots.map((slot) => [slot.slotId, slot.selectedAsset]));
  const orderedAssets = layout.imageSlots.map((slot) => slot.selectedAsset).filter(Boolean) as MediaAsset[];
  const fallbackAsset = (fallbackIndex = 0) =>
    orderedAssets.length ? orderedAssets[Math.abs(fallbackIndex) % orderedAssets.length] : undefined;
  const heroAsset =
    slotMap.get(layout.hero.slotId) ??
    layout.imageSlots.find((slot) => slot.role === "hero")?.selectedAsset ??
    fallbackAsset(0);

  const resolveAsset = (slotId?: string | null, role?: string, fallbackIndex = 0) => {
    if (slotId && slotMap.get(slotId)) {
      return slotMap.get(slotId);
    }
    if (role) {
      const roleAsset = layout.imageSlots.find((slot) => slot.role === role)?.selectedAsset;
      if (roleAsset) {
        return roleAsset;
      }
    }
    return fallbackAsset(fallbackIndex);
  };

  return (
    <article className={`lesson-renderer lesson-renderer-${renderMode} visual-mode-${visualMode}`}>
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
              <MediaFigure asset={heroAsset} className="hero-figure" caption={assetCaption(heroAsset)} />
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
                  asset={resolveAsset(section.slotId, index % 2 === 0 ? "section" : "artifact", index + 1)}
                />
              );
            }

            if (section.blockType === "timeline") {
              return (
                <SectionTimeline
                  key={section.id}
                  section={section}
                  asset={resolveAsset(section.slotId, "timeline", index + 1)}
                />
              );
            }

            if (section.blockType === "person_card_grid") {
              return (
                <section key={section.id} className="visual-section grid-section person-grid-section">
                  <SectionIntro label="Персоны" section={section} />
                  <div className="entity-grid">
                    {section.personCards.map((card, cardIndex) => (
                      <PersonTile
                        key={`${section.id}-${card.name}`}
                        card={card}
                        asset={resolveAsset(card.slotId, "person", cardIndex + index + 1)}
                      />
                    ))}
                  </div>
                </section>
              );
            }

            if (section.blockType === "artifact_gallery") {
              return (
                <section key={section.id} className="visual-section gallery-section">
                  <SectionIntro label="Артефакты" section={section} />
                  <div className="artifact-grid">
                    {section.artifactCards.map((card, cardIndex) => (
                      <ArtifactTile
                        key={`${section.id}-${card.title}`}
                        card={card}
                        asset={resolveAsset(card.slotId, "artifact", cardIndex + index + 1)}
                      />
                    ))}
                  </div>
                </section>
              );
            }

            return (
              <section key={section.id} className="visual-section quote-section">
                <div className="quote-panel">
                  <span className="section-kicker">Источник настроения</span>
                  <h2>{section.title}</h2>
                  {section.quoteText ? <blockquote>{section.quoteText}</blockquote> : null}
                  {section.quoteCaption ? <p className="quote-caption">{section.quoteCaption}</p> : null}
                </div>
                <MediaFigure
                  asset={resolveAsset(section.slotId, "quote", index + 1)}
                  className="section-image quote-image"
                  caption={assetCaption(resolveAsset(section.slotId, "quote", index + 1))}
                />
              </section>
            );
          })}
      </div>
    </article>
  );
}
