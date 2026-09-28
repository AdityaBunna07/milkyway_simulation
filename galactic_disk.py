import numpy as np
import moderngl
import glm

def stellar_rgb(temperature):
    """Approximate blackbody color with a compact interpolation table."""
    kelvin = np.array([2800.0, 4000.0, 5200.0, 6500.0, 9000.0, 16000.0, 30000.0])
    rgb = np.array([
        [1.00, 0.30, 0.08], [1.00, 0.58, 0.30], [1.00, 0.78, 0.54],
        [1.00, 0.91, 0.80], [0.72, 0.83, 1.00], [0.55, 0.70, 1.00],
        [0.48, 0.64, 1.00],
    ])
    log_temp = np.log(np.clip(temperature, kelvin[0], kelvin[-1]))
    return np.stack([
        np.interp(log_temp, np.log(kelvin), rgb[:, channel])
        for channel in range(3)
    ], axis=1)

class GalacticDisk:
    def __init__(self, ctx, base_dir, nebula_stars=None):
        self.ctx = ctx
        rng = np.random.default_rng(20260926)
        self.num_stars = 2000000

        # Load shaders (reusing bulge shaders for now, but they will have u_galaxyAngle)
        with open(base_dir / "shaders" / "bulge_vert.glsl", encoding="utf-8") as f:
            vert_code = f.read()
        with open(base_dir / "shaders" / "bulge_frag.glsl", encoding="utf-8") as f:
            frag_code = f.read()

        self.program = self.ctx.program(
            vertex_shader=vert_code,
            fragment_shader=frag_code,
        )

        # ==========================================================
        # Spiral Galaxy Parameters
        # ==========================================================
        ARM_COUNT = 4
        SPIRAL_TIGHTNESS = 2.5      # 'b' in theta = b * log(r/r0)
        ARM_WIDTH = 0.24       # Base angular width
        ARM_STRENGTH = 0.85     # Max proportion of stars in arms
        BAR_ANGLE = 0.34         # Align the major arms with the central bar
        INNER_RADIUS = 2.0
        OUTER_RADIUS = 45.0
        BULGE_RADIUS = 6.0          # Where arms fully emerge

        DISK_SCALE = 8.0

        # 1. Generate Radii
        # Use Gamma distribution (shape=2) to get probability P(r) ~ r * exp(-r / DISK_SCALE)
        # This accounts for increasing circumference area at larger radii.
        radius = rng.gamma(shape=2.0, scale=DISK_SCALE, size=self.num_stars)

        # Truncate via rejection sampling instead of clipping to avoid artificial rings
        invalid = (radius < INNER_RADIUS) | (radius > OUTER_RADIUS)
        while np.any(invalid):
            radius[invalid] = rng.gamma(shape=2.0, scale=DISK_SCALE, size=np.sum(invalid))
            invalid = (radius < INNER_RADIUS) | (radius > OUTER_RADIUS)

        # 2. Determine Arm vs Inter-arm Population (Density Waves)
        # Arms emerge smoothly from the bulge
        def smoothstep(edge0, edge1, x):
            t = np.clip((x - edge0) / (edge1 - edge0), 0.0, 1.0)
            return t * t * (3.0 - 2.0 * t)

        arm_strength = smoothstep(INNER_RADIUS, BULGE_RADIUS, radius)

        # Probability of a star belonging to an arm
        p_arm = ARM_STRENGTH * arm_strength
        is_arm = rng.random(self.num_stars) < p_arm

        # 3. Calculate Angles
        theta = np.zeros(self.num_stars)

        # Inter-arm stars: uniformly distributed in angle
        theta[~is_arm] = rng.uniform(0, 2 * np.pi, np.sum(~is_arm))

        # Arm stars: distributed along logarithmic spirals
        num_arm_stars = np.sum(is_arm)

        # Slightly vary density between arms to make it less perfect
        # Two major arms dominate; the other two are weaker branches/segments.
        arm_probs = np.array([0.36, 0.14, 0.35, 0.15])
        arm_indices = rng.choice(ARM_COUNT, p=arm_probs, size=num_arm_stars)
        arm_base_angles = arm_indices * (2 * np.pi / ARM_COUNT) + BAR_ANGLE

        # Base logarithmic spiral angle: theta = theta0 + b * log(r / r0)
        ideal_theta = arm_base_angles + SPIRAL_TIGHTNESS * np.log(radius[is_arm] / INNER_RADIUS)

        # Slightly vary width between arms
        arm_widths = np.array([1.0, 1.1, 0.9, 1.05]) * ARM_WIDTH

        # Angular spread: tighter near the core, slightly wider at the edges (optional, but realistic)
        # Using a Gaussian falloff around the arm center
        spread = rng.normal(0, arm_widths[arm_indices], num_arm_stars)

        arm_theta = ideal_theta + spread
        branch_mask = rng.random(num_arm_stars) < 0.18
        branch_direction = np.where(rng.random(num_arm_stars) < 0.5, -1.0, 1.0)
        branch_drift = np.clip((radius[is_arm] - 12.0) / 33.0, 0.0, 1.0)
        arm_theta[branch_mask] += branch_direction[branch_mask] * (0.12 + 0.18 * branch_drift[branch_mask])
        theta[is_arm] = arm_theta

        # The Sun's Orion Spur is a partial, low-density branch between major arms.
        spur_mask = (~is_arm) & (radius > 13.0) & (radius < 31.0) & (rng.random(self.num_stars) < 0.10)
        spur_radius = radius[spur_mask]
        theta[spur_mask] = (
            BAR_ANGLE + np.pi / 4.0
            + SPIRAL_TIGHTNESS * np.log(spur_radius / INNER_RADIUS)
            + rng.normal(0.0, 0.075, spur_radius.size)
        )
        # 4. 3D Structure
        x = radius * np.cos(theta)
        z = radius * np.sin(theta)

        # Thin stellar disk that gradually flares at its outer edge.
        thickness_scale = 0.16 + 0.10 * smoothstep(20.0, OUTER_RADIUS, radius)
        y = rng.normal(0, 1.0, self.num_stars) * thickness_scale

        positions = np.column_stack((x, y, z)).astype('f4')

        # Sample temperatures by population, then map temperature to approximate
        # blackbody RGB. Arms are younger/hotter; inter-arm stars skew cooler.
        arm_mask = is_arm | spur_mask
        n_arm = np.sum(arm_mask)
        temperature = np.empty(self.num_stars)
        temperature[~arm_mask] = rng.lognormal(np.log(4800.0), 0.32, (~arm_mask).sum())
        temperature[arm_mask] = rng.lognormal(np.log(6800.0), 0.48, n_arm)
        temperature[arm_mask] *= rng.uniform(0.92, 1.12, n_arm)
        # The outer disk is older on average and has fewer hot, blue stars.
        temperature *= 1.0 - 0.12 * smoothstep(8.0, OUTER_RADIUS, radius)
        colors = stellar_rgb(temperature).astype('f4')
        colors += rng.normal(0, 0.025, (self.num_stars, 3))
        colors = np.clip(colors, 0.0, 1.0)

        # 6. Star Sizes: 90% tiny, 8% medium, 2% bright
        sizes = np.zeros(self.num_stars, dtype='f4')
        rand_s = rng.random(self.num_stars)
        tiny = rand_s < 0.9
        med_s = (rand_s >= 0.9) & (rand_s < 0.98)
        large = rand_s >= 0.98

        sizes[tiny] = rng.uniform(0.01, 0.03, tiny.sum())
        sizes[med_s] = rng.uniform(0.04, 0.07, med_s.sum())
        sizes[large] = rng.uniform(0.1, 0.2, large.sum())

        # Approximate a broad stellar luminosity function: many dim stars,
        # fewer luminous giants. Arm stars skew younger and more luminous.
        brightness = np.clip(rng.lognormal(mean=-0.85, sigma=0.48, size=self.num_stars), 0.08, 1.2).astype('f4')
        brightness[large] = rng.uniform(0.9, 1.7, large.sum())
        brightness[arm_mask] *= rng.uniform(1.0, 1.25, n_arm).astype('f4')
        brightness = np.clip(brightness, 0.05, 1.8)

        star_data = np.column_stack((positions, colors, sizes, brightness)).astype('f4')

        if nebula_stars is not None and len(nebula_stars) > 0:
            star_data = np.vstack((star_data, nebula_stars))
            self.num_stars += len(nebula_stars)

        self.vbo = self.ctx.buffer(star_data.tobytes())
        self.vao = self.ctx.vertex_array(
            self.program,
            [(self.vbo, '3f 3f 1f 1f', 'in_position', 'in_color', 'in_size', 'in_brightness')]
        )

    def render(self, camera, aspect_ratio, visibility, rotation_angle):
        if visibility <= 0.001:
            return

        self.ctx.enable(moderngl.PROGRAM_POINT_SIZE)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE

        if "u_visibility" in self.program:
            self.program["u_visibility"].value = visibility
        if "u_farBlend" in self.program:
            t = np.clip((camera.absolute_distance - 18.0) / (80.0 - 18.0), 0.0, 1.0)
            self.program["u_farBlend"].value = float(t * t * (3.0 - 2.0 * t))

        if "u_view" in self.program:
            self.program["u_view"].write(camera.get_view_matrix())
        if "u_projection" in self.program:
            self.program["u_projection"].write(camera.get_projection_matrix(aspect_ratio))
        if "u_model" in self.program:
            model = glm.rotate(glm.mat4(1.0), rotation_angle, glm.vec3(0.0, 1.0, 0.0))
            self.program["u_model"].write(model)

        self.vao.render(moderngl.POINTS)
