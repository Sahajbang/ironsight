import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";

import { useSearch } from "../api/client";
import { Icon, type IconName } from "../design";
import { useApp } from "../state/store";

/** Debounce so keystrokes don't each fire a request; 180ms is short enough that results
 *  feel like they arrive as you type, long enough to skip most intermediate states. */
function useDebounced(value: string, ms = 180) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), ms);
    return () => clearTimeout(id);
  }, [value, ms]);
  return debounced;
}

const TYPE_ICON: Record<string, IconName> = {
  video: "video",
  handbook: "book",
  checklist: "check",
  instructor: "user",
  simulation: "sim",
};

export function GlobalSearch() {
  const { operatorId } = useApp();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const debounced = useDebounced(query);
  const { data, isFetching } = useSearch(debounced, operatorId);
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onDown = (e: MouseEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, []);

  const showPanel = open && debounced.trim().length >= 2;

  return (
    <div className="search" ref={box} data-guide-id="search-bar">
      <div className="input search__input">
        <Icon name="search" size={17} />
        <input
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={(e) => e.key === "Escape" && setOpen(false)}
          placeholder="Search manuals, procedures, training…"
          aria-label="Search"
        />
        {isFetching && <span className="search__spin" aria-hidden />}
      </div>

      <AnimatePresence>
        {showPanel && (
          <motion.div
            className="search__panel"
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.16 }}
          >
            {data?.quick_answer && (
              <div className="search__answer">
                <span className="label">Quick answer</span>
                <p>{data.quick_answer.text}</p>
                <span className="search__src">from {data.quick_answer.source_title}</span>
              </div>
            )}

            {data && data.total === 0 && !isFetching && (
              <p className="search__none">Nothing matched “{debounced}”.</p>
            )}

            {data?.groups.map((group) => (
              <div key={group.type} className="search__group">
                <span className="label">{group.type}</span>
                {group.items.slice(0, 3).map((item) => (
                  <div key={item.id} className="search__hit">
                    <Icon name={TYPE_ICON[item.content_type] ?? "file"} size={16} />
                    <span className="col grow" style={{ gap: 1 }}>
                      <strong className="search__hittitle">{item.title}</strong>
                      <span className="search__hitsnip">{item.snippet}</span>
                      {item.context_reasons.length > 0 && (
                        <span className="search__why">Ranked up — {item.context_reasons[0]}</span>
                      )}
                    </span>
                    {item.duration_min && <span className="search__dur">{item.duration_min}m</span>}
                  </div>
                ))}
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
