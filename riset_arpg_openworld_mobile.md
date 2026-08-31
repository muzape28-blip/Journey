# Riset: Kamera, Dodge, Floor, Spawn & Kontrol Dasar pada ARPG Openworld Third-Person Mobile AAA

## Cara Membaca Dokumen Ini (Wajib Dibaca Dulu)

Supaya bisa **jujur 100%**, setiap poin di bawah saya beri label status bukti. Alasannya: studio game **tidak pernah** mempublikasikan file konfigurasi internal mereka (nilai persis di source code/config engine). Yang bisa diverifikasi publik cuma 4 jenis:

| Label | Artinya | Tingkat kepercayaan |
|---|---|---|
| **[RESMI]** | Dari menu pengaturan in-game atau pernyataan developer langsung | Tinggi — bisa dicek sendiri di game |
| **[WIKI/KOMUNITAS]** | Hasil testing/reverse-engineering komunitas (Fandom wiki, guide) | Sedang-tinggi — biasanya dites berulang kali oleh banyak pemain, tapi bukan angka resmi dari developer |
| **[PATEN]** | Dari dokumen paten resmi milik studio (USPTO/Google Patents) | Tinggi untuk *logika/algoritma* — ini deskripsi teknis asli dari engineer studio tsb, meski belum tentu 1:1 sama dengan build final di game |
| **[POLA UMUM ENGINE]** | Cara standar industri (dokumentasi resmi Unity/Unreal/Godot) yang **kemungkinan besar** jadi basis game-game ini, tapi bukan konfirmasi bahwa game spesifik X memakai angka persis ini | Sedang — ini benchmark/starting point, bukan bocoran internal |

Kalau saya tidak menemukan sumber yang layak, saya tulis terus terang "tidak ditemukan" — bukan mengarang angka.

## Game yang Dianalisis (semua openworld, third-person, ARPG/action-combat, tersedia di Android)

| Game | Developer/Publisher | Catatan relevansi |
|---|---|---|
| **Genshin Impact** | miHoYo / HoYoverse | Benchmark genre, dokumentasi komunitas paling lengkap |
| **Wuthering Waves** | Kuro Games | Kombat lebih cepat, parry+dodge jadi inti sistem |
| **Tower of Fantasy** | Hotta Studio (Level Infinite/Tencent) | Sistem lock-on kamera paling eksplisit di menu pengaturan |
| **Black Desert Mobile** | Pearl Abyss | Hybrid MMORPG-ARPG, kamera Action Mode |
| **Where Winds Meet** | NetEase / EverStone Studios | Baru rilis mobile Des 2025, kombat parry-heavy ala Sekiro |
| **Infinity Nikki** | Infold Games | Openworld third-person, kuat di sisi kamera & floor/climb/glide (kombatnya minim, jadi bagian dodge tidak relevan untuk game ini) |

---

## 1. LOGIKA KAMERA (Semua Jenis Movement)

### 1.1 Fondasi Teknis Universal: Spring Arm / Camera Collision System

Hampir semua kamera third-person AAA — termasuk genre ini — dibangun di atas satu pola dasar yang disebut **spring arm** (Unreal Engine: `SpringArmComponent`; Godot: `SpringArm3D`; Unity: biasanya custom script atau Cinemachine). **[POLA UMUM ENGINE]**

Cara kerjanya:
- Kamera adalah **child object** dari sebuah "lengan" virtual yang menempel di pivot karakter (biasanya di atas bahu/kepala).
- Lengan ini melakukan **sweep collision test** (raycast/spherecast) dari pivot ke arah *target length* (jarak kamera maksimum).
- Kalau sweep ini kena tembok/objek, kamera otomatis "ditarik masuk" ke titik tabrakan — supaya kamera **tidak pernah menembus geometri** (clip through wall).
- Begitu halangan hilang, lengan "pegas" kembali memanjang ke jarak normal.

Parameter standar yang dikonfigurasi (nama field asli dari Unreal/Unity, dipakai sebagai referensi karena inilah yang tersedia publik di dokumentasi engine):
- **Target Arm Length** — jarak maksimum kamera dari pivot.
- **Socket Offset** — offset posisi kamera dari titik ujung lengan (biasanya sedikit ke kanan/atas untuk over-the-shoulder).
- **Target Offset** — offset titik pivot dari origin karakter.
- **Do Collision Test** — on/off untuk sweep collision di atas.
- **Collision Probe/Resolution** — jumlah ray yang dipakai untuk sweep (makin banyak = makin akurat tapi makin berat).
- **Camera Lag / Movement Smooth Time** — waktu interpolasi kamera mengejar posisi target (inilah yang bikin kamera terasa "smooth" alih-alih kaku menempel).

