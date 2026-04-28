import styles from "./ErrorBox.module.css";

interface Props {
  message: string;
}

export default function ErrorBox({ message }: Props) {
  return (
    <div className={styles.errorBox}>
      <div className={styles.title}>Error</div>
      <div>{message}</div>
    </div>
  );
}
