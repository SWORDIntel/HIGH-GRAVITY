#version 450

layout(location = 0) out vec4 out_color;

layout(push_constant, std140) uniform HmiPush {
    vec4 resolution_time_health;
    vec4 traffic;
    vec4 stream;
    vec4 rag;
    vec4 accel;
    vec4 pulse;
} pc;

float aa_width(vec2 resolution) {
    return 1.5 / max(resolution.x, resolution.y);
}

float sd_circle(vec2 p, float radius) {
    return length(p) - radius;
}

float sd_box(vec2 p, vec2 b) {
    vec2 d = abs(p) - b;
    return length(max(d, 0.0)) + min(max(d.x, d.y), 0.0);
}

float sd_segment(vec2 p, vec2 a, vec2 b) {
    vec2 pa = p - a;
    vec2 ba = b - a;
    float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
    return length(pa - ba * h);
}

float stroke(float distance_to_shape, float width, float aa) {
    return 1.0 - smoothstep(width - aa, width + aa, abs(distance_to_shape));
}

float fill(float signed_distance, float aa) {
    return 1.0 - smoothstep(-aa, aa, signed_distance);
}

float bar(vec2 p, vec2 center, vec2 half_size, float value, float aa) {
    vec2 q = p - center;
    float shell = stroke(sd_box(q, half_size), 0.004, aa);
    float fill_width = half_size.x * clamp(value, 0.0, 1.0);
    vec2 fill_center = vec2(-half_size.x + fill_width, 0.0);
    float core = fill(sd_box(q - fill_center, vec2(fill_width, half_size.y * 0.58)), aa);
    return max(shell * 0.45, core);
}

void main() {
    vec2 resolution = max(pc.resolution_time_health.xy, vec2(1.0));
    vec2 p = (gl_FragCoord.xy * 2.0 - resolution) / resolution.y;
    float aa = aa_width(resolution);

    float health = clamp(pc.resolution_time_health.w, 0.0, 1.0);
    float alert = clamp(pc.pulse.y, 0.0, 1.0);
    float phase = pc.resolution_time_health.z;

    vec3 bg = mix(vec3(0.012, 0.016, 0.018), vec3(0.050, 0.030, 0.022), alert);
    vec3 cyan = vec3(0.10, 0.78, 0.88);
    vec3 green = vec3(0.18, 0.92, 0.52);
    vec3 amber = vec3(0.95, 0.66, 0.18);
    vec3 red = vec3(0.94, 0.12, 0.10);

    float ring = stroke(sd_circle(p, 0.42), 0.014, aa);
    float core = fill(sd_circle(p, 0.07 + 0.015 * sin(phase * 3.0)), aa);
    float sweep = stroke(sd_segment(p, vec2(0.0), vec2(cos(phase), sin(phase)) * 0.55), 0.004, aa);
    float left = stroke(sd_box(p - vec2(-0.82, 0.0), vec2(0.25, 0.62)), 0.004, aa);
    float right = stroke(sd_box(p - vec2(0.82, 0.0), vec2(0.25, 0.62)), 0.004, aa);

    float requests = bar(p, vec2(-0.82, 0.28), vec2(0.18, 0.03), pc.traffic.x / max(pc.traffic.x + 500.0, 1.0), aa);
    float errors = bar(p, vec2(-0.82, 0.12), vec2(0.18, 0.03), pc.traffic.w / 8.0, aa);
    float cache = bar(p, vec2(0.82, 0.28), vec2(0.18, 0.03), pc.rag.y / max(pc.rag.y + 64.0, 1.0), aa);
    float accel = bar(p, vec2(0.82, 0.12), vec2(0.18, 0.03), (pc.accel.x + pc.accel.y + pc.accel.z) / 3.0, aa);

    vec3 signal = mix(red, green, health);
    signal = mix(signal, amber, step(0.42, alert) * (1.0 - step(0.82, alert)));

    vec3 color = bg;
    color = mix(color, cyan, max(left, right) * 0.35);
    color = mix(color, signal, max(ring, core));
    color = mix(color, cyan, sweep * 0.75);
    color = mix(color, green, max(requests, cache) * 0.72);
    color = mix(color, red, errors * 0.8);
    color = mix(color, amber, accel * 0.65);

    out_color = vec4(color, 1.0);
}
