import math
import random

class Galaxy:

    def __init__(self):

        # ==================================================
        # Galaxy Dimensions
        # ==================================================

        self.radius = 1.0
        self.disk_thickness = 0.15

        # ==================================================
        # Galactic Bulge
        # ==================================================

        self.bulge_radius = 0.20

        # ==================================================
        # Galactic Bar
        # ==================================================

        self.bar_length = 0.35
        self.bar_width = 0.06
        self.bar_thickness = 0.035

        # Rotation of the bar inside the galactic plane
        self.bar_angle = math.radians(20.0)

        # ==================================================
        # Spiral Structure
        # ==================================================

        self.num_arms = 4

        # Pitch-angle related winding.
        # Smaller values = more open arms.
        self.arm_tightness = 2.5

        # Width of the spiral-arm density enhancement
        self.arm_width = 0.35

        # How strongly stars concentrate toward spiral arms
        self.arm_strength = 1.8

        # Relative strength of each arm
        self.arm_strengths = [
            1.00,
            0.90,
            0.80,
            0.70
        ]

        # ==================================================
        # Stellar Populations
        # ==================================================

        # Relative fractions used for the disk.
        # These are rendering/model parameters, not literal
        # observed Milky Way star-count percentages.

        self.young_star_fraction = 0.12
        self.old_star_fraction = 0.88

    # ======================================================
    # Generate Stellar Properties
    # ======================================================

    def generate_stellar_properties(self):

        # Random stellar temperature in Kelvin.
        #
        # This is intentionally weighted toward cooler stars,
        # since low-mass cool stars are much more numerous.

        temperature = random.choices(
            [
                3000.0,
                4000.0,
                5000.0,
                5800.0,
                7000.0,
                10000.0,
                20000.0
            ],
            weights=[
                30,
                25,
                20,
                12,
                7,
                4,
                2
            ]
        )[0]

        # Relative brightness.
        #
        # Most stars are relatively faint.
        # A small number are much brighter.

        brightness = random.lognormvariate(
            0.0,
            0.45
        )

        brightness = min(
            brightness,
            5.0
        )

        return brightness, temperature
    # ======================================================
    # Generate Star Position
    # ======================================================

    def generate_star_position(self):

        radius = random.uniform(
            0.0,
            self.radius
        )

        angle = random.uniform(
            0.0,
            2.0 * math.pi
        )

        x = radius * math.cos(angle)
        z = radius * math.sin(angle)

        y = random.uniform(
            -self.disk_thickness,
            self.disk_thickness
        )

        return x, y, z

    # ======================================================
    # Generate Galactic Bar Position
    # ======================================================

    def generate_bar_position(self):

        # Position along the long axis of the bar
        bar_x = random.uniform(
            -self.bar_length,
            self.bar_length
        )

        # Thickness across the bar
        bar_z = random.gauss(
            0.0,
            self.bar_width
        )

        # Vertical thickness
        bar_y = random.gauss(
            0.0,
            self.bar_thickness
        )

        # Rotate the bar inside the galactic plane
        cos_a = math.cos(self.bar_angle)
        sin_a = math.sin(self.bar_angle)

        x = (
            bar_x * cos_a
            - bar_z * sin_a
        )

        z = (
            bar_x * sin_a
            + bar_z * cos_a
        )

        return x, bar_y, z
    
    # ======================================================
    # Sample Exponential Disk Radius
    # ======================================================

    def sample_disk_radius(self):

        scale_length = 0.28

        while True:

            radius = random.uniform(
                self.bulge_radius,
                self.radius
            )

            # Radial probability for an exponential disk
            probability = (
                radius *
                math.exp(-radius / scale_length)
            )

            # Maximum occurs near radius = scale_length
            max_probability = (
                scale_length *
                math.exp(-1.0)
            )

            if random.random() < probability / max_probability:
                return radius

    # ======================================================
    # Spiral Arm Density
    # ======================================================

    def spiral_arm_density(self, radius, angle):

        if radius <= self.bulge_radius:
            return 0.0

        best_density = 0.0

        for arm in range(self.num_arms):

            # Starting angle of this arm
            arm_angle = (
                2.0 * math.pi * arm / self.num_arms
            )

            # Spiral curve (Logarithmic)
            expected_angle = (
                arm_angle +
                self.arm_tightness * math.log(radius / self.bulge_radius)
            )

            # Difference between the star and the arm
            difference = (
                angle -
                expected_angle
            )

            # Wrap angle into [-pi, pi]
            difference = (
                difference + math.pi
            ) % (2.0 * math.pi) - math.pi
            

            # Gaussian density around the arm
            density = math.exp(
                -0.5 *
                (difference / self.arm_width) ** 2
            )

            # Apply individual arm strength
            density *= self.arm_strengths[arm]

            best_density = max(
                best_density,
                density
            )

        return best_density
                
    # ======================================================
    # Generate Star With Spiral Density
    # ======================================================

    def generate_spiral_star_position(self):

        while True:

            # Choose radius from the normal disk distribution
            radius = self.sample_disk_radius()

            # Any angle is initially possible
            angle = random.uniform(
                0.0,
                2.0 * math.pi
            )

            # Find spiral-arm density at this position
            arm_density = self.spiral_arm_density(
                radius,
                angle
            )

            # Base probability of accepting this star
            probability = (
                1.0 +
                self.arm_strength *
                arm_density
            )

            # Maximum possible probability
            max_probability = (
                1.0 +
                self.arm_strength
            )

            # Accept the position
            if random.random() < (
                probability /
                max_probability
            ):

                x = radius * math.cos(angle)
                z = radius * math.sin(angle)

                # Thin stellar disk
                y = random.gauss(
                    0.0,
                    self.disk_thickness * 0.3
                )

                return x, y, z

    # ======================================================
    # Generate Stellar Properties
    # ======================================================

    def generate_star_properties(self, population):

        # --------------------------------------------------
        # OLD / NORMAL POPULATION
        # --------------------------------------------------

        if population == "old":

            # Older stars tend to be cooler and visually
            # warmer in this simplified rendering model.

            temperature = random.uniform(
                0.45,
                0.75
            )

            brightness = random.uniform(
                0.35,
                1.0
            )

        # --------------------------------------------------
        # YOUNG POPULATION
        # --------------------------------------------------

        else:

            # Young massive stars are hotter and bluer.

            temperature = random.uniform(
                0.75,
                1.0
            )

            brightness = random.uniform(
                0.6,
                1.0
            )

        return brightness, temperature
    
    # ======================================================
    # Generate Star Properties
    # ======================================================

    def generate_star_properties(self):

        # Random temperature in Kelvin
        temperature = random.uniform(
            3000.0,
            10000.0
        )

        # Most stars should be relatively dim.
        # A few stars are much brighter.
        brightness = random.random() ** 2.0

        return brightness, temperature

    # ======================================================
    # Generate Multiple Stars
    # ======================================================

    def generate_stars(self, count):

        stars = []

        for _ in range(count):

            choice = random.random()

            # ==================================================
            # CENTRAL BULGE
            # ==================================================

            if choice < 0.15:

                bulge_scale = (
                    self.bulge_radius / 2.5
                )

                x = random.gauss(
                    0.0,
                    bulge_scale
                )

                y = random.gauss(
                    0.0,
                    bulge_scale
                )

                z = random.gauss(
                    0.0,
                    bulge_scale
                )

                radius = math.sqrt(
                    x*x + y*y + z*z
                )

                if radius > self.bulge_radius:

                    scale = (
                        self.bulge_radius /
                        radius
                    )

                    x *= scale
                    y *= scale
                    z *= scale

            # ==================================================
            # DISK + SPIRAL DENSITY
            # ==================================================

            else:

                x, y, z = (
                    self.generate_spiral_star_position()
                )

            # ==================================================
            # STELLAR PROPERTIES
            # ==================================================

            brightness, temperature = (
                self.generate_stellar_properties()
            )

            stars.append(
                (
                    x,
                    y,
                    z,
                    brightness,
                    temperature
                )
            )

        return stars