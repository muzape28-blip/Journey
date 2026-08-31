# Riset: Fisika Jubah Berkibar (Cape/Wing) pada ARPG Openworld Third-Person Mobile — Lengkap dengan Perhitungan

## Cara Membaca Dokumen Ini

Sama seperti dokumen sebelumnya, setiap poin diberi label status bukti:

| Label | Artinya |
|---|---|
| **[RUMUS/ALGORITMA TERBUKA]** | Formula matematis dari paper/dokumentasi open-source yang bisa Anda cek & pakai langsung |
| **[RESMI ENGINE]** | Dari dokumentasi resmi Unity/Unreal/plugin fisika populer |
| **[RESMI STUDIO]** | Pernyataan langsung dari developer/studio game terkait — level kepercayaan tertinggi untuk klaim spesifik-game |
| **[PATEN]** | Dokumen hukum resmi |
| **[REKAYASA-BALIK DARI LOGIKA ALGORITMA]** | Ini bagian penting yang perlu jujur saya tandai: untuk pertanyaan "bagaimana perilaku jubah saat idle/walk/run/dodge", saya **tidak** menemukan dokumen resmi yang membedah persis per-state seperti itu untuk tiap game. Yang saya lakukan di Bagian 4 adalah **menurunkan perilaku yang diharapkan secara matematis** dari cara kerja algoritma inti (Bagian 1–3) — ini penalaran teknis yang valid (dan bisa Anda verifikasi sendiri dengan logika yang sama), tapi ini **bukan** kutipan langsung dari config internal game manapun |

## Ringkasan Temuan Terpenting

Temuan paling berharga dari riset ini: **Apple Developer (developer.apple.com)** mempublikasikan artikel resmi berisi penjelasan langsung dari **Infold Games** (studio Infinity Nikki) tentang bagaimana mereka membangun sistem fisika kain mereka — dan itu **persis** menggunakan pendekatan yang sama dengan algoritma open-source klasik yang saya temukan (Bagian 1). Ini bukan kebetulan — ini konfirmasi nyata bahwa teori dan praktik industri di sini nyambung.

---

## 1. FONDASI MATEMATIS: Algoritma Inti di Balik Hampir Semua Simulasi Kain Game

### 1.1 Kenapa Ini Soal Fisika Partikel, Bukan Animasi Tangan

Jubah/cape yang berkibar **tidak** digambar frame-by-frame oleh animator. Yang terjadi: mesh kain (atau rantai tulang/bone) diperlakukan sebagai **sistem partikel** yang posisinya dihitung ulang setiap frame berdasarkan gaya (gravitasi, angin, gerakan karakter) dan batasan jarak (constraint) antar titik. Ada dua pendekatan besar yang dipakai industri (dijelaskan detail di Bagian 2):
- **(A) Full cloth mesh simulation** — setiap vertex mesh kain disimulasikan
- **(B) Spring bone / joint-chain** — hanya rantai beberapa tulang (5–15 bone) yang disimulasikan, mesh kain "menempel" (skinned) ke tulang itu

### 1.2 Algoritma Sumber Terbuka: Verlet Integration **[RUMUS/ALGORITMA TERBUKA]**

Ini adalah algoritma yang sama yang dipakai pertama kali untuk simulasi kain real-time di *Hitman: Codename 47* (2000, IO Interactive, oleh Thomas Jakobsen), dan sampai sekarang jadi basis konseptual hampir semua sistem cloth/spring-bone di game — termasuk yang saya temukan dipakai eksplisit di repo open-source untuk hair/cape anime-style di Unity. Paper aslinya ("Advanced Character Physics") tersedia gratis dan sudah diterjemahkan ulang di GitHub (`krisives/advanced-character-physics`).

**Rumus intinya** — alih-alih menyimpan posisi (x) DAN kecepatan (v) secara terpisah seperti integrasi Euler biasa, Verlet hanya menyimpan **posisi sekarang** dan **posisi sebelumnya**, lalu kecepatan diturunkan secara implisit:

```
x_baru = x + (x - x_lama) + a · Δt²
```

