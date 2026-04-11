interface Props {
  message: string;
}

export default function ErrorBox({ message }: Props) {
  return (
    <div className="error-box active">
      <div className="title">Error</div>
      <div>{message}</div>
    </div>
  );
}
