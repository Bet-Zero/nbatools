import { useState, type HTMLAttributes } from "react";
import styles from "./TeamBadge.module.css";

export type TeamBadgeSize = "sm" | "md";

export interface TeamBadgeProps extends HTMLAttributes<HTMLSpanElement> {
  abbreviation?: string;
  name?: string;
  logoUrl?: string | null;
  size?: TeamBadgeSize;
  showName?: boolean;
}

function joinClassNames(...classNames: Array<string | false | undefined>) {
  return classNames.filter(Boolean).join(" ");
}

function fallbackAbbreviation(name: string | undefined): string {
  if (!name) return "TM";
  const cleaned = name.trim();
  if (!cleaned) return "TM";
  const parts = cleaned.split(/\s+/).filter(Boolean);
  if (parts.length === 1) return parts[0].slice(0, 3).toUpperCase();
  return parts
    .slice(0, 3)
    .map((part) => part[0].toUpperCase())
    .join("");
}

function accessibleLabel(
  name: string | undefined,
  abbreviation: string,
): string {
  if (!name) return abbreviation;
  if (name.toUpperCase() === abbreviation.toUpperCase()) return name;
  return `${name} (${abbreviation})`;
}

interface TeamBadgeLogoProps {
  logoUrl: string;
  abbreviation: string;
}

function TeamBadgeLogo({ logoUrl, abbreviation }: TeamBadgeLogoProps) {
  const [logoUnavailable, setLogoUnavailable] = useState(false);

  if (logoUnavailable) {
    return abbreviation;
  }

  return (
    <img
      className={styles.logo}
      src={logoUrl}
      alt=""
      onError={() => setLogoUnavailable(true)}
    />
  );
}

export function TeamBadge({
  abbreviation,
  name,
  logoUrl = null,
  size = "md",
  showName = true,
  className,
  ...props
}: TeamBadgeProps) {
  const abbr = (abbreviation ?? fallbackAbbreviation(name)).toUpperCase();
  const label = accessibleLabel(name, abbr);
  const showLogo = Boolean(logoUrl);

  return (
    <span
      aria-label={label}
      className={joinClassNames(styles.badge, styles[size], className)}
      {...props}
    >
      <span
        className={joinClassNames(styles.mark, showLogo && styles.logoMark)}
        aria-hidden="true"
      >
        {showLogo && logoUrl ? (
          <TeamBadgeLogo key={logoUrl} logoUrl={logoUrl} abbreviation={abbr} />
        ) : (
          abbr
        )}
      </span>
      {showName && <span className={styles.name}>{name ?? abbr}</span>}
    </span>
  );
}
