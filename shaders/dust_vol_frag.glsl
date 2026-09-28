#version 330

in vec2 v_uv;
out vec4 fragColor;

uniform vec3 u_camPos;
uniform mat4 u_invVP;
uniform mat4 u_galaxyModel; // inverse rotation of galaxy

uniform float u_dustWeight;

// Tunable params
uniform float u_dustOpacity;
uniform float u_dustWidth;
uniform float u_dustArmOffset;
uniform float u_dustNoiseScale;
uniform float u_dustDensity;

// New params for upgraded dust
uniform float u_dustHeightScale;   // vertical thickness control
uniform float u_dustLaneWidth;     // narrow dense lane half-width
uniform float u_dustDiffuseWidth;  // broader diffuse envelope half-width
uniform float u_camDist;           // camera distance for LOD

// ============================================================
// Hash and Noise — coherent 3D value noise with smooth interp
// ============================================================

float hash(vec3 p) {
    p = fract(p * 0.3183099 + 0.1);
    p *= 17.0;
    return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}

float noise(vec3 x) {
    vec3 i = floor(x);
    vec3 f = fract(x);
    // Quintic interpolation for smoother derivatives
    f = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);
    return mix(mix(mix(hash(i + vec3(0,0,0)), hash(i + vec3(1,0,0)), f.x),
                   mix(hash(i + vec3(0,1,0)), hash(i + vec3(1,1,0)), f.x), f.y),
               mix(mix(hash(i + vec3(0,0,1)), hash(i + vec3(1,0,1)), f.x),
                   mix(hash(i + vec3(0,1,1)), hash(i + vec3(1,1,1)), f.x), f.y), f.z);
}

// 5-octave FBM with configurable lacunarity
float fbm5(vec3 p) {
    float f = 0.0;
    float w = 0.5;
    float totalW = 0.0;
    for (int i = 0; i < 5; i++) {
        f += w * noise(p);
        totalW += w;
        p *= 2.03;   // slight lacunarity variation avoids grid artifacts
        w *= 0.48;
    }
    return f / totalW;
}

// 3-octave FBM for cheaper large-scale features
float fbm3(vec3 p) {
    float f = 0.0;
    float w = 0.5;
    float totalW = 0.0;
    for (int i = 0; i < 3; i++) {
        f += w * noise(p);
        totalW += w;
        p *= 2.07;
        w *= 0.5;
    }
    return f / totalW;
}

// Interleaved gradient noise for temporally stable ray jitter
// (no flickering unlike hash-based jitter)
float interleavedGradientNoise(vec2 pixel) {
    return fract(52.9829189 * fract(0.06711056 * pixel.x + 0.00583715 * pixel.y));
}

// ============================================================
// Slab intersection
// ============================================================

vec2 intersectSlab(vec3 ro, vec3 rd, float H) {
    // Handle rays nearly parallel to the slab
    if (abs(rd.y) < 1e-6) {
        if (abs(ro.y) < H) return vec2(0.0, 200.0);
        else return vec2(0.0, -1.0); // miss
    }
    float t1 = (-H - ro.y) / rd.y;
    float t2 = (H - ro.y) / rd.y;
    float tmin = min(t1, t2);
    float tmax = max(t1, t2);
    tmin = max(0.0, tmin);
    return vec2(tmin, tmax);
}

// ============================================================
// Galaxy parameters — must match galactic_disk.py exactly
// ============================================================

const float PI = 3.14159265;
const float TWO_PI = 6.28318530;
const float INNER_RADIUS = 2.0;
const float OUTER_RADIUS = 45.0;
const float ARM_COUNT = 4.0;
const float SPIRAL_TIGHTNESS = 2.5;
const float BAR_ANGLE = 0.34;

// ============================================================
// Dust density function — the core of the upgrade
// ============================================================

