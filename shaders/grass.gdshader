shader_type spatial;
// Rumput kartu MultiMesh — alpha SCISSOR (bukan blend!) biar overdraw murah
// di GPU TBDR kelas GE8320 [riset: r/godot 2023, godot-proposals #7366].
// Angin = goyangan vertex sederhana (murah, tanpa tekstur noise).
// Fade jarak = "tenggelam ke tanah" (lebih bersih dari alpha-fade di scissor).
// Cutout biner via discard di fragment (alpha_scissor BUKAN render mode
// shader di 4.7; itu properti StandardMaterial3D). Piksel dibuang = murah.
render_mode cull_disabled, specular_disabled;

uniform sampler2D albedo_tex : source_color, filter_linear_mipmap;
uniform sampler2D alpha_tex : filter_linear_mipmap;
uniform float wind_strength : hint_range(0.0, 0.2) = 0.045;
uniform float fade_near = 16.0;
uniform float fade_far = 24.0;

void vertex() {
	vec3 wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float ph = TIME * 1.8 + wp.x * 0.7 + wp.z * 0.9;
	float h = max(VERTEX.y, 0.0);
	VERTEX.x += sin(ph) * wind_strength * h * 2.0;
	VERTEX.z += cos(ph * 0.8) * wind_strength * 0.6 * h * 2.0;
	float dist = distance(wp, CAMERA_POSITION_WORLD);
	VERTEX.y -= smoothstep(fade_near, fade_far, dist);
}

void fragment() {
	vec4 c = texture(albedo_tex, UV);
	float a = texture(alpha_tex, UV).r;
	if (a < 0.45) {
		discard;
	}
	ALBEDO = c.rgb;
	ROUGHNESS = 0.9;
	ALPHA = 1.0;
}
