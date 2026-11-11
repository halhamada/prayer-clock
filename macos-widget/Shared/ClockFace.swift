// The mosque clock face from app/clockface.py, in SwiftUI: navy backdrop with soft lights, the dates in green,
// the analog clock on its mint card, four prayer tiles (the next one green) and the countdown in yellow.

import SwiftUI

enum Palette {
    static func rgb(_ r: Double, _ g: Double, _ b: Double) -> Color { Color(red: r / 255, green: g / 255, blue: b / 255) }
    static let navyTop = rgb(10, 20, 72), navyBottom = rgb(3, 8, 40)
    static let bokeh = rgb(60, 110, 200)
    static let greenText = rgb(196, 245, 190)
    static let card = rgb(178, 235, 232), cardEdge = rgb(232, 138, 122)
    static let ink = rgb(20, 20, 22)
    static let hand = rgb(120, 160, 240)
    static let center = rgb(232, 188, 48)
    static let purple = rgb(124, 58, 237)
    static let tileLine = rgb(205, 225, 240)
    static let tileBg = rgb(6, 8, 20), tileNext = rgb(8, 122, 30)
    static let timeBlue = rgb(190, 225, 255)
    static let nameYellow = rgb(250, 225, 60)
    static let labelBlue = rgb(180, 215, 255)
    static let pink = rgb(250, 120, 160)
    static let countBg = rgb(10, 10, 12)
    static let countYellow = rgb(240, 205, 60)
}

func plex(_ size: CGFloat, bold: Bool = true) -> Font {
    .custom(bold ? "IBMPlexSansArabic-Bold" : "IBMPlexSansArabic-Medium", fixedSize: size)
}

struct ClockState {
    var now: Date
    var location: Location

    var next: (Prayer, Date) { DayTimes.next(after: now, location: location) }
    var today: DayTimes { DayTimes(day: now, location: location) }
}

/// Night-blue gradient with out-of-focus lights.
struct Backdrop: View {
    var body: some View {
        GeometryReader { g in
            ZStack {
                LinearGradient(colors: [Palette.navyTop, Palette.navyBottom], startPoint: .top, endPoint: .bottom)
                ForEach(Array(Self.lights.enumerated()), id: \.offset) { _, l in
                    Circle()
                        .fill(RadialGradient(colors: [Palette.bokeh.opacity(l.3), .clear], center: .center,
                                             startRadius: 0, endRadius: g.size.width * l.2))
                        .frame(width: g.size.width * l.2 * 2, height: g.size.width * l.2 * 2)
                        .position(x: g.size.width * l.0, y: g.size.height * l.1)
                }
            }
        }
    }

    static let lights: [(Double, Double, Double, Double)] = [
        (0.16, 0.16, 0.16, 0.45), (0.84, 0.3, 0.2, 0.35), (0.1, 0.58, 0.14, 0.4), (0.9, 0.7, 0.18, 0.4),
        (0.22, 0.86, 0.18, 0.42), (0.76, 0.93, 0.15, 0.35), (0.52, 0.04, 0.13, 0.3),
    ]
}

/// The mint card with the dial and hands. Widgets cannot tick, so there is no second hand: the digital time
/// under the centre shows hours and minutes.
struct AnalogClock: View {
    var now: Date

