extends Node3D
## CameraRig — "cameraman sidecar" (CameraPivot).
##
## KONTRAK E-strafe:
## - Yaw/pitch HANYA dari drag satu jari di zona kanan layar. Tidak ada
##   auto-recenter, tidak ada lateral tracking, tidak ada auto-follow.
##   (Vaksin bug "dunia berputar" & "jalan melingkar" — semua auto-rule OFF.)
## - Pivot adalah anak Player di scene tree, tapi top_level=true →
##   transform global-nya independen; tiap physics frame disetel ke posisi player.
##   Rotasi badan player TIDAK PERNAH bocor ke kamera → nol feedback loop.

@export var sens := 0.005          # rad per piksel drag
@export var pitch_min_deg := -35.0
@export var pitch_max_deg := 70.0  # S3: dongak sampai langit (user buru aset awan)
@export var eye_height := 1.45     # tinggi mata di atas kaki player

var yaw := 0.0
var pitch := -8.0                  # sedikit menunduk, enak buat lihat kaki & tanah

var _idx := -1


func _ready() -> void:
	top_level = true
	$SpringArm.add_excluded_object(get_parent())
	print("CAMRIG-READY top_level=true")


func _physics_process(_delta: float) -> void:
	var p := get_parent() as Node3D
	global_position = p.global_position + Vector3(0.0, eye_height, 0.0)
	global_rotation = Vector3(deg_to_rad(pitch), yaw, 0.0)


# ---- Antarmuka drag (dipanggil HUD; hanya event zona kanan) ----

func on_touch_down(ev: InputEventScreenTouch) -> void:
	if _idx < 0:
		_idx = ev.index


func on_drag(ev: InputEventScreenDrag) -> void:
	if ev.index != _idx:
		return
	# S3 (UAT user 2026-09-03): drag kanan = LIHAT kanan (tanda yaw dibalik;
	# sebelumnya kamera malah mengorbit kiri — keluhan user).
	# Drag atas → pitch naik → mendongak ke langit (dome sky.glb).
	yaw -= ev.relative.x * sens
	pitch = clamp(pitch - ev.relative.y * sens, deg_to_rad(pitch_min_deg), deg_to_rad(pitch_max_deg))


func on_up(ev: InputEventScreenTouch) -> void:
	if ev.index == _idx:
		_idx = -1


func release() -> void:
	_idx = -1