Dalam kode (persis seperti pseudocode aslinya):
```cpp
// x = posisi sekarang, oldx = posisi frame sebelumnya, a = percepatan (gravitasi, dll)
Vector3 temp = x;
x += (x - oldx) + a * dt * dt;
oldx = temp;
```

**Kenapa ini penting untuk "kibasan" yang natural**: suku `(x - oldx)` itu SECARA MATEMATIS adalah jarak yang ditempuh partikel di frame sebelumnya — alias representasi implisit dari kecepatan. Karena kecepatan tidak disimpan eksplisit tapi "diwariskan" dari sejarah posisi, sistem ini **otomatis stabil** dan tidak gampang "meledak" (particle blow-up) dibanding Euler biasa — ini terbukti dari eksperimen open-source yang saya temukan (`gracefkang/Unity-Mass-Spring-Cloth-Simulation`): Euler cenderung "spin out of control" pada stiffness tinggi, sementara Verlet lebih stabil.

**Damping (peredaman)**: cukup dengan mengecilkan koefisien "2" implisit dalam rumus (menjadi mis. 1.99), sedikit energi "dibuang" tiap frame — inilah yang bikin kain akhirnya diam alih-alih berayun selamanya.

### 1.3 Constraint Satisfaction: Menjaga Kain Tetap "Kain" **[RUMUS/ALGORITMA TERBUKA]**

Verlet sendiri cuma menggerakkan partikel individual — supaya partikel-partikel itu **tetap terhubung sebagai kain** (bukan berhamburan bebas), tiap pasangan titik yang bertetangga diberi **distance constraint** (jarak wajib = rest length):

```cpp
delta = x2 - x1;
deltalength = sqrt(delta·delta);
diff = (deltalength - restlength) / deltalength;
x1 -= delta * 0.5 * diff;
x2 += delta * 0.5 * diff;
```

Constraint ini dijalankan berulang (**relaxation iteration**, biasanya 1–10 kali per frame tergantung objek — di Hitman asli, jumlah iterasi disesuaikan per jenis objek) sampai seluruh kain "mengendur" ke bentuk yang valid. Karena Verlet stabil, tidak semua constraint harus 100% terpenuhi di frame yang sama — sistem konvergen bertahap selama beberapa frame, dan justru ketidaksempurnaan kecil inilah yang bikin gerakannya terlihat organik, bukan kaku.

**Optimasi kecepatan** (dipakai di Hitman asli untuk menghindari `sqrt()` yang mahal secara komputasi): approksimasi Taylor orde-1 terhadap fungsi akar:
```cpp
delta = x2 - x1;
delta *= restlength*restlength / (delta·delta + restlength*restlength) - 0.5;
x1 -= delta;
x2 += delta;
```
Ini menurunkan biaya per-constraint jadi **nol** operasi akar kuadrat dan **satu** pembagian saja — krusial untuk budget performa mobile.

**Versi dengan massa berbeda** (`invmass` = 1/massa; particle "jangkar" diberi invmass=0 supaya tidak bisa digerakkan — ini teknik yang dipakai untuk "menjahit" titik atas jubah ke bahu karakter):
```cpp
diff = (deltalength - restlength) / (deltalength * (invmass1 + invmass2));
x1 -= invmass1 * delta * diff;
x2 += invmass2 * delta * diff;
```

### 1.4 Bukti Bahwa Ini Bukan Cuma Teori Akademis **[PATEN]**

Saya menemukan **3 paten resmi** yang secara eksplisit mengutip paper Jakobsen ini sebagai dasar teknis mereka:
- **US7463265B2** & **US7830375B2** ("Constraint schemes for computer simulation of cloth and other materials") — assignee: **Sony Computer Entertainment America** (sekarang Sony Interactive Entertainment), inventor Andrew Graham Styles
- Paten serupa dari pengembang cloth-simulation Korea (**WO2008146972A1** / **US20100070246A1**) yang secara eksplisit menyebut keterbatasan Havok/PhysX untuk cloth spesifik dan mengadopsi pendekatan Verlet yang sama

