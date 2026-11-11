# ويدجت ساعة الصلاة للماك

نفس شكل «ساعة المسجد» في المشروع: الخلفية الكحلية، التاريخ الهجري والميلادي، الساعة بعقارب، مربعات الفجر والشروق
والظهر والمغرب (القادمة بالأخضر)، والعد التنازلي بالأصفر. الأوقات بالحساب الجعفري نفسه في `app/prayertimes.py`.

ثلاثة أحجام: صغير (العد التنازلي والأوقات)، متوسط (الساعة بجانب الأوقات)، كبير (الساعة كاملة).
الموقع الافتراضي الأحساء. لتغييره: اضغط بالزر الأيمن على الويدجت ← «تعديل» وأدخل خط العرض والطول وتعديل الهجري.

## البناء والتثبيت

```bash
brew install xcodegen
cd macos-widget
xcodegen generate
xcodebuild -project PrayerClockWidget.xcodeproj -scheme PrayerClock -configuration Release -derivedDataPath build build
cp -R build/Build/Products/Release/PrayerClock.app ~/Applications/
open ~/Applications/PrayerClock.app
```

بعدها: زر أيمن على سطح المكتب ← «تعديل عناصر واجهة المستخدم» ← ابحث عن «ساعة الصلاة».

التوقيع محلي (Sign to Run Locally)، فالتطبيق يشتغل على الجهاز اللي بُني عليه بدون حساب مطوّر.
الويدجت لا تعرض عقرب الثواني لأن macOS يحدّث الويدجت كل دقيقة، لكن العد التنازلي يتحرك كل ثانية.
