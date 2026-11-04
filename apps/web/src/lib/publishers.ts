/** Domain penerbit resmi yang cocok dengan URL (domain itu sendiri atau subdomainnya); null bila tidak ada atau bukan https. */
export function matchPublisher(url: string, domains: string[]): string | null {
  let u: URL;
  try {
    u = new URL(url);
  } catch {
    return null;
  }
  if (u.protocol !== "https:" || u.username || u.password) return null;
  const host = u.hostname.toLowerCase();
  return domains.find((d) => host === d || host.endsWith(`.${d}`)) ?? null;
}
