# EXPORT — Shibahu untuk Mixamo (v4: satu file bertekstur)

Karakter **lengkap** (ekor + blush), **T-pose**, satu mesh, TANPA skeleton, cm, tinggi ≈ 157, menghadap +Z.
Dibuang: ground plane 2,5 m (artefak floor source) & outline shell (tak terlihat tanpa shader toon).

## ⬆️ UPLOAD INI: `shibahu_mixamo.fbx` — SATU FILE, tekstur EMBEDDED

Binary FBX 7.4 (= FBX SDK 2014, batas yang dibaca Mixamo) dengan 7 tekstur PNG
tertanam di dalamnya (Video node `Content`). Tidak perlu zip, tidak perlu file pendamping.
Plan B bila ekor ditolak auto-rigger: `shibahu_lite_mixamo.fbx` (tanpa ekor/blush).

Kenapa bukan OBJ tunggal? Spesifikasi OBJ **tidak punya fitur embed** — .obj selalu
menunjuk .mtl & tekstur eksternal. Wadah "satu file" yang benar = FBX embed media
(dok resmi Mixamo: "Make sure embed media is turned on for FBX files to upload your
textures — OBJ files don't include textures, making characters appear gray"
[helpx.adobe.com](https://helpx.adobe.com/creative-cloud/help/mixamo-rigging-animation.html)).

Kenapa zip riskan? Pesan error Mixamo untuk zip: "The ZIP contains an unsupported File
type. Please use FBX or OBJ Formats" — sesuai pengalaman user: isi zip selain obj/fbx
bisa ditolak. Maka zip di sini hanya fallback: `shibahu_mixamo.zip` / `shibahu_lite_mixamo.zip`.

## Isi folder

| File | Isi |
|---|---|
| **`shibahu_mixamo.fbx`** (24,4 MB) | SATU FILE: mesh+UV+normal+material+7 tekstur embedded |
| `shibahu_lite_mixamo.fbx` | Varian tanpa ekor/blush, embedded juga |
| `shibahu_mixamo.zip` / `shibahu_lite_mixamo.zip` | Fallback obj+mtl+png |
| `shibahu.obj`/`.mtl`/`.fbx`(ascii) & `shibahu_lite.*` | File longgar untuk DCC/engine |
| `textures/` | 7 tekstur 2K |

## Langkah di Mixamo
1. Upload `shibahu_mixamo.fbx`.
2. Auto-Rigger: seret marker CHIN/WRISTS/ELBOWS/KNEES/GROIN, Use Symmetry on, NEXT.
3. Skeleton LOD Standard (65) → rig → animasi → download.
4. Hasil download Mixamo di beberapa DCC tetap perlu re-link tekstur dari `textures/` (normal).

## Verifikasi (jujur)
- `RENDERS/fbx_embedded_verify.png` = render yang dibuat dengan **membaca balik** binary
  FBX ini (parser binary independen di `tools/fbx2gltf/obj2fbx_embedded.py verify`) —
  geometri + 7 tekstur embedded terbaca utuh.
- Uji akhir tetap di Mixamo (sandbox tak bisa login). Bila muncul "Unsupported FBX type",
  kabari — itu artinya soal versi/format, dan fallback zip/obj masih tersedia.

Riwayat: v1 ground plane+A-pose → error rig. v2 lite → rig OK, look kurang.
v3 zip ber-tekstur → user: zip selain obj/fbx ditolak. v4 = satu FBX embedded ini.
