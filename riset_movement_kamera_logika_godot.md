# Riset: Logika Movement (Walking/Jogging/Running/Sprint) + Logika Kamera — Awal Pembuatan Game, Target Godot

> **Status dokumen**: laporan riset 45+ menit (perintah user 2026-09-02, mulai ±16:11 WIB, T0 tercatat agen 16:14:39 WIB / epoch 1788340479).
> **Label bukti**: `[RESMI]` dokumentasi engine/developer; `[KODE]` saya BACA LANGSUNG source-nya (repo/demo); `[KOMUNITAS]` wiki/frame-count/analisis independen; `[ARTIKEL]` tulisan industri pihak-ketiga; `[OPINI-AGEN]` sintesis/simpulan saya (jelas ditandai).
> Dokumen riset user sebelumnya (`riset_arpg_openworld_mobile.md`, `riset_konfigurasi_arpg_openworld.md`, `riset_fisika_jubah_cape_mobile.md`) sudah saya baca ulang dan saya perlakukan sebagai input; di bawah saya kutip secukupnya dengan sumber aslinya.

---

## 0. TL;DR — Apa yang Saya Pahami

1. **ZDEV-RPG gagal bukan karena kurang riset, tapi karena tidak pernah ada SATU PUN yang bisa dimainkan.** Repo itu = gudang aset + dokumen (1 commit "Add files via upload"), tanpa project engine, tanpa kode, tanpa scene, tanpa prioritas. Visinya AAA open-world (Elden Ring/PGR/Where Winds Meet) di HP entry-level — dan tidak ada langkah "movement dulu" sama sekali. Risetnya sendiri berkualitas tinggi dan berlabel bukti; eksekusinya tidak pernah mulai dari inti.
2. **Konsensus industri "awal pembuatan game"**: prototype menjawab *"should we make it"* (murah, cepat, inti loop), vertical slice menjawab *"can we make it"* (Rami Ismail, LTPF). Kegagalan klasik vertical slice = membuktikan visual, bukan core loop. Kanon game-feel (Juice it or lose it 2012; The Art of Screenshake 2013) dan praktik Celeste (coyote time, jump buffer, corner correction) semua bilang: **movement + kamera adalah hal pertama yang harus terasa benar**, dengan aset placeholder.
3. **Movement = beberapa angka, bukan satu angka "speed"**: max speed + acceleration + braking deceleration (UE5 CMC `[RESMI]`: 600 cm/s walk default, accel 2048, braking 2000; air control 0.05). Deceleration harus > acceleration biar berhenti terasa "nempel"; input diagonal wajib di-clamp; semua smoothing harus framerate-independent (exponential damping `1-exp(-λ·Δt)` / critically damped spring `[ARTIKEL Juckett]`).
4. **Walking/jogging/running/sprint** punya angka dunia nyata `[ARTIKEL mocap]`: jalan 2–4 km/j (0.6–1.1 m/s), jog 6–8 (1.7–2.2), lari 10–12 (2.8–3.3), sprint 15+ (4.2+). Di blend space, minimal **3 tier kecepatan bersih**; posisi tiap klip di sumbu = kecepatan aslinya (ukur jarak-per-siklus animasinya!), kalau mismatch → foot sliding; obatnya speed/time warping.
5. **Kamera third-person = spring arm + damped spring + camera-relative input** `[RESMI Unreal & Godot]`. Godot punya semua padanannya native: `SpringArm3D` (spring_length, margin, exclude player), `CharacterBody3D` (floor_max_angle 45°, floor_snap_length 0.1, move_and_slide), `AnimationTree` (BlendSpace1D/2D, StateMachine, OneShot). Demo resmi Godot (3d/platformer) memberi angka rujukan nyata `[KODE]`: MAX_SPEED 6.0, ACCEL/DEACCEL 14, snap-turn >140°, jump variable (lepas tombol → vy×0.7), kamera min/max distance 0.5–3.5 + autoturn 3-ray.
6. **Mobile**: joystick kiri + area drag kamera kanan; kecepatan = besar kemiringan joystick (velocity-control; Genshin walk/run = sedikit vs penuh `[RESMI guide]`); dodge terarah satu-jempol via drag-dari-tombol (paten NetEase US11185764B2 `[PATEN via riset user]`); FOV third-person nyaman 75–85°, HP mengekspos "jarak kamera" bukan FOV; dead zone ±20–30% radial.
7. **Mapping konkret ke Godot untuk Shibahu + arena rumput/gurun** sudah saya susun (bab 5) sebagai *proposal* — belum diverifikasi runtime karena sandbox tidak bisa menjalankan Godot; jalur verifikasi hidup = GitHub Actions (barichello/godot-ci) ekspor Web/APK.

