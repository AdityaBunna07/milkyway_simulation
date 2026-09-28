#version 330

uniform float u_inclination;
uniform float u_azimuth;
uniform float u_galaxyRadius;
uniform float u_bulgeRadius;
uniform float u_armTightness;
uniform float u_numArms;

out vec4 fragColor;

void main()
{
    // --------------------------------------------------------
    // Convert screen coordinates to centered coordinates
    // --------------------------------------------------------

    vec2 uv = gl_FragCoord.xy / vec2(1280.0, 720.0);

    vec2 p = uv * 2.0 - 1.0;

    // Correct for screen aspect ratio
    p.x *= 1280.0 / 720.0;

    // --------------------------------------------------------
    // Galaxy inclination
    // --------------------------------------------------------

    float squish = max(
        0.15,
        cos(u_inclination)
    );

    p.y /= squish;

    // --------------------------------------------------------
    // Polar coordinates
    // --------------------------------------------------------

    float radius = length(p);
    float angle = atan(p.y, p.x);

    // --------------------------------------------------------
    // Central galactic bulge
    // --------------------------------------------------------

    float normalizedRadius =
        radius / u_galaxyRadius;

    float bulge = exp(
        -normalizedRadius *
        normalizedRadius *
        5.0
    );

    // --------------------------------------------------------
    // Spiral structure
    // --------------------------------------------------------

    float safeRadius = max(radius, 0.0001);
    float spiralAngle =
        angle
        - u_armTightness * log(safeRadius / max(u_bulgeRadius, 0.001))
        + u_azimuth;

    float spiral = 0.5 + 0.5 * cos(
        spiralAngle * u_numArms
    );

    // Make spiral arms stronger farther from the center
    float armStrength =
        spiral *
        smoothstep(0.12, 0.9, radius);

    // --------------------------------------------------------
    // Galaxy density
    // --------------------------------------------------------

    float disk =
        exp(-radius * 1.8) *
        (0.25 + 0.75 * armStrength);

    // Remove the galaxy outside its radius
    float galaxyMask =
        1.0 - smoothstep(0.85, 1.0, radius);

    disk *= galaxyMask;

    // --------------------------------------------------------
    // Combine bulge and disk
    // --------------------------------------------------------

    float brightness =
        bulge * 1.5 +
        disk;

    brightness = clamp(
        brightness,
        0.0,
        1.0
    );

    // --------------------------------------------------------
    // Temporary galaxy colour
    // --------------------------------------------------------

    vec3 galaxyColor = vec3(
        brightness * 0.95,
        brightness * 0.75,
        brightness * 0.45
    );

    vec3 background = vec3(
        0.005,
        0.005,
        0.015
    );

    vec3 finalColor = mix(
        background,
        galaxyColor,
        brightness
    );

    fragColor = vec4(
        finalColor,
        1.0
    );
}
