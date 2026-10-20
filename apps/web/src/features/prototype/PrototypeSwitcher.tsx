import { useEffect } from "react";
import { useSearchParams } from "react-router-dom";

export type PrototypeVariantKey = "A" | "B" | "C";

const VARIANTS: ReadonlyArray<{ key: PrototypeVariantKey; name: string }> = [
  { key: "A", name: "Decision Inbox" },
  { key: "B", name: "Evidence Journey" },
  { key: "C", name: "Creative Lab" },
];

function isEditableTarget(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) return false;
  return target.matches("input, textarea, select, [contenteditable='true']");
}

export function PrototypeSwitcher({ current }: { current: PrototypeVariantKey }) {
  const [searchParams, setSearchParams] = useSearchParams();

  function selectVariant(offset: number) {
    const currentIndex = VARIANTS.findIndex((item) => item.key === current);
    const nextIndex = (currentIndex + offset + VARIANTS.length) % VARIANTS.length;
    const next = new URLSearchParams(searchParams);
    next.set("variant", VARIANTS[nextIndex].key);
    setSearchParams(next, { replace: true });
  }

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (isEditableTarget(event.target)) return;
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        selectVariant(-1);
      }
      if (event.key === "ArrowRight") {
        event.preventDefault();
        selectVariant(1);
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  });

  if (import.meta.env.PROD) return null;
  const label = VARIANTS.find((item) => item.key === current)?.name ?? current;

  return (
    <div className="prototype-switcher" aria-label="原型版本切换器">
      <button type="button" aria-label="上一个原型版本" onClick={() => selectVariant(-1)}>←</button>
      <span><strong>{current}</strong> — {label}</span>
      <button type="button" aria-label="下一个原型版本" onClick={() => selectVariant(1)}>→</button>
    </div>
  );
}