float getDustDensity(vec3 p) {
    float r = length(p.xz);

    // Hard cutoffs with smooth ramps
    if (r < 2.5 || r > 47.0) return 0.0;

    // ----------------------------------------------------------
    // 1. RADIAL DISTRIBUTION
    //    Weak near center, prominent across disk, smooth outer fade
    // ----------------------------------------------------------
    // Ramp up from inner edge: 0 at r=2.5 → 1 at r=6
    float inner_ramp = smoothstep(2.5, 6.0, r);
    // Exponential disk profile (matches star distribution shape)
    float disk_profile = r * exp(-r / 10.0);  // peaks around r=10
    // Normalize so peak ≈ 1
    disk_profile = disk_profile / (10.0 * exp(-1.0));
    // Smooth outer fade
    float outer_fade = 1.0 - smoothstep(35.0, 46.0, r);

    float radial = inner_ramp * disk_profile * outer_fade;

    // ----------------------------------------------------------
    // 2. VERTICAL PROFILE
    //    Thin Gaussian, height varies smoothly with radius
    // ----------------------------------------------------------
    float scale_height = u_dustHeightScale * (0.25 + 0.2 * smoothstep(5.0, 30.0, r));
    float y_norm = p.y / scale_height;
    float vertical = exp(-0.5 * y_norm * y_norm);

    // ----------------------------------------------------------
    // 3. SPIRAL ARM ALIGNMENT
    //    Same log-spiral as galactic_disk.py, with narrow lane + diffuse envelope
    // ----------------------------------------------------------
    float theta = atan(p.z, p.x);

    // Find angular distance to closest arm
    float min_dist = 100.0;
    float closest_arm_weight = 0.0;
    for (int i = 0; i < int(ARM_COUNT); i++) {
        float arm_base = float(i) * (TWO_PI / ARM_COUNT);
        // Exact same spiral equation as galactic_disk.py line 72
        float ideal_theta = arm_base + BAR_ANGLE + SPIRAL_TIGHTNESS * log(r / INNER_RADIUS);
        // Real arms meander and branch instead of following a perfect equation.
        ideal_theta += 0.025 * sin(r * 0.42 + arm_base * 1.7)
                     + 0.012 * sin(r * 0.91 - arm_base * 2.3);

        float d_theta = mod(theta - ideal_theta + PI, TWO_PI) - PI;
        // Apply the arm offset so dust is slightly inside the stellar arm
        float d_arm = abs(d_theta - u_dustArmOffset);
        float prominence = (i == 0 || i == 2) ? 1.0 : 0.58;
        if (d_arm < min_dist) {
            min_dist = d_arm;
            closest_arm_weight = prominence;
        }

        // The two main arms shed faint, widening branches at larger radii.
        if (i == 0 || i == 2) {
            float branch_offset = 0.16 * smoothstep(12.0, 34.0, r);
            float d_branch_pos = abs(d_theta - branch_offset - u_dustArmOffset);
            if (d_branch_pos < min_dist) {
                min_dist = d_branch_pos;
                closest_arm_weight = 0.34;
            }
            float d_branch_neg = abs(d_theta + branch_offset - u_dustArmOffset);
            if (d_branch_neg < min_dist) {
                min_dist = d_branch_neg;
                closest_arm_weight = 0.34;
            }
        }
    }

    // Convert angular distance to approximate linear distance
    // (more physically correct than pure angular)
    float linear_dist = min_dist * r;

    // Narrow dense lane (Gaussian core)
    float lane_w = u_dustLaneWidth * r * (0.88 + 0.18 * sin(r * 0.31));
    float dense_lane = exp(-linear_dist * linear_dist / (lane_w * lane_w + 0.001));

    // Broader diffuse envelope
    float diff_w = u_dustDiffuseWidth * r;
    float diffuse_env = exp(-linear_dist * linear_dist / (diff_w * diff_w + 0.001)) * 0.16;

    float arm_factor = (dense_lane + diffuse_env) * closest_arm_weight;

    // The Orion Spur is a shorter, fainter branch between two major arms.
    float spur_theta = BAR_ANGLE + 0.785398 + SPIRAL_TIGHTNESS * log(r / INNER_RADIUS);
    float spur_delta = mod(theta - spur_theta + PI, TWO_PI) - PI;
    float spur_width = 0.085 * r;
    float spur_lane = exp(-(spur_delta * r) * (spur_delta * r) / (spur_width * spur_width + 0.001));
    float spur_extent = smoothstep(13.0, 17.0, r) * (1.0 - smoothstep(27.0, 32.0, r));
    arm_factor += 0.30 * spur_lane * spur_extent;

    // ----------------------------------------------------------
    // 4. MULTI-SCALE NOISE — domain-warped for filamentary structure
    // ----------------------------------------------------------
    float ns = u_dustNoiseScale;

    // Domain warp: offset sample position with noise to create filaments
    vec3 warp_offset = vec3(
        fbm3(p * ns * 0.12 + vec3(5.2, 1.3, 9.7)),
        fbm3(p * ns * 0.12 + vec3(3.7, 8.1, 2.4)),
        fbm3(p * ns * 0.12 + vec3(1.9, 4.6, 7.3))
    ) * 3.0;

    vec3 warped = p + warp_offset;

    // Large-scale: broad clouds and gaps across the galaxy
    float n_large = fbm3(warped * ns * 0.15);
    // Threshold to create distinct cloud/gap regions
    float cloud_mask = smoothstep(0.28, 0.55, n_large);

    // Medium-scale: broken lanes, clumps
    float n_medium = fbm5(warped * ns * 0.5 + vec3(12.3, 4.5, 6.7));
    // Create clumpy structure
    float clumps = smoothstep(0.2, 0.6, n_medium);

    // Fine-scale: wisps and irregular boundaries
    float n_fine = fbm3(p * ns * 1.5 + vec3(7.1, 2.8, 5.3));
    float wisps = 0.6 + 0.4 * n_fine;  // subtle edge variation

    // Leave gaps between molecular clouds while retaining faint diffuse dust.
    float noise_combined = cloud_mask * mix(0.28, 1.0, clumps) * wisps;

    // ----------------------------------------------------------
    // 5. COMBINE all factors
    // ----------------------------------------------------------
    float density = radial * vertical * arm_factor * noise_combined * u_dustDensity;

    return max(density, 0.0);
}