Sumber: dokumentasi resmi Unreal Engine (forum resmi), Godot Engine docs versi 4.4/stable/latest, dan implementasi open-source `SpringArmComponent` untuk Unity di GitHub yang secara eksplisit menyebut fitur: multiple collision detection via raycast, collision test resolution, TPS camera movement terintegrasi.

### 1.2 Kamera per Kondisi Movement

| Kondisi | Perilaku kamera tipikal | Bukti |
|---|---|---|
| **Diam/Jalan pelan** | Kamera lag rendah, mengikuti smooth, FOV/jarak normal | [POLA UMUM] |
| **Lari/Sprint** | Beberapa game menambah sedikit *FOV kick* atau menjauhkan jarak kamera untuk kesan kecepatan (pola umum genre racing/action, belum terverifikasi persis di tiap game di atas) | [POLA UMUM, belum terverifikasi per-game] |
| **Combat/Lock-on** | Kamera memendek & sedikit lebih dekat ke bahu — pola ini didokumentasikan resmi dalam **paten Microsoft US8523677** ("Camera control for third-person console video game"), yang menjelaskan transisi non-linear antara viewpoint **"explorer"** (lebar, untuk eksplorasi medan) dan viewpoint **"ready"** (sempit, dekat karakter, untuk aiming saat combat) | [PATEN] |
| **Lock-on target** | Tower of Fantasy secara eksplisit punya 3 mode di menu: **Smart** (auto-pilih target terdekat/di depan), **Manual**, dan **Distance** (target berdasarkan jarak, bukan sudut pandang) — bisa diganti di Settings > Camera > Mode of Operation > Locking Method | [RESMI — menu in-game, didokumentasikan Game8 & BlueStacks] |
| **Climbing (panjat dinding)** | Kamera biasanya menyempit jaraknya dan mengorbit mengikuti permukaan dinding; rotasi bebas kadang dibatasi (clamp pitch) supaya tidak "menembus" tembok yang sedang dipanjat | [POLA UMUM, dikonfirmasi tidak langsung lewat pola climbing Genshin di §3.2] |
| **Berenang/Menyelam** | Kamera turun ketinggian, kadang efek distorsi/warna berbeda saat submerged | [POLA UMUM] |
| **Meluncur/Glide** | Kamera menjauh untuk memberi pandangan lebih lebar (dipakai di Infinity Nikki saat Gliding Ability aktif) | [WIKI — Infinity Nikki Fandom, halaman Gliding] |
| **Mode Aim (karakter jarak jauh seperti bow user)** | Di Genshin, mode Aimed Shot mengubah sudut pandang dari third-person ke **hampir first-person**, dan uniknya **tidak me-reset sudut kamera** setelah serangan normal/charged selesai — beda dari kamera combat biasa yang biasanya snap kembali | [WIKI/KOMUNITAS — GameWith Gameplay & Control Guide] |

### 1.3 Contoh Nyata Menu Pengaturan Kamera per Game **[RESMI]**

**Genshin Impact** (dari Settings > Controls & Camera, didokumentasikan Genshin Impact Wiki/Fandom):
- Camera Sensitivity — horizontal & vertical terpisah
- Camera Sensitivity (Aimed Shot Mode) — sensitivitas berbeda khusus saat mode bidik
- Camera Y-Axis Resets Automatically — toggle apakah kamera auto-center secara vertikal
- Default Camera Distance — slider jarak kamera baseline
- Combat Camera Settings — pengaturan khusus perilaku kamera saat masuk combat
- Automatic Boat Camera Angle Correction (Sailing) — auto-koreksi sudut kamera saat naik perahu

**Tower of Fantasy** (Settings > Camera):
- Mode of Operation > Locking Method (Smart/Manual/Distance)
- Camera Vibration on/off (efek shake kamera saat kena hit/skill besar)
- Auto Climb toggle (auto climb berguna saat eksplorasi tapi mengganggu saat combat/kabur — makanya disediakan opsi mati)

