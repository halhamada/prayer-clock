import SwiftUI

/// The widget needs a containing app. It shows the large face live and how to add the widget.
@main
struct PrayerClockApp: App {
    var body: some Scene {
        WindowGroup("ساعة الصلاة") {
            VStack(spacing: 16) {
                TimelineView(.periodic(from: .now, by: 1)) { ctx in
                    LargeFace(state: ClockState(now: ctx.date, location: Location()))
                        .environment(\.layoutDirection, .leftToRight)
                        .frame(width: 364, height: 382)
                        .background(Backdrop())
                        .clipShape(RoundedRectangle(cornerRadius: 20))
                }
                Text("لإضافة الويدجت: اضغط بالزر الأيمن على سطح المكتب ← «تعديل عناصر واجهة المستخدم» ← ابحث عن «ساعة الصلاة».")
                    .font(plex(13, bold: false))
                    .multilineTextAlignment(.center)
                    .fixedSize(horizontal: false, vertical: true)
                    .frame(width: 364)
            }
            .padding(24)
        }
        .windowResizability(.contentSize)
    }
}
