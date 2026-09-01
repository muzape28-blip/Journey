# EXPORT — Shibahu untuk Mixamo (v2, Mixamo-optimized)

File hasil pipeline `tools/fbx2gltf` (dari `ASSETS/shibahu.zip`), diekspor dalam kondisi yang disukai auto-rigger Mixamo:

- **T-pose** (lengan horizontal, di-rotate lewat skin weight, halus di bahu)
- **SATU mesh gabungan, TANPA skeleton**, satuan cm, tinggi ≈ 157, menghadap +Z
- **Dibuang** (karena pemblokir auto-rigger menurut Mixamo FAQ):
  - ground plane 2,5 m (`lambert2`) — tak terlihat di render depan tapi fatal buat solver
  - overlay blush melayang (`Cheek_mt`) — "floating parts" ditolak auto-rigger
  - ekor (`Shibahu_Tail1..7`) — "large extra appendages" ditolak auto-rigger
  - outline shell (`*_line`) — permukaan dobel
- 61.997 vertex / 71.988 tris, 6 material bertekstur

| File | Isi |
|---|---|
| `shibahu.fbx` | FBX ASCII 7.4: mesh + UV + normal + material + ref tekstur |
| `shibahu.obj` + `shibahu.mtl` | OBJ standar + material (`map_Kd`, `map_d` untuk rambut) |
| `textures/` | 6 tekstur 2K yang dipakai material |

**Cara pakai di Mixamo (HP maupun desktop):**
1. Upload `shibahu.fbx` (atau zip `shibahu.obj` + `shibahu.mtl` + `textures/`).
2. Di Auto-Rigger, **seret semua marker** ke karakter: CHIN (dagu), WRISTS (pergelangan), ELBOWS (siku), KNEES (lutut), GROIN (selangkangan). Centang *Use Symmetry* supaya kiri-kanan cermin. Marker wajib ditempel sebelum NEXT — kalau tidak muncul "Oops! Please place all markers".
3. Skeleton LOD: Standard (65). NEXT → tunggu rig → pilih animasi → download FBX.
4. Kalau skala terasa aneh, ingat sumbernya cm (tinggi ≈ 157).

**Yang sengaja tidak ada di varian ini:** ekor, blush overlay, dan outline.
Untuk game, pasang lagi ekor/cheek dari hasil pipeline glTF (`tools/fbx2gltf/fbx2gltf.py` + `ASSETS/shibahu.zip`) setelah rig Mixamo jadi — atau pakai secondary motion (spring bone) di engine.

Bukti file valid: `RENDERS/obj_file_verify.png` = render yang dibuat LANGSUNG dari `shibahu.obj` ini (T-pose terlihat di situ).

Riwayat: v1 (commit 39d5cdf) masih memuat ground plane/cheek/ekor dan memicu "Unknown error while generating motion" di Mixamo. v2 = isi folder ini sekarang.
