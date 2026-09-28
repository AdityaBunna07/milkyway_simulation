#version 330

in vec3 in_position;
in float in_brightness;
in float in_temperature;

out float starBrightness;
out float starTemperature;

uniform mat4 u_model;
uniform mat4 u_view;
uniform mat4 u_projection;

void main()
{
    // ======================================================
    // 1. Pass stellar properties
    // ======================================================
    starBrightness = in_brightness;
    starTemperature = in_temperature;

    // ======================================================
    // 2. Transform position
    // ======================================================
    vec4 world_pos = u_model * vec4(in_position, 1.0);
    vec4 view_pos = u_view * world_pos;
    gl_Position = u_projection * view_pos;

    // ======================================================
    // 3. Point Size
    // ======================================================
    // view_pos.z is negative in standard OpenGL right-handed coordinates.
    float dist = max(0.1, -view_pos.z);
    
    // Base size depends on brightness
    float baseSize = 1.5 + in_brightness * 3.0;
    
    // Scale by distance (closer = bigger, farther = smaller)
    // Avoid making points huge when close
    gl_PointSize = clamp(baseSize * (10.0 / dist), 1.0, 15.0);
}