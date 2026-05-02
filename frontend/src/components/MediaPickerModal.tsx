import { useEffect, useRef, useState } from "react";

import type { ImageSlot, MediaAsset } from "../types";

type Props = {
  slot: ImageSlot;
  refreshing: boolean;
  canRefresh: boolean;
  onSelect: (asset: MediaAsset) => void;
  onRefresh: () => void;
  onUpload: (file: File) => Promise<MediaAsset>;
  onClose: () => void;
};

export function MediaPickerModal({
  slot,
  refreshing,
  canRefresh,
  onSelect,
  onRefresh,
  onUpload,
  onClose,
}: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");

  useEffect(() => {
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKey);
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", handleKey);
      document.body.style.overflow = "";
    };
  }, [onClose]);

  const handleFile = async (file: File) => {
    setUploadError("");
    setUploading(true);
    try {
      const asset = await onUpload(file);
      onSelect(asset);
      onClose();
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Не удалось загрузить файл.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="media-picker-backdrop" onClick={onClose} role="presentation">
      <div
        className="media-picker-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="media-picker-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="media-picker-head">
          <div>
            <span className="media-picker-kicker">Сменить изображение</span>
            <h3 id="media-picker-title">{slot.label}</h3>
          </div>
          <div className="media-picker-actions">
            <button
              type="button"
              className="primary-button media-picker-upload"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
            >
              {uploading ? "Загружаем..." : "Загрузить свою"}
            </button>
            {canRefresh ? (
              <button
                type="button"
                className="ghost-button"
                onClick={onRefresh}
                disabled={refreshing}
              >
                {refreshing ? "Ищем..." : "Обновить подбор"}
              </button>
            ) : null}
            <button
              type="button"
              className="media-picker-close"
              onClick={onClose}
              aria-label="Закрыть"
            >
              ×
            </button>
          </div>
        </header>

        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp,image/gif"
          style={{ display: "none" }}
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) void handleFile(file);
            event.target.value = "";
          }}
        />

        {uploadError ? <div className="media-picker-error">{uploadError}</div> : null}

        {slot.searchQueries.length ? (
          <div className="media-picker-queries">
            {slot.searchQueries.map((query) => (
              <span key={`${slot.slotId}-${query}`} className="query-pill">
                {query}
              </span>
            ))}
          </div>
        ) : null}

        <div className="media-picker-grid">
          {slot.candidateAssets.length ? (
            slot.candidateAssets.map((asset) => {
              const selected = slot.selectedAsset?.assetId === asset.assetId;
              return (
                <button
                  type="button"
                  key={asset.assetId}
                  className={`media-picker-card ${selected ? "selected" : ""}`}
                  onClick={() => {
                    onSelect(asset);
                    onClose();
                  }}
                >
                  <img src={asset.thumbUrl || asset.imageUrl} alt={asset.alt || asset.title} />
                  <div className="media-picker-card-meta">
                    <strong>{asset.title}</strong>
                    <small>{asset.provider}</small>
                  </div>
                  {selected ? <span className="media-picker-badge">Сейчас</span> : null}
                </button>
              );
            })
          ) : (
            <div className="media-picker-empty">
              Нет кандидатов. Загрузите свою фотографию или нажмите «Обновить подбор».
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