**Infinity Nikki** (khusus untuk Photo Mode "Momo's Camera", bukan kamera gameplay utama):
- Rotation (tilt kamera)
- Aperture — dalam satuan f-stop, mengatur depth of field
- Focal Length — dalam mm, menentukan tingkat zoom
- Free Movement Mode (ditambahkan v1.5) — kamera lepas dari karakter untuk komposisi foto

**Where Winds Meet** (mobile, rilis 12 Des 2025):
- Camera sensitivity + acceleration + smoothing — secara eksplisit disebut kritikal untuk timing parry karena delay kecil di kamera berdampak ke reaksi combat pada perangkat mobile

### 1.4 FOV (Field of View) & Jarak Kamera

Tidak ada satupun dari game-game di atas yang mengekspos slider "FOV" literal ke pemain mobile (beda dari game PC yang sering punya FOV slider eksplisit) — yang diekspos biasanya **"jarak kamera" (camera distance)**, karena FOV murni lebih relevan untuk kontrol mouse/PC dan lebih riskan menyebabkan distorsi di device kecil. **[RESMI — observasi dari menu-menu di atas]**

Sebagai konteks standar industri third-person secara umum (bukan klaim spesifik ke game-game di atas): third-person action umumnya berkisar **60°–100°** horizontal, dibanding first-person shooter yang bisa 70°–90°+ dan racing game 80°–100°. Unity sendiri secara default memakai FOV vertikal 60° untuk kamera baru. **[POLA UMUM — sumber: dokumentasi FOV genre, Unity Discussions]**

### 1.5 Teknik Anti-Clipping Selain Spring Arm

Selain "mendorong kamera masuk" saat collision, ada teknik pelengkap: **karakter jadi transparan/fade** saat kamera terlalu dekat (misalnya saat kamera terdorong sangat rapat ke tembok di belakang karakter), supaya model karakter tidak menghalangi pandangan. Ini pola umum yang direplikasi di berbagai implementasi third-person camera (termasuk mod yang secara eksplisit meniru gaya kamera Genshin Impact menyebut fitur "Auto Character Fade"). **[POLA UMUM, konfirmasi tidak langsung]**

---

## 2. LOGIKA DODGE

### 2.1 Genshin Impact — Data i-Frame Paling Presisi yang Berhasil Ditemukan **[WIKI/KOMUNITAS — sudah diuji berulang oleh komunitas]**

Genshin membedakan **dua jenis** invincibility frame:
1. **Hitbox-removing i-frames** — hitbox karakter dinonaktifkan sementara terhadap sebagian besar serangan (tapi TIDAK semua — ada serangan boss tertentu, misalnya *Body Slam* milik Azhdaha, yang tetap bisa kena walau sedang dash).
2. **HP-locking i-frames** — karakter full invulnerable termasuk terhadap status effect (Sheer Cold, Corrosion, Attrition), tapi hitbox TIDAK dihilangkan (jadi status non-damage seperti elemental application tetap bisa "kena", cuma HP-nya tidak berkurang). Jenis ini didapat dari skill elemen tertentu (misal Elemental Skill milik Arlecchino), bukan dari dash biasa.

Angka presisi untuk dash (hitbox-removing i-frame): **dimulai 40 milidetik setelah tombol dash ditekan, dan bertahan selama 300 milidetik.**

Karakter-swap (ganti karakter aktif di party) juga memberi i-frame, tapi jendela waktunya jauh lebih singkat dari dash.

### 2.2 Wuthering Waves — Parry & Dodge Window **[WIKI/KOMUNITAS — sebagian dari guide site, perlakukan sebagai perkiraan komunitas bukan angka resmi]**

- **Parry**: dipicu saat "yellow ring" (weakness halo) overlap dengan animasi serangan musuh — jendela overlap ini disebut berdurasi **~0.5 detik**, dengan toleransi buffer input **0.1–0.2 detik** lebih awal dari titik ideal (artinya sistem cukup permisif terhadap sedikit keterlambatan input akibat lag animasi/device).
- **Dodge**: invulnerability dimulai **hampir instan** setelah input dodge ditekan. **"Perfect Dodge"** butuh timing hampir frame-perfect tepat sebelum kena hit, dan sebagai reward memicu efek **bullet-time** (slow-motion singkat).
- Parry dan dodge berbagi resource **Stamina** yang sama, dan stamina ter-regenerasi setiap kali parry/dodge berhasil (bukan cuma dari waktu diam).
- Catatan kejujuran: angka 0.5 detik ini saya ambil dari guide pihak ketiga yang juga menjual top-up in-game — saya sertakan karena konsisten dengan banyak video/testing komunitas lain, tapi ini **bukan** angka yang dipublikasikan resmi oleh Kuro Games.

