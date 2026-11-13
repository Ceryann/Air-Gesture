# GestureInput — Fase 0 (Proof of Concept)

Pipeline Python murni: webcam → MediaPipe HandLandmarker → klasifikasi heuristik → state machine → One Euro Filter → injeksi mouse Windows.
Tujuan Fase 0: **validasi latensi, kehalusan kursor, dan kelayakan** di satu laptop target — bukan fitur lengkap.

## Cakupan Fase 0

| Gestur | Aksi |
|---|---|
| Telapak terbuka | Kursor bergerak (titik acuan: pusat telapak) |
| Pinch (ibu jari + telunjuk) | Klik kiri (sekali per pinch) |
| Pinch dua kali cepat | Double-click (digabung oleh OS, lihat catatan) |
| Dua jari (telunjuk + tengah), naik/turun | Scroll (rate control) |
| **Shaka** (ibu jari + kelingking), tahan 2 dtk | **Freeze / unfreeze** |

Ditunda ke Fase 1: drag (kepalan), zoom dua tangan, overlay final, guard input fisik (FR-12), kalibrasi.

## Menjalankan (Windows, Python 3.10–3.12)

```bat
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python scripts\download_model.py        :: sekali saja; setelah itu offline
python -m gesture_core --dry-run        :: UJI PERTAMA: preview saja, mouse asli tidak disentuh
python -m gesture_core                  :: kontrol mouse sungguhan
python -m gesture_core --no-preview     :: ukur latensi tanpa beban jendela preview
python -m pytest tests                  :: atau: python -m unittest discover -s tests -t .
```

**Pengaman:** `Ctrl+Alt+F` = freeze/unfreeze, `Ctrl+Alt+Q` = keluar, `q`/`ESC` di jendela preview, `Ctrl+C` di terminal.
Gunakan `--dry-run` dulu sampai label di preview stabil.

## Build tanpa install apa pun (GitHub Actions)

Workflow `.github/workflows/build-windows.yml` menjalankan tes, membangun `GestureInput.exe` (PyInstaller, **model sudah terbundel**), lalu menjalankan `--selfcheck` pada exe hasil build.

```bash
git init && git add . && git commit -m "GestureInput Fase 0"
git branch -M main
git remote add origin https://github.com/<user>/<repo>.git
git push -u origin main
```

1. Buka tab **Actions** → run **Build Windows** (±5–10 menit).
2. Unduh artifact **GestureInput-windows-x64**, ekstrak, klik dua kali `GestureInput-DryRun.bat`.
3. Rilis permanen: `git tag v0.1.0 && git push origin v0.1.0` → zip otomatis muncul di halaman **Releases**.

Build manual: Actions → Build Windows → *Run workflow*. Artifact `requirements-lock` berisi versi persis dependensi yang dipakai (untuk di-pin nanti).
Repo privat memakai kuota menit Actions (runner Windows dihitung lebih mahal); repo publik gratis.

## Jalankan dari kode sumber, semua dalam satu folder (tanpa .exe)

Cocok bila Smart App Control memblokir exe/DLL hasil bundle. Butuh Python 3.10–3.12 yang sudah terpasang.

1. Ekstrak proyek ke satu folder (mis. `D:\GestureInput`). Bila dari zip unduhan: klik kanan zip → Properties → **Unblock** sebelum ekstrak.
2. Klik dua kali **`setup.bat`** (sekali saja): membuat `.venv`, memasang library, mengunduh model, lalu menjalankan cek instalasi.
3. Sehari-hari: **`jalankan-dryrun.bat`** (uji, mouse tidak disentuh) atau **`jalankan.bat`** (mouse sungguhan). `cek-instalasi.bat` untuk diagnosis.

Isi folder yang dibuat setup: `.venv` (library; kira-kira beberapa ratus MB), `models` (model tangan), `.cache` (cache pip/matplotlib/pyc).
**Menghapus folder = menghapus semuanya.** Di luar folder hanya Python itu sendiri dan file sementara Windows (TEMP).
Update kode: timpa file proyek lalu klik `setup.bat` lagi (cepat; hanya menambah yang kurang).

