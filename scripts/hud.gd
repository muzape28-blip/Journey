extends CanvasLayer
## HUD — router zona sentuh + DIAG.
##
## Zona (kontrak E-strafe): x < 50% lebar = JOYSTICK (kiri),
## x >= 50% = KAMERA (kanan). Zona dikunci saat SENTUH TURUN —
## drag tidak pernah berpindah pemilik di tengah jalan (vaksin
## konflik drag-vs-zoom ala ZDEV; pola "lock-in" dari riset gesture).

const ZONE_SPLIT := 0.5

var pivot_rig: Node = null          # camera_rig (di-set main.gd)
var player: CharacterBody3D = null  # untuk DIAG (di-set main.gd)

@onready var joystick: Control = $Joystick
@onready var diag: Label = $DIAG

var _owners := {}   # event.index -> "stick" | "cam"
var _diag_t := 0.0


func _input(event: InputEvent) -> void:
	if event is InputEventScreenTouch:
		if event.pressed:
			var w := get_viewport().get_visible_rect().size.x
			var zone := "stick" if event.position.x < w * ZONE_SPLIT else "cam"
			_owners[event.index] = zone
			if zone == "stick":
				joystick.on_touch_down(event.position, event.index)
			elif pivot_rig:
				pivot_rig.on_touch_down(event)
		else:
			var zone: String = _owners.get(event.index, "")
			if zone == "stick":
				joystick.on_up(event.index)
			elif zone == "cam" and pivot_rig:
				pivot_rig.on_up(event)
			_owners.erase(event.index)
	elif event is InputEventScreenDrag:
		var zone2: String = _owners.get(event.index, "")
		if zone2 == "stick":
			joystick.on_drag(event.position, event.index)
		elif zone2 == "cam" and pivot_rig:
			pivot_rig.on_drag(event)


func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		# Vaksin ghost-stick Android (ref ZDEV / moonlight #1536).
		joystick.release_all()
		if pivot_rig:
			pivot_rig.release()
		_owners.clear()


func _process(delta: float) -> void:
	_diag_t += delta
	if _diag_t < 0.25:
		return
	_diag_t = 0.0
	var v := 0.0
	var a := "-"
	if player:
		v = Vector2(player.velocity.x, player.velocity.z).length()
	diag.text = "fps %d | v %.2f m/s | stick (%.2f, %.2f)" % [
		Engine.get_frames_per_second(), v, joystick._vec.x, joystick._vec.y
	]
