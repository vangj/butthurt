import { getDocument, GlobalWorkerOptions } from "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.5.136/build/pdf.mjs";

GlobalWorkerOptions.workerSrc =
  "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.5.136/build/pdf.worker.mjs";

self.addEventListener("message", async (event) => {
  const data = event.data;
  if (!data || data.type !== "render") {
    return;
  }

  if (typeof OffscreenCanvas === "undefined") {
    self.postMessage({
      type: "error",
      message: "OffscreenCanvas is not supported in this browser."
    });
    return;
  }

  const { pdfBytes, scale = 2, quality = 0.92 } = data;

  if (!(pdfBytes instanceof ArrayBuffer)) {
    self.postMessage({ type: "error", message: "Invalid PDF data supplied." });
    return;
  }

  try {
    const pdf = await getDocument({ data: new Uint8Array(pdfBytes) }).promise;

    for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
      const page = await pdf.getPage(pageNum);
      const viewport = page.getViewport({ scale });
      const width = Math.max(1, Math.floor(viewport.width));
      const height = Math.max(1, Math.floor(viewport.height));

      const canvas = new OffscreenCanvas(width, height);
      const context = canvas.getContext("2d", { alpha: false });

      if (!context) {
        throw new Error("Unable to initialize canvas context.");
      }

      await page.render({ canvasContext: context, viewport }).promise;

      const blob = await canvas.convertToBlob({ type: "image/jpeg", quality });
      const buffer = await blob.arrayBuffer();
      self.postMessage({ type: "page", pageNum, buffer }, [buffer]);

      page.cleanup?.();
    }

    pdf.cleanup?.();
    self.postMessage({ type: "complete" });
  } catch (error) {
    console.error(error);
    self.postMessage({
      type: "error",
      message: error?.message ?? "Failed to render PDF."
    });
  }
});
