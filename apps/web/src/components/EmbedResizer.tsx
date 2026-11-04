"use client";
import { useEffect } from "react";

/** Memberi tahu halaman induk (embed.js) tinggi konten. Hanya angka tinggi yang dikirim. */
export function EmbedResizer() {
  useEffect(() => {
    if (window.parent === window) return;
    const send = () => window.parent.postMessage({ type: "silsilah:height", height: document.documentElement.scrollHeight }, "*");
    const ro = new ResizeObserver(send);
    ro.observe(document.documentElement);
    send();
    return () => ro.disconnect();
  }, []);
  return null;
}