## Urutan validasi (sesuai PRD §13)

1. `--dry-run`: lihat skeleton; pastikan label `open_palm / pinch / two_finger / shaka` benar. Perhatikan baris `ext i/m/r/p` dan `pinch=` — itu angka yang perlu di-tuning.
2. Pinch + kursor: apakah klik meleset? Atur `pinch_on/pinch_off`, `post_click_lock_s`.
3. Kehalusan kursor: atur `one_euro_min_cutoff` (naik = lebih responsif, lebih jitter) dan `one_euro_beta` (naik = lag cepat berkurang).
4. Scroll dua jari: atur `scroll_deadzone`, `scroll_gain`, `scroll_invert`.
5. Baca log latensi p50/p95/p99 setiap 100 frame.

Override konfigurasi: buat JSON berisi kunci dari `gesture_core/config.py`, lalu `--config profil.json`.

## Keputusan desain yang menyimpang / memperjelas PRD

1. **Freeze = gestur shaka**, bukan "telapak tertutup": telapak tertutup ≈ kepalan, dan drag (200 ms) selalu terpicu lebih dulu dari freeze (2 dtk).
2. **Titik kursor = pusat telapak**, bukan pergelangan: lebih stabil saat pinch. Kursor juga ditahan begitu pinch mulai terbentuk, supaya klik tidak menggeser target.
3. **One Euro Filter diterapkan di piksel layar**, bukan koordinat ternormalisasi. `beta=0.02` dari PRD hanya bermakna pada satuan piksel/detik.
4. **Debounce klik 150 ms, bukan 300–400 ms** (PRD §10.5): debounce 300–400 ms bertabrakan dengan jendela double-click ≤ 400 ms (FR-04). Double-click dihasilkan OS dari dua klik cepat; kursor dikunci 400 ms pasca-klik agar tidak melampaui toleransi ~4 px Windows.
5. **Scroll = rate control**: kecepatan sebanding offset vertikal dari titik awal pose (tangan naik = scroll naik, tahan = terus scroll, kembali ke tengah = berhenti). Menghindari masalah "gerakan balik" pada scroll berbasis delta. Perlu divalidasi dalam uji pengguna.
6. **Output mouse via ctypes murni** (`SetCursorPos`, `mouse_event`); `pynput` hanya untuk hotkey global. `SetProcessDPIAware()` dipanggil agar koordinat tidak meleset di layar DPI tinggi.
7. `two_finger` dibaca sebagai pose + gerak oleh state machine; classifier ML belum diperlukan di Fase 0. `num_hands=1`.
8. Pipeline memiliki 3 thread dengan buffer tunggal; control loop berjalan di thread utama (bersama preview OpenCV).

## Batasan pengukuran latensi (penting)

Metrik `frame_total` dan `pinch->click` dihitung dari saat `cap.read()` kembali. **Latensi sensor kamera + driver USB (sering 30–80 ms) dan latensi tampilan layar tidak terukur.** Untuk target p95 < 120 ms yang sebenarnya, ukur end-to-end dengan kamera eksternal (mis. video 240 fps dari ponsel yang merekam tangan dan layar sekaligus). `pinch->click` sudah memasukkan penundaan konfirmasi `pinch_confirm_frames`.

## Status verifikasi

- Teruji otomatis (34 tes, tanpa kamera): One Euro Filter, classifier (landmark sintetis), state machine, pemetaan kursor, pipeline end-to-end dengan backend dry-run.
- **Belum teruji pada perangkat nyata:** capture kamera, callback MediaPipe `LIVE_STREAM`, injeksi mouse Windows, hotkey. Semua ambang batas klasifikasi (`ext_ratio`, `pinch_on`, dst.) adalah tebakan awal dan perlu di-tuning dengan tangan nyata.