    var body: some View {
        GeometryReader { g in
            let side = min(g.size.width, g.size.height)
            let s = side / 590
            let r = side * 0.46
            let c = CGPoint(x: g.size.width / 2, y: g.size.height / 2)
            let comps = Calendar.gregorianLocal.dateComponents([.hour, .minute, .second], from: now)
            let minute = Double(comps.minute!) + Double(comps.second!) / 60
            let hour = Double(comps.hour! % 12) + minute / 60
            ZStack {
                RoundedRectangle(cornerRadius: 12 * s).fill(Palette.card)
                RoundedRectangle(cornerRadius: 12 * s).strokeBorder(Palette.cardEdge, lineWidth: max(1.5, 5 * s))
                ForEach(0..<60, id: \.self) { i in
                    let a = Double(i) * 6 * .pi / 180
                    let d = (i % 5 == 0 ? 3.4 : 2.2) * s * 2
                    Circle().fill(Palette.ink).frame(width: d, height: d)
                        .position(x: c.x + r * sin(a), y: c.y - r * cos(a))
                }
                ForEach(1...12, id: \.self) { n in
                    let a = Double(n) * 30 * .pi / 180
                    Text("\(n)").font(plex(66 * s, bold: false)).foregroundStyle(Palette.ink)
                        .position(x: c.x + r * 0.83 * sin(a), y: c.y - r * 0.83 * cos(a))
                }
                Text(String(format: "%d : %02d", comps.hour! % 12 == 0 ? 12 : comps.hour! % 12, comps.minute!))
                    .font(plex(40 * s)).foregroundStyle(Palette.purple)
                    .position(x: c.x, y: c.y + 112 * s)
                Hand(center: c, angle: hour * 30, length: r * 0.55, width: 20 * s).fill(Palette.hand)
                Hand(center: c, angle: minute * 6, length: r * 0.93, width: 7 * s).fill(Palette.hand)
                Circle().fill(Palette.center).frame(width: 66 * s, height: 66 * s).position(c)
            }
        }
        .aspectRatio(580.0 / 590.0, contentMode: .fit)
    }
}

struct Hand: Shape {
    var center: CGPoint, angle: Double, length: CGFloat, width: CGFloat

    func path(in rect: CGRect) -> Path {
        let a = angle * .pi / 180
        let sx = sin(a), cy = cos(a)
        let px = cy * width / 2, py = sx * width / 2
        let tip = CGPoint(x: center.x + sx * length, y: center.y - cy * length)
        var p = Path()
        p.move(to: CGPoint(x: center.x - px, y: center.y - py))
        p.addLine(to: CGPoint(x: tip.x - px * 0.5, y: tip.y - py * 0.5))
        p.addLine(to: CGPoint(x: tip.x + px * 0.5, y: tip.y + py * 0.5))
        p.addLine(to: CGPoint(x: center.x + px, y: center.y + py))
        p.closeSubpath()
        return p
    }
}

struct PrayerTile: View {
    var prayer: Prayer
    var time: Date
    var highlighted: Bool
    var size: CGFloat

    var body: some View {
        HStack {
            Text(DateLines.h12(time)).foregroundStyle(Palette.timeBlue)
            Spacer(minLength: 2)
            Text(prayer.name).foregroundStyle(Palette.nameYellow)
        }
        .font(plex(size))
        .lineLimit(1)
        .minimumScaleFactor(0.6)
        .padding(.horizontal, size * 0.5)
        .frame(maxWidth: .infinity, minHeight: size * 2)
        .background(RoundedRectangle(cornerRadius: size * 0.33).fill(highlighted ? Palette.tileNext : Palette.tileBg))
        .overlay(RoundedRectangle(cornerRadius: size * 0.33).strokeBorder(Palette.tileLine, lineWidth: 1))
    }
}

/// Fajr and Dhuhr on the right, Sunrise and Maghrib on the left, like the wall clock.
struct TileGrid: View {
    var state: ClockState
    var size: CGFloat
    var spacing: CGFloat

    var body: some View {
        let times = state.today.times
        let next = state.next.0
        HStack(spacing: spacing) {
            VStack(spacing: spacing) {
                PrayerTile(prayer: .sunrise, time: times[.sunrise]!, highlighted: next == .sunrise, size: size)
                PrayerTile(prayer: .maghrib, time: times[.maghrib]!, highlighted: next == .maghrib, size: size)
            }
            VStack(spacing: spacing) {
                PrayerTile(prayer: .fajr, time: times[.fajr]!, highlighted: next == .fajr, size: size)
                PrayerTile(prayer: .dhuhr, time: times[.dhuhr]!, highlighted: next == .dhuhr, size: size)
            }
        }
    }
}

