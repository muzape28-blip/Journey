# EXPORT — Shibahu untuk Mixamo (v3)

Karakter **lengkap seperti semula** (ekor + blush ikut), **T-pose**, satu mesh gabungan,
TANPA skeleton, cm, tinggi ≈ 157, menghadap +Z.
Yang tetap dibuang: ground plane 2,5 m (`lambert2`, artefak floor dari source — bukan bagian karakter)
dan outline shell (`*_line`, permukaan dobel yang tak terlihat tanpa shader toon).

## File

| File | Isi |
|---|---|
| **`shibahu_mixamo.zip`** | ⬆️ **UPLOAD INI KE MIXAMO** — berisi `shibahu.obj` + `shibahu.mtl` (ref tekstur flat) + 7 tekstur PNG di root zip |
| `shibahu_lite_mixamo.zip` | Fallback bila auto-rigger menolak ekor: varian tanpa ekor/blush, struktur zip sama |
| `shibahu.obj` / `shibahu.mtl` / `shibahu.fbx` | Varian FULL (ekor+blush) longgar, buat DCC/engine |
| `shibahu_lite.obj` / `shibahu_lite.mtl` | Varian lite longgar |
| `textures/` | 7 tekstur 2K |

## Kenapa harus ZIP, bukan .obj polos

Menurut dokumentasi resmi Mixamo: *"OBJ files don't include textures, making characters
appear gray. To show textures for an .obj file, put the .obj, .mtl and textures into a .zip
and upload the whole .zip file."* [helpx.adobe.com](https://helpx.adobe.com/creative-cloud/help/mixamo-rigging-animation.html)
Itu sebabnya upload `.obj` sendirian kemarin tampil abu-abu silver.

## Langkah di Mixamo

1. Upload `shibahu_mixamo.zip`.
2. Auto-Rigger: seret marker CHIN/WRISTS/ELBOWS/KNEES/GROIN ke tubuh (Use Symmetry on), NEXT.
3. Skeleton LOD Standard (65) → rig → pilih animasi → download.
4. Bila muncul error rig karena ekor → upload `shibahu_lite_mixamo.zip` sebagai plan B
   (ekor/blush dipasang lagi nanti di engine dari pipeline glTF repo ini).

Catatan: hasil DOWNLOAD dari Mixamo memang datang tanpa tekstur ter-link di beberapa DCC —
re-link PNG dari folder `textures/` di Blender/engine (normal, bukan bug file ini).

Bukti valid: `RENDERS/obj_file_verify.png` (depan) & `RENDERS/obj_file_verify_back.png`
(belakang, ekor kelihatan) — keduanya dirender LANGSUNG dari isi `shibahu_mixamo.zip`.

Riwayat: v1 (39d5cdf) memuat ground plane/cheek/ekor + A-pose → "Unknown error".
v2 (859f4bc) T-pose tapi ekor/blush dibuang → rig OK tapi user minta look lengkap.
v3 = folder ini sekarang.