---

## 1. Postmortem ZDEV-RPG — Kenapa Proyek Itu Gagal

### 1.1 Fakta isi repo `[KODE — saya clone & baca semua file, 2026-09-02]`

| Item | Isi | Catatan teknis saya |
|---|---|---|
| Commit | **1 buah**: `f8b0194 "Add files via upload"` | Tidak ada sejarah iterasi; repo = tempat taruh file, bukan proyek |
| `README.md` | Tema ARPG open world; referensi Epic Conquest, Punishing Gray Raven, Elden Ring, Where Winds Meet; fitur: combat, skills, touch pad movement, jump, dodge, parry, berbagai senjata, adventure, map; "tampilan carachter second person"; bahasa: rust, kotlin, java, C#, C++, python, html, js "(dll)"; device test: **INFINIX SMART9 HD ARMV7** | Daftar 8+ bahasa = **tidak ada keputusan engine/stack sama sekali** |
| `AGENTS.md` | Universal agent operating agreement (jujur + meticulous) | Sama dengan yang mengikat saya sekarang |
| `riset_konfigurasi_arpg_openworld.md` | 31 KB — kamera spring arm, damping, lock-on ER/GoW/HFW/AC/Wukong/Genshin, dodge i-frame per game, floor detection, first spawn, input set, buffering, state machine | Kualitas tinggi, berlabel bukti |
| `riset_arpg_openworld_mobile.md` | 30 KB — versi mobile: menu kamera Genshin/ToF/WuWa/WWMeets, i-frame dash Genshin 40ms+300ms, paten NetEase dodge-drag US11185764B2, paten Microsoft 8523677 explorer/ready, floor/climbing/swim/glide, respawn per game | Sama, tinggi |
| `riset_fisika_jubah_cape_mobile.md` | 27 KB — Verlet integration, constraint, spring-bone, wind relative-velocity | Di luar fokus turn ini, saya cek struktur headings saja |
| `desert.fbx` | 1 mesh, 200.337 verts, **66.779 tris**, 0 joints; bounds ±9.780 unit; tinggi −980…+306 | Kalau satuannya cm (konvensi FBX umum) ≈ **195×195 m**, relief ±10 m — gurun datar ber-ripple; render top/front saya buat (lihat RENDERS) |
| `Hair.fbx` | 2 mesh, 6.091 tris, 0 joints | Aset rambut karakter |
| `Standing Dodge Forward.fbx` | Berisi referensi **`mixamorig`×439** + tekstur "Arissa" (karakter demo Mixamo) | = animasi dodge dari **Mixamo** — pipeline lama kita yang dulu bermasalah di saga EXPORT |
| `Texture.rar` | **Tidak bisa dibuka di sandbox** (tak ada unrar/7z) | Jujur: isi belum saya lihat |

### 1.2 Diagnosis kegagalan `[OPINI-AGEN, berdasarkan fakta 1.1]`

