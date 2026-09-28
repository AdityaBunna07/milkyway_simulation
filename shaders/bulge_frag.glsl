#version 330

in vec3 v_color;
out vec4 fragColor;

void main() {
    // Render soft circular stars
    vec2 coord = gl_PointCoord * 2.0 - vec2(1.0);
    float r = length(coord);
    
    if (r > 1.0) {
        discard;
    }
    
    // Soft falloff for star glow
    float alpha = exp(-r * r * 4.0) * (1.0 - r);
    
    // Retain star temperature hues after additive blending, with a modest
    // saturation lift for smaller stars that otherwise look nearly white.
    float gray = dot(v_color, vec3(0.2126, 0.7152, 0.0722));
    vec3 star_color = clamp(mix(vec3(gray), v_color, 1.35), 0.0, 1.0);
    fragColor = vec4(star_color, alpha);
}