### 2.3 Tower of Fantasy — Perfect Dodge & Time Freeze **[WIKI/KOMUNITAS]**

Target di-lock otomatis saat combat. Dodge tersedia relatif bebas (dibatasi stamina, bukan cooldown ketat), dan **"perfect dodge"** (dodge dengan timing tepat) memicu **time freeze** — dalam jendela waktu beku ini pemain bisa ganti senjata (weapon-swap) untuk langsung melepas *discharge skill* dari senjata baru tanpa membuang waktu combo. Combat di ToF disebut komunitasnya cenderung "floaty" dibanding ARPG lain karena penekanan kuat pada aerial combat (serangan sambil melayang).

### 2.4 Black Desert (Catatan Kehati-hatian Penting)

Saya menemukan data presisi untuk **Black Desert Online (versi PC/console NA/EU)**: tombol darurat **"V" (Emergency Escape)** memberi **5 detik invulnerability**, dengan **cooldown 5 menit**. **Ini bukan Black Desert Mobile** — game yang berbeda meski dari studio sama (Pearl Abyss), dan saya **tidak menemukan** angka i-frame/cooldown yang sama persis terverifikasi untuk versi Mobile-nya. Yang terkonfirmasi untuk Black Desert Mobile hanyalah bahwa dodge/evasion adalah kebutuhan combat inti (mengelak serangan telegraphed boss), dikontrol lewat tombol combat yang bisa di-remap. Saya sengaja tidak menebak angka mobile-nya — itu akan melanggar instruksi "jujur" Anda. **[RESMI untuk PC/console; TIDAK DITEMUKAN untuk Mobile]**

### 2.5 Bukti Primer Terkuat: Paten Resmi Soal Logika Input Dodge **[PATEN — sumber primer]**

Ini bagian paling berharga dari riset ini: saya menemukan **paten AS resmi** — **US11185764B2** ("Method for Controlling Game Character"), terdaftar atas nama **Netease (Hangzhou) Network Co., Ltd.** — yang secara harfiah mendeskripsikan **algoritma logika dodge berbasis arah sentuhan** yang dipakai di ARPG mobile buatan Tiongkok:

**Alur logikanya (istilah asli dari paten):**
1. **(S1)** Sistem cek: apakah tombol skill/dodge dilepas langsung setelah ditap (tanpa geser)? → Jika ya: karakter melakukan aksi (dodge/jump/attack — paten eksplisit menyebut ketiganya sebagai contoh) **ke arah hadap karakter saat ini** (arah ini diambil dari kontrol joystick gerak sebelumnya).
2. **(S2)** Jika jari **tidak dilepas** dan mulai **digeser (drag)** dari posisi awal tombol skill: sistem **mengunci joystick gerak utama** — supaya tidak ada konflik input arah antara joystick kiri dan gesture tombol kanan.
3. **(S3)** Sistem menghitung **vektor a** dari titik sentuh awal (P1) ke posisi sentuh saat ini (P2) secara real-time, dan biasanya menampilkan indikator visual mengikuti arah geseran sebagai feedback ke pemain.
4. **(S4)** Aksi (dodge/skill) benar-benar dieksekusi **ke arah vektor a** ini, dipicu oleh SALAH SATU dari dua kondisi: (a) jari dilepas dari layar, ATAU (b) panjang vektor melewati **threshold L** yang sudah ditentukan sebelumnya (artinya sistem bisa fire otomatis begitu geseran cukup jauh, tanpa menunggu jari dilepas — untuk kecepatan reaksi lebih tinggi). Setelah itu joystick gerak kembali di-unlock.

**Kenapa ini penting:** paten ini eksplisit menyebut tombol dodge sebagai salah satu contoh utama ("*the skill button is a dodging skill button... controlling the game character to dodge in the direction of the vector a*"), dan alasan desainnya dijelaskan sendiri oleh penemunya: mengurangi *misoperation rate* — karena secara default, dodge terarah butuh **koordinasi dua tangan** (joystick kiri untuk set arah + tombol kanan untuk trigger), yang sering gagal sinkron justru di momen genting saat pemain panik menghindari serangan. Dengan skema drag-dari-tombol ini, **satu jempol saja** bisa menentukan arah *dan* memicu dodge sekaligus.

