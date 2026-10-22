import { useEffect, useRef, useState } from "react"

// Lightweight searchable combobox (ported from EasyPC tracker).
// items: [{id, label, sub}]. Selecting via click or Enter on highlighted row.
export default function SearchableSelect({ items = [], value, onChange, placeholder }) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState("")
  const wrap = useRef(null)

  const selected = items.find((i) => i.id === value)
  const filtered = items.filter((i) =>
    (i.label + " " + (i.sub || "")).toLowerCase().includes(query.toLowerCase())
  )

  useEffect(() => {
    const close = (e) => { if (wrap.current && !wrap.current.contains(e.target)) setOpen(false) }
    document.addEventListener("mousedown", close)
    return () => document.removeEventListener("mousedown", close)
  }, [])

  return (
    <div ref={wrap} className="relative">
      <input
        className="w-full h-11 rounded-md border border-input bg-background px-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
        placeholder={placeholder}
        value={open ? query : selected ? selected.label : query}
        onFocus={() => { setOpen(true); setQuery("") }}
        onChange={(e) => { setQuery(e.target.value); setOpen(true) }}
      />
      {open && (
        <div className="absolute z-20 mt-1 w-full rounded-md border border-border bg-popover shadow-md max-h-52 overflow-auto">
          {filtered.length === 0 && (
            <div className="px-3 py-2 text-sm text-muted-foreground">No matches</div>
          )}
          {filtered.map((i) => (
            <button
              key={i.id}
              type="button"
              className={
                "w-full text-left px-3 py-2 text-sm hover:bg-accent " +
                (i.id === value ? "text-primary font-medium" : "")
              }
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => { onChange(i.id); setOpen(false); setQuery("") }}
            >
              <div>{i.label}</div>
              {i.sub && <div className="text-xs text-muted-foreground">{i.sub}</div>}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