void main() {
    // 1. Reconstruct ray direction
    vec2 ndc = v_uv * 2.0 - 1.0;
    vec4 target = u_invVP * vec4(ndc, 1.0, 1.0);
    vec3 rd = normalize(target.xyz / target.w - u_camPos);
    vec3 ro = u_camPos;

    // 2. Intersect with galactic dust slab
    // Height varies: thicker slab to encompass the full dust volume
    float slab_H = 2.0;
    vec2 t_bounds = intersectSlab(ro, rd, slab_H);

    float optical_depth = 0.0;
    float front_depth = -1.0;   // linear distance to first significant dust

    if (t_bounds.y > t_bounds.x && u_dustWeight > 0.001) {
        float t = t_bounds.x;
        float t_end = min(t_bounds.y, 150.0);

        // Adaptive step count: use more steps when the path through dust is short
        // (which means we're close and need detail) but stay within budget
        int steps = 32;
        float dt = (t_end - t) / float(steps);

        // Stable jitter using interleaved gradient noise
        vec2 pixel = gl_FragCoord.xy;
        float jitter = interleavedGradientNoise(pixel);
        t += dt * jitter;

        // Ray march with early termination
        float transmittance = 1.0;

        for (int i = 0; i < 32; i++) {
            if (t > t_end) break;
            if (transmittance < 0.01) break;  // early termination

            vec3 p = ro + rd * t;

            // Transform to galaxy local coordinates (undo galaxy rotation)
            vec4 p_local = u_galaxyModel * vec4(p, 1.0);

            float dens = getDustDensity(p_local.xyz);

            if (dens > 0.001) {
                // Record front depth: first significant dust distance
                if (front_depth < 0.0) {
                    front_depth = t;
                }
                optical_depth += dens * dt;
                transmittance = exp(-optical_depth * u_dustOpacity * u_dustWeight);
            }

            t += dt;
        }
    }

    // Transmittance: exp(-optical_depth * opacity * weight)
    float final_transmittance = exp(-optical_depth * u_dustOpacity * u_dustWeight);

    // Encode front depth as linear distance, -1 means no dust hit
    // Normalize to a reasonable range for the float16 texture
    float encoded_depth = (front_depth < 0.0) ? 0.0 : front_depth / 200.0;

    fragColor = vec4(final_transmittance, encoded_depth, 0.0, 1.0);
}