Saya juga menemukan paten terkait dari **Tencent Technology (Shenzhen) Co., Ltd.** (US10661164B2 / US20180290058A1, "Method for controlling character movement in game, server, and client") yang membahas sinkronisasi kontrol pergerakan karakter antara client dan server — relevan untuk aspek anti-cheat/lag-compensation, tapi saya tidak berhasil menggali detail teknisnya sedalam paten NetEase di atas, jadi saya sebutkan keberadaannya saja tanpa detail lebih jauh (jujur soal keterbatasan ini).

---

## 3. LOGIKA FLOOR / GROUND

### 3.1 Deteksi Tanah — Pola Standar Engine **[POLA UMUM ENGINE — dokumentasi resmi Unity]**

Pola paling umum (dan hampir pasti jadi basis logika di game-game besar, walau implementasi persisnya proprietary):

- **Metode dasar**: `CharacterController.isGrounded` (Unity) — bernilai true/false berdasar apakah collider karakter menyentuh permukaan di bawahnya pada frame tersebut.
- **Masalah yang didokumentasikan resmi**: `isGrounded` bisa "jitter" (berubah-ubah tidak stabil) terutama di puncak slope atau saat gerak cepat. Solusinya, developer profesional biasanya menambah **raycast/spherecast custom** dari titik kaki karakter sebagai pengecekan tambahan yang lebih stabil.
- **Slope Limit** — parameter sudut kemiringan maksimum yang masih dianggap "bisa dipijak berjalan"; di atas sudut ini karakter dianggap di permukaan curam/dinding dan biasanya slide-down otomatis alih-alih bisa dipijak.
- **Step Offset** — tinggi maksimum "anak tangga"/undakan yang bisa dilewati otomatis tanpa perlu jump eksplisit.
- **Ground Snapping** — supaya karakter tidak "terbang" sesaat setiap turun dari slope curam ke slope landai, sistem secara aktif menempelkan posisi karakter ke permukaan tanah, dan me-reorientasi arah kecepatan (velocity) mengikuti kemiringan permukaan — bukan sekadar diproyeksikan matematis.
- Sistem yang lebih baru (Unity Character Controller package versi fisika) bahkan melakukan **multi-raycast prediktif** (beberapa ray searah gerakan, disebut B/C/E-raycast dalam dokumentasi resminya) untuk mendeteksi perubahan kemiringan **sebelum** karakter benar-benar sampai di sana — mencegah karakter "meluncur"/terlempar di puncak tanjakan tajam.
- Untuk custom controller berbasis capsule (bukan built-in `CharacterController`), pola umum: **SphereCast ke bawah** untuk deteksi awal, lalu diikuti **dua Raycast tambahan** ke masing-masing sisi permukaan yang berdekatan untuk mendapat *normal permukaan* yang akurat (karena SphereCast sendiri menghasilkan normal hasil interpolasi yang kurang presisi di tepi slope).

### 3.2 Floor yang Diperluas ke Dinding: Climbing **[WIKI — Genshin Impact, Game8]**

Contoh paling terdokumentasi: sistem climbing Genshin Impact memakai tombol **Jump yang sama** tapi konteksnya berubah otomatis berdasar apa yang dihadapi karakter:
- Kalau karakter menghadap **dinding yang bisa dipanjat** dan joystick didorong ke arah dinding tsb → karakter otomatis masuk mode **climb**.
- Climbing **mengonsumsi Stamina** secara kontinu.
- Kalau stamina habis saat memanjat → karakter **otomatis lepas dan jatuh** dari dinding (auto-drop).

Secara teknis, ini contoh nyata bagaimana "floor logic" tidak cuma soal tanah datar — deteksi permukaan (surface normal) dipakai untuk membedakan: permukaan horizontal (jalan biasa) vs permukaan vertikal yang "climbable" (butuh tag/material khusus di level design supaya sistem tahu dinding ini boleh dipanjat, bukan sekadar tembok biasa) vs permukaan terlalu curam untuk dipijak biasa.

### 3.3 Air Sebagai "Floor" Alternatif **[WIKI]**

- **Berenang**: begitu karakter masuk ke body of water, sistem berpindah ke swim-state; arah joystick jadi arah berenang. Ada tombol terpisah untuk "berenang cepat" yang juga menguras stamina (pola sama seperti climb — resource-gated movement khusus).
- **Meluncur (Glide)**: dipicu saat karakter jatuh dari ketinggian tertentu (bukan floor biasa) — di Infinity Nikki, kemampuan ini terikat ke outfit tertentu ("Gliding" ability), dan durasinya dibatasi stamina; outfit rarity lebih tinggi (5-star) memberi durasi glide lebih panjang & konsumsi stamina lebih hemat, menurut testing komunitas map-completion.

