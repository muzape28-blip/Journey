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

const GROUND_SIZE := 60.0
const GRASS_R12_COUNT := 600
const GRASS_07C_COUNT := 150
const GRASS_RADIUS := 26.0     # sebaran dalam disk sekitar spawn
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
	mat.uv1_scale = Vector3(10.0, 10.0, 1.0)   # tile ~6 m
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
