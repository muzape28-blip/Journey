# 💤 Harta Karun "HP Gahar" — JANGAN dipasang sekarang

Catatan S3 (2026-09-03): dua aset commit user di `origin/main` diaudit biner
dan dinyatakan **terlalu berat** untuk Infinix Smart 9 HD (Mali/PowerVR GE8320,
OS 32-bit). Atas perintah user: *catat saja untuk kalau sudah punya HP gahar*.
Jangan di-load, di-import, atau di-copy ke `assets/` sampai ada perintah baru.

| Aset di root `origin/main` | Tris | Mesh (draw call) | Tekstur | Vonis |
|---|---|---|---|---|
| `tree.glb` | 256,652 | **2,712** | 11× 1024 | Ribuan draw call = cekik GPU mobile. Bila nanti dipakai: merge semua surface per-material jadi 1 mesh (SurfaceTool) dulu, baru sebar. |
| `alaskan_cliff_rock_9_free (1).glb` | **999,998** | 11 | 3× 2048 | High-poly Poly Haven mentah + 57 MB (lewat rekomendasi GitHub). Bila nanti dipakai: decimate/LOD eksternal dulu. |

## Yang SUDAP dipasang di S3 (aman GE8320)
- `sky.glb` → dome skala 300, unlit, ikut player (3,968 tris, 1 draw call).
- `rock_game_assets (1).glb` → 10 sebaran, skala 0.015–0.04 (1,500 tris each).
- `geranium_flower (1).glb` → 2 aksen spawn, skala 0.35–0.4 (95k tris — batas!).
- Pohon Retro super-low (ZDEV-RPG): tree_rt_1 ×6, tree_rt_3 ×6, small_tree_rt_1 ×8
  (8–94 tris each, tekstur ≤ 310×440).

## HP gahar nanti = boleh coba
1. Merge `tree.glb` → 1–2 draw call, sebar sebagai hutan.
2. Decimate `alaskan` → tebing landmark 10–20k tris.
3. Naikkan grass count & shadow props.
