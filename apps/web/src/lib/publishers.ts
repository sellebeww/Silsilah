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

export interface Publisher {
  domain: string;
  name: string;
}

/** Hanya tautan yang penerbitnya terdaftar DAN URL-nya benar-benar di domain penerbit itu (https). Pertahanan kedua di atas constraint DB. */
export function trustedLinks<T extends { url: string; publisher: string }>(
  links: T[],
  publishers: Publisher[],
): (T & { publisher_name: string })[] {
  const names = new Map(publishers.map((p) => [p.domain, p.name]));
  return links.flatMap((l) => {
    const name = names.get(l.publisher);
    return name && matchPublisher(l.url, [l.publisher]) ? [{ ...l, publisher_name: name }] : [];
  });
}
