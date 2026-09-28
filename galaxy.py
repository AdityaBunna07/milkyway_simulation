import numpy as np
import moderngl
import glm
from galactic_disk import stellar_rgb

class GalacticBulge:
    def __init__(self, ctx, base_dir):
        self.ctx = ctx
        rng = np.random.default_rng(41073)
        self.num_stars = 800000
        
        # Load shaders
        with open(base_dir / "shaders" / "bulge_vert.glsl", encoding="utf-8") as f:
            vert_code = f.read()
        with open(base_dir / "shaders" / "bulge_frag.glsl", encoding="utf-8") as f:
            frag_code = f.read()
            
        self.program = self.ctx.program(
            vertex_shader=vert_code,
            fragment_shader=frag_code,
        )
        
        # Dense old bulge plus an elongated central bar, with a compact core.
        component = rng.random(self.num_stars)
        x = np.empty(self.num_stars)
        y = np.empty(self.num_stars)
        z = np.empty(self.num_stars)

        spheroid = component < 0.665
        r_sph = np.minimum(rng.gamma(2.0, 1.15, spheroid.sum()), 9.0)
        cos_phi = rng.uniform(-1.0, 1.0, spheroid.sum())
        phi = np.arccos(cos_phi)
        theta = rng.uniform(0.0, 2.0 * np.pi, spheroid.sum())
        x[spheroid] = r_sph * np.sin(phi) * np.cos(theta)
        z[spheroid] = r_sph * np.sin(phi) * np.sin(theta)
        y[spheroid] = r_sph * cos_phi * 0.38

        bar = (component >= 0.665) & (component < 0.925)
        bar_r = np.minimum(rng.gamma(2.0, 1.35, bar.sum()), 8.0)
        # Offset the bar from the disk's reference axis, as in a barred spiral.
        bar_angle = rng.normal(0.34, 0.16, bar.sum())
        x[bar] = bar_r * np.cos(bar_angle) * 1.7
        z[bar] = bar_r * np.sin(bar_angle) * 0.72
        y[bar] = rng.normal(0.0, 0.38, bar.sum())

        core = (component >= 0.925) & (component < 0.98)
        core_r = rng.exponential(0.42, core.sum())
        core_theta = rng.uniform(0.0, 2.0 * np.pi, core.sum())
        x[core] = core_r * np.cos(core_theta)
        z[core] = core_r * np.sin(core_theta)
        y[core] = rng.normal(0.0, 0.18, core.sum())

        # Sparse, extended stellar halo: old stars and globular-cluster-like outliers.
        halo = component >= 0.98
        halo_r = np.exp(rng.uniform(np.log(8.0), np.log(35.0), halo.sum()))
        halo_cos_phi = rng.uniform(-1.0, 1.0, halo.sum())
        halo_sin_phi = np.sqrt(1.0 - halo_cos_phi * halo_cos_phi)
        halo_theta = rng.uniform(0.0, 2.0 * np.pi, halo.sum())
        x[halo] = halo_r * halo_sin_phi * np.cos(halo_theta)
        z[halo] = halo_r * halo_sin_phi * np.sin(halo_theta)
        y[halo] = halo_r * halo_cos_phi
        
        # Create a small hollow center so stars don't overlap the exact singularity center (optional)
        # But the prompt says the black hole is at 0,0,0 and bulge around it.
        
        positions = np.column_stack((x, y, z)).astype('f4')
        
        # The old bulge is dominated by cooler evolved stars.
        temperature = rng.lognormal(np.log(4550.0), 0.30, self.num_stars)
        temperature[core] *= 1.08
        temperature[halo] = rng.lognormal(np.log(4300.0), 0.34, halo.sum())
        halo_blue_giants = halo & (rng.random(self.num_stars) < 0.06)
        temperature[halo_blue_giants] = rng.lognormal(np.log(9000.0), 0.18, halo_blue_giants.sum())
        colors = stellar_rgb(temperature).astype('f4')
        colors += rng.normal(0, 0.025, (self.num_stars, 3))
        colors = np.clip(colors, 0.0, 1.0)
        
        # Sizes: 90% tiny, 8% medium, 2% bright
        sizes = np.zeros(self.num_stars, dtype='f4')
        rand_s = rng.random(self.num_stars)
        tiny = rand_s < 0.9
        med_s = (rand_s >= 0.9) & (rand_s < 0.98)
        large = rand_s >= 0.98
        
        sizes[tiny] = rng.uniform(0.01, 0.04, tiny.sum())
        sizes[med_s] = rng.uniform(0.05, 0.1, med_s.sum())
        sizes[large] = rng.uniform(0.12, 0.25, large.sum())
        
        # Brightness
        brightness = np.clip(rng.lognormal(mean=-0.72, sigma=0.45, size=self.num_stars), 0.08, 1.0).astype('f4')
        brightness[large] = rng.uniform(0.9, 1.8, large.sum())
        brightness[halo] *= 0.28
        
        star_data = np.column_stack((positions, colors, sizes, brightness)).astype('f4')
        
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
        # Disable depth write so stars don't occlude each other in weird ways, 
        # but MilkyWay simulation probably runs without depth test anyway.
        
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