struct RemainingLabel: View {
    var prayer: Prayer
    var size: CGFloat

    var body: some View {
        HStack(spacing: size * 0.5) {
            Triangle().fill(Palette.pink).frame(width: size * 0.8, height: size * 0.45)
            Text(prayer.remaining).font(plex(size)).foregroundStyle(Palette.labelBlue)
        }
    }
}

struct Triangle: Shape {
    func path(in r: CGRect) -> Path {
        Path { p in
            p.move(to: CGPoint(x: r.minX, y: r.minY))
            p.addLine(to: CGPoint(x: r.maxX, y: r.minY))
            p.addLine(to: CGPoint(x: r.midX, y: r.maxY))
            p.closeSubpath()
        }
    }
}

/// The black box with the yellow countdown; the system keeps it ticking between timeline entries.
struct Countdown: View {
    var from: Date
    var to: Date
    var size: CGFloat

    var body: some View {
        Text(timerInterval: from...max(from, to), countsDown: true)
            .font(plex(size).monospacedDigit())
            .foregroundStyle(Palette.countYellow)
            .multilineTextAlignment(.center)
            .lineLimit(1)
            .minimumScaleFactor(0.5)
            .padding(.vertical, size * 0.12)
            .frame(maxWidth: .infinity)
            .background(RoundedRectangle(cornerRadius: size * 0.3).fill(Palette.countBg))
            .overlay(RoundedRectangle(cornerRadius: size * 0.3).strokeBorder(Palette.tileLine, lineWidth: 1.5))
    }
}

// MARK: - The three widget sizes

/// Large: the whole wall clock, upright.
struct LargeFace: View {
    var state: ClockState

    var body: some View {
        let (prayer, at) = state.next
        VStack(spacing: 5) {
            Text(DateLines.hijri(state.now, offset: state.location.hijriOffset))
                .font(plex(15)).foregroundStyle(Palette.greenText)
            Text(DateLines.gregorian(state.now)).font(plex(14)).foregroundStyle(Palette.greenText)
            AnalogClock(now: state.now).frame(maxHeight: 170)
            TileGrid(state: state, size: 14, spacing: 6).padding(.horizontal, 18)
            HStack(spacing: 10) {
                RemainingLabel(prayer: prayer, size: 14)
                Countdown(from: state.now, to: at, size: 20).frame(width: 130)
            }
        }
        .padding(.vertical, 14)
        .padding(.horizontal, 12)
    }
}

/// Medium: the clock card on the left and the column beside it, like the landscape TV layout.
struct MediumFace: View {
    var state: ClockState

    var body: some View {
        let (prayer, at) = state.next
        HStack(spacing: 10) {
            AnalogClock(now: state.now)
            VStack(spacing: 5) {
                Text(DateLines.hijri(state.now, offset: state.location.hijriOffset))
                    .font(plex(12)).foregroundStyle(Palette.greenText)
                    .lineLimit(1).minimumScaleFactor(0.7)
                TileGrid(state: state, size: 11.5, spacing: 4)
                RemainingLabel(prayer: prayer, size: 11)
                Countdown(from: state.now, to: at, size: 17).padding(.horizontal, 20)
            }
        }
        .padding(12)
    }
}

/// Small: the next prayer and its countdown over the four times.
struct SmallFace: View {
    var state: ClockState

    var body: some View {
        let (prayer, at) = state.next
        let times = state.today.times
        VStack(spacing: 4) {
            RemainingLabel(prayer: prayer, size: 12)
            Countdown(from: state.now, to: at, size: 18)
            ForEach([Prayer.fajr, .sunrise, .dhuhr, .maghrib], id: \.self) { p in
                PrayerTile(prayer: p, time: times[p]!, highlighted: p == prayer, size: 10.5)
            }
        }
        .padding(12)
    }
}
