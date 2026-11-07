from solarsystem import config
from solarsystem.playback import Playback


def test_default_speed_is_one_day():
    assert Playback().minutes_per_frame == 1440


def test_speed_is_clamped():
    pb = Playback()
    for _ in range(50):
        pb.slower()
    assert pb.minutes_per_frame == config.SPEEDS_MINUTES[0] == 1
    for _ in range(50):
        pb.faster()
    assert pb.minutes_per_frame == config.SPEEDS_MINUTES[-1]
    assert pb.seconds_per_frame == 64 * 86400


def test_toggle_pause():
    pb = Playback()
    pb.toggle_pause()
    assert pb.paused
    pb.toggle_pause()
    assert not pb.paused