Ini konfirmasi kuat: algoritma yang sama yang tersedia gratis di internet ini **memang** jadi fondasi produk komersial dari studio besar.

---

## 2. DUA PENDEKATAN TEKNIS DI GAME MODERN

### 2.1 Pendekatan A — Full Cloth Mesh Simulation **[RESMI ENGINE]**

**Unity Cloth** (built-in, `UnityEngine.Cloth`), parameter resmi dari dokumentasi/source Unity:
| Parameter | Fungsi |
|---|---|
| `stretchingStiffness` | resistensi terhadap peregangan (0–1) |
| `bendingStiffness` | resistensi terhadap lipatan (0–1; nilai 0 = simulasi bending dimatikan) |
| `damping` | seberapa cepat gerakan kain kehilangan energi |
| `externalAcceleration` | percepatan konstan eksternal (mis. angin searah tetap) |
| `randomAcceleration` | percepatan acak (untuk efek turbulensi) |
| `useGravity` | on/off gravitasi |
| Self-Collision / Inter-Collision Distance & Stiffness | mencegah kain menembus dirinya sendiri atau kain lain |

Catatan resmi dari Unity: menaikkan `bendingStiffness` tidak selalu cara terbaik bikin kain lebih kaku — **mengurangi jumlah vertex** sering memberi hasil lebih baik SEKALIGUS lebih hemat performa. Ini prinsip optimasi yang sangat relevan untuk mobile.

**Unreal Engine — Chaos Cloth**, secara resmi dideskripsikan Epic sebagai solusi yang bisa jalan **"dari perangkat mobile sampai mesin sinematik kelas atas"**. Parameter kunci: **Density, Drag, Lift** (parameter aerodinamika — lihat Bagian 3), **Iteration Count** (setara relaxation iteration di §1.3), dan fitur **Animation Drive** — sistem yang men-"deform" mesh kain supaya tetap mengikuti Skeletal Mesh animasi induknya (mencegah kain "lepas" terlalu jauh dari pose animasi dasar). Parameter Chaos Cloth bisa diubah real-time lewat Blueprint berdasarkan kondisi gameplay — misalnya Epic sendiri memberi contoh: pakaian karakter bisa bereaksi beda saat di dalam air.

**Obi Cloth** (plugin pihak ketiga populer untuk Unity, dipakai banyak developer indie-ke-menengah): memakai istilah *stiffness* (distance constraint) dan *slack* (compression stiffness), plus *skin constraints* untuk mengatur blending antara hasil animasi vs hasil simulasi fisika per-partikel (skin radius, backstop).

### 2.2 Pendekatan B — Spring Bone / Joint-Chain **[ALGORITMA TERBUKA / RESMI ENGINE]**

Ini pendekatan yang jauh **lebih murah secara komputasi** dan sangat umum dipakai untuk cape/hair/pita di game mobile bergaya anime — karena yang disimulasikan cuma **rantai beberapa tulang** (bukan ratusan vertex mesh).

Saya menemukan implementasi open-source yang menjelaskan algoritmanya persis langkah-demi-langkah (`LoveGraphics/Dynamic-Hair-Bone`, GitHub):
1. **Verlet integration** per-bone — infer kecepatan dari `currentPosition - previousPosition`, terapkan damping, gravitasi, gaya eksternal
2. **Pull toward animation** — hasil fisika di-blend kembali ke posisi target animasi memakai parameter **stiffness** (0 = full fisika bebas, 1 = full ikut animasi)
3. **Distance constraint** — reproyeksi tiap tulang secara iteratif supaya panjang tulang ke induknya tetap sama (urutan root → tip)
4. **Apply to transform** — rotasi tulang induk dihitung dari delta quaternion relatif-terhadap-rest-pose (menghindari gimbal lock ala `LookAt`), lalu posisi anak di-set
5. **Bone root selalu ikut pose animasi 100%** — hanya bone anak yang disimulasikan fisika