1. **Tidak ada executable game sama sekali.** Nol project engine, nol scene, nol script. Seluruh "proyek" adalah persiapan (aset + riset). Dalam kosakata bab 2: tidak ada prototype, apalagi vertical slice — lompatan langsung dari konsep ke wishlist fitur AAA.
2. **Tidak ada keputusan teknologi.** README menyebut 8+ bahasa; riset membahas Unreal/Unity sebagai "blueprint" tanpa memilih; device target entry-level. Tanpa keputusan, tidak ada yang bisa dibangun.
3. **Scope vs device bertabrakan keras.** ARPG open-world ala Elden Ring di **Infinix Smart 9 HD** (terverifikasi turn ini: Helio G50 = 8× Cortex-A53, GPU **PowerVR GE8320**, RAM 3 GB, Android 14 Go Edition `[ARTIKEL specs]`) — bahkan game AAA mobile (Genshin) tidak menarget kelas ini. Catatan README "ARMV7" tidak tepat: A53 adalah ARMv8 64-bit (walau OS Go edition bisa 32-bit) — relevan untuk pilihan export template nanti.
4. **Pipeline aset tidak disiplin**: satu commit upload mentah; FBX tanpa konversi/LOD; RAR yang bahkan tidak terbuka; animasi dari Mixamo (pipeline yang kita tahu dari saga EXPORT sering gagal retarget).
5. **Urutan kerja terbalik**: riset AAA (i-frame Elden Ring, one-shot GoW) dilakukan **sebelum** ada karakter yang bisa berjalan 1 meter. Riset itu berharga, tapi tidak ada wadah untuk memakainya.
6. **Yang benar dari proyek lama**: metodologi riset (label bukti, kejujuran "tidak ditemukan"), koleksi referensi desain, dan aset awal (desert = kandidat lantai arena; Hair; dodge anim). Ini modal, bukan sampah.

**Kesimpulan postmortem**: kegagalan = *execution gap* (tidak ada playable core, tidak ada engine decision, scope tak terpotong), bukan *knowledge gap*. Perbaikan = mulai dari vertical slice movement+kamera di Godot dengan aset yang ada (Shibahu + padang), angka dari bab 3–4.

---

## 2. Prinsip "Awal Pembuatan Game" — Kenapa Movement & Kamera Dulu

- **Prototype = "should", vertical slice = "can"** `[ARTIKEL — Rami Ismail, ltpf.ramiismail.com]`. Prototype murah-cepat untuk tahu apakah loop-nya layak dikejar; vertical slice membuktikan kamu *mampu* memproduksinya (pipeline, budget, kecepatan kerja).
- **Kegagalan klasik vertical slice** `[ARTIKEL — tonogameconsultants]`: membuktikan visual bukan core loop; effort "hero mode" yang tidak mencerminkan kecepatan produksi; tidak menjawab pertanyaan scope/waktu/risiko.
- **Kanon game feel**: *Juice it or lose it* (Jonasson & Purho, 2012) dan *The Art of Screenshake* (Jan Willem Nijman/Vlambeer, 2013) `[ARTIKEL + talk]` — game harus *merespons* setiap input pemain; daftar ±30 trik Vlambeer berangkat dari shooter dasar yang movement-nya sudah benar dulu.
- **Respons & pemaafan input**: klaim pihak-ketiga bahwa jump harus merespons <50 ms dan coyote time ~6 frame `[ARTIKEL mygamedesign]`; data Celeste: coyote 6 frame + jump buffer 4 frame menaikkan keberhasilan lompatan yang diniatkan dari ~78% → 99.2% `[ARTIKEL, konsisten dengan thread resmi dev Celeste di r/gamedev]`; perbandingan Mario Odyssey 8/6, Hollow Knight 4/3 `[ARTIKEL sama]`. Dev Celeste sendiri: teknik-teknik ini mengubah input biner jadi gerakan "manusiawi"; timing <120 ms pada manusia pada dasarnya noise, jadi memaafkan pemain = menghapus trial-and-error acak `[KOMUNITAS — thread r/gamedev 2020]`.
- **Greyboxing** `[ARTIKEL jackw-gamedesign, Roblox create docs, yamii guide]`: block-out level dengan bentuk sederhana SEBELUM art, untuk mengetes scale & flow ("does the player fit through doors?"); pakai referensi skala nyata (pintu ≈2.1 m, manusia ≈1.8 m — kita: Shibahu 1.575 m). Doom meng-greybox arena untuk menguji lompatan & cover sebelum level jadi klasik.
- **Implikasi untuk kita**: urutan benar = (1) karakter berjalan/jog/lari/sprint terasa enak di arena greybox, (2) kamera nyaman di layar 6.7" 720p, (3) baru combat/parry/dodge/peta besar. Placeholder dulu (bahkan kapsul + balok), Shibahu + rumput masuk begitu movement terbukti.

---

## 3. Logika Movement — Angka & Pola yang Saya Kumpulkan

### 3.1 Kecepatan: dunia nyata vs game

