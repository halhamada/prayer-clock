// Prayer times by the Jafari method (Leva Institute, Qum): Fajr at 16°, Maghrib at 4° below the horizon,
// Isha at 14°, Asr at a shadow ratio of one. A port of app/prayertimes.py and app/schedule.py, so the widget
// shows the same times as the Pi clock.

import Foundation

enum PrayerTimes {
    static let fajrAngle = 16.0, maghribAngle = 4.0, ishaAngle = 14.0, riseSetAngle = 0.833

    /// Hours after local midnight: fajr, sunrise, dhuhr, asr, sunset, maghrib, isha.
    static func compute(year: Int, month: Int, day: Int, lat: Double, lng: Double, zone: Double) -> [Double] {
        let jDate = julian(year, month, day) - lng / (15 * 24.0)
        var t: [Double] = [5, 6, 12, 13, 18, 18, 18]
        for _ in 0..<2 {
            let p = t.map { $0 / 24 }
            t = [
                sunAngleTime(jDate, lat, fajrAngle, p[0], true),
                sunAngleTime(jDate, lat, riseSetAngle, p[1], true),
                midDay(jDate, p[2]),
                asrTime(jDate, lat, 1, p[3]),
                sunAngleTime(jDate, lat, riseSetAngle, p[4], false),
                sunAngleTime(jDate, lat, maghribAngle, p[5], false),
                sunAngleTime(jDate, lat, ishaAngle, p[6], false),
            ]
        }
        return t.map { $0 + zone - lng / 15 }
    }

    private static func julian(_ y: Int, _ m: Int, _ d: Int) -> Double {
        var year = Double(y), month = Double(m)
        if month <= 2 { year -= 1; month += 12 }
        let a = floor(year / 100), b = 2 - a + floor(a / 4)
        return floor(365.25 * (year + 4716)) + floor(30.6001 * (month + 1)) + Double(d) + b - 1524.5
    }

    private static func sunPosition(_ jd: Double) -> (decl: Double, eqt: Double) {
        let d = jd - 2451545.0
        let g = fix(357.529 + 0.98560028 * d, 360)
        let q = fix(280.459 + 0.98564736 * d, 360)
        let l = fix(q + 1.915 * dsin(g) + 0.020 * dsin(2 * g), 360)
        let e = 23.439 - 0.00000036 * d
        let ra = atan2(dcos(e) * dsin(l), dcos(l)) * 180 / .pi / 15
        return (asin(dsin(e) * dsin(l)) * 180 / .pi, q / 15 - fix(ra, 24))
    }

    private static func midDay(_ j: Double, _ time: Double) -> Double { fix(12 - sunPosition(j + time).eqt, 24) }

    private static func sunAngleTime(_ j: Double, _ lat: Double, _ angle: Double, _ time: Double, _ beforeNoon: Bool) -> Double {
        let decl = sunPosition(j + time).decl
        let noon = midDay(j, time)
        let c = (-dsin(angle) - dsin(decl) * dsin(lat)) / (dcos(decl) * dcos(lat))
        let t = acos(max(-1, min(1, c))) * 180 / .pi / 15
        return noon + (beforeNoon ? -t : t)
    }

    private static func asrTime(_ j: Double, _ lat: Double, _ factor: Double, _ time: Double) -> Double {
        let decl = sunPosition(j + time).decl
        let angle = -atan(1 / (factor + tan(abs(lat - decl) * .pi / 180))) * 180 / .pi
        return sunAngleTime(j, lat, angle, time, false)
    }

    private static func dsin(_ d: Double) -> Double { sin(d * .pi / 180) }
    private static func dcos(_ d: Double) -> Double { cos(d * .pi / 180) }
    private static func fix(_ a: Double, _ m: Double) -> Double { a - m * floor(a / m) }
}

struct Location {
    var latitude = 25.3833     // الأحساء, the Pi clock's default
    var longitude = 49.5858
    var hijriOffset = 0
}

enum Prayer: String, CaseIterable {
    case fajr, sunrise, dhuhr, maghrib

    var name: String {
        switch self { case .fajr: "فجر"; case .sunrise: "شروق"; case .dhuhr: "ظهر"; case .maghrib: "مغرب" }
    }
    var remaining: String { "المتبقي لل" + name }
    var index: Int {
        switch self { case .fajr: 0; case .sunrise: 1; case .dhuhr: 2; case .maghrib: 5 }
    }
}

struct DayTimes {
    let times: [Prayer: Date]

    init(day: Date, location: Location, calendar: Calendar = .current) {
        let start = calendar.startOfDay(for: day)
        let c = calendar.dateComponents([.year, .month, .day], from: start)
        let noon = calendar.date(byAdding: .hour, value: 12, to: start)!
        let zone = Double(calendar.timeZone.secondsFromGMT(for: noon)) / 3600
        let h = PrayerTimes.compute(year: c.year!, month: c.month!, day: c.day!,
                                    lat: location.latitude, lng: location.longitude, zone: zone)
        var out: [Prayer: Date] = [:]
        for p in Prayer.allCases {
            let minute = Int(floor(h[p.index] * 60 + 0.5))
            out[p] = calendar.date(byAdding: .minute, value: minute, to: start)!
        }
        times = out
    }

    /// The next prayer on the tiles after `now`, tomorrow's Fajr once they have all passed.
    static func next(after now: Date, location: Location, calendar: Calendar = .current) -> (Prayer, Date) {
        let today = DayTimes(day: now, location: location)
        for p in [Prayer.fajr, .sunrise, .dhuhr, .maghrib] where today.times[p]! > now {
            return (p, today.times[p]!)
        }
        let tomorrow = calendar.date(byAdding: .day, value: 1, to: now)!
        return (.fajr, DayTimes(day: tomorrow, location: location).times[.fajr]!)
    }
}

enum DateLines {
    static let arDays = ["الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"]
    static let months = ["محرم", "صفر", "ربيع الأول", "ربيع الآخر", "جمادى الأولى", "جمادى الآخرة",
                         "رجب", "شعبان", "رمضان", "شوال", "ذو القعدة", "ذو الحجة"]

    static func hijri(_ date: Date, offset: Int) -> String {
        let weekday = Calendar.current.component(.weekday, from: date) - 1
        var cal = Calendar(identifier: .islamicUmmAlQura)
        cal.timeZone = .current
        let shifted = cal.date(byAdding: .day, value: offset, to: date)!
        let c = cal.dateComponents([.year, .month, .day], from: shifted)
        return "\(arDays[weekday])، \(c.day!) \(months[c.month! - 1]) \(c.year!)"
    }

    static func gregorian(_ date: Date) -> String {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.dateFormat = "EEE, MMM d, yyyy"
        return f.string(from: date)
    }

    static func h12(_ date: Date) -> String {
        let c = Calendar.current.dateComponents([.hour, .minute], from: date)
        return String(format: "%d:%02d", (c.hour! % 12 == 0) ? 12 : c.hour! % 12, c.minute!)
    }
}
