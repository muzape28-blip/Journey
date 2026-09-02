# UAT Log — E-strafe (Infinix Smart 9 HD, Helio G50 / PowerVR GE8320, 720×1600)

Format: `#nomor | build | cek | hasil (✅/❌) | catatan`

## S1–S2 — UAT #1 (build pertama)

| # | Cek | Hasil | Catatan |
|---|-----|-------|---------|
| 1 | Tahan stick ke KANAN → Shibahu jalan lurus ke kanan | ⬜ | wajib: NOL lingkaran |
| 2 | Saat strafe, dunia TIDAK berputar sendiri | ⬜ | vaksin bug ZDEV |
| 3 | Drag kanan = orbit kamera; drag kiri = joystick; tak tertukar | ⬜ | |
| 4 | Joystick timbul di titik sentuh, knob bulat, snap-back mulus | ⬜ | |
| 5 | Tap murni di zona kiri TIDAK menggerakkan karakter | ⬜ | |
| 6 | Jog maju: animasi Jog Forward, tidak sempoyongan maju-mundur | ⬜ | sanitasi hips-XZ |
| 7 | Strafe kiri/kanan pakai klip Jog Forward Left/Right | ⬜ | |
| 8 | Netral → idle nana kawaii | ⬜ | |
| 9 | FPS ≥ 30 di padang rumput (DIAG kiri-atas) | ⬜ | tahap sedang |
| 10 | Orientasi Shibahu benar (tidak lari mundur) | ⬜ | knob: orient_fix_deg |
| 11 | Kamera tidak menembus tanah | ⬜ | spring arm |
| 12 | Minimize/restore app → tidak ada ghost-stick | ⬜ | release_all |

## Knob yang boleh dibumbui (S3)
`JOG_SPEED`, `ACCEL`, `DECEL`, `TURN_RATE`, `sens` kamera, `DZ`, `BASE_R`,
`orient_fix_deg`, `play_rate`, arah tanda yaw/pitch di camera_rig.