| Tier | Dunia nyata `[ARTIKEL mocaponline]` | Rujukan game |
|---|---|---|
| Walk | 2–4 km/j = 0.6–1.1 m/s | UE blend "walk @2 m/s"; UE5 template WalkSpeed 500 cm/s |
| Jog | 6–8 km/j = 1.7–2.2 m/s | "Jog 300–400 u/s" (UE) |
| Run | 10–12 km/j = 2.8–3.3 m/s | "Run 500–600 u/s"; UE5 CMC default MaxWalkSpeed 600 cm/s = 6 m/s (nilai game, lebih cepat dari manusia) |
| Sprint | 15+ km/j = 4.2+ m/s | "Sprint 700+ u/s"; template SprintSpeed 900 cm/s |

- **UE5 CharacterMovementComponent** `[RESMI via uhiyama-lab]`: MaxAcceleration 2048 cm/s², BrakingDecelerationWalking 2000, JumpZVelocity 420, AirControl 0.05. "Speed adalah TIGA angka" (ceiling + ramp-up + brake); game action terasa snappy karena accel/braking tinggi.
- **Lompatan**: tinggi puncak = vz²/(2g); hang time = 2·vz/g; trik "hilangkan floaty" = naikkan GravityScale **dan** naikkan JumpZVelocity bersamaan `[RESMI UE]`.
- **Godot 3D Platformer Demo** `[KODE — saya baca player.gd dari godotengine/godot-demo-projects]`: `MAX_SPEED 6.0`, `ACCEL 14.0`, `DEACCEL 14.0`, `AIR_ACCEL_FACTOR 0.5`, `JUMP_VELOCITY 12.5`, `SHARP_TURN_THRESHOLD deg_to_rad(140)` (belok >140° = hadap langsung, jangan lerp), `TURN_SPEED 40` dipakai sebagai `1/speed * 40` (makin pelan, putaran relatif makin cepat — pola menarik), **variable jump height** (lepas tombol jump saat naik → `vertical_velocity *= 0.7`), input **camera-relative** (`cam_basis * Vector3(move.x,0,move.y)` lalu y=0), gravity via `velocity += get_gravity()*delta`, dan blend AnimationTree per-frame: `run = hspeed/MAX_SPEED`, `speed-blend = minf(1, hspeed/(MAX*0.5))`, `state` FLOOR/AIR, `air_dir`, `gun`.
- **Akselerasi/decelerasi rasa**: deceleration > acceleration `[ARTIKEL Amazon GameMaker "Juicing Your Movements": aSpeed 0.2 vs dSpeed 0.5]`; clamping kecepatan diagonal wajib `[forum gamedev.se]`; semua smoothing harus `1-exp(-λ·Δt)` supaya identik di 30/60/144 fps `[ARTIKEL; juga disebut di riset user]`.
- **Coyote time & jump buffer**: 0.1 s tiap arah sebagai angka implementasi umum `[KODE tutorial Godot indiegameacademy: COYOTE_TIME_THRESHOLD 0.1, JUMP_BUFFER 0.1]`; data Celeste di atas sebagai acuan rasa.

### 3.2 Walking vs jogging vs running vs sprint — desain transisi

- **Analog magnitude mapping**: kecepatan = fungsi kemiringan joystick (velocity-control: makin jauh dari pusat makin cepat) `[ARTIKEL riset York Univ. Tilt-Touch Synergy]`; Genshin console: "slightly tilt left analog stick" = walk, penuh = run `[RESMI GameWith control guide]`; di mobile Genshin ada toggle run/walk terpisah + tombol sprint `[RESMI sama]`. Pola kita: deadzone 0.15 → tilt memetakan walk→run; sprint = tombol/hold atau tilt >0.9.
- **Blend space minimal 3 tier bersih** `[ARTIKEL mocaponline]`: idle@0, walk@~1.5–2, jog/run@~3–4, sprint@~5–6 (dalam m/s Godot); posisi klip = kecepatan aktual yang diukur dari jarak-per-siklus animasi; jika klip "terlihat 8 m/s" dipasang di 5 m/s → foot sliding.
- **Sprint + stamina** `[ARTIKEL tutorial UE5]`: walk 300 / sprint 600 cm/s; drain tick 0.1–0.2 s; upgrade wajib: recovery delay setelah stop, blokir sprint sampai stamina di atas threshold, drain hanya saat benar-benar bergerak, state "lelah". Untuk vertikal slice v1 kita: sprint tanpa stamina dulu (jaga scope), stamina masuk babak combat.

