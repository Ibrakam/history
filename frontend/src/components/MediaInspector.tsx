import type { ImageSlot, MediaAsset } from "../types";

type Props = {
  slots: ImageSlot[];
  currentSlotId?: string;
  refreshingSlotId?: string | null;
  canRefresh: boolean;
  onSelectAsset: (slotId: string, asset: MediaAsset) => void;
  onRefreshSlot: (slotId: string) => void;
};

export function MediaInspector({
  slots,
  currentSlotId,
  refreshingSlotId,
  canRefresh,
  onSelectAsset,
  onRefreshSlot,
}: Props) {
  return (
    <section className="media-panel">
      <div className="section-heading">
        <div>
          <h3>Медиа инспектор</h3>
          <p>Выбор изображений по секциям, персонам и артефактам.</p>
        </div>
      </div>

      {slots.map((slot) => (
        <article
          key={slot.slotId}
          className={`media-slot-card ${slot.slotId === currentSlotId ? "active" : ""}`}
        >
          <div className="media-slot-header">
            <div>
              <strong>{slot.label}</strong>
              <small>{slot.role}</small>
            </div>
            {canRefresh ? (
              <button
                type="button"
                className="ghost-button"
                onClick={() => onRefreshSlot(slot.slotId)}
                disabled={refreshingSlotId === slot.slotId}
              >
                {refreshingSlotId === slot.slotId ? "Ищем..." : "Обновить подбор"}
              </button>
            ) : null}
          </div>

          {slot.searchQueries.length ? (
            <div className="query-strip">
              {slot.searchQueries.map((query) => (
                <span key={`${slot.slotId}-${query}`} className="query-pill">
                  {query}
                </span>
              ))}
            </div>
          ) : null}

          <div className="candidate-grid">
            {slot.candidateAssets.map((asset) => (
              <button
                type="button"
                key={asset.assetId}
                className={`candidate-card ${
                  slot.selectedAsset?.assetId === asset.assetId ? "selected" : ""
                }`}
                onClick={() => onSelectAsset(slot.slotId, asset)}
              >
                <img src={asset.thumbUrl || asset.imageUrl} alt={asset.alt || asset.title} />
                <strong>{asset.title}</strong>
                <small>{asset.provider}</small>
              </button>
            ))}
          </div>
        </article>
      ))}
    </section>
  );
}

