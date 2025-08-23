export function isNumeric(v: unknown) {
  return v !== null && v !== "" && !Number.isNaN(Number(v));
}

export function formatErrorMessage(err: unknown): string {
  if (!err) return "An unknown error occurred.";
  const str = String((err as any)?.message ?? err);
  const match = str.match(/"([^"]+)"/);
  return match?.[1] ?? str;
}
