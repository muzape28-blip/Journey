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
