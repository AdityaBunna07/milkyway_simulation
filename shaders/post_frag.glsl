#version 330

uniform sampler2D scene;
in vec2 uv;
out vec4 fragColor;

uniform float u_overviewWeight;
uniform float u_galaxyDistance;
uniform float u_cameraInclination;
uniform float u_galaxyAngle;
uniform float u_aspectRatio;

const float PI = 3.14159265;
const float TWO_PI = 6.28318530;
const float BAR_ANGLE = 0.34;
const float INNER_RADIUS = 2.0;
const float SPIRAL_TIGHTNESS = 2.5;

const int samples = 48;
const float radius = 0.018;
const float threshold = 0.50;
const float intensity = 1.6;
const float GOLDEN_ANGLE = 2.39996323;

float hash21(vec2 p) {
    p = fract(p * vec2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return fract(p.x * p.y);
}

float valueNoise2D(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash21(i), hash21(i + vec2(1.0, 0.0)), f.x),
               mix(hash21(i + vec2(0.0, 1.0)), hash21(i + vec2(1.0, 1.0)), f.x), f.y);
}

float fbm2(vec2 p) {
    float value = 0.0;
    float amplitude = 0.5;
    for (int i = 0; i < 4; i++) {
        value += amplitude * valueNoise2D(p);
        p = p * 2.03 + vec2(7.1, 3.7);
        amplitude *= 0.5;
    }
    return value;
}

float wrapAngle(float angle) {
    return mod(angle + PI, TWO_PI) - PI;
}

vec2 rotate2(vec2 p, float angle) {
    float c = cos(angle);
    float s = sin(angle);
    return vec2(c * p.x - s * p.y, s * p.x + c * p.y);
}

vec3 milkyWayOverview(vec2 screenUV) {
    // Convert screen pixels back to approximate galactic-disk coordinates.
    float halfView = u_galaxyDistance * 0.41421356;
    vec2 p = (screenUV * 2.0 - 1.0) * vec2(u_aspectRatio, 1.0) * halfView;
    p.y /= max(cos(u_cameraInclination), 0.25);
    p = rotate2(p, u_galaxyAngle);

    float r = length(p);
    float safeR = max(r, INNER_RADIUS);
    float theta = atan(p.y, p.x);
    float radialFade = (1.0 - smoothstep(45.0, 53.0, r));
    float innerFade = smoothstep(2.2, 5.5, r);
    float spiralWarp = (fbm2(vec2(theta * 2.1, r * 0.19) + vec2(5.0, 12.0)) - 0.5) * 0.20;

    // Two strong arms and two fainter arms, all winding away from a tilted bar.
    float majorDistance = 1000.0;
    float minorDistance = 1000.0;
    float branchDistance = 1000.0;
    for (int arm = 0; arm < 4; arm++) {
        float armBase = BAR_ANGLE + float(arm) * (TWO_PI / 4.0);
        float idealAngle = armBase + SPIRAL_TIGHTNESS * log(safeR / INNER_RADIUS);
        idealAngle += spiralWarp / safeR;
        float laneDistance = abs(wrapAngle(theta - idealAngle)) * r;
        if (arm == 0 || arm == 2) majorDistance = min(majorDistance, laneDistance);
        else minorDistance = min(minorDistance, laneDistance);
        if (arm == 0 || arm == 2) {
            float branchOffset = 0.18 * smoothstep(12.0, 34.0, r);
            float branchPos = abs(wrapAngle(theta - idealAngle - branchOffset)) * r;
            float branchNeg = abs(wrapAngle(theta - idealAngle + branchOffset)) * r;
            branchDistance = min(branchDistance, min(branchPos, branchNeg));
        }
    }

    float armWidth = 1.65 + 0.030 * r;
    float majorCore = exp(-pow(majorDistance / armWidth, 2.0));
    float majorHalo = exp(-pow(majorDistance / (armWidth * 2.6), 2.0));
    float minorHalo = exp(-pow(minorDistance / (armWidth * 2.6), 2.0));
    float branchHalo = exp(-pow(branchDistance / (armWidth * 2.1), 2.0));

    // Dust and star-forming clouds break the smooth arms into filaments and knots.
    float cloudNoise = fbm2(p * 0.23 + vec2(8.0, 3.0));
    float cloudMask = smoothstep(0.29, 0.67, cloudNoise);
    float armClouds = (majorCore * 0.62 + majorHalo * 0.48 + minorHalo * 0.27 + branchHalo * 0.18)
                    * (0.48 + 0.52 * cloudMask) * radialFade * innerFade;
    float fineNoise = fbm2(p * 0.78 + vec2(19.0, 5.0));
    float knotCellSize = 1.55;
    vec2 knotCell = floor(p / knotCellSize);
    vec2 knotJitter = vec2(hash21(knotCell + 13.0), hash21(knotCell + 41.0));
    vec2 knotCenter = (knotCell + 0.18 + 0.64 * knotJitter) * knotCellSize;
    float knotRandom = hash21(knotCell + vec2(floor(theta * 2.0)));
    float knotShape = exp(-pow(length(p - knotCenter) / 0.25, 2.0));
    float pinkKnots = smoothstep(0.58, 0.92, knotRandom) * knotShape
                    * smoothstep(0.38, 0.76, fineNoise)
                    * clamp(majorCore + 0.45 * majorHalo + 0.18 * minorHalo + 0.20 * branchHalo, 0.0, 1.0)
                    * radialFade * innerFade;

    // Resolve some individual blue-white and warm stars at overview scale.
    float starCellSize = 0.34;
    vec2 starCell = floor(p / starCellSize);
    vec2 starJitter = vec2(hash21(starCell + 17.0), hash21(starCell + 53.0));
    vec2 starCenter = (starCell + 0.12 + 0.76 * starJitter) * starCellSize;
    float starDistance = length(p - starCenter);
    float starRandom = hash21(starCell + 101.0);
    float starDensity = clamp(0.012 + 0.14 * armClouds + 0.025 * exp(-r / 21.0) * radialFade
                              + 0.012 * exp(-r * r / 120.0), 0.0, 0.20);
    float starSelection = smoothstep(1.0 - starDensity, 1.0, starRandom);
    float starMask = starSelection * exp(-pow(starDistance / 0.060, 2.0)) * radialFade;
    float starGlow = starSelection * exp(-pow(starDistance / 0.16, 2.0)) * radialFade;
    float starHue = hash21(starCell + 211.0);
    vec3 starColor = starHue < 0.22 ? vec3(1.0, 0.56, 0.46)
                   : (starHue < 0.52 ? vec3(0.60, 0.76, 1.0) : vec3(0.90, 0.94, 1.0));
    float starPower = 0.45 + 2.4 * hash21(starCell + 307.0);
    vec3 starSpecks = starColor * (starMask * starPower + starGlow * starPower * 0.12);

    // A narrow, offset absorption lane gives the arms their dark dust silhouettes.
    float dustLane = exp(-pow((majorDistance - armWidth * 0.38) / (armWidth * 0.17), 2.0));
    float dustPattern = mix(0.25, 0.85, cloudMask) * radialFade * innerFade;

    // Tilted, luminous old-star bar and compact golden nucleus.
    vec2 barP = rotate2(p, -BAR_ANGLE);
    float bar = exp(-pow(abs(barP.x) / 12.5, 1.7) - pow(abs(barP.y) / 3.0, 1.7));
    float nucleus = exp(-dot(p, p) / (2.0 * 2.8 * 2.8));

    float diskGlow = exp(-r / 21.0) * radialFade;
    float outerHaze = exp(-pow(max(r - 27.0, 0.0) / 7.0, 2.0))
                    * (1.0 - smoothstep(39.0, 49.0, r));

    vec3 blueDisk = vec3(0.17, 0.25, 0.43) * diskGlow * (0.48 + 0.52 * cloudMask);
    vec3 blueArms = vec3(0.36, 0.49, 0.74) * armClouds * (0.62 + 0.38 * fineNoise);
    vec3 faintArms = vec3(0.19, 0.29, 0.50) * (minorHalo + 0.18 * branchHalo) * radialFade * innerFade * 0.48;
    vec3 warmBar = vec3(1.0, 0.70, 0.34) * bar * 1.65;
    vec3 warmCore = vec3(1.0, 0.83, 0.56) * nucleus * 1.05;
    vec3 starFormingRegions = vec3(1.0, 0.18, 0.27) * pinkKnots * 2.5;
    vec3 dustSilhouette = vec3(0.035, 0.055, 0.10) * dustLane * dustPattern * majorHalo * 0.45;
    vec3 halo = vec3(0.11, 0.17, 0.29) * outerHaze * 0.48;

    return max(blueDisk + blueArms + faintArms + warmBar + warmCore
               + starFormingRegions + starSpecks + halo - dustSilhouette, vec3(0.0));
}