### 3.3 Grounding / floor

- **Godot `CharacterBody3D`** `[RESMI docs 4.7 — saya baca halaman class]`: `motion_mode` grounded/floating; `floor_max_angle` **0.7853982 rad (45°)**; `floor_snap_length` **0.1**; `floor_stop_on_slope` true; `floor_constant_speed` false; `max_slides` 6; `safe_margin` 0.001; `wall_min_slide_angle` 0.2617994 (15°); method `move_and_slide()` sekali per `_physics_process`; **`is_on_floor()` basi jika dipanggil sebelum move_and_slide frame yang sama** (pola benar: move dulu, cek kemudian); `get_floor_normal()/get_floor_angle()/get_real_velocity()`.
- UE: WalkableFloorAngle default 45°, aturan komunitas 50–55° `[RESMI+KOMUNITAS via riset user]`; Unity `isGrounded` 1-frame-delay → dev pro pakai spherecast custom `[RESMI+KOMUNITAS riset user]`; foot IK 2-bone + speed warping = pembeda AAA vs murahan di third-person `[riset user, pola industri]`.
- Untuk v1: andalkan `floor_snap_length` + `floor_max_angle` bawaan; spherecast custom hanya jika jump-buffer terasa salah; foot IK (SkeletonIK3D + raycast per kaki `[ARTIKEL uhiyama-lab Godot]`) = babak 2, setelah movement terbukti.

### 3.4 Root motion vs in-place

- **In-place**: responsif (input → gerak instan), mudah di-tune, ramah jaringan & fisika (knockback, platform bergerak) `[ARTIKEL salivity + mocaponline]`. **Root motion**: kaki presisi nol sliding, momentum authored; tapi terasa laggy untuk input cepat.
- **Pola hibrida dominan** `[ARTIKEL sama + forum UE]`: locomotion in-place (dikode), **dodge/attack/landing = root motion** (UE: "Root Motion from Montages Only"); jump biasanya horizontal dari kode + vertikal opsional root motion.
- **Di Godot**: root motion track diset di AnimationPlayer, dibaca via `AnimationTree.get_root_motion_position()/delta` `[ARTIKEL mocaponline Godot guide]`. Untuk Dodge (Mixamo Arissa atau pengganti) nanti: OneShot node; kalau klip ber-root-motion, terapkan ke velocity saat state Dodge.
- **Relevansi 6 klip Cinevva**: sebelum dipasang ke BlendSpace, **ukur jarak per siklus** tiap klip walk/run (root delta), biar posisi blend = angka benar; jika siklus tidak cocok kecepatan target → `AnimationNodeTimeScale` (speed warp) `[KODE demo platformer memakai AnimationNodeTimeScale untuk run-blend]`.
- **Turn-to-move vs strafing** `[FORUM/SE + pola BotW]`: turn-to-move (karakter berputar ke arah gerak; kamera auto-follow pelan) = lebih ramah audiens luas & lebih kecil risiko mual; strafing 8-arah = kebutuhan shooter/stealth dan **wajib klip strafe kiri/kanan/mundur** di blend space 2D. Karena 6 klip Cinevva kita TIDAK berisi strafe, keputusan v1 `[OPINI-AGEN]`: **turn-to-move** (persis pola demo Godot + Breath of the Wild); BlendSpace2D strafing = babak combat.
- **Retarget Mixamo→Shibahu di Godot**: addon **MixaBridge** (Godot 4.4+, MIT) `[ARTIKEL repo/asset-lib]` meng-otomatisasi bone-map `mixamorig:*` → `SkeletonProfileHumanoid`, konfigurasi retarget import, dan pembangunan `AnimationLibrary` (termasuk opsi buang root motion). Karena rig Cinevva kita juga mixamorig (22 joints), ini jalur retarget placeholder-animasi yang paling murah nanti.

---

## 4. Logika Kamera

### 4.1 Fondasi: spring arm `[RESMI Unreal docs via riset user + RESMI Godot docs saya baca]`

