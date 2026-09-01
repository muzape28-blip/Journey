# EXPORT — Shibahu untuk Mixamo

File hasil pipeline `tools/fbx2gltf` (dari `ASSETS/shibahu.zip`), diekspor dalam **pose bind (A-pose), satuan cm, SATU mesh gabungan, TANPA skeleton** — kondisi ideal untuk auto-rig Mixamo.

| File | Isi |
|---|---|
| `shibahu.fbx` | FBX ASCII 7.4: mesh + UV + normal + material + referensi tekstur |
| `shibahu.obj` + `shibahu.mtl` | OBJ standar + material (map_Kd, map_d untuk rambut) |
| `textures/` | 7 tekstur 2K yang dipakai material |

**Catatan ekspor:**
- Outline shell (`*_line`) **dibuang** supaya auto-rig tidak bingung oleh permukaan dobel.
- Overlay blush (`Cheek_mt`) dan kartu rambut alpha tetap ikut (kosmetik).
- 98.428 vertex / 72.352 tris.

**Cara pakai di Mixamo:**
1. Upload `shibahu.fbx` (atau zip `shibahu.obj` + `shibahu.mtl` + `textures/` sekaligus).
2. Pilih "No skeleton / autorig" — ikuti marker placement Mixamo (pergelangan, siku, lutut, dll).
3. Download hasil rig/animasi sebagai FBX for Unity/Unreal sesuai kebutuhanmu.
4. Kalau skala terasa aneh di Mixamo, ingat sumbernya cm (tinggi ≈ 157 cm).

Bukti file OBJ valid: lihat `RENDERS/obj_file_verify.png` (render yang dibuat LANGSUNG dari file OBJ ini, bukan dari glTF).
