// Kompresja zdjęcia PO STRONIE KLIENTA przed wysłaniem (runda P11).
//
// Wydzielona z Checkin.tsx, żeby raport tygodniowy i „Przepisz ze zdjęcia"
// używały dokładnie tej samej ścieżki: obrót zgodny z orientacją EXIF
// (imageOrientation: "from-image"), ograniczenie dłuższego boku i JPEG.
// Przejście przez canvas naturalnie USUWA wszystkie metadane EXIF (w tym
// GPS) — backendowy strip z P4 zostaje jako druga warstwa (i jedyna, gdy
// kompresja się nie powiedzie i leci oryginał).

/** Domyślny limit dłuższego boku dla zdjęć postępu (jak w P11). */
export const PHOTO_MAX_PX = 2048;

/** Limit dla zdjęć do przepisania tekstu: 1600 px to tyle, ile i tak
 * zobaczy silnik OCR na serwerze (DZIK_OCR_MAX_PX) — wysyłanie większego
 * pliku obciąża sieć i maszynę 512 MB bez żadnego zysku dla rozpoznania. */
export const OCR_MAX_PX = 1600;

export async function compressImage(file: File, maxPx = PHOTO_MAX_PX): Promise<File> {
  try {
    const bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
    const scale = Math.min(1, maxPx / Math.max(bitmap.width, bitmap.height));
    const w = Math.max(1, Math.round(bitmap.width * scale));
    const h = Math.max(1, Math.round(bitmap.height * scale));
    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    if (!ctx) return file;
    ctx.drawImage(bitmap, 0, 0, w, h);
    bitmap.close();
    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, "image/jpeg", 0.85)
    );
    if (!blob) return file;
    const base = file.name.replace(/\.[^.]+$/, "") || "zdjecie";
    return new File([blob], `${base}.jpg`, { type: "image/jpeg" });
  } catch {
    // Świadomie: stara przeglądarka / uszkodzony plik — wysyłamy oryginał,
    // EXIF/GPS i rozdzielczość utnie backend (file_safety.process_image).
    return file;
  }
}
