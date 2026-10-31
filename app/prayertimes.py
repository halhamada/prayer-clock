"""Prayer times by the Jafari method (Leva Institute, Qum): Fajr at 16 degrees, Maghrib when the sun is
4 degrees below the horizon, Isha at 14 degrees, Asr at a shadow ratio of one. The solar maths is
PrayTimes.org's, computed on the device with no network. Times are hours after local midnight.

A port of PrayerTimes.java from the MITV launcher, so both devices show the same times."""

import math

FAJR, SUNRISE, DHUHR, ASR, SUNSET, MAGHRIB, ISHA = range(7)

FAJR_ANGLE, MAGHRIB_ANGLE, ISHA_ANGLE, RISE_SET_ANGLE = 16, 4, 14, 0.833


def compute(date, lat, lng, zone_hours):
    """The seven times for date, indexed by the constants above; zone_hours is the UTC offset."""
    j_date = _julian(date.year, date.month, date.day) - lng / (15 * 24.0)
    t = [5, 6, 12, 13, 18, 18, 18]
    for _ in range(2):   # the second pass refines with the first pass's times
        p = [x / 24 for x in t]
        t = [
            _sun_angle_time(j_date, lat, FAJR_ANGLE, p[FAJR], True),
            _sun_angle_time(j_date, lat, RISE_SET_ANGLE, p[SUNRISE], True),
            _mid_day(j_date, p[DHUHR]),
            _asr_time(j_date, lat, 1, p[ASR]),
            _sun_angle_time(j_date, lat, RISE_SET_ANGLE, p[SUNSET], False),
            _sun_angle_time(j_date, lat, MAGHRIB_ANGLE, p[MAGHRIB], False),
            _sun_angle_time(j_date, lat, ISHA_ANGLE, p[ISHA], False),
        ]
    return [x + zone_hours - lng / 15 for x in t]


def _julian(year, month, day):
    if month <= 2:
        year -= 1
        month += 12
    a = math.floor(year / 100.0)
    b = 2 - a + math.floor(a / 4)
    return math.floor(365.25 * (year + 4716)) + math.floor(30.6001 * (month + 1)) + day + b - 1524.5


def _sun_position(jd):
    """(declination in degrees, equation of time in hours)."""
    d = jd - 2451545.0
    g = _fix(357.529 + 0.98560028 * d, 360)
    q = _fix(280.459 + 0.98564736 * d, 360)
    l = _fix(q + 1.915 * _dsin(g) + 0.020 * _dsin(2 * g), 360)
    e = 23.439 - 0.00000036 * d
    ra = math.degrees(math.atan2(_dcos(e) * _dsin(l), _dcos(l))) / 15
    return math.degrees(math.asin(_dsin(e) * _dsin(l))), q / 15 - _fix(ra, 24)


def _mid_day(j_date, time):
    return _fix(12 - _sun_position(j_date + time)[1], 24)


def _sun_angle_time(j_date, lat, angle, time, before_noon):
    decl = _sun_position(j_date + time)[0]
    noon = _mid_day(j_date, time)
    cos = (-_dsin(angle) - _dsin(decl) * _dsin(lat)) / (_dcos(decl) * _dcos(lat))
    t = math.degrees(math.acos(max(-1, min(1, cos)))) / 15
    return noon + (-t if before_noon else t)


def _asr_time(j_date, lat, factor, time):
    decl = _sun_position(j_date + time)[0]
    angle = -math.degrees(math.atan(1 / (factor + math.tan(math.radians(abs(lat - decl))))))
    return _sun_angle_time(j_date, lat, angle, time, False)


def _dsin(d):
    return math.sin(math.radians(d))


def _dcos(d):
    return math.cos(math.radians(d))


def _fix(a, mod):
    return a - mod * math.floor(a / mod)