---

## 4. FIRST SPAWN (Spawn Pertama & Respawn)

Frasa "first spawn" saya pecah jadi dua makna berbeda supaya tidak ambigu — **jujur ke Anda soal ini penting** karena keduanya pakai mekanisme yang cukup berbeda:

### 4.1 (A) Spawn Awal Dunia — Saat Karakter Pertama Dimuat ke Openworld

Pola yang konsisten di genre ini: momen spawn pertama **dibungkus narasi/cutscene**, bukan sekadar karakter "muncul begitu saja". Fungsinya dua: menyembunyikan proses loading aset openworld di background, dan sekaligus jadi tutorial terselubung. **[WIKI — dikonfirmasi kuat untuk Genshin, pola serupa terlihat di game lain tapi tidak saya verifikasi detail satu-satu]**

Contoh terdokumentasi jelas — **Genshin Impact**: prolog membuka dengan Traveler "terbangun setelah rentang waktu tidak diketahui", lalu berjalan di sekitar Cape Oath sampai menemukan Paimon tenggelam di laut. Baru dari titik itu openworld & kontrol dasar diperkenalkan bertahap.

### 4.2 (B) Spawn Point sebagai Objek Teknis di Engine **[POLA UMUM ENGINE + PATEN untuk konteks QA]**

Secara teknis generik (bukan klaim spesifik ke satu game): spawn point biasanya disimpan sebagai **penanda posisi tetap di world-space** (Transform/Vector3), dan saat karakter "di-spawn" di titik itu, engine umumnya melakukan validasi tambahan — misalnya **raycast/sphere-sweep ke bawah** dari titik spawn untuk memastikan karakter benar-benar "menempel" ke permukaan collision/navmesh terdekat, mencegah karakter ter-spawn menembus lantai atau melayang di udara.

Saya juga menemukan paten (US11878249, terkait sistem AI playtesting berbasis reinforcement learning) yang mendefinisikan "spawn point" sebagai objek dunia dengan **spawn threshold** yang bisa berubah-ubah posisi berdasar kondisi tertentu — ini bukan soal spawn point pemain biasa, tapi soal AI agent yang otomatis menjelajah dunia game untuk testing, saya sertakan karena tetap menggambarkan konsep umum "spawn point sebagai objek dengan kondisi pemicu", bukan sekadar titik statis.

### 4.3 Sistem Respawn/Revive Setelah Kalah — Perbandingan Antar Game **[WIKI/RESMI — cukup terverifikasi]**

Ini bagian yang paling terdokumentasi dengan baik:

| Game | Mekanisme revive | Detail |
|---|---|---|
| **Genshin Impact** | Klik "Revive" di layar Game Over | Party respawn di **Teleport Waypoint terdekat yang sudah di-unlock**, HP terisi **35%**. Selain itu, **Statue of The Seven** berfungsi sebagai titik heal pasif (aura healing otomatis saat party berdiri cukup dekat) — beberapa lokasi statue bahkan menempatkan pemain cukup dekat begitu teleport supaya auto-heal langsung aktif, sementara lokasi lain butuh pemain jalan sedikit mendekat dulu |
| **Wuthering Waves** | Fast-travel ke **Resonance Nexus** terdekat | Otomatis me-revive party member yang tumbang **dan** full-heal seluruh party sekaligus (bukan partial seperti Genshin) |
| **Where Winds Meet (mobile)** | Mode solo: auto-prompt tekan tombol untuk respawn | Karakter dipindah ke **checkpoint/shrine aktif terakhir** dengan HP full; progres quest, loot, dan state dunia **di luar titik itu tidak ikut ter-rollback**. Mode co-op punya sistem revive manual antar pemain terpisah |

---

## 5. KONFIGURASI ACTION DASAR (Basic Action Configuration)

### 5.1 Layout Kontrol Standar yang Konsisten Lintas Game **[RESMI/WIKI — dikonfirmasi di Genshin, ToF, Where Winds Meet]**

Semua game di atas (dan hampir seluruh genre ARPG mobile Tiongkok/global) memakai pola dasar yang sama:

