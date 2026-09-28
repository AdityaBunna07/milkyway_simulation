class LODManager:
    """
    Determines which level of detail should be used
    based on the camera's distance from the object.
    """

    NEAR = 0
    MEDIUM = 1
    FAR = 2

    def __init__(self):
        # Configurable distances and transition widths
        self.near_distance = 10.0
        self.medium_distance = 50.0
        
        self.near_transition_width = 4.0
        self.medium_transition_width = 10.0

    def smoothstep(self, edge0, edge1, x):
        t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
        return t * t * (3.0 - 2.0 * t)

    def get_state(self, distance):
        # Calculate transition factors
        near_start = self.near_distance - self.near_transition_width / 2.0
        near_end = self.near_distance + self.near_transition_width / 2.0
        
        # Overlap transition band for MEDIUM -> FAR is 40 to 50
        med_start = 40.0
        med_end = 50.0
        
        # t1 goes from 0 (at near_start) to 1 (at near_end)
        t1 = self.smoothstep(near_start, near_end, distance)
        
        # t2 goes from 0 (at med_start) to 1 (at med_end)
        t2 = self.smoothstep(med_start, med_end, distance)
        
        near_weight = 1.0 - t1
        medium_weight = t1 * (1.0 - t2)
        far_weight = t2
        
        # Ray-march detail strictly drops during the 8-12 transition
        ray_march_detail = 1.0 - t1
        
        # Volumetric detail drops over 25-35 for the MEDIUM turbulence
        volumetric_detail = 1.0 - self.smoothstep(25.0, 35.0, distance)
        
        # Disk thickness: 
        # 8-12: 1.0 -> 0.2
        # 25-50: 0.2 -> 0.01 (thinner)
        if distance < 12.0:
            disk_thickness = 1.0 - 0.8 * self.smoothstep(8.0, 12.0, distance)
        else:
            disk_thickness = 0.2 - 0.19 * self.smoothstep(25.0, 50.0, distance)
            
        # Outer disk radius starts reducing at 25, disappears at 50 (shrinks to inner ring)
        disk_outer_radius = 12.0 - 8.0 * self.smoothstep(25.0, 50.0, distance)
        
        # Glow smoothly increases from 25 to 50
        glow_intensity = self.smoothstep(25.0, 50.0, distance)
        
        # Inner ring strength turns on during NEAR->MEDIUM, stays on
        inner_ring_strength = self.smoothstep(8.0, 12.0, distance)
        
        # Doppler subtly reduces as the disk compacts
        doppler_strength = 1.0 - 0.8 * self.smoothstep(25.0, 50.0, distance)
        
        # Bulge becomes visible at distance 40, fully visible at 100
        bulge_visibility = self.smoothstep(40.0, 100.0, distance)
            
        return {
            "near_weight": near_weight,
            "medium_weight": medium_weight,
            "far_weight": far_weight,
            "t1": t1,
            "t2": t2,
            "ray_march_detail": ray_march_detail,
            "volumetric_detail": volumetric_detail,
            "disk_thickness": disk_thickness,
            "glow_intensity": glow_intensity,
            "inner_ring_strength": inner_ring_strength,
            "doppler_strength": doppler_strength,
            "disk_outer_radius": disk_outer_radius,
            "bulge_visibility": bulge_visibility
        }