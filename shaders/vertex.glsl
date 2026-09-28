#version 330

in vec2 in_position;

out vec2 frag_pos;

void main()
{
    frag_pos = in_position;
    gl_Position = vec4(in_position, 0.0, 1.0);
}
