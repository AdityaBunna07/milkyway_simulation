class BlackHole:
    """
    Stores the physical and visual properties
    of the central supermassive black hole.
    """

    # ------------------------------------------------------------------
    # World-scale contract
    # ------------------------------------------------------------------
    # The black-hole raymarch operates in its own local coordinate system
    # where the accretion disk spans radii ~2.5–12.0.  Galaxy world-space
    # positions (where camera.distance=1 means "close") are multiplied by
    # this factor to enter black-hole local space.
    #
    #   bh_local_pos = world_pos * BLACK_HOLE_LOCAL_SCALE
    #
    # This is the SINGLE authoritative conversion factor.  Do NOT hard-code
    # 12.0 in shaders or other Python files.
    # ------------------------------------------------------------------
    BLACK_HOLE_LOCAL_SCALE = 12.0

    def __init__(
        self,
        radius=0.05,
        aspect_ratio=1280 / 720,
    ):

        # ==================================================
        # Physical Properties
        # ==================================================

        # Sagittarius A*
        self.mass = 4.154e6          # Solar masses

        # Kerr spin parameter (0 = Schwarzschild)
        self.spin = 0.0

        # ==================================================
        # Visual Properties
        # ==================================================

        self.event_horizon_radius = radius

        self.photon_sphere_radius = radius * 1.5

        self.inner_disk_radius = radius * 3.0

        self.outer_disk_radius = radius * 6.0

        # ==================================================
        # Rendering
        # ==================================================

        self.aspect_ratio = aspect_ratio