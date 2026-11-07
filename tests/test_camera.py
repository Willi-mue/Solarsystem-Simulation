import math

from solarsystem import config
from solarsystem.camera import Camera
from solarsystem.physics import Body

from .conftest import by_name

W, H = 1920, 1080


def test_origin_is_centered():
    assert Camera().world_to_screen(0, 0, 800, 600) == (400, 300)


def test_north_is_up():
    sx, sy = Camera().world_to_screen(0, config.AU, W, H)
    assert sx == W / 2 and sy < H / 2


def test_world_screen_roundtrip_with_zoom_and_pan():
    cam = Camera(zoom=2.5)
    cam.pan(130, -40)
    x, y = 1.3 * config.AU, -0.7 * config.AU
    sx, sy = cam.world_to_screen(x, y, W, H)
    rx, ry = cam.screen_to_world(sx, sy, W, H)
    assert math.isclose(rx, x) and math.isclose(ry, y)


def test_zoom_is_clamped():
    cam = Camera()
    for _ in range(300):
        cam.zoom_in()
    assert cam.zoom == config.ZOOM_MAX
    for _ in range(300):
        cam.zoom_out()
    assert cam.zoom == config.ZOOM_MIN


def test_zoom_at_keeps_point_under_cursor():
    cam = Camera()
    sx, sy = 1500, 200
    before = cam.screen_to_world(sx, sy, W, H)
    cam.zoom_at(True, sx, sy, W, H)
    cam.zoom_at(True, sx, sy, W, H)
    after = cam.screen_to_world(sx, sy, W, H)
    assert math.isclose(before[0], after[0]) and math.isclose(before[1], after[1])


def test_pan_moves_view_with_mouse_and_stops_following():
    cam = Camera()
    cam.follow = Body("x", 0, 0, 1, (0, 0, 0), 1)
    cam.pan(100, 50)
    assert cam.follow is None
    sx, sy = cam.world_to_screen(0, 0, W, H)
    assert math.isclose(sx, W / 2 + 100) and math.isclose(sy, H / 2 + 50)


def test_follow_centers_body(bodies):
    earth = by_name(bodies, "Earth")
    cam = Camera(follow=earth)
    cam.update_follow()
    assert cam.world_to_screen(earth.x, earth.y, W, H) == (W / 2, H / 2)


def test_reset():
    cam = Camera(zoom=3.0, center_x=5.0, center_y=-2.0)
    cam.follow = Body("x", 0, 0, 1, (0, 0, 0), 1)
    cam.reset()
    assert (cam.zoom, cam.center_x, cam.center_y, cam.follow) == (config.ZOOM_DEFAULT, 0, 0, None)


def test_pick_finds_body_and_misses_empty_space(bodies):
    cam = Camera()
    earth = by_name(bodies, "Earth")
    sx, sy, _ = cam.layout(bodies, W, H)[earth]
    assert cam.pick(bodies, sx + 3, sy - 3, W, H) is earth
    assert cam.pick(bodies, 5, 5, W, H) is None


def test_stylized_moons_sit_outside_their_planet(bodies):
    cam = Camera()
    layout = cam.layout(bodies, W, H)
    for body, (x, y, r) in layout.items():
        if body.parent is not None:
            px, py, pr = layout[body.parent]
            assert math.hypot(x - px, y - py) > pr + r


def test_true_scale_sizes_and_hidden_moons(bodies):
    cam = Camera(realistic=True, zoom=20_000)
    jupiter, earth = by_name(bodies, "Jupiter"), by_name(bodies, "Earth")
    ratio = cam.body_radius_px(jupiter) / cam.body_radius_px(earth)
    assert 10.5 < ratio < 11.5
    # Bei Zoom 1 verschwinden die Monde optisch in ihren Planeten -> ausgeblendet
    assert all(b.parent is None for b in Camera(realistic=True).layout(bodies, W, H))