- Unreal: TargetArmLength 400, bEnableCameraLag + CameraLagSpeed 3.0, probe sphere, socket/target offset.
- Godot `SpringArm3D` `[RESMI class page 4.7]`: `spring_length` (default 1.0), `margin` (0.01 — kamera ditarik sedikit MUNDUR dari titik tabrakan supaya tidak persis di dinding), `shape` (jika kosong & Camera3D anak langsung → pakai **piramida near-plane kamera**; sphere umum karena mulus di tepi), `collision_mask`, `add_excluded_object(RID)` (wajib exclude collider player), `get_hit_length()`.
- Tutorial resmi Godot `[RESMI]`: pola 3 node **Pivot(Node3D, +2 Y) → SpringArm3D(length 3) → Camera3D**; input mouse memutar pivot (pitch clamp `deg_to_rad(75)`); hapus kamera lama.
- Demo resmi follow_camera `[KODE]`: jarak min 0.5 / max 3.5, clamp tinggi 0–2, **autoturn 3 ray** (kiri/tengah/kanan, aperture 25°, putar 50°/s saat sisi terhalang), `set_as_top_level(true)`, look_at target + `angle_v_adjust`.

### 4.2 Smoothing yang benar: damped spring, bukan lerp naif `[ARTIKEL Ryan Juckett — saya baca halaman aslinya]`

Tiga syarat kamera: (1) tanpa diskontinuitas gerak; (2) **tidak boleh kalah cepat dari player** — gaya pengejar sebanding jarak; (3) identik lintas framerate. Solusinya damped spring; **critically damped (ζ=1)** = sampai target secepat mungkin tanpa osilasi — dasar Unity SmoothDamp & kamera AAA. Kode integrasi Juckett: koefisien `posPos/posVel/velPos/velVel` dihitung sekali per (ω, ζ, Δt) — bisa di-cache untuk fixed timestep (pas untuk `_physics_process` Godot). Lerp naif `lerp(a,b,0.1)` per-frame TIDAK framerate-independent `[riset user + artikel]`.

### 4.3 Camera-relative movement, FOV, dead zone, profil

- Input diputar oleh yaw kamera (`cam_basis * input`, y=0) `[KODE demo + pola industri]`.
- FOV third-person nyaman **75–85° (horizontal)**; hindari >110° (fisheye) `[ARTIKEL switchbladegaming]`; di mobile game besar tidak ada slider FOV — yang diekspos **jarak kamera** `[RESMI observasi riset user]`.
- **Koreksi penting yang saya temukan saat baca class page** `[RESMI Godot 4.7]`: `Camera3D.fov` default **75** diukur pada sumbu yang dikunci `keep_aspect` — defaultnya `KEEP_HEIGHT` (Hor+, enum 1), artinya fov = sudut **VERTIKAL**, dan di layar landscape horizontal melebar otomatis. `[OPINI-AGEN — hitungan trig]` Di layar Infinix 1612×720 (aspect 2.239): fov vertikal 75 → horizontal = 2·atan(tan 37.5° × 2.239) ≈ **119°** = jauh di atas zona nyaman! Supaya horizontal ≈ 85–90°, fov vertikal harus ≈ **45–48°**. Ini detail yang gampang bikin mual kalau salah, dan tidak disebut di artikel PC manapun.
- Dead zone stick ±20–30% radial, inner+outer `[riset user, spesifikasi input umum]`.
- Profil per-state (explorer vs ready) `[PATEN Microsoft 8523677 via riset user]`; look-ahead di depan arah gerak, di-smooth `[riset user]`; lock-on = frontal cone + camera view + jarak `[KOMUNITAS analisis ER]`; anti-clip pelengkap = fade transparan karakter `[POLA UMUM riset user]`.

### 4.4 Kamera + kontrol mobile