Parameter yang konsisten muncul di semua implementasi sejenis (Unity-chan Toon Shader Spring Bone milik **Unity Japan** sendiri, `naelstrof/JigglePhysics`, dll.): **Stiffness** (tarikan balik ke pose animasi) dan **Drag/Damping** (peredam kecepatan per-frame — makin tinggi = makin cepat berhenti "jiggle").

**Magica Cloth** disebut sebagai solusi hybrid yang bisa melakukan **kedua-duanya** (spring bone DAN full cloth) sebagai alternatif performa-tinggi dari Unity Cloth bawaan.

---

## 3. KENAPA JUBAH BERGERAK BAHKAN TANPA "ANGIN" — Prinsip Kecepatan Relatif

### 3.1 Rumus Gaya Angin **[RUMUS/ALGORITMA TERBUKA — sumber akademis]**

Dari literatur simulasi kain (paper "Fine-grained differentiable physics: a yarn-level model for fabrics"), gaya angin pada satu permukaan segitiga kain dihitung:

```
F_w = ρ_w · a · |v_n| · v_n · n_f  +  d_w · v_t
```

Di mana:
- **ρ_w** = densitas udara/angin (seberapa "berat" tekanan angin)
- **a** = luas permukaan segitiga kain
- **n_f** = normal permukaan (arah tegak lurus kain)
- **v_n** = komponen kecepatan **relatif** yang tegak lurus permukaan kain
- **v_t** = komponen kecepatan relatif yang sejajar permukaan (menghasilkan gaya drag/gesekan, dikali koefisien drag **d_w**)

Bentuk `|v_n|·v_n` ini pola **drag kuadratik** standar dalam dinamika fluida (mirip `F = ½·ρ·v²·Cd·A`) — artinya **gaya yang dirasakan kain naik secara kuadratik terhadap kecepatan relatif**, bukan linear. Ini penjelasan matematis kenapa kibasan jubah terasa jauh lebih dramatis saat lari kencang dibanding jalan pelan — bukan cuma "2x lebih cepat gerak = 2x lebih kibas", tapi jauh lebih dari itu.

### 3.2 Prinsip Kunci: yang Dihitung adalah Kecepatan RELATIF

Dokumentasi resmi Obi Physics (plugin cloth Unity) menyatakan eksplisit: *"tidak perlu ada angin sama sekali agar aerodinamika berpengaruh, karena kecepatan relatif antara kain dan angin itulah yang dihitung — bahkan tanpa angin, kalau kain [atau karakternya] bergerak..."* — poin ini **langsung menjawab** pertanyaan Anda: kenapa jubah tetap berkibar dramatis saat karakter lari kencang walau di dunia game itu "tidak ada angin". Secara matematis, `v_n` dan `v_t` di rumus §3.1 dihitung dari **selisih** antara kecepatan angin dunia dan kecepatan kain itu sendiri — jadi karakter yang berlari kencang menciptakan "angin semu" (apparent wind) dari sudut pandang kainnya sendiri, sama seperti tangan Anda terasa ada angin saat dijulurkan keluar jendela mobil yang melaju walau udaranya sendiri diam.

### 3.3 Implementasi Praktis Wind Zone **[RESMI ENGINE]**

**Unity WindZone** — parameter resmi dengan contoh nilai default dari dokumentasi:
```csharp
wind.mode = WindZoneMode.Directional;
wind.windMain = 0.70f;          // kekuatan dasar angin
wind.windTurbulence = 0.1f;     // variasi acak cepat
wind.windPulseMagnitude = 2.0f; // kekuatan "hembusan" periodik
wind.windPulseFrequency = 0.25f;// seberapa sering hembusan terjadi
```

**Teknik turbulensi sederhana** (pola klasik dari diskusi teknis game dev, masih relevan & dipakai luas): angin acak di-blend halus dengan exponential moving average supaya tidak "meledak-ledak" acak tiap frame:
```
w = w * (1 - a) + RandomWind() * a
```

**Unreal Wind Directional Source** — actor bawaan Unreal yang secara native mempengaruhi cloth (dan SpeedTree); pada versi lama (APEX Cloth) cakupannya terbatas ke objek cloth & speedtree saja, versi Chaos Cloth modern lebih fleksibel dan bisa diatur per-material/gameplay-state.

