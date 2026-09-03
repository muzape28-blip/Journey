extends Node3D
## WorldBuilder — terrain "tahap sedang" (keputusan user 2026-09-02):
## bukan greybox polos, bukan Field(free).fbx 1.14M tris.
## = PlaneMesh 60x60 m bermaterial rostlinka 07_ground (2K)
## + rumput MultiMesh (rostlinka12 2K + kartu 07c) dengan shader
##   alpha-SCISSOR (bukan alpha-blend!), tanpa cast-shadow,
##   angin vertex sederhana, dan fade "tenggelam" berbasis jarak.
##
## Bukti riset: alpha-blend grass = overdraw pembunuh GPU TBDR kelas
## GE8320 (r/godot 2023, gamedev.net 2015, godot-proposals #7366);
## MultiMesh = 1 draw call per jenis rumput; rumput TIDAK boleh
## melempar bayangan; fade jarak via sink lebih bersih daripada
## alpha-fade (tidak ada popping/flicker di scissor).

const GROUND_SIZE := 140.0     # S3: arena 60 → 140 m (keputusan user)
const GRASS_R12_COUNT := 2000  # S3: 600 → 2000 (±2500 total, 2 draw call)
const GRASS_07C_COUNT := 500   # S3: 150 → 500
const GRASS_RADIUS := 66.0     # S3: disk sebaran mengikuti arena baru
const SEED := 1337             # deterministik — UAT bisa mereproduksi


func build() -> void:
	_build_ground()
	_build_grass(
		"res://assets/grass/rostlinka12_2k_difuse.jpeg",
		"res://assets/grass/rostlinka12_2k_alfa.jpeg",
		Vector2(0.8, 0.7), GRASS_R12_COUNT
	)
	_build_grass(
		"res://assets/grass/rostlinka_07c_diffuse.jpeg",
		"res://assets/grass/rostlinka_07c_alfa.jpeg",
		Vector2(1.4, 1.1), GRASS_07C_COUNT
	)
	_build_props()
	print("WORLD-S3: arena=%dm grass=%d props+sky terpasang" % [
		GROUND_SIZE, GRASS_R12_COUNT + GRASS_07C_COUNT])


func _build_ground() -> void:
	var mesh_inst := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(GROUND_SIZE, GROUND_SIZE)
	plane.subdivide_width = 8
	plane.subdivide_depth = 8
	mesh_inst.mesh = plane

	var mat := StandardMaterial3D.new()
	var albedo: Texture2D = load("res://assets/ground/rostlinka_07_ground_albedo.jpeg")
	var normal: Texture2D = load("res://assets/ground/rostlinka_07_ground_NormalsMap.jpeg")
	var occl: Texture2D = load("res://assets/ground/rostlinka_07_ground_occlusion.jpeg")
	if albedo:
		mat.albedo_texture = albedo
	if normal:
		mat.normal_enabled = true
		mat.normal_texture = normal
	if occl:
		mat.ao_enabled = true
		mat.ao_texture = occl
	mat.roughness = 0.95
	mat.uv1_scale = Vector3(23.3, 23.3, 1.0)   # tile ~6 m di arena 140 m
	mesh_inst.material_override = mat
	mesh_inst.name = "Ground"
	add_child(mesh_inst)

	# Tabrakan: WorldBoundary = lantai tak terbatas, super murah.
	var body := StaticBody3D.new()
	var col := CollisionShape3D.new()
	col.shape = WorldBoundaryShape3D.new()
	body.add_child(col)
	body.name = "GroundBody"
	add_child(body)


func _build_grass(albedo_path: String, alfa_path: String, card: Vector2, count: int) -> void:
	var albedo: Texture2D = load(albedo_path)
	var alfa: Texture2D = load(alfa_path)
	if albedo == null or alfa == null:
		push_warning("E-strafe: tekstur rumput hilang: " + albedo_path)
		return

	var quad := QuadMesh.new()
	quad.size = card
	quad.center_offset = Vector3(0.0, card.y * 0.5, 0.0)  # akar di y=0

	var shader: Shader = load("res://shaders/grass.gdshader")
	var mat := ShaderMaterial.new()
	mat.shader = shader
	mat.set_shader_parameter("albedo_tex", albedo)
	mat.set_shader_parameter("alpha_tex", alfa)

	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.mesh = quad
	mm.instance_count = count

	var rng := RandomNumberGenerator.new()
	rng.seed = SEED
	for i in count:
		var ang := rng.randf() * TAU
		var rad := sqrt(rng.randf()) * GRASS_RADIUS
		var pos := Vector3(cos(ang) * rad, 0.0, sin(ang) * rad)
		var yaw := rng.randf() * TAU
		var s := rng.randf_range(0.8, 1.3)
		var basis := Basis(Vector3.UP, yaw).scaled(Vector3(s, s, s))
		mm.set_instance_transform(i, Transform3D(basis, pos))

	var mmi := MultiMeshInstance3D.new()
	mmi.multimesh = mm
	mmi.material_override = mat
	mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mmi.name = "Grass_%s" % albedo_path.get_file().get_basename()
	add_child(mmi)


