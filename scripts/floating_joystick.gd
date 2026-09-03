extends Control
## FloatingJoystick — bulat, DYNAMIC, timbul di titik sentuh.
##
## Spesifikasi terkunci (riset Virtual Joystick DX + Gamedeaver scaled-radial):
## - DYNAMIC: base muncul tepat di titik sentuh (zona kiri saja — router di HUD).
## - CLAMP 1.5x radius: kalau jempol lewat batas, base ikut MELUNCUR
##   ("pembatas sedikit lebih lega").
## - Deadzone 0.10 SCALED-RADIAL: out = dir * (mag-dz)/(1-dz) → gradien mulus
##   dari 0 ke 1, presisi dalam-deadzone tidak hilang.
## - Tap murni tidak pernah menggerakkan karakter (output tetap 0 sampai drag).
## - Satu event.index dimiliki sampai lepas; tidak ada handoff di tengah drag.
## - release_all() saat aplikasi kehilangan fokus (vaksin ghost-stick Android).

signal moved(v: Vector2)   # x = kanan(+), y = MAJU(+) — sudah dibalik dari koordinat layar

const BASE_R := 95.0         # S4: 120 → 95 (UAT: joystick "naikin sensitifitas
                             # sedikit" — stick penuh tercapai lebih cepat)
const CLAMP_MUL := 1.5       # clampzone = 180 px
const KNOB_R := 30.0
const HALO_R := 38.0
const DZ := 0.10             # scaled-radial deadzone
const HINT_ALPHA := 0.13
const SNAPBACK_S := 0.15

var hint_center := Vector2(160.0, 0.0)   # di-set saat _ready (size.y - 200)

var _idx := -1
var _origin := Vector2.ZERO
var _vec := Vector2.ZERO
var _snap: Tween = null


func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	hint_center = Vector2(160.0, size.y - 200.0)
	print("JOYSTICK-READY size=", size, " hint=", hint_center)


func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		release_all()


# ---- Antarmuka sentuh (dipanggil router HUD; hanya zona kiri) ----

func on_touch_down(pos: Vector2, idx: int) -> void:
	if _idx >= 0:
		return
	_idx = idx
	_origin = pos
	_vec = Vector2.ZERO
	if _snap and _snap.is_valid():
		_snap.kill()
	queue_redraw()


func on_drag(pos: Vector2, idx: int) -> void:
	if idx != _idx:
		return
	var d := pos - _origin
	var clen := BASE_R * CLAMP_MUL
	if d.length() > clen:
		# Base ikut meluncur — jempol tidak pernah "ketinggalan".
		_origin = pos - d.normalized() * clen
		d = pos - _origin
	var mag: float = minf(d.length() / BASE_R, 1.0)
	var dir := d.normalized() if mag > 0.0001 else Vector2.ZERO
	var scaled: float = clampf((mag - DZ) / (1.0 - DZ), 0.0, 1.0)
	# Layar: atas = -y. Kontrak kita: maju = +y → balik.
	_vec = Vector2(dir.x, -dir.y) * scaled
	moved.emit(_vec)
	queue_redraw()


func on_up(idx: int) -> void:
	if idx != _idx:
		return
	_idx = -1
	if _snap and _snap.is_valid():
		_snap.kill()
	_snap = create_tween()
	_snap.tween_method(_release_step, _vec, Vector2.ZERO, SNAPBACK_S)


func release_all() -> void:
	if _idx >= 0:
		_idx = -1
	_release_step(Vector2.ZERO)


func _release_step(v: Vector2) -> void:
	_vec = v
	moved.emit(_vec)
	queue_redraw()


func _draw() -> void:
	# Ukuran live (layout mungkin belum final saat _ready).
	var hc := Vector2(160.0, size.y - 200.0)
	if _idx < 0:
		# Cincin petunjuk idle — kawaii, tidak mengganggu.
		draw_arc(hc, BASE_R, 0.0, TAU, 48, Color(1, 1, 1, HINT_ALPHA), 3.0)
		draw_circle(hc, 6.0, Color(1, 1, 1, HINT_ALPHA * 0.8))
	else:
		draw_circle(_origin, BASE_R, Color(1, 1, 1, 0.05))
		draw_arc(_origin, BASE_R, 0.0, TAU, 64, Color(1, 1, 1, 0.28), 3.0)
		draw_arc(_origin, BASE_R * CLAMP_MUL, 0.0, TAU, 64, Color(1, 1, 1, 0.10), 2.0)
		var knob_pos := _origin + Vector2(_vec.x, -_vec.y) * BASE_R
		draw_circle(knob_pos, HALO_R, Color(1, 1, 1, 0.10))
		draw_circle(knob_pos, KNOB_R, Color(1, 1, 1, 0.55))
