extends CharacterBody3D
## PlayerController — kontrak E-strafe (eksperimen).
##
## ATURAN BAKU (jangan diubah tanpa UAT):
## - Gerak RELATIF KAMERA: stick atas = jog maju searah pandang kamera.
## - Kiri/kanan = STRAFE murni (geser samping), badan selalu meluruh (lerp)
##   menghadap yaw kamera dengan laju TURN_RATE. Badan TIDAK PERNAH
##   memengaruhi kamera (kamera di-override global oleh camera_rig) →
##   tidak ada feedback loop → tidak ada bug "jalan melingkar".
## - Semua kecepatan dirampai move_toward (accel/decel) — berhenti halus.
##
## Bukti pola: ZDEV-RPG M0 (accel 40, gravity 20, max_slides 6 default,
## floor_snap, wall_min_slide) + riset r/PS4Dreams & gamedev.net 2011
## (camera auto-rotate + camera-relative input = lingkaran).

const JOG_SPEED := 2.5      # m/s — stick penuh
const ACCEL := 40.0         # m/s^2 — responsif (ZDEV)
const DECEL := 24.0         # m/s^2 — berhenti halus, bukan hard-stop
const GRAV := 20.0          # m/s^2 (ZDEV)
const FALL_CLAMP := -30.0
const TURN_RATE := 10.0     # rad/s lerp badan → yaw kamera

@export var orient_fix_deg := 180.0  # mesh mixamorig menghadap +Z; Godot -Z → koreksi 180 (riset 2026-09-03)
@export var play_rate := 1.0        # kecepatan pemutaran klip (kalibrasi foot-slide)

var move_input := Vector2.ZERO      # x = kanan(+), y = MAJU(+). Di-set oleh joystick via HUD.

var _anim_player: AnimationPlayer = null
var _cur_anim := ""
@onready var _pivot: Node3D = $CameraPivot
@onready var _mesh: Node3D = get_node_or_null("Shibahu")


func _ready() -> void:
	floor_snap_length = 0.5
	if _mesh:
		_mesh.rotation.y = deg_to_rad(orient_fix_deg)


func setup_player(p: AnimationPlayer) -> void:
	_anim_player = p
	_play("idle")


func set_move_input(v: Vector2) -> void:
	move_input = v


func _physics_process(delta: float) -> void:
	# 1) Vektor harapan relatif kamera (diratakan ke bidang XZ).
	var fwd := -_pivot.global_transform.basis.z
	fwd.y = 0.0
	if fwd.length_squared() < 0.000001:
		fwd = Vector3(0.0, 0.0, -1.0)
	else:
		fwd = fwd.normalized()
	var right := _pivot.global_transform.basis.x
	right.y = 0.0
	if right.length_squared() < 0.000001:
		right = Vector3(1.0, 0.0, 0.0)
	else:
		right = right.normalized()

	var wish := fwd * move_input.y + right * move_input.x
	if wish.length() > 1.0:
		wish = wish.normalized()

	# 2) Rampai kecepatan (analog: besaran stick mengalikan kecepatan).
	var target := wish * JOG_SPEED
	var a := (ACCEL if wish.length_squared() > 0.0001 else DECEL) * delta
	velocity.x = move_toward(velocity.x, target.x, a)
	velocity.z = move_toward(velocity.z, target.z, a)

	# 3) Gravitasi.
	velocity.y = max(velocity.y - GRAV * delta, FALL_CLAMP)

	move_and_slide()

	# 4) Badan menghadap yaw kamera (gaya strafe) — hanya sumber putaran badan.
	if move_input.length() > 0.05:
		global_rotation.y = lerp_angle(
			global_rotation.y,
			_pivot.global_rotation.y,
			1.0 - exp(-TURN_RATE * delta)
		)

	_update_anim()


func _update_anim() -> void:
	if _anim_player == null:
		return
	var m := move_input
	var want := "idle"
	if m.length() > 0.12:
		if abs(m.x) > abs(m.y) * 1.4:
			want = "jog_right" if m.x > 0.0 else "jog_left"
		else:
			want = "jog_fwd"
	if want != _cur_anim:
		_play(want)


func _play(n: String) -> void:
	if _anim_player == null:
		return
	if not _anim_player.has_animation(n):
		push_warning("E-strafe: animasi tidak ada: " + n)
		return
	_anim_player.play(n, 0.18, play_rate)
	_cur_anim = n
