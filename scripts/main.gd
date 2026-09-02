extends Node3D
## Main — perakitan eksperimen E-strafe.
##
## Tugas:
## 1. Bangun dunia (world_builder).
## 2. Siapkan perpustakaan animasi Shibahu:
##    - glb v1 (shibahu_new_animated.glb) = instance visual + anim dasar.
##    - glb v2 (shibahu_animated_v2.glb) = DI-LOAD OFF-TREE, keenam animnya
##      DISALIN ke player v1 (rig identik: 22 joint mixamorig — terverifikasi
##      audit 2026-09-02), lalu instance v2 dibuang → hemat VRAM/draw call.
##    - SANITASI: track translasi Hips dibekukan di sumbu X/Z (jejak
##      root-motion "bend-back" Cinevva ±13 cm → tanpa ini Shibahu
##      sempoyongan maju-mundur), komponen Y (bob) dipertahankan.
##    - Loop mode di-set eksplisit untuk klip lokomosi.
## 3. Kabel: joystick.moved → player.set_move_input; drag zona kanan → camera_rig.
## 4. Smoke runtime: cek player tidak jatuh + daftar animasi tersedia.

const NAME_MAP := {
	"Cute children female idle like nana from (e35b49)": "idle",
	"Jog Forward": "jog_fwd",
	"Jog Forward Left": "jog_left",
	"Jog Forward Right": "jog_right",
	"Jog Forward Lean Right": "jog_lean_r",
	"Sprint": "sprint",
	"Sprint Exit": "sprint_exit",
	"Dodge Left Root Motion": "dodge_l",
	"Dodge Right Root Motion": "dodge_r",
	"Ground Sit Enter": "sit_enter",
	"Ground Sit Idle": "sit_idle",
	"Ground Sit Exit": "sit_exit",
}
const LOOP_ANIMS := ["idle", "jog_fwd", "jog_left", "jog_right", "jog_lean_r", "sprint"]

@onready var player: CharacterBody3D = $Player
@onready var hud: CanvasLayer = $HUD


func _ready() -> void:
	$Sun.rotation_degrees = Vector3(-50.0, -35.0, 0.0)
	$World.build()

	var ap := player.find_child("AnimationPlayer", true, false) as AnimationPlayer
	if ap == null:
		push_error("E-strafe: AnimationPlayer tidak ditemukan di instance Shibahu!")
	else:
		_sanitize_existing(ap)
		_merge_v2(ap)
		player.setup_player(ap)

	hud.pivot_rig = $Player/CameraPivot
	hud.player = player
	hud.joystick.moved.connect(player.set_move_input)

	$SmokeTimer.start()
	print("E-strafe S1 boot OK — anim: ", _anim_list(ap))


func _anim_list(ap: AnimationPlayer) -> Array:
	var out := []
	for lib_name in ap.get_animation_library_list():
		var lib := ap.get_animation_library(lib_name)
		for n in lib.get_animation_list():
			out.append(n)
	return out


func _sanitize_existing(ap: AnimationPlayer) -> void:
	for lib_name in ap.get_animation_library_list():
		var lib := ap.get_animation_library(lib_name)
		for n in lib.get_animation_list():
			var anim := lib.get_animation(n)
			_freeze_hips_xz(anim)
			var mapped: String = NAME_MAP.get(n, "")
			if mapped in LOOP_ANIMS:
				anim.loop_mode = Animation.LOOP_LINEAR


func _merge_v2(ap: AnimationPlayer) -> void:
	var ps: PackedScene = load("res://shibahu_animated_v2.glb")
	if ps == null:
		push_error("E-strafe: shibahu_animated_v2.glb tidak bisa di-load!")
		return
	var inst := ps.instantiate()
	var src := inst.find_child("AnimationPlayer", true, false) as AnimationPlayer
	if src == null:
		push_error("E-strafe: v2 tidak punya AnimationPlayer!")
		inst.free()
		return
	for lib_name in src.get_animation_library_list():
		var lib := src.get_animation_library(lib_name)
		for n in lib.get_animation_list():
			var mapped: String = NAME_MAP.get(n, "")
			if mapped == "":
				push_warning("E-strafe: nama anim v2 tak dikenal: " + n)
				continue
			var anim: Animation = lib.get_animation(n).duplicate(true)
			_freeze_hips_xz(anim)
			if mapped in LOOP_ANIMS:
				anim.loop_mode = Animation.LOOP_LINEAR
			ap.add_animation(mapped, anim)
	inst.free()


func _freeze_hips_xz(anim: Animation) -> void:
	# Bekukan translasi Hips di X/Z pada nilai key pertama; Y (bob) tetap hidup.
	for t in anim.get_track_count():
		if anim.track_get_type(t) != Animation.TYPE_VECTOR3:
			continue
		var path := String(anim.track_get_path(t))
		if not (path.ends_with("Hips:position") or path.ends_with("Hips:xform")):
			continue
		var kc := anim.track_get_key_count(t)
		if kc < 1:
			continue
		var first: Vector3 = anim.track_get_key_value(t, 0)
		for k in kc:
			var v: Vector3 = anim.track_get_key_value(t, k)
			anim.track_set_key_value(t, k, Vector3(first.x, v.y, first.z))


func _on_smoke_timer_timeout() -> void:
	if player.global_position.y < -3.0:
		push_error("SMOKE FAIL: player jatuh ke " + str(player.global_position))
	else:
		print("SMOKE OK: pos=", player.global_position, " on_floor=", player.is_on_floor())
