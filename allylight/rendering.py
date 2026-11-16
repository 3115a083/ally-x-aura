"""Hardware-independent telemetry validation, routing and RGB rendering."""
from __future__ import annotations
import hashlib
import math

MODES = ('off', 'health', 'endurance', 'sound', 'combined')
CATEGORIES = ('all', 'world', 'zombie', 'vehicle', 'player', 'gunshot', 'alarm')
COLORS = {'world': (255, 180, 20), 'zombie': (255, 70, 0),
          'vehicle': (40, 130, 255), 'player': (150, 80, 255),
          'gunshot': (255, 255, 255), 'alarm': (255, 20, 100)}


def finite(value, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('Expected number')
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError('Number out of range')
    return value


def device_id(name, kind, count, occurrence=0):
    # SDK v3.1 exposes no serial number. An occurrence disambiguates identical devices.
    return hashlib.sha256(f'{name}|{kind}|{count}|{occurrence}'.encode()).hexdigest()[:20]


def validate_frame(frame):
    if not isinstance(frame, dict) or frame.get('protocol') != 1:
        raise ValueError('Unsupported protocol')
    finite(frame.get('seq'), 0, 10**15)
    if not isinstance(frame.get('session'), str) or len(frame['session']) > 80:
        raise ValueError('Invalid session')
    players = frame.get('players')
    routes = frame.get('routes')
    if not isinstance(players, list) or len(players) > 4:
        raise ValueError('Invalid players')
    if not isinstance(routes, list) or len(routes) > 128:
        raise ValueError('Invalid routes')
    seen = set()
    for p in players:
        n = finite(p.get('id'), 0, 3)
        if int(n) != n or n in seen:
            raise ValueError('Duplicate/invalid player')
        seen.add(n)
        finite(p.get('health'), 0, 1)
        finite(p.get('endurance'), 0, 1)
        sounds = p.get('sounds', [])
        if not isinstance(sounds, list) or len(sounds) > 32:
            raise ValueError('Invalid sounds')
        for s in sounds:
            finite(s.get('bearing'), -math.pi, math.pi)
            finite(s.get('strength'), 0, 1)
            finite(s.get('age'), 0, 10)
            if s.get('category') not in COLORS:
                raise ValueError('Invalid sound category')
    targets = set()
    for r in routes:
        if not isinstance(r.get('target'), str) or len(r['target']) > 100 or r['target'] in targets:
            raise ValueError('Invalid/duplicate target')
        targets.add(r['target'])
        if r.get('mode') not in MODES or r.get('category') not in CATEGORIES:
            raise ValueError('Invalid route mode/category')
        n = finite(r.get('player'), 0, 3)
        if int(n) != n:
            raise ValueError('Invalid route player')
        finite(r.get('brightness'), 0, 1)
    return frame


def scale(color, factor):
    return tuple(round(max(0, min(255, c * factor))) for c in color)


def health_color(value):
    # Red -> yellow -> green, no rapid blinking.
    return (round(255 * min(1, 2 * (1-value))), round(255 * min(1, 2*value)), 0)


def render(route, player, size, now=0.0, bearing_offset=0.0, reverse=False):
    """0 rad = screen top. LED order clockwise after user calibration."""
    mode, brightness = route['mode'], route['brightness']
    if mode == 'off' or player is None:
        return [(0, 0, 0)] * size
    if mode in ('health', 'combined'):
        base = health_color(player['health'])
    elif mode == 'endurance':
        base = (round(255*(1-player['endurance'])), round(200*player['endurance']),
                round(255*player['endurance']))
    else:
        base = (0, 0, 0)
    output = [scale(base, brightness) for _ in range(size)]
    if mode not in ('sound', 'combined'):
        return output
    sounds = [s for s in player.get('sounds', []) if s['age'] < 1.2
              and route['category'] in ('all', s['category'])]
    # Strongest surviving event wins, independent of event arrival order.
    if not sounds or size == 0:
        return output
    sound = max(sounds, key=lambda s: s['strength'] * (1-s['age']/1.2))
    amplitude = sound['strength'] * max(0, 1-sound['age']/1.2)
    bearing = sound['bearing'] + bearing_offset
    if reverse:
        bearing = -bearing
    target = (bearing % (2*math.pi)) / (2*math.pi) * size
    for i in range(size):
        distance = min(abs(i-target), size-abs(i-target))
        weight = max(0, 1-distance/max(1.0, size/6)) * amplitude
        sound_color = scale(COLORS[sound['category']], brightness)
        output[i] = tuple(round(a*(1-weight)+b*weight) for a,b in zip(output[i],sound_color))
    return output


def make_endpoints(devices, zones):
    """Each device has one whole-device target OR explicitly calibrated disjoint zones."""
    if not isinstance(zones, dict):
        raise ValueError('zones.json must contain an object')
    endpoints = []
    for device in devices:
        custom = zones.get(device['id'])
        if custom is None:
            custom = [{'id': 'all', 'name': device['name'], 'leds': list(range(device['led_count']))}]
        if not isinstance(custom, list) or not custom:
            raise ValueError('Zones must be a nonempty list')
        used, zone_ids = set(), set()
        for zone in custom:
            zid = zone['id']
            if not isinstance(zid, str) or not zid or not all(c.isalnum() or c in '_-' for c in zid) or zid in zone_ids:
                raise ValueError('Invalid/duplicate zone ID')
            zone_ids.add(zid)
            leds = zone['leds']
            if not isinstance(leds, list) or not leds:
                raise ValueError('Empty LED zone')
            for led in leds:
                if type(led) is not int or not 0 <= led < device['led_count'] or led in used:
                    raise ValueError('Invalid/overlapping LED zone')
                used.add(led)
            offset = finite(zone.get('offset_degrees', 0), -360, 360)
            if type(zone.get('reverse', False)) is not bool:
                raise ValueError('reverse must be boolean')
            endpoints.append({'id': device['id'] + ':' + zid, 'name': str(zone.get('name', zid)),
                              'device': device['id'], 'leds': leds,
                              'offset': math.radians(offset), 'reverse': zone.get('reverse', False)})
    return endpoints
