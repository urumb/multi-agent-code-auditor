/**
 * Re-mounts on every navigation, replaying a CSS-only entrance animation.
 * No JS animation runtime and no exit-wait, so route changes feel instant.
 */
export default function Template({ children }: { children: React.ReactNode }) {
  return <div className="page-enter">{children}</div>;
}