| Elemen | Fungsi | Posisi layar tipikal |
|---|---|---|
| Virtual joystick | Gerak/arah karakter | Kiri bawah |
| Area swipe/drag | Kontrol rotasi kamera | Sisi kanan layar (area kosong, bukan tombol spesifik) |
| Tombol Normal Attack | Tap berulang = combo string | Kluster tombol kanan bawah |
| Tombol Charged Attack | Sering **tombol yang sama** dengan Normal Attack tapi ditahan (hold) alih-alih di-tap | Sama seperti Normal Attack |
| Tombol Skill (Elemental Skill/Weapon Skill) | Cooldown-based; sebagian karakter/senjata punya varian **hold** untuk efek berbeda (contoh: Yaoyao di Genshin — hold Skill untuk melempar sasaran lebih presisi) | Kluster kanan, biasanya di atas Attack |
| Tombol Burst/Ultimate | **Energy-gated**, bukan cooldown murni — beda konseptual dari Skill biasa | Kluster kanan, biasanya paling menonjol/besar |
| Tombol Jump | Dobel fungsi jadi trigger climb saat menghadap permukaan climbable | Dekat joystick atau kluster kanan |
| Tombol Sprint | Toggle atau hold tergantung game; di Genshin, **tap dash berulang** justru lebih cepat dari sprint kontinu karena setiap tap memicu i-frame (lihat §2.1) | Dekat joystick |
| Tombol Dodge/Evade | Kadang jadi tombol berdiri sendiri (WuWa, ToF), kadang menyatu dengan gesture dari tombol lain (lihat paten §2.5) | Bervariasi per game |
| Tombol Interact | **Context-sensitive** — hanya muncul dinamis saat dekat objek yang bisa diinteraksi | Muncul dekat objek di layar |
| Mode Aim | Toggle, mengubah sudut kamera (lihat §1.2) untuk karakter jarak jauh | Tombol terpisah, biasanya dekat Attack |

### 5.2 Logika Teknis "Kenapa Tombol Dodge Bisa Diarahkan dengan Geser Jari" **[PATEN — sama seperti §2.5, dilihat dari sudut basic-config]**

Ini poin yang sama dengan paten NetEase di §2.5, tapi relevan juga dimasukkan di sini karena ini **inti dari basic action configuration** genre ini: alih-alih dua tombol terpisah (arah + aksi) yang butuh dua tangan sinkron, banyak ARPG mobile Tiongkok memakai skema **satu tombol dengan drag-to-direction**. State machine-nya (istilah dari klaim paten, disederhanakan):

1. Tap-lepas cepat tanpa geser → aksi dieksekusi ke **arah hadap karakter saat ini**.
2. Tap-tahan-geser → **joystick gerak dikunci sementara** (mencegah input ganda yang saling tabrak), sistem menghitung vektor dari titik-tap-awal ke posisi-jari-sekarang.
3. Aksi dieksekusi ke **arah vektor tsb**, dipicu oleh jari dilepas ATAU panjang geseran melewati ambang batas tertentu (yang mana lebih dulu terjadi).
4. Setelah aksi selesai, joystick otomatis ter-unlock kembali & ikon tombol kembali ke posisi awal.

### 5.3 Perbedaan Kecil Antar Game **[RESMI/WIKI]**

- **Genshin Impact**: Attack/Skill/Burst = 3 tombol yang jelas terpisah secara visual; karakter bow punya mode Aim yang mengganti total gaya kontrol (lihat §1.2).
- **Tower of Fantasy**: Normal Attack (tap), Charge Attack (hold), Aim (khusus senjata tipe bow/pistol/senapan), Weapon Skill, plus tombol **ganti senjata** yang juga berfungsi sebagai combo-extender (ganti senjata di tengah combo memperpanjang rantai serangan).
- **Where Winds Meet (mobile)**: guide resmi komunitasnya secara eksplisit menyarankan menempatkan tombol dodge & skill **sedekat mungkin ke jempol dominan**, karena delay kecil akibat jempol harus "melakukan perjalanan" ke tombol yang jauh terbukti bikin timing parry terasa telat — ini insight praktis soal kenapa posisi tombol di layar kecil itu bukan cuma estetika, tapi langsung memengaruhi keberhasilan mekanik combat presisi tinggi.

---

## Tabel Ringkasan Lintas Game

