import { useId, type ReactNode } from "react";
import type { OuiNon } from "./api";

export const Check = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
    <path d="M4.5 12.5l5 5L19.5 7" />
  </svg>
);

export const InfoIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
    <circle cx="12" cy="12" r="9.5" />
    <path d="M12 11v6M12 7.5v.5" strokeLinecap="round" />
  </svg>
);

export const Pencil = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinejoin="round" aria-hidden>
    <path d="M15.5 4.5l4 4L8 20H4v-4z" />
  </svg>
);

export const Trash = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden>
    <path d="M5 7h14M10 7V4.5h4V7M7 7l1 13h8l1-13" />
  </svg>
);

export const Plus = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" aria-hidden>
    <path d="M12 5v14M5 12h14" />
  </svg>
);

export const FileUp = () => (
  <svg width="32" height="36" viewBox="0 0 24 26" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" aria-hidden>
    <path d="M14 2H6a2 2 0 00-2 2v18a2 2 0 002 2h12a2 2 0 002-2V8z" />
    <path d="M14 2v6h6M12 19v-7M9 15l3-3 3 3" strokeLinecap="round" />
  </svg>
);

export function Steps({
  items,
  current,
  done,
  light,
  onSelect,
}: {
  items: string[];
  current: number;
  done: (i: number) => boolean;
  light?: boolean;
  onSelect?: (i: number) => void;
}) {
  return (
    <ul className={`steps${light ? " light" : ""}`}>
      {items.map((label, idx) => {
        const i = idx + 1;
        const isCurrent = i === current;
        const isDone = !isCurrent && done(i);
        return (
          <li
            key={label}
            className={`step${isCurrent ? " current" : ""}${isDone ? " done" : ""}`}
            onClick={() => isDone && onSelect?.(i)}
            aria-current={isCurrent ? "step" : undefined}
          >
            {isDone ? (
              <span className="step-check">
                <Check />
              </span>
            ) : (
              <span className="step-num">{String(i).padStart(2, "0")}</span>
            )}
            <span>{label}</span>
          </li>
        );
      })}
    </ul>
  );
}

export function Field({
  label,
  required,
  optional,
  children,
  error,
}: {
  label: ReactNode;
  required?: boolean;
  optional?: string;
  children: ReactNode;
  error?: string | null;
}) {
  return (
    <div className="field">
      <label className="label">
        {label}
        {optional && <span className="opt"> {optional}</span>}
        {required && <span className="req">*</span>}
      </label>
      {children}
      {error && <div className="field-error">{error}</div>}
    </div>
  );
}

export function Radios<T extends string>({
  value,
  onChange,
  options,
}: {
  value: T | "" | undefined;
  onChange: (v: T) => void;
  options: [T, string][];
}) {
  const name = useId();
  return (
    <div className="radios" role="radiogroup">
      {options.map(([v, label]) => (
        <label className="radio" key={v}>
          <input type="radio" name={name} checked={value === v} onChange={() => onChange(v)} />
          {label}
        </label>
      ))}
    </div>
  );
}

export function OuiNonField({
  label,
  value,
  onChange,
  children,
}: {
  label: string;
  value: OuiNon | undefined;
  onChange: (v: "oui" | "non") => void;
  children?: ReactNode;
}) {
  return (
    <div className="field">
      <label className="label">
        {label}
        <span className="req">*</span>
      </label>
      <Radios
        value={value}
        onChange={onChange}
        options={[
          ["oui", "Oui"],
          ["non", "Non"],
        ]}
      />
      {value === "oui" && children && <div className="sub">{children}</div>}
    </div>
  );
}

export function DateInput({ value, onChange, max }: { value?: string; onChange: (v: string) => void; max?: string }) {
  return (
    <input
      type="date"
      className="input date"
      value={value ?? ""}
      max={max}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

export function InfoDocs({ libelles }: { libelles: string[] }) {
  if (!libelles.length) return null;
  return (
    <div className="info">
      <InfoIcon />
      <div>
        <div className="info-title">Document(s) requis ultérieurement</div>
        Le ou les documents justificatifs{" "}
        {libelles.map((l, i) => (
          <span key={l}>
            {i > 0 && ", "}
            <b>{l}</b>
          </span>
        ))}{" "}
        vous seront demandés à l'étape <b>06 Documents justificatifs</b>.
      </div>
    </div>
  );
}

export function Erreurs({ items }: { items: string[] }) {
  if (!items.length) return null;
  return (
    <div className="errors" role="alert">
      <b>Merci de compléter :</b>
      <ul>
        {items.map((e) => (
          <li key={e}>{e}</li>
        ))}
      </ul>
    </div>
  );
}

export const aujourdhui = () => new Date().toISOString().slice(0, 10);