# ---- S3: props & skydome (harta karun user; diaudit biner 2026-09-03) ----
# Hasil audit: rock_game_assets tinggi-Y 104 unit → skala 0.015–0.04;
# pohon Retro GLB "tidur" (tinggi di −Z) → rotation.x +90° menegakkan;
# geranium tinggi-Y 166 unit → skala 0.35–0.45; sky = bola radius 1 m
# (doubleSided=true) → skala 300 + unlit.

func _build_props() -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = SEED + 7
	_scatter("res://assets/rocks/rock_game_assets.glb", 10, rng,
			0.015, 0.04, 8.0, 62.0, 0.0, true)
	_scatter("res://assets/trees/tree_rt_1.glb", 6, rng,
			4.0, 6.0, 12.0, 64.0, 90.0, false)
	_scatter("res://assets/trees/tree_rt_3.glb", 6, rng,
			3.0, 5.0, 12.0, 64.0, 90.0, false)
	_scatter("res://assets/trees/small_tree_rt_1.glb", 8, rng,
			0.8, 1.4, 6.0, 60.0, 90.0, false)
	# Geranium: 2 aksen kawaii dekat spawn saja (95k tris — jangan disebar!).
	_place("res://assets/props/geranium_flower.glb",
			Vector3(2.2, 0.0, 1.6), 0.4, 0.0, false)
	_place("res://assets/props/geranium_flower.glb",
			Vector3(-2.5, 0.0, 2.1), 0.35, 0.0, false)
	_sky()


func _scatter(path: String, count: int, rng: RandomNumberGenerator,
		s_min: float, s_max: float, r_min: float, r_max: float,
		tilt_x_deg: float, shadow: bool) -> void:
	for i in count:
		var ang := rng.randf() * TAU
		var rad := rng.randf_range(r_min, r_max)
		var pos := Vector3(cos(ang) * rad, 0.0, sin(ang) * rad)
		_place(path, pos, rng.randf_range(s_min, s_max), tilt_x_deg, shadow,
				rng.randf() * TAU)


func _place(path: String, pos: Vector3, s: float, tilt_x_deg: float,
		shadow: bool, yaw: float = 0.0) -> void:
	var ps: PackedScene = load(path)
	if ps == null:
		push_warning("E-strafe: prop hilang: " + path)
		return
	var inst := ps.instantiate()
	inst.position = pos
	inst.scale = Vector3(s, s, s)
	# Euler YXZ: tilt-X (menegakkan pohon) diterapkan dulu, baru yaw dunia.
	inst.rotation = Vector3(deg_to_rad(tilt_x_deg), yaw, 0.0)
	for mi in inst.find_children("*", "MeshInstance3D", true, false):
		(mi as MeshInstance3D).cast_shadow = (
			GeometryInstance3D.SHADOW_CASTING_SETTING_ON if shadow
			else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF)
	inst.name = "Prop_" + path.get_file().get_basename()
	add_child(inst)


func _sky() -> void:
	var ps: PackedScene = load("res://assets/sky/sky.glb")
	if ps == null:
		push_warning("E-strafe: sky.glb gagal load")
		return
	var inst := ps.instantiate()
	inst.name = "SkyDome"
	inst.scale = Vector3(300.0, 300.0, 300.0)  # radius asli 1 m
	for mi in inst.find_children("*", "MeshInstance3D", true, false):
		var m3 := mi as MeshInstance3D
		m3.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		var mat := m3.mesh.surface_get_material(0)
		if mat is StandardMaterial3D:
			# Unlit biar dome tak di-shade matahari (setengah bola gelap).
			# SHADING_MODE_UNLIT = 1 (Godot 4.3+); via set() biar compile aman.
			mat.set("shading_mode", 1)
	add_child(inst)
	print("SKY-READY scale=300 unlit")