---

## 4. PERILAKU JUBAH PER JENIS MOVEMENT — Analisis & Perhitungan **[REKAYASA-BALIK DARI LOGIKA ALGORITMA]**

**Penting**: bagian ini adalah penurunan logis dari matematika di Bagian 1–3 di atas — bukan kutipan config spesifik satu game (karena, sekali lagi jujur, saya tidak menemukan dokumen publik yang membedah angka persis per-state seperti ini untuk game manapun). Tapi karena rumusnya sudah pasti (dipakai luas & terbukti di paten + Bagian 5 di bawah), penurunan logikanya solid dan bisa Anda pakai langsung sebagai basis tuning game Anda sendiri.

### 4.1 Diam (Idle/Standing)

Kecepatan karakter = 0, jadi **kecepatan relatif** (§3.2) hanya berasal dari `windMain` environment (biasanya di-set kecil, mis. 0.1–0.3 skala Unity) dan `windTurbulence` (noise kecil). Karena F_w berbanding kuadratik dengan `v_n` (§3.1) dan `v_n` di sini kecil, gaya yang bekerja pada kain juga kecil. **Yang dominan justru gravitasi** — Verlet integration (§1.2) dengan `a` = gravitasi murni akan menarik partikel bawah jubah turun ke posisi rest/drape alami, dan parameter **stiffness/pull-toward-animation** (§2.2) menariknya kembali ke pose dasar. Hasil visual: ayunan lambat, amplitudo kecil, dominan naik-turun mengikuti napas/idle-sway animasi dasar, BUKAN mengarah horizontal.

### 4.2 Berjalan (Walk)

Kecepatan root karakter rendah-sedang, konstan (tidak ada percepatan mendadak). Karena Verlet menyimpan **posisi sebelumnya** sebagai representasi implisit kecepatan (§1.2), pergerakan root yang smooth & prediktif ini menghasilkan **lag/trailing kecil yang halus** — tulang/vertex ujung jubah "mengejar" root dengan sedikit keterlambatan yang konstan, disinkronkan ke ritme ayunan pinggul tiap langkah (tiap constraint chain meneruskan impuls kecil dari root ke tip). `v_t` (komponen tangensial di rumus §3.1) mulai terasa tapi masih kecil.

### 4.3 Berlari/Sprint (Run)

Di sinilah rumus kuadratik §3.1 benar-benar terlihat. `v_n` dan `v_t` naik signifikan → `F_w` naik **jauh lebih dari proporsional**. Efek visual: jubah tertarik kencang ke arah **berlawanan dari arah gerak**, cenderung "menempel rata"/streamlined mengikuti arah angin-semu, dengan turbulensi (`windTurbulence`/`randomAcceleration`) menambah riak-riak kecil di tepi kain di atas pola utama itu. Ini alasan kenapa parameter **Drag** & **Lift** (istilah resmi Chaos Cloth, §2.1) krusial di-tuning terpisah dari `Density` — sesuai catatan praktisi (studi kasus Chaos Cloth di §2.1): drag/lift yang pas membuat reaksi kain saat karakter "bergerak melalui ruang" terasa konsisten dengan reaksi kain saat kena angin statis — kalau tidak di-tuning, kain saat lari bisa terasa "mengambang" tidak natural alih-alih "tertiup".

### 4.4 Dodge ke Segala Arah

Ini kasus paling menarik secara matematis. Dodge ditandai oleh **perubahan posisi/kecepatan root yang MENDADAK** (bukan percepatan bertahap seperti walk→run), dalam durasi sangat singkat (dari riset sebelumnya: i-frame dodge Genshin cuma berdurasi 300ms total). Konsekuensi terhadap sistem Verlet (§1.2):