void main() {
    vec3 base_color = texture(scene, uv).rgb;
    vec3 overview = milkyWayOverview(uv);
    // At galaxy scale, resolve the crowded point field into the diffuse
    // spiral structure; individual stars return smoothly during zoom-in.
    base_color = mix(base_color, overview, u_overviewWeight);
    float base_lum = dot(base_color, vec3(0.2126, 0.7152, 0.0722));

    // Bloom accumulation (Fibonacci spiral sampling)
    vec3 bloom = vec3(0.0);
    float total_weight = 0.0;

    for (int i = 0; i < samples; i++) {
        float theta = float(i) * GOLDEN_ANGLE;
        float r = radius * sqrt(float(i) / float(samples));
        vec2 offset = vec2(cos(theta), sin(theta)) * r;

        vec3 sc = texture(scene, uv + offset).rgb;
        float brightness = dot(sc, vec3(0.2126, 0.7152, 0.0722));
        float contribution = max(0.0, brightness - threshold);

        if (contribution > 0.0) {
            float weight = exp(-float(i) / float(samples) * 3.0);
            bloom += sc * weight * contribution;
            total_weight += weight;
        }
    }

    if (total_weight > 0.0) {
        bloom /= total_weight;
    }

    // CRITICAL: suppress bloom inside the event horizon.
    // If the base pixel is very dark, it is the void - do not add glow.
    float bloom_mask = smoothstep(0.0, 0.06, base_lum);

    float pointStarBloom = 1.0 - u_overviewWeight;
    vec3 final_color = base_color + bloom * intensity * bloom_mask * pointStarBloom;

    // ACES filmic tonemapping
    final_color = (final_color * (2.51 * final_color + 0.03)) /
                  (final_color * (2.43 * final_color + 0.59) + 0.14);

    fragColor = vec4(final_color, 1.0);
}
