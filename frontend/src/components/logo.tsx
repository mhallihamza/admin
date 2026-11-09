/**
 * Platform logo mark: a deep green square with a white open-book symbol.
 */
export default function Logo() {
  return (
    <span className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary">
      <svg
        aria-hidden="true"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        className="h-5 w-5 text-white"
      >
        <path d="M2 4h6a4 4 0 0 1 4 4v12a3 3 0 0 0-3-3H2z" />
        <path d="M22 4h-6a4 4 0 0 0-4 4v12a3 3 0 0 1 3-3h7z" />
      </svg>
    </span>
  );
}