1. Root/bone-teratas jubah (yang menempel ke bahu karakter) berpindah **instan** ke posisi baru.
2. Tapi bone/vertex di ujung jubah **belum tahu** — posisi `oldx`-nya masih dari sebelum dodge terjadi, karena kecepatannya dihitung murni dari riwayat posisinya sendiri, independen dari root.
3. Ini membuat **distance constraint** (§1.3) antara root-baru dan ujung-lama jadi jauh melebihi `restlength` di frame itu juga.
4. Relaxation solver menariknya kembali, tapi **hanya sebagian** per frame (karena iterasi dibatasi demi performa) — sehingga koreksi penuh butuh beberapa frame untuk "mengejar".

**Hasilnya**: efek "whip"/cambukan/lag sesaat di mana ujung jubah tertinggal jauh dari posisi root selama beberapa frame pertama pasca-dodge, lalu "menyusul" dengan gerakan melengkung yang khas. Karena matematika ini **tidak peduli arah** (hanya peduli besar & kecepatan perubahan posisi), efek whip-lag ini terjadi **secara simetris ke segala arah dodge** — dodge ke kiri, kanan, depan, atau belakang menghasilkan pola fisik yang sama, hanya orientasinya yang berbeda mengikuti arah dodge tsb. Inilah justru filosofi asli Jakobsen soal "believability over accuracy" (§1.2) — efek whip yang sedikit "berlebihan"/overshoot inilah yang bikin dodge terasa bertenaga secara visual, bukan bug.

---

## 5. BUKTI KONKRET DARI GAME SUNGGUHAN: Infinity Nikki **[RESMI STUDIO — via Apple Developer]**

Ini temuan paling kuat dari seluruh riset ini. **Apple Developer** (developer.apple.com/news) mempublikasikan artikel resmi berisi penjelasan langsung dari tim **Infold Games** soal bagaimana engine kostum Infinity Nikki dibangun — dan detailnya cocok persis dengan teori di Bagian 1–2:

> Tim mengganti algoritma berbasis-collision tradisional (yang mereka sebut "costly and unstable") dengan **algoritma berbasis-constraint** yang "lebih stabil dan terkontrol" — via **"proprietary skeletal chain algorithms"** (setara Pendekatan B, §2.2) yang dikombinasikan dengan **"enhanced cloth solvers"** (setara Pendekatan A, §2.1).

Poin teknis tambahan yang mereka ungkap:
- Ada **tahap constraint fleksibel & soft-driven saat preprocessing** — supaya pakaian tidak "clipping" ke tubuh karakter bahkan saat gerakan dramatis (ini analog dengan `SpringCollider`/skin-constraint yang saya temukan di Obi Cloth §2.1 dan tutorial spring-bone §2.2)
- Sistem tetap menjaga **siluet artistik yang diinginkan** — khususnya untuk garmen berstruktur (petticoat) yang harus tetap "mengalir seperti kain" TAPI tetap konsisten dengan bentuk konstruksinya (artinya: fisika murni tidak dibiarkan liar 100%, tetap "digiring" ke arah visi seni — sama seperti konsep `stiffness`/pull-toward-animation di §2.2)
- Ada **collision handling antar jenis garmen & antar-layer pakaian** — supaya kombinasi outfit bebas (fitur inti gameplay Infinity Nikki) tetap stabil tanpa vertex saling menembus

Sumber tambahan (kualitas lebih rendah — situs sekunder, bukan pernyataan resmi developer, jadi saya beri bobot lebih rendah) menyebut pipeline produksi kostum: **Marvelous Designer** (software simulasi pola kain standar industri fashion digital) → **Houdini** (VFX prosedural, disebut khusus untuk menghasilkan "pergerakan cair rok dan cape saat berlari atau melompat") → **Unreal Engine 5** (dengan Lumen untuk pencahayaan) → 3ds Max & Photoshop untuk shading/tekstur. Infinity Nikki sendiri terkonfirmasi (Wikipedia) dibangun di atas **Unreal Engine 5**.

---

## 6. GENSHIN IMPACT & GAME LAIN — Kejujuran soal Batas Riset

