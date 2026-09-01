# EXPORT — Shibahu untuk Mixamo (v5: satu file biner bertekstur, header benar)

Karakter **lengkap** (ekor + blush), **T-pose**, satu mesh, TANPA skeleton, cm, tinggi ≈ 157, menghadap +Z.
Dibuang: ground plane 2,5 m (artefak floor source) & outline shell (tak terlihat tanpa shader toon).

## ⬆️ UPLOAD INI: `shibahu_mixamo.fbx` — SATU FILE, tekstur EMBEDDED

Binary FBX 7.4 dengan 7 tekstur PNG tertanam (node Video, property `Content` = byte PNG mentah),
array zlib-compressed. Tidak perlu zip / file pendamping.
Plan B bila auto-rigger menolak ekor: `shibahu_lite_mixamo.fbx` (tanpa ekor/blush, embedded juga).

### Kenapa bukan "OBJ include tekstur"
Spesifikasi Wavefront OBJ **tidak punya wadah embed** — .obj selalu menunjuk .mtl + tekstur
eksternal, jadi satu-file dari OBJ mustahil. Wadah single-file yang didukung Mixamo justru
**FBX embed media**: "Make sure embed media is turned on for FBX files to upload your textures —
OBJ files don't include textures, making characters appear gray"
([docs resmi](https://helpx.adobe.com/creative-cloud/help/mixamo-rigging-animation.html)).

### Kenapa v4 (commit 17d6e02) ditolak Mixamo
Writer v4 menulis header **tanpa byte `\x1a\x00`** sesudah magic (version ada di offset 21,
seharusnya 23). Detektor tipe file Mixamo melihat magic rusak → "Unexpected File Type".
v5 (`tools/fbx2gltf/export_fbx_bin.py`) menulis header identik dengan file referensi:
`Kaydara FBX Binary  \0` + `1A 00` + version 7400 di offset 23 (dibandingkan byte-per-byte
dengan FBX sumber yang valid).

## Isi folder

| File | Isi |
|---|---|
| **`shibahu_mixamo.fbx`** (15,6 MB) | SATU FILE: mesh+UV+normal+material+7 tekstur embedded (full look) |
| `shibahu_lite_mixamo.fbx` (15,5 MB) | Varian tanpa ekor/blush, embedded juga |
| `shibahu_mixamo.zip` / `shibahu_lite_mixamo.zip` | Fallback: obj+mtl+png (jalur resmi docs untuk OBJ berwarna) |
| `shibahu.obj`/`.mtl`/`.fbx`(ascii) & `shibahu_lite.obj/.mtl` | File longgar untuk DCC/engine |
| `textures/` | 7 tekstur 2K |

## Langkah di Mixamo
1. Upload `shibahu_mixamo.fbx`.
2. Auto-Rigger: seret marker CHIN/WRISTS/ELBOWS/KNEES/GROIN ke tubuh (Use Symmetry on) → NEXT.
3. Skeleton LOD Standard (65) → rig → pilih animasi → download.
4. Hasil download di beberapa DCC tetap perlu re-link tekstur dari `textures/` (normal).

## Verifikasi (jujur)
- `RENDERS/fbx_embed_verify.png` = render yang dibuat dengan **membaca balik** binary FBX ini
  lewat parser FBX biner independen (`tools/fbx2gltf/fbx2gltf.py`, parser yang sama yang sukses
  membaca FBX sumber Sketchfab): 62.969 vert / 72.312 tris, 7 PNG embedded **identical
  byte-for-byte**, UV tidak flip.
- Uji akhir tetap di situs Mixamo (sandbox tak bisa login). Bila masih ada error, kirim
  screenshot — fallback zip/obj/lite semua tersedia di folder ini.

Riwayat: v1 ground plane+A-pose → "Unknown error". v2 lite T-pose → rig OK, look kurang.
v3 zip ber-tekstur → user lapor zip asli dulu ditolak "unsupported file". v4 satu FBX embedded
tapi header rusak → "Unexpected File Type". v5 = folder ini sekarang.

## v5 — jalur alternatif selain Mixamo (hasil riset 2026-09-01)

Mixamo terbukti tidak stabil (outage massal Juni 2025, maintenance mode, error upload
"trouble receiving your upload" di banyak user). Alternatif GRATIS yang lebih worth it:

| Tool | Platform | Catatan |
|---|---|---|
| **Mesh2Motion** https://mesh2motion.org/ | browser (HP oke) | open-source, auto-rig humanoid+quadruped+burung, export anim |
| **Cinevva Auto Rigger** https://app.cinevva.com | browser | GLB/FBX/OBJ in → rigged GLB out; ada text-to-motion gratis |
| **Quaternius UAL** | library | 250+ animasi CC0 rig universal, retarget Unity/Unreal/Godot |
| **AccuRIG 2.0** | Windows | auto-rigger desktop terbaik, gratis (butuh PC) |
| **Blender Rigify** | PC | kontrol penuh, gratis |

File untuk jalur ini: **`shibahu.glb`** (15,1 MB) — single-file GLB bertekstur embedded,
T-pose, tanpa rig. Terverifikasi round-trip (`RENDERS/glb_verify.png`).

## v6 — `shibahu_rigged.glb` (17,6 MB): jawaban error Cinevva "MIA seam duplicates disagree"

Error itu artinya pipeline mereka menuntut vertex duplikat di seam UV punya skin weight
identik. GLB v5 tak ber-weight → proses internal mereka gagal. v6 menyertakan skeleton
sederhana 20 bone (Hips/Spine/Chest/Neck/Head/Tail + rantai lengan & kaki, gaya Mixamo)
+ weight hasil collapse rig sumber 218 joint. Weight asli identik di seam-duplicates,
terverifikasi: 14.545 posisi duplikat exact, 0 yang weight-nya berbeda.
File ini juga langsung dipakai di Unity/Unreal/Godot TANPA auto-rigger.
Urutan coba di Cinevva: (1) shibahu_rigged.glb, (2) shibahu.glb, (3) Mesh2Motion.

## v7 — perbaikan besar: validator resmi + GLB khusus Mesh2Motion

1. `shibahu_rigged.glb` DIPERBAIKI (sebelumnya cacat, ketahuan dari gltf-transform
   validate): JOINTS_0 sekarang USHORT sesuai spec (dulu float — bikin validator
   crash & loader ketat menolak), hierarki tulang disambungkan via `children`
   (dulu orphan!), root skeleton masuk scene. Sekarang: 0 error / 0 warning /
   0 hint, 20 bone di scene graph, 14.545 seam-duplicate → 0 beda weights.
2. BARU: `shibahu_m2m.glb` (3,2 MB) — khusus auto-rigger browser (Mesh2Motion dkk):
   satu mesh, satu primitive, material polos + tekstur 1x1 embedded, tanpa
   skeleton/ground/cheek/outline. Juga 0 error/warning/hint.
3. Ketiga GLB kini lolos `npx @gltf-transform/cli validate`.
Urutan coba: rigged → m2m (Mesh2Motion) → shibahu.glb.

## v8 — SATUAN METER + paket khusus Mesh2Motion (semua laporan user dijawab)

1. SEMUA export kini dalam METER (tinggi 1,575 m). Sebelumnya masih sentimeter
   (157,5 unit) — itu penyebab "raksasa" di Cinevva/M2M dan kamera nembus badan
   (near-plane). Mesh2Motion halaman retarget terbukti dari source code-nya
   TIDAK auto-scale model ber-skin.
2. `shibahu_m2m.glb` (polos/putih 1x1, tampil merah di Cinevva) DIGANTI
   `shibahu_m2m.zip` = shibahu.gltf + shibahu.bin + 6 tekstur — jalur ZIP-GLTF
   Mesh2Motion (loader zip mereka HANYA baca .gltf/.dae; zip OBJ lama memang
   tidak akan pernah muncul di sana).
3. Cara pakai Mesh2Motion (dari source code repo mereka):
   - halaman CREATE (auto-rig): upload `shibahu_m2m.zip`
   - halaman RETARGET (animasi ke rig yang sudah ada): upload
     `shibahu_rigged.glb` (butuh SkinnedMesh — mesh polos ditolak
     "No SkinnedMesh found")
4. Verifikasi: ketiga artefak lolos `gltf-transform validate` (0/0/0), rigged
   20 bone di scene, Hips rest 1,041 m, 14.545 seam-dup → 0 beda weights,
   render round-trip OK.