| Aspek | Genshin Impact | Wuthering Waves | Tower of Fantasy | Where Winds Meet |
|---|---|---|---|---|
| i-Frame dodge | 40ms delay + 300ms durasi (dash) | Invuln ~instan, "Perfect Dodge" = bullet-time | Dodge relatif bebas (stamina-gated), Perfect Dodge = time freeze | Tidak ditemukan angka presisi |
| Sistem parry terpisah? | Tidak ada parry formal | Ya — jendela ~0.5 detik | Tidak ada parry formal | Ya — parry jadi inti combat (gaya Sekiro) |
| Lock-on kamera | Auto, tanpa opsi mode eksplisit | Auto | 3 mode eksplisit (Smart/Manual/Distance) | Tidak ditemukan detail |
| Revive/respawn | Teleport Waypoint terdekat, 35% HP | Resonance Nexus, full heal+revive | Tidak ditemukan detail spesifik | Checkpoint/shrine terakhir, full HP |
| Resource dodge | Stamina | Stamina (dibagi dgn parry) | Stamina | Tidak ditemukan detail |

---

## Catatan Kejujuran Terakhir & Keterbatasan Riset

1. **Tidak satu pun** angka di atas berasal dari file konfigurasi internal/source code studio — itu tidak pernah dipublikasikan dan saya tidak akan mengarang seolah-olah saya punya aksesnya.
2. Bagian yang paling **solid** secara epistemik adalah bagian [PATEN] — karena itu dokumen hukum resmi yang ditulis sendiri oleh engineer studio terkait (NetEase, Tencent, Microsoft), bukan tebakan komunitas.
3. Bagian [WIKI/KOMUNITAS] (terutama angka i-frame Genshin dan window parry WuWa) adalah hasil testing berulang oleh basis pemain sangat besar selama bertahun-tahun, jadi cukup dipercaya sebagai *approximation* yang berguna — tapi tetap bukan angka "resmi dari developer".
4. Untuk **Black Desert Mobile**, saya sengaja tidak memberi angka i-frame karena tidak menemukan sumber yang layak — saya tidak mau mengarang, sesuai instruksi Anda.
5. Kalau tujuan Anda adalah **membangun game sendiri**: gunakan angka-angka di atas sebagai **starting point/benchmark untuk playtesting**, bukan nilai yang di-copy-paste mentah — feel combat sangat bergantung pada frame rate target, ukuran hitbox karakter Anda sendiri, dan device tier yang Anda sasar (mobile Android low-end vs high-end punya toleransi input-lag yang beda jauh).

---

## Daftar Sumber

- Genshin Impact Wiki (Fandom): halaman *Invincibility Frame*, *Settings*, *Fallen Character*, *Statue of The Seven*, *Teleport Waypoint*, *Prologue*
- Game8.co — *List of Controls* & *Recommended Settings Guide (Tower of Fantasy)*
- GameWith — *Genshin Impact Gameplay & Control Guide*
- BlueStacks — *Tower of Fantasy PvP Guide*, *Black Desert Mobile Combat Guide*
- AndroidPolice — *Tower of Fantasy Guide*
- GuildJen, GameMarket.gg, Buffget — *Wuthering Waves Combat Guides*
- Black Desert NA/EU Official Wiki — *Game Controls*
- Unity Technologies — dokumentasi resmi *Character Controller* (Slope Management, Grounding)
- Roystan Ross — *Custom Character Controller in Unity Part 6: Ground Detection*
- Godot Engine — dokumentasi resmi *Spring Arm*
- GitHub — `GloriousPtr/SpringArmComponent`
- US Patent **11185764B2** (Netease (Hangzhou) Network Co., Ltd.) — *Method for Controlling Game Character*, via Google Patents & Justia
- US Patent **10661164B2 / 20180290058A1** (Tencent Technology Shenzhen) — *Method for controlling character movement in game, server, and client*
- US Patent **8523677** (Microsoft) — *Camera control for third-person console video game*
- US Patent **11878249** — *Playtesting coverage with curiosity driven reinforcement learning agents*
- Infinity Nikki Fandom Wiki — halaman *Gliding*; ScreenRant — *Infinity Nikki Camera Settings*
- TechRadar, OnThaSticks, BoostRoom, Google Play — *Where Winds Meet* (kontrol & rilis mobile)
- Pixune — *A Complete Guide to Game Camera Setups*; Grokipedia — *Field of View in Video Games*
- Wikipedia — *Third-person (video games)*, *Spawning (video games)*, *Genshin Impact*, *Wuthering Waves*, *Infinity Nikki*
