import type { ArtifactCard, LessonSection, PersonCard, TimelineItem } from "../types";

function splitParagraphs(value: string): string[] {
  return value
    .split(/\n{2,}/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function joinParagraphs(value: string[]): string {
  return value.join("\n\n");
}

const BLOCK_LABELS: Record<LessonSection["blockType"], string> = {
  narrative: "Текст урока",
  timeline: "Хронология",
  person_card_grid: "Персоны",
  artifact_gallery: "Артефакты",
  quote_callout: "Цитата",
};

type Props = {
  section: LessonSection;
  onUpdate: (sectionId: string, mutate: (section: LessonSection) => void) => void;
};

export function SectionEditor({ section, onUpdate }: Props) {
  const update = (mutate: (s: LessonSection) => void) => onUpdate(section.id, mutate);

  const updateTimelineItem = (index: number, patch: Partial<TimelineItem>) => {
    update((s) => {
      s.timelineItems = s.timelineItems.map((item, i) =>
        i === index ? { ...item, ...patch } : item,
      );
    });
  };

  const updatePersonCard = (index: number, patch: Partial<PersonCard>) => {
    update((s) => {
      s.personCards = s.personCards.map((item, i) =>
        i === index ? { ...item, ...patch } : item,
      );
    });
  };

  const updateArtifactCard = (index: number, patch: Partial<ArtifactCard>) => {
    update((s) => {
      s.artifactCards = s.artifactCards.map((item, i) =>
        i === index ? { ...item, ...patch } : item,
      );
    });
  };

  return (
    <article className="section-editor-card">
      <div className="section-card-head">
        <strong>{BLOCK_LABELS[section.blockType]}</strong>
      </div>

      <label>
        Заголовок
        <input
          value={section.title}
          onChange={(event) =>
            update((s) => {
              s.title = event.target.value;
            })
          }
        />
      </label>

      {"lead" in section ? (
        <label>
          Подзаголовок
          <textarea
            rows={2}
            value={section.lead ?? ""}
            onChange={(event) =>
              update((s) => {
                s.lead = event.target.value;
              })
            }
          />
        </label>
      ) : null}

      {section.blockType === "narrative" ? (
        <label>
          Текст
          <textarea
            rows={8}
            value={joinParagraphs(section.body)}
            onChange={(event) =>
              update((s) => {
                s.body = splitParagraphs(event.target.value);
              })
            }
          />
        </label>
      ) : null}

      {section.blockType === "timeline" ? (
        <div className="card-stack">
          {section.timelineItems.map((item, index) => (
            <div key={`${section.id}-timeline-${index}`} className="subcard">
              <label>
                Год / этап
                <input
                  value={item.year}
                  onChange={(event) => updateTimelineItem(index, { year: event.target.value })}
                />
              </label>
              <label>
                Заголовок
                <input
                  value={item.title}
                  onChange={(event) => updateTimelineItem(index, { title: event.target.value })}
                />
              </label>
              <label>
                Описание
                <textarea
                  rows={3}
                  value={item.description}
                  onChange={(event) =>
                    updateTimelineItem(index, { description: event.target.value })
                  }
                />
              </label>
            </div>
          ))}
        </div>
      ) : null}

      {section.blockType === "person_card_grid" ? (
        <div className="card-stack">
          {section.personCards.map((card, index) => (
            <div key={`${section.id}-person-${index}`} className="subcard">
              <label>
                Имя
                <input
                  value={card.name}
                  onChange={(event) => updatePersonCard(index, { name: event.target.value })}
                />
              </label>
              <label>
                Роль
                <input
                  value={card.role}
                  onChange={(event) => updatePersonCard(index, { role: event.target.value })}
                />
              </label>
              <label>
                Описание
                <textarea
                  rows={3}
                  value={card.summary}
                  onChange={(event) => updatePersonCard(index, { summary: event.target.value })}
                />
              </label>
            </div>
          ))}
        </div>
      ) : null}

      {section.blockType === "artifact_gallery" ? (
        <div className="card-stack">
          {section.artifactCards.map((card, index) => (
            <div key={`${section.id}-artifact-${index}`} className="subcard">
              <label>
                Название
                <input
                  value={card.title}
                  onChange={(event) => updateArtifactCard(index, { title: event.target.value })}
                />
              </label>
              <label>
                Описание
                <textarea
                  rows={3}
                  value={card.summary}
                  onChange={(event) => updateArtifactCard(index, { summary: event.target.value })}
                />
              </label>
            </div>
          ))}
        </div>
      ) : null}

      {section.blockType === "quote_callout" ? (
        <>
          <label>
            Цитата
            <textarea
              rows={4}
              value={section.quoteText ?? ""}
              onChange={(event) =>
                update((s) => {
                  s.quoteText = event.target.value;
                })
              }
            />
          </label>
          <label>
            Подпись
            <input
              value={section.quoteCaption ?? ""}
              onChange={(event) =>
                update((s) => {
                  s.quoteCaption = event.target.value;
                })
              }
            />
          </label>
        </>
      ) : null}
    </article>
  );
}
