import styles from "./SampleQueries.module.css";

const SAMPLES = [
  "Jokic last 10 games",
  "Jokic vs Embiid 2024-25",
  "top 10 scorers 2024-25",
  "Celtics home vs away 2024-25",
  "Luka 30+ point games",
  "Lakers longest winning streak 2024-25",
  "top team games by points 2024-25",
];

interface Props {
  onSelect: (query: string) => void;
}

export default function SampleQueries({ onSelect }: Props) {
  return (
    <div>
      <div className={styles.label}>Try a sample query</div>
      <div className={styles.samples}>
        {SAMPLES.map((q) => (
          <button key={q} type="button" onClick={() => onSelect(q)}>
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
