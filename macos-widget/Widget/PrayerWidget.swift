import AppIntents
import SwiftUI
import WidgetKit

struct LocationIntent: WidgetConfigurationIntent {
    static var title: LocalizedStringResource = "الموقع"
    static var description = IntentDescription("موقع حساب أوقات الصلاة وتعديل التاريخ الهجري.")

    @Parameter(title: "خط العرض", default: 25.3833)
    var latitude: Double

    @Parameter(title: "خط الطول", default: 49.5858)
    var longitude: Double

    @Parameter(title: "تعديل الهجري (أيام)", default: 0, inclusiveRange: (-2, 2))
    var hijriOffset: Int

    var location: Location { Location(latitude: latitude, longitude: longitude, hijriOffset: hijriOffset) }
}

struct Entry: TimelineEntry {
    let date: Date
    let location: Location
}

struct Provider: AppIntentTimelineProvider {
    func placeholder(in context: Context) -> Entry { Entry(date: .now, location: Location()) }

    func snapshot(for config: LocationIntent, in context: Context) async -> Entry {
        Entry(date: .now, location: config.location)
    }

    /// One entry a minute for the hands, for the next hour; then WidgetKit asks again.
    func timeline(for config: LocationIntent, in context: Context) async -> Timeline<Entry> {
        let cal = Calendar.gregorianLocal
        let first = cal.dateInterval(of: .minute, for: .now)?.start ?? .now
        let entries = (0..<60).map { Entry(date: cal.date(byAdding: .minute, value: $0, to: first)!, location: config.location) }
        return Timeline(entries: entries, policy: .atEnd)
    }
}

struct PrayerWidgetView: View {
    @Environment(\.widgetFamily) var family
    var entry: Entry

    var body: some View {
        let state = ClockState(now: entry.date, location: entry.location)
        Group {
            switch family {
            case .systemSmall: SmallFace(state: state)
            case .systemMedium: MediumFace(state: state)
            default: LargeFace(state: state)
            }
        }
        .environment(\.layoutDirection, .leftToRight)
        .containerBackground(for: .widget) { Backdrop() }
    }
}

@main
struct PrayerWidget: Widget {
    var body: some WidgetConfiguration {
        AppIntentConfiguration(kind: "PrayerClock", intent: LocationIntent.self, provider: Provider()) { entry in
            PrayerWidgetView(entry: entry)
        }
        .configurationDisplayName("ساعة الصلاة")
        .description("أوقات الصلاة بتنسيق ساعة المسجد.")
        .supportedFamilies([.systemSmall, .systemMedium, .systemLarge])
        .contentMarginsDisabled()
    }
}
