#version 330

in vec3 in_position;
in vec3 in_color;
in float in_size;
in float in_brightness;

out vec3 v_color;

uniform mat4 u_model;
uniform mat4 u_view;
uniform mat4 u_projection;
uniform float u_visibility;
uniform float u_farBlend;

void main() {
    // Transform to world space
    vec4 world_pos = u_model * vec4(in_position, 1.0);
    
    // Transform to view space
    vec4 view_pos = u_view * world_pos;
    
    // Perspective projection
    gl_Position = u_projection * view_pos;
    
    // Size attenuation based on distance
    float dist = max(0.1, -view_pos.z);
    float projected_size = clamp(in_size * (300.0 / dist), 1.0, 20.0);
    float diffuse_size = max(projected_size, 1.0 + 2.0 * u_farBlend);
    gl_PointSize = mix(projected_size, diffuse_size, u_farBlend);
    
    // Pass color out (fade in with u_visibility)
    v_color = in_color * in_brightness * u_visibility / (1.0 + 1.2 * u_farBlend);
}