- **Genshin Impact**: terkonfirmasi (Wikipedia, infobox resmi) memakai **engine Unity**. Ini secara logis berarti kemungkinan besar mereka memakai Unity Cloth bawaan dan/atau versi custom/enhanced di atasnya (pola umum di industri Unity — banyak studio AAA menulis solver cloth sendiri di atas Unity karena keterbatasan built-in Cloth component untuk kasus kompleks). Saya menemukan pernyataan umum dari MiHoYo Fandom Wiki bahwa sejak era Honkai Gakuen 2/3rd (~2015) miHoYo sudah mengembangkan **"physics-based animation system"** in-house yang mensimulasikan gerakan tubuh "berdasarkan formula fisika" — tapi ini pernyataan umum, **bukan** detail teknis spesifik soal cape/jubah. Saya mencari 2 GDC talk resmi Genshin ("Crafting an Anime-Style Open World" dan "Building a Scalable AI System") — keduanya **tidak** membahas cloth simulation secara spesifik berdasarkan deskripsi resmi sesi tersebut. **Kesimpulan jujur: tidak ditemukan sumber resmi sedetail Infinity Nikki untuk Genshin.**
- **Wuthering Waves, Tower of Fantasy, Black Desert Mobile, Where Winds Meet**: saya **tidak menemukan** artikel/talk teknis resmi sedetail kasus Infinity Nikki di atas untuk cloth/cape fisika mereka secara spesifik. Yang bisa dipastikan hanya observasi umum: Wuthering Waves & Infinity Nikki sama-sama Unreal Engine (jadi kemungkinan besar memakai varian Chaos Cloth atau APEX Cloth versi lama, §2.1), sementara Genshin & kemungkinan besar Tower of Fantasy berbasis Unity. Saya **tidak** akan mengarang detail spesifik yang tidak bisa saya verifikasi — jadi bagian ini sengaja saya biarkan terbuka.

---

## 7. OPTIMASI MOBILE — Kenapa Versi Mobile Tidak Bisa Sama Detailnya dengan PC **[RESMI/TEKNIS]**

Karena target Anda adalah **mobile Android**, ini bagian yang tidak boleh dilewatkan:

- **LOD berbasis jarak kamera**: makin jauh karakter dari kamera, resolusi simulasi diturunkan — untuk cloth berarti pindah ke grid mass-spring resolusi lebih rendah; untuk hair/cape berbasis bone berarti mengurangi jumlah bone aktif atau beralih ke mesh statis (skinned, tanpa fisika sama sekali).
- **Culling dinamis**: simulasi **dihentikan total** untuk karakter di luar frustum kamera atau tertutup occlusion — lalu "di-warm-up ulang" selama beberapa frame saat karakter kembali terlihat, supaya tidak ada "loncatan" visual mendadak.
- **CPU vs GPU**: cloth/hair resolusi tinggi biasanya lebih cocok GPU (paralel, banyak vertex sekaligus), sementara cloth resolusi rendah yang gameplay-critical (misalnya cape yang bisa memicu collision event) lebih baik di CPU karena perlu interaksi logika gameplay yang presisi.
- **Reduksi bone/skinning influence**: alat seperti **Simplygon** (dipakai luas industri, didokumentasikan resmi lewat Microsoft Developer Blog) punya fitur khusus "bone reducer" — otomatis memangkas jumlah tulang & bobot skinning per karakter untuk device low-end, karena kalkulasi skinning terbukti berat di CPU/GPU perangkat lawas.
- **Chaos Cloth resmi diklaim Epic bisa jalan dari mobile sampai cinematic-grade** (§2.1) — artinya sistemnya memang dirancang scalable, dengan asumsi developer men-tuning Iteration Count & resolusi mesh secara berbeda per platform.

---

## Tabel Ringkasan Parameter Lintas Sistem

| Sistem | Parameter Kekakuan | Parameter Peredam | Parameter Angin | Constraint Anti-Clipping |
|---|---|---|---|---|
| Unity Cloth | stretchingStiffness, bendingStiffness | damping | externalAcceleration, randomAcceleration | Self/Inter-Collision Distance & Stiffness |
| Unreal Chaos Cloth | (kekakuan built-in solver) | (built-in) | Density, Drag, Lift | Animation Drive, Kinematic Collider |
| Obi Cloth | Distance stiffness, Slack | (via constraint iterasi) | Wind Zone: intensity, turbulence | Skin Radius, Backstop |
| Spring Bone (Dynamic-Hair-Bone dkk) | Stiffness (pull-to-animation) | Drag/velocity decay per frame | gaya eksternal manual | SpringCollider (sphere) |
| Algoritma dasar Jakobsen | restlength (via distance constraint) | koefisien Verlet (2 → 1.99) | `a` (accumulated force) | Projection ke collider |