- Layout standar genre: joystick kiri bawah; **area kanan = drag kamera**; kluster tombol kanan tidak boleh mencuri event area look `[RESMI/WIKI riset user; docs Opsive Virtual Controls]`.
- Dodge satu jempol: tap = dodge arah hadap; tap-tahan-geser = arah vektor geseran, joystick dikunci sementara, fire saat dilepas ATAU melewati threshold L — **paten NetEase US11185764B2** `[PATEN via riset user]`. Alasan desain tertulis di paten: mengurangi misoperation karena dodge terarah normally butuh dua tangan sinkron.
- Where Winds Meet: posisi tombol dodge/skill sedekat mungkin ke jempol dominan karena delay perjalanan jempol merusak timing parry `[WIKI via riset user]`.
- Godot touch API: `InputEventScreenTouch/ScreenDrag`; proyek setting "Emulate Touch from Mouse" ON / "Emulate Mouse from Touch" OFF untuk multitouch benar `[RESMI docs + thread r/godot]`; addon virtual joystick (MarcoFazioRandom/Virtual-Joystick-Godot) mode Fixed/Dynamic/Following + dead zone + clamp `[ARTIKEL repo]`.
- Motion sickness: camera-shake OFF toggle, FOV wajar, frame rate stabil `[FORUM/ARTIKEL]` — relevan untuk layar 90 Hz + GPU lemah (stabil 30 fps lebih baik daripada 40–70 yang naik-turun).

---

## 5. Proposal Mapping ke Godot — Vertical Slice Shibahu `[OPINI-AGEN / PROPOSAL, belum diverifikasi runtime]`

**Skala** `[KODE EXPORT/README + FORUM]`: Shibahu v5+ sudah diekspor dalam **meter** (tinggi 1.575 m) → aman. `desert.fbx` mentah kemungkinan cm (±9.780 unit): saat import FBX di Godot, perilaku skala ufbx bervariasi per aset (komunitas melaporkan perlu "root scale 100" untuk aset cm tertentu) → **wajib dicek visual saat import**; kalau benar cm, arena = ±98 m per sisi (masuk akal untuk arena), kalau ternyata meter = 19.5 km (pasti salah).
**Scene tree**:
```
Player (CharacterBody3D, CapsuleShape3D r0.3 h1.2)
├─ Shibahu (MeshInstance3D / instantiated glb rigged) + AnimationTree
├─ Pivot (Node3D, y ≈ 1.35)
│   └─ SpringArm3D (spring_length 3.0, margin 0.1, shape SphereShape3D 0.15, exclude Player RID)
│       └─ Camera3D (fov VERTIKAL 45–48 → ±85–90° horizontal di 20:9, pitch clamp ±75° lewat rotasi pivot)
```
**Angka v1** (sumber di bab 3): walk 1.4, jog 2.4, run 3.8, sprint 5.5 m/s; accel 14–20 m/s², decel ≥ accel (pakai pola `approach`/exponential); snap-turn >140°; TURN ~ pola `1/speed*40` demo; coyote 0.1 s, buffer 0.12 s, variable jump (×0.7); gravity default Godot 9.8 (jump height target ±0.8 m → vz ≈ 4 m/s).
**Animasi v1**: AnimationTree = StateMachine{ Locomotion(BlendSpace1D: idle@0, walk@1.4, run@3.8; jog@2.4 jika klip ada), JumpStart, Fall(OneShot/blend) }; 6 klip Cinevva dipetakan SETELAH diukur stride-nya; TimeScale untuk koreksi.
**Kamera v1**: pivot yaw/pitch dari drag kanan (sensitivitas ≈0.006 rad/px, kalibrasi di device), SpringArm bawaan untuk collision; autoturn 3-ray & look-ahead = babak 2.
**Touch v1**: addon Virtual-Joystick (Dynamic, deadzone 0.15, clamp 1.0) → aksi `move_*`; sprint = tombol kecil dekat joystick; tilt-mapping walk→run otomatis dari magnitude.
**Performa** `[ARTIKEL gtsu/bugnet, pola resmi Godot]`: renderer **Compatibility (`gl_compatibility`, GLES 3.0)** — "safety net for the low end"; target **30 fps stabil** (cap `Engine.max_fps = 30`; stabil lebih penting dari tinggi di GPU lemah & menghindari thermal throttle); 720p; **draw call: <200 aman, >500 thermal-throttle di chip budget** → rumput/cards wajib **MultiMeshInstance3D** (ribuan instance = 1 draw call) + atlas tekstur; kompresi **ETC2/ASTC** saat import; lighting statis di-bake; **GPUParticles TIDAK jalan di Compatibility** → CPUParticles; tekstur ≤1K; desert 66.8k tris wajib decimate/pakai sebagian atau ganti lantai GRASS 07_ground; dan **jangan percaya FPS editor** — profil wajib di device asli (remote debugger via USB; frame time <33.3 ms untuk 30 fps).
**Physics interpolation** `[KODE — demo 3d/physics_interpolation, renderer Compatibility]`: fixed-timestep interpolation bikin gerak terlihat mulus walau render-fps ≠ physics tick — **kunci untuk cap 30 fps di device lemah** (physics 60 Hz + render 30 + interpolation = mulus). Caveat resmi: sedikit latency ekstra & objek teleport perlu `reset_physics_interpolation()` (dipakai di semua demo karakter setelah respawn — saya lihat langsung di player.gd & cubio.gd). Catatan kontras `[KODE]`: demo kinematic_character memakai `hvel.lerp(target, accel*delta)` — lerp naif ber-delta yang justru diperingatkan Juckett tidak konsisten lintas framerate; pakai pola exponential/spring kita, jangan tiru mentah.
**Referensi demo resmi lain** `[KODE — ls-tree godot-demo-projects]`: `3d/kinematic_character`, `3d/rigidbody_character`, `3d/ik` (foot IK babak 2), `3d/navigation`, `3d/occlusion_culling_mesh_lod` (performa), `3d/physics_interpolation` — semua tersedia untuk dirujuk babak berikutnya.
**Verifikasi hidup**: sandbox TIDAK bisa menjalankan Godot (download biner diblokir — terbukti turn lalu); jalur = GitHub Actions `barichello/godot-ci` headless export Web + Android → artifact APK yang kamu install langsung di Infinix (sideload, bukan Play Store, jadi isu 64-bit Play tidak menghalangi; A53 = 64-bit anyway).

