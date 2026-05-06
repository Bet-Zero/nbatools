import type { ReactNode } from "react";
import { Card } from "../../../design-system";
import styles from "./ResultHero.module.css";

export type HeroTone =
  | "neutral"
  | "warm"
  | "cool"
  | "team"
  | "accent";

interface Props {
  /**
   * The plain-English sentence that answers the query.
   * Example: "Nikola Jokic has averaged 26.7 points, 12.5 rebounds and
   * 9.4 assists in his last 10 games."
   */
  sentence: ReactNode;

  /**
   * Subject illustration on the left side of the hero card. Typically a
   * player headshot or team logo. Optional — if absent, the sentence
   * fills the card.
   */
  subjectIllustration?: ReactNode;

  /**
   * Optional small subtitle directly under the sentence used for parser
   * disambiguation, e.g. "Interpreted as: most ppg by a player in 2025
   * playoffs."
   */
  disambiguationNote?: ReactNode;

  /**
   * Visual tone for the hero. Patterns choose a tone appropriate to the
   * subject (team color, neutral for general queries, etc.). Tones are
   * intentionally constrained — patterns may not introduce ad-hoc
   * colors.
   */
  tone?: HeroTone;
}

/**
 * Sentence-style hero card per the StatMuse-baseline answer pattern.
 * Renders a colored card with an optional subject illustration on the
 * left and a one-sentence answer on the right.
 *
 * This primitive is the *default* hero for every result pattern. If a
 * pattern needs a different hero treatment, that's a sign the pattern
 * itself should be reconsidered, not that this primitive should grow
 * more flags.
 */
export default function ResultHero({
  sentence,
  subjectIllustration,
  disambiguationNote,
  tone = "neutral",
}: Props) {
  return (
    <Card
      className={`${styles.hero} ${styles[`tone_${tone}`]}`}
      depth="elevated"
      padding="none"
    >
      {subjectIllustration && (
        <div className={styles.illustration}>{subjectIllustration}</div>
      )}
      <div className={styles.body}>
        <p className={styles.sentence}>{sentence}</p>
        {disambiguationNote && (
          <p className={styles.disambiguation}>{disambiguationNote}</p>
        )}
      </div>
    </Card>
  );
}
