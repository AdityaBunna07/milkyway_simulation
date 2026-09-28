import numpy as np

class NebulaManager:
    def __init__(self, num_nebulae=100):
        # Independent deterministic stream: nebulae do not change the star field.
        rng = np.random.default_rng(1337)
        
        self.num_nebulae = num_nebulae
        self.nebulae_data = [] # List of dicts for shader uniforms
        self.stars_data = []   # List of stars to add to galactic disk
        
        # Spiral Parameters (must match galactic_disk.py)
        ARM_COUNT = 4
        SPIRAL_TIGHTNESS = 2.5
        INNER_RADIUS = 2.0
        BAR_ANGLE = 0.34
        
        # We want nebulae mostly in the active star-forming ring
        MIN_R = 6.0
        MAX_R = 40.0
        
        # Emission colors (Realistic Astrophotography H-II palette)
        # H-alpha (656 nm, deep red) + H-beta (486 nm, blue-cyan) + O-III (500 nm, teal)
        color_hii_crimson = np.array([1.00, 0.035, 0.015]) # H-alpha red
        color_hii_magenta = np.array([1.00, 0.08, 0.38]) # H-alpha pink
        color_hii_salmon  = np.array([1.00, 0.25, 0.40]) # Warm ionized gas
        color_hii_pale    = np.array([1.00, 0.42, 0.66]) # Bright mixed emission
        color_oiii_teal   = np.array([0.015, 0.62, 1.00]) # O-III blue-cyan
        color_oiii_violet = np.array([0.28, 0.12, 1.00]) # Blue-violet gas
        
        # Blue/white for reflection nebulae (dust scattering hot young star light)
        color_ref_bright = np.array([0.30, 0.58, 1.00])
        color_ref_dusty  = np.array([0.12, 0.28, 0.88])
        
        for i in range(num_nebulae):
            # 1. Position along spiral arms
            # Preferentially place in the denser parts (r ~ 10-35)
            r = rng.gamma(shape=4.0, scale=4.0) + MIN_R
            r = np.clip(r, MIN_R, MAX_R)
            
            # Select arm
            arm_index = rng.choice(ARM_COUNT, p=[0.36, 0.14, 0.35, 0.15])
            arm_base_angle = arm_index * (2 * np.pi / ARM_COUNT)
            
            # Ideal log spiral angle
            ideal_theta = arm_base_angle + BAR_ANGLE + SPIRAL_TIGHTNESS * np.log(r / INNER_RADIUS)
            
            # Slight offset inside/outside the arm
            theta_offset = rng.normal(0, 0.15)
            theta = ideal_theta + theta_offset
            
            # 3D Position
            x = r * np.cos(theta)
            z = r * np.sin(theta)
            
            # Nebulae are very close to the galactic plane (thin disk)
            y = rng.normal(0, 0.1)
            
            # 2. Size and Type
            size_roll = rng.random()
            if size_roll < 0.1: # 10% hero regions
                radius = rng.uniform(3.0, 5.0)
                density = rng.uniform(1.0, 1.5)
            elif size_roll < 0.3: # 20% medium regions
                radius = rng.uniform(1.5, 3.0)
                density = rng.uniform(0.7, 1.1)
            else: # 70% small faint regions
                radius = rng.uniform(0.6, 1.5)
                density = rng.uniform(0.4, 0.7)
                
            # Reflection fraction (minority are blue)
            ref_roll = rng.random()
            if ref_roll < 0.25: # Blue reflection nebulae
                c = color_ref_bright
                emission_strength = rng.uniform(1.2, 1.8)
            elif ref_roll < 0.42: # Blue-cyan O-III regions with a hint of H-alpha
                c = color_oiii_teal * 0.65 + color_oiii_violet * 0.20 + color_hii_magenta * 0.15
                emission_strength = rng.uniform(1.3, 1.9)
            elif ref_roll < 0.62: # Mixed H-alpha and O-III regions
                c = color_ref_dusty * 0.35 + color_hii_magenta * 0.25 + color_oiii_teal * 0.40
                emission_strength = rng.uniform(1.2, 1.8)
            else: # H-alpha regions remain common in star-forming arms
                c_roll = rng.random()
                if c_roll < 0.30: c = color_hii_crimson
                elif c_roll < 0.65: c = color_hii_magenta
                else: c = color_hii_salmon
                emission_strength = rng.uniform(1.0, 1.6)
                
            # Add some variance to color
            c = c + rng.normal(0, 0.035, 3)
            c = np.clip(c, 0.0, 1.0)
            
            # Pack metadata into the shader
            # w of position = radius
            # w of color = combined density/emission parameter
            self.nebulae_data.append({
                'position': [x, y, z, radius],
                'color': [c[0], c[1], c[2], density * emission_strength]
            })
            
            # 3. Generate Young Bright Stars associated with this nebula
            # Create dense star clusters (aggregates) that stand out from the surrounding disk
            if size_roll < 0.4: # Top 40% of nebulae get star clusters
                if size_roll < 0.1: # Hero regions get massive clusters
                    num_stars = rng.integers(200, 500)
                elif size_roll < 0.25: # Medium regions get dense clusters
                    num_stars = rng.integers(70, 150)
                else: # Smaller regions get sparse clusters
                    num_stars = rng.integers(20, 50)
                    
                for _ in range(num_stars):
                    # Place star concentrated around the nebula core
                    dist_scale = rng.gamma(shape=1.5, scale=0.3)
                    theta_star = rng.uniform(0, 2 * np.pi)
                    phi_star = rng.uniform(0, np.pi)
                    
                    # 3D offset (flattened slightly in the Y axis)
                    dx = radius * dist_scale * np.sin(phi_star) * np.cos(theta_star)
                    dy = (radius * dist_scale * np.cos(phi_star)) * 0.4
                    dz = radius * dist_scale * np.sin(phi_star) * np.sin(theta_star)
                    
                    sx = x + dx
                    sy = y + dy
                    sz = z + dz
                    
                    # Cluster star colors:
                    # Blend of extremely hot young blue stars, white giants, 
                    # and intensely colored stars matching the nebula gas to simulate unresolved glowing knots.
                    sc_roll = rng.random()
                    if sc_roll < 0.3:
                        scolor = [0.7, 0.85, 1.0] # Bright young blue
                    elif sc_roll < 0.5:
                        scolor = [0.9, 0.95, 1.0] # Blue-white
                    elif sc_roll < 0.65:
                        scolor = [1.0, 1.0, 1.0] # Pure white
                    else:
                        # 35% of stars in the cluster take on the glowing gas color of the nebula itself
                        scolor = c 
                        
                    # Add subtle variance
                    scolor = np.clip(np.array(scolor) + rng.normal(0, 0.05, 3), 0.0, 1.0)
                        
                    # Sizes and brightness
                    # A few very bright massive stars, mostly smaller cluster members
                    s_roll = rng.random()
                    if s_roll < 0.02:
                        ssize = rng.uniform(0.12, 0.25) # O-type giant
                        sbright = rng.uniform(2.0, 3.5)
                    elif s_roll < 0.15:
                        ssize = rng.uniform(0.06, 0.12) # B-type
                        sbright = rng.uniform(1.2, 2.0)
                    else:
                        ssize = rng.uniform(0.02, 0.05) # Standard cluster members
                        sbright = rng.uniform(0.5, 1.0)
                    
                    self.stars_data.append([sx, sy, sz, scolor[0], scolor[1], scolor[2], ssize, sbright])

    def get_stars_array(self):
        if not self.stars_data:
            return np.zeros((0, 8), dtype='f4')
        return np.array(self.stars_data, dtype='f4')

    def get_shader_uniforms(self):
        """Returns two flat lists of floats for the shader arrays."""
        positions = []
        colors = []
        for n in self.nebulae_data:
            positions.extend(n['position'])
            colors.extend(n['color'])
            
        # Pad up to a maximum number (e.g. 150) if needed
        MAX_NEBULAE = 150
        while len(positions) // 4 < MAX_NEBULAE:
            positions.extend([0.0, 0.0, 0.0, 0.0])
            colors.extend([0.0, 0.0, 0.0, 0.0])
            
        return positions, colors
