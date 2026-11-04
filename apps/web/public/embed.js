/* Silsilah: menyisipkan widget pohon mutasi. Pakai:
 *   <div data-silsilah-id="UUID-KELUARGA"></div>
 *   <script async src="https://DOMAIN-SILSILAH/embed.js"></script>
 * Tidak memakai cookie, penyimpanan, atau pelacak. Hanya tinggi iframe yang diterima dari widget. */
(function () {
  var self = document.currentScript;
  if (!self || !self.src) return;
  var origin = new URL(self.src).origin;
  var UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  var frames = [];

  document.querySelectorAll("[data-silsilah-id]:not([data-silsilah-done])").forEach(function (node) {
    var id = node.getAttribute("data-silsilah-id") || "";
    if (!UUID.test(id)) return;
    node.setAttribute("data-silsilah-done", "1");
    var f = document.createElement("iframe");
    f.src = origin + "/embed/" + id;
    f.title = "Pohon mutasi pesan berantai (Silsilah)";
    f.loading = "lazy";
    f.referrerPolicy = "no-referrer";
    // tanpa allow-same-origin: widget berjalan di origin buram dan tidak bisa menyentuh halaman induk
    f.setAttribute("sandbox", "allow-scripts allow-popups allow-popups-to-escape-sandbox");
    f.style.cssText = "display:block;width:100%;max-width:640px;height:460px;border:1px solid #9ca3af;border-radius:8px";
    if (node.tagName === "SCRIPT") node.parentNode.insertBefore(f, node.nextSibling);
    else node.appendChild(f);
    frames.push(f);
  });

  window.addEventListener("message", function (e) {
    var d = e.data;
    if (!d || d.type !== "silsilah:height" || typeof d.height !== "number") return;
    // origin iframe tersandbox adalah "null", jadi pengirim dicocokkan lewat contentWindow
    for (var i = 0; i < frames.length; i++) {
      if (frames[i].contentWindow === e.source) frames[i].style.height = Math.min(Math.max(d.height, 200), 1200) + "px";
    }
  });
})();
