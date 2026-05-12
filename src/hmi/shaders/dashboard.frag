#version 450

layout(location = 0) in vec2 v_uv;
layout(location = 0) out vec4 out_color;

layout(push_constant) uniform HmiPush {
    vec4 resolution_time_health;
    vec4 traffic;
    vec4 stream;
    vec4 rag;
    vec4 accel;
    vec4 pulse;
} pc;

float aa_width() {
    return 1.5 / max(pc.resolution_time_health.x, pc.resolution_time_health.y);
}

float stroke(float distance_to_shape, float width) {
    float a = aa_width();
    return 1.0 - smoothstep(width - a, width + a, abs(distance_to_shape));
}

float fill(float signed_distance) {
    float a = aa_width();
    return 1.0 - smoothstep(-a, a, signed_distance);
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

float ring(vec2 p, float radius, float width) {
    return stroke(length(p) - radius, width);
}

float arc_mask(vec2 p, float value) {
    float angle = atan(p.y, p.x);
    float normalized = clamp((angle + 3.14159265) / 6.2831853, 0.0, 1.0);
    return step(normalized, clamp(value, 0.0, 1.0));
}

float bar(vec2 p, vec2 center, vec2 half_size, float value) {
    vec2 q = p - center;
    float shell = stroke(sd_box(q, half_size), 0.005);
    float fill_width = half_size.x * clamp(value, 0.0, 1.0);
    vec2 fill_center = vec2(-half_size.x + fill_width, 0.0);
    float core = fill(sd_box(q - fill_center, vec2(fill_width, half_size.y * 0.58)));
    return max(shell * 0.55, core);
}

float tick_field(vec2 p, float radius) {
    vec2 n = normalize(p + vec2(0.0001));
    float ticks = 0.0;
    for (int i = 0; i < 32; ++i) {
        float a = float(i) * 0.19634954;
        vec2 d = vec2(cos(a), sin(a));
        float radial = abs(length(p) - radius);
        float angular = abs(dot(n, vec2(-d.y, d.x)));
        float tick_on = step(0.995, dot(n, d));
        ticks = max(ticks, tick_on * (1.0 - smoothstep(0.0, 0.008, radial)) * (1.0 - smoothstep(0.0, 0.06, angular)));
    }
    return ticks;
}

void main() {
    vec2 res = max(pc.resolution_time_health.xy, vec2(1.0));
    vec2 uv = (gl_FragCoord.xy / res) * 2.0 - 1.0;
    uv.x *= res.x / res.y;

    float health = clamp(pc.resolution_time_health.w, 0.0, 1.0);
    float alert = clamp(pc.pulse.y, 0.0, 1.0);
    float t = pc.resolution_time_health.z;

    vec3 bg = mix(vec3(0.015, 0.018, 0.020), vec3(0.045, 0.035, 0.028), alert * 0.55);
    float grid_x = 1.0 - smoothstep(0.0, 0.006, abs(fract((uv.x + 8.0) * 8.0) - 0.5));
    float grid_y = 1.0 - smoothstep(0.0, 0.006, abs(fract((uv.y + 8.0) * 8.0) - 0.5));
    float grid = max(grid_x, grid_y) * 0.06;

    vec3 cyan = vec3(0.15, 0.82, 0.92);
    vec3 green = vec3(0.20, 0.94, 0.55);
    vec3 amber = vec3(0.94, 0.66, 0.18);
    vec3 red = vec3(0.96, 0.18, 0.12);
    vec3 signal = mix(red, green, health);
    signal = mix(signal, amber, step(0.42, alert) * (1.0 - step(0.82, alert)));

    vec2 center = uv;
    float main_ring = ring(center, 0.42, 0.012);
    float health_arc = ring(center, 0.36, 0.024) * arc_mask(center, health);
    float ticks = tick_field(center, 0.49);

    float left_panel = stroke(sd_box(uv - vec2(-1.02, 0.0), vec2(0.32, 0.78)), 0.004);
    float right_panel = stroke(sd_box(uv - vec2(1.02, 0.0), vec2(0.32, 0.78)), 0.004);
    float bottom_panel = stroke(sd_box(uv - vec2(0.0, -0.82), vec2(1.34, 0.13)), 0.004);

    float requests = bar(uv, vec2(-1.02, 0.46), vec2(0.23, 0.032), pc.traffic.x / max(pc.traffic.x + 500.0, 1.0));
    float open_streams = bar(uv, vec2(-1.02, 0.28), vec2(0.23, 0.032), pc.traffic.y / 16.0);
    float routes = bar(uv, vec2(-1.02, 0.10), vec2(0.23, 0.032), pc.traffic.z / max(pc.traffic.z + 100.0, 1.0));
    float errors = bar(uv, vec2(-1.02, -0.08), vec2(0.23, 0.032), pc.traffic.w / 8.0);

    float rag_inject = bar(uv, vec2(1.02, 0.46), vec2(0.23, 0.032), pc.rag.x / max(pc.rag.x + 64.0, 1.0));
    float cache = bar(uv, vec2(1.02, 0.28), vec2(0.23, 0.032), pc.rag.y / max(pc.rag.y + 64.0, 1.0));
    float saved = bar(uv, vec2(1.02, 0.10), vec2(0.23, 0.032), pc.rag.z / max(pc.rag.z + 64.0, 1.0));
    float reasoning = bar(uv, vec2(1.02, -0.08), vec2(0.23, 0.032), pc.rag.w / max(pc.rag.w + 64.0, 1.0));

    float cuda = fill(sd_box(uv - vec2(-0.80, -0.82), vec2(0.07, 0.042))) * step(0.5, pc.accel.x);
    float ov = fill(sd_box(uv - vec2(-0.56, -0.82), vec2(0.07, 0.042))) * step(0.5, pc.accel.y);
    float myriad = fill(sd_box(uv - vec2(-0.32, -0.82), vec2(0.07, 0.042))) * step(0.5, pc.accel.z);
    float myriad_fail = fill(sd_box(uv - vec2(-0.08, -0.82), vec2(0.07, 0.042))) * step(0.5, pc.accel.w);

    float sweep = stroke(sd_segment(uv, vec2(0.0), vec2(cos(t * 1.7), sin(t * 1.7)) * 0.52), 0.004) * 0.65;
    float alert_pulse = (0.5 + 0.5 * sin(t * 8.0)) * alert;
    float fail_open = bar(uv, vec2(0.80, -0.82), vec2(0.22, 0.032), pc.pulse.z / 8.0);
    float control_plane_cache = bar(uv, vec2(0.80, -0.64), vec2(0.22, 0.032), pc.pulse[3]);

    vec3 color = bg + vec3(grid);
    color = mix(color, cyan, max(left_panel, right_panel) * 0.35);
    color = mix(color, cyan, bottom_panel * 0.35);
    color = mix(color, signal, max(main_ring, health_arc));
    color = mix(color, cyan, max(ticks, sweep));
    color = mix(color, green, max(max(requests, open_streams), routes) * 0.75);
    color = mix(color, red, errors * 0.78);
    color = mix(color, cyan, max(max(rag_inject, cache), max(saved, reasoning)) * 0.72);
    color = mix(color, green, max(cuda, ov) * 0.8);
    color = mix(color, amber, myriad * 0.8);
    color = mix(color, red, max(myriad_fail, fail_open) * (0.65 + alert_pulse * 0.35));
    color = mix(color, green, control_plane_cache * 0.6);

    out_color = vec4(color, 1.0);
}