---

## Catatan Kejujuran Terakhir

1. **Rumus dan algoritma di Bagian 1–3 adalah fakta terverifikasi** — bisa Anda cek sendiri di sumber aslinya, dan terbukti dipakai di paten komersial nyata (Sony) serta produk komersial (Havok Cloth, Chaos Cloth, Obi Physics).
2. **Bagian 4 (perilaku per movement state) adalah penurunan logis**, bukan kutipan config. Saya beri label ini jujur karena, sejauh riset saya, **tidak ada game di daftar ini yang mempublikasikan angka stiffness/damping/drag persis mereka untuk publik** — itu memang tidak pernah dipublikasikan oleh studio manapun.
3. **Bagian 5 (Infinity Nikki) adalah pengecualian langka** — ini kasus di mana studio benar-benar bicara terbuka soal pendekatan teknis mereka (walau tetap tanpa angka parameter persis, karena itu tetap rahasia dagang).
4. Untuk game lain di Bagian 6, saya sengaja **tidak mengarang** kedalaman yang setara Infinity Nikki karena memang tidak saya temukan — kejujuran soal batas riset ini adalah bagian dari instruksi Anda yang saya pegang serius.
5. Kalau Anda ingin coba salah satu algoritma di atas sendiri: mulai dari `krisives/advanced-character-physics` di GitHub (fondasi konsep) atau `LoveGraphics/Dynamic-Hair-Bone` (implementasi Unity siap pakai, sudah open-source dan bisa langsung diadaptasi untuk cape/jubah).

---

## Daftar Sumber

- **GitHub — `krisives/advanced-character-physics`**: terjemahan lengkap paper "Advanced Character Physics" oleh Thomas Jakobsen (Gamasutra, 2003)
- **Pikuma & Envato Tuts+**: penjelasan Verlet integration dengan implementasi C++
- **GitHub — `gracefkang/Unity-Mass-Spring-Cloth-Simulation`**: perbandingan empiris Euler vs Verlet vs Symplectic integrator
- **US Patent 7463265B2 / 7830375B2** (Sony Computer Entertainment America) & **WO2008146972A1**: paten cloth simulation yang mengutip Jakobsen
- **Unity Technologies**: dokumentasi resmi `Cloth` class, `WindZone` class, Manual halaman Cloth & Wind Zones
- **Epic Games**: dokumentasi resmi Chaos Physics/Chaos Cloth (UE 4.27 & UE 5.8)
- **Obi Physics (Virtual Method Studio)**: manual resmi Aerodynamics & Unity-Chan Clothing Tutorial
- **GitHub — `LoveGraphics/Dynamic-Hair-Bone`**, `naelstrof/JigglePhysics`, `unitycoder/Unity-Spring-Bone-Assistant`: implementasi open-source spring bone
- **Noveltech.dev**: tutorial spring bone berbasis repo resmi Unity Japan (Unity-chan Toon Shader)
- **arXiv 2202.00504** ("Fine-grained differentiable physics: a yarn-level model for fabrics"): rumus gaya angin pada kain
- **Apple Developer (developer.apple.com/news)**: artikel resmi wawancara Infold Games soal engine kostum Infinity Nikki
- **Wikipedia**: Genshin Impact (infobox engine), Infinity Nikki (infobox engine)
- **cgguru.com**: studi kasus praktisi Chaos Cloth (hooded cloak simulation)
- **salivity.github.io**: artikel teknis optimasi cloth/hair di game
- **Microsoft Developer Blog (Simplygon)**: automated asset/bone optimization untuk mobile
- **apjcriweb.org**: paper akademis optimasi multi-layer garment simulation di UE Chaos Cloth