---

## 6. Log Waktu (WIB, dari timestamp tool turn ini)

| Waktu | Kegiatan |
|---|---|
| 16:14:39 | T0; clone ZDEV-RPG → /tmp/zdev |
| 16:15–16:16 | Baca README/AGENTS/3 riset; inventory aset; konversi desert.fbx & Hair.fbx; strings Mixamo; Texture.rar gagal dibuka |
| 16:17–16:18 | Search: speed m/s & UE5 CMC; Godot CharacterBody3D/SpringArm docs; vertical slice; mobile touch; clone godot-demo-projects (sparse 3d/platformer); baca player.gd + follow_camera.gd + player.tscn; root motion; FOV; screenshake/game feel |
| 16:19–16:20 | Baca riset mobile user §1–5; Juckett damped springs (chunk 0 & 3; chunk 4 proxy error); BlendSpace1D class page; Godot touch API |
| 16:21–16:22 | armv7/Godot4 compat; Genshin walk/run tilt; CharacterBody3D class resmi; coyote/buffer; Infinix Smart 9 HD specs |
| 16:22–16:24 | Render desert top/front (lihat gambar); statistik shibahu.glb (71.988 tris, 0 skin — cocok angka lama); AnimationTree tutorial resmi; SpringArm3D class resmi; stamina/sprint |
| 16:24+ | Menyusun dokumen ini |

**Catatan kejujuran**: laporan dikirim ≥ T0+45 menit sesuai perintah; jika penyusunan selesai lebih awal, sisa waktu diisi verifikasi tambahan dan/atau tunggu yang saya nyatakan, bukan diam-diam.

## 7. Gap / Belum Terverifikasi (jujur)

1. Tidak ada satu baris pun kode Godot yang saya JALANKAN turn ini (sandbox tanpa engine). Semua klaim Godot = docs/demo yang saya baca (`[RESMI]/[KODE-baca]`), bukan runtime-proof.
2. `Texture.rar` belum terbuka; isi tidak diketahui.
3. `desert.fbx` satuan cm → 195 m adalah asumsi konvensi, belum dikonfirmasi pembuat aset.
4. Parser fbx2gltf saya gagal pada `Standing Dodge Forward.fbx` (prop type 'b') dan `EXPORT/shibahu.fbx` — keterbatasan tool saya, bukan bukti file rusak (glb-nya terbaca normal).
5. Nama persis 6 klip Cinevva tidak tersimpan di repo (perlu unduh ulang untuk verifikasi; angka stride belum diukur).
6. Angka kenyamanan FOV & "<50 ms" berasal dari artikel pihak ketiga, bukan dokumen studio.
7. Perilaku Vulkan vs GLES di Helio G50/Android Go hanya bisa diputuskan lewat APK test di device kamu.
