#version 330

in float starBrightness;
in float starTemperature;

out vec4 fragColor;

void main()
{
    vec3 starColor;

    // Hot blue stars
    if (starTemperature > 7500.0)
    {
        starColor = vec3(
            0.65,
            0.80,
            1.0
        );
    }

    // White stars
    else if (starTemperature > 6000.0)
    {
        starColor = vec3(
            0.9,
            0.95,
            1.0
        );
    }

    // Yellow stars
    else if (starTemperature > 4500.0)
    {
        starColor = vec3(
            1.0,
            0.9,
            0.65
        );
    }

    // Orange/red stars
    else
    {
        starColor = vec3(
            1.0,
            0.55,
            0.3
        );
    }

    float alpha = 0.35 + starBrightness * 0.65;

    fragColor = vec4(
        starColor,
        alpha
    );
}