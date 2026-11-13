# ساعة الصلاة على Raspberry Pi 3 B+

*Prayer clock for Raspberry Pi: turns a Pi and any HDMI TV into a mosque-style prayer clock with the adhan.*

تحوّل الـ Pi وأي تلفزيون HDMI إلى ساعة صلاة مثل ساعات المساجد: ساعة بعقارب، التاريخ الهجري والميلادي،
الفجر والشروق والظهر والمغرب، وعدّ تنازلي للوقت القادم. تشتغل وحدها بعد كل إعادة تشغيل، وفيها نظام الأذان والأدعية
نفسه الموجود في مشروع MITV، بصيغة `schedule.json` نفسها ولوحة تحكم من الجوال.

## ما تحتاجه

- Raspberry Pi 3 B+ وبطاقة microSD (8 جيجا أو أكثر) وشاحن 5V 2.5A
- كيبل HDMI عادي للتلفزيون
- كيبل شبكة (اختياري): وصّله بالراوتر وما تحتاج Wi-Fi، وهو أضمن لضبط الوقت بعد كل إقلاع
- الصوت يطلع من سماعات التلفزيون عبر HDMI. لسماعة خارجية وصّلها بمخرج 3.5 ملم واختره من الإعدادات في اللوحة

## التثبيت

كل الخطوات من الـ Pi نفسه، ولا تحتاج ويندوز. *(English instructions below.)*

**1. جهّز البطاقة**
- في برنامج [Raspberry Pi Imager](https://www.raspberrypi.com/software/) اختر **Raspberry Pi OS Lite (64-bit)**.
- من إعدادات التخصيص اضبط: اسم مستخدم وكلمة مرور، وشبكة الواي فاي (أو استخدم كيبل الشبكة)، وفعّل **SSH**.
- ركّب البطاقة في الجهاز وانتظر 3 دقائق لأول تشغيل.

**2. ادخل على الجهاز** من أي كمبيوتر أو جوال. استبدل `pi` باسم المستخدم الذي اخترته، و`xxx` بعنوان الجهاز:

```bash
ssh pi@192.168.1.xxx
```

**3. نزّل النظام وثبّته.** اختر الفرع المناسب لجهازك:

لجهاز **Pi Zero 2 W**:

```bash
sudo apt-get update && sudo apt-get install -y git
git clone -b main https://github.com/halhamada/prayer-clock.git
sudo bash prayer-clock/deploy/setup.sh && sudo reboot
```

لجهاز **Pi 3 B+**: نفس الأوامر، لكن غيّر `-b main` إلى `-b pi3b-plus`.

بعد إعادة التشغيل تظهر الساعة وحدها بعد كل تشغيل، واللوحة على `http://عنوان-الجهاز:8080`.

**طريقة ثانية من ويندوز:** من داخل مجلد المشروع على الكمبيوتر، يرسل هذا السكربت الملفات ويثبّتها ويعيد التشغيل:

```powershell
.\deploy\install-from-windows.ps1 -Address 192.168.1.xxx -User pi
```

## Installation (English)

Everything runs on the Pi itself; no Windows needed.

**1. Prepare the card**
- In [Raspberry Pi Imager](https://www.raspberrypi.com/software/) choose **Raspberry Pi OS Lite (64-bit)**.
- In the customisation settings set a username and password, your Wi-Fi network (or use an Ethernet cable), and
  turn on **SSH**.
- Put the card in the Pi and wait 3 minutes for the first boot.

**2. Log in to the Pi** from any computer or phone, with your username and the Pi's address:

```bash
ssh pi@192.168.1.xxx
```

**3. Download and install.** Pick the branch for your board:

For a **Pi Zero 2 W**:

```bash
sudo apt-get update && sudo apt-get install -y git
git clone -b main https://github.com/halhamada/prayer-clock.git
sudo bash prayer-clock/deploy/setup.sh && sudo reboot
```

For a **Pi 3 B+**: the same commands with `-b pi3b-plus` instead of `-b main`.

After the reboot the clock comes up on its own at every start, and the dashboard is at `http://<pi-address>:8080`.
The first visit asks you to choose a PIN for it.

**To update later:**

```bash
cd prayer-clock && git pull && sudo bash deploy/setup.sh && sudo reboot
```

Settings, the audio schedule and uploaded files are kept: they live in `/var/lib/prayer-clock`, outside the
downloaded folder.

**From Windows instead:** inside the project folder, this script copies the files, installs them and reboots:

```powershell
.\deploy\install-from-windows.ps1 -Address 192.168.1.xxx -User pi
```

The rest of this guide is in Arabic: the dashboard, the screen faces, moving to another network, the clock time
without internet, and troubleshooting.

## اللوحة

افتح `http://prayerclock.local:8080` من الجوال أو الكمبيوتر. أول مرة تختار رمزاً سرياً.
منها تضبط الأذان ودعاء الأيام والأدعية المجدولة، وترفع الملفات، وتوقف الصوت، وتغيّر مستوى الصوت واتجاه الشاشة
والموقع والتاريخ الهجري، وتعدّل دقائق كل صلاة لتطابق تقويم مسجدك.

زر **🔇 كتم الصوت** فوق اللوحة يوقف الأذان والأدعية المجدولة حتى تلغيه، ويبقى بعد إعادة التشغيل. وقت الكتم تظهر سماعة
عليها علامة × بجانب العد التنازلي.

## شكل الشاشة

من «الإعدادات» في اللوحة، «شكل الشاشة»:
- **ساعة المسجد:** الساعة بعقارب مثل الصورة الأصلية.
- **صور العتبات:** نفس شاشة التلفزيون TCL في مشروع MITV. صورة من العتبات المقدسة تتبع وقت اليوم وتتغير مع كل أذان،
  واليوم والتاريخ، والوقت بخط كبير، والطقس، والصلاة القادمة فوق مواقيت اليوم، والأيام الباقية لرمضان.
  الطقس يحتاج إنترنت، ويختفي إذا ما وصل له الجهاز أبداً. الصور من ويكيميديا كومنز، واسم المصور يظهر أسفل الشاشة.

قسم **صور الخلفية** في اللوحة مثل MITV: «تبديل صور العتبات تلقائيًا مع كل أذان»، أو صورك أنت: صورة لكل الأوقات، أو صورة
لكل وقت (الفجر، النهار، الغروب، الليل)، وصورة الوقت نفسه تتقدم على «كل الأوقات». رفع أي صورة يوقف التبديل التلقائي.
صور الجوال تتعدل وتتصغر وقت الرفع، وتنحفظ في `/var/lib/prayer-clock/backgrounds` فما تتأثر بالتحديث.

## نقل الجهاز لشبكة ثانية

زر **⚙ الشبكة** في اللوحة يعرض الشبكة الحالية وعنوان الجهاز، والشبكات القريبة للاتصال بأي منها.
إذا نقلت الجهاز لمكان ما يعرف شبكته، ينتظر دقيقة ونص ثم يشغّل شبكة إعداد باسم `PrayerClock`، وتظهر على الشاشة
كلمة مرورها والخطوات: اتصل بها من الجوال، وافتح `10.42.0.1:8080`، واختر شبكة المكان. بعد الاتصال يظهر العنوان الجديد
أسفل الشاشة 10 دقائق. مع كيبل الشبكة يتصل وحده بدون أي إعداد. الساعة والأذان يعملان طوال الوقت.

## الاتجاه

الافتراضي طولي، والتلفزيون معلق بالطول مثل الصورة الأصلية. لو كانت الشاشة مقلوبة اختر «طولي مقلوب» من الإعدادات،
ولتلفزيون بالعرض اختر «عرضي» وتتغير الواجهة إلى عمودين.

## الوقت

الـ Pi ما فيه بطارية ساعة. بعد الإقلاع يبدأ من آخر وقت محفوظ، ويتصحح لما يوصل للإنترنت. لهذا ما يشغّل الجهاز الأذان حتى
يتأكد من الوقت، أو تمر 3 دقايق من الإقلاع. وبدون إنترنت تظهر رسالة تحت الشاشة، وتقدر تضبط الوقت من اللوحة.
للبيت اللي ينقطع عنه الإنترنت كثيراً، ركّب وحدة ساعة DS3231 ويتعرف عليها البرنامج بعد تفعيلها في `config.txt`.

## استكشاف الأخطاء

```bash
systemctl status prayer-clock
journalctl -u prayer-clock -n 50
aplay -L
```

- **ما فيه صوت:** اختر مخرج الصوت من الإعدادات، وتأكد إن صوت التلفزيون شغّال.
- **بداية الأذان مقطوعة:** بعض التلفزيونات تأخذ ثانية لتفتح صوت HDMI. أضف ثانية صمت في بداية الملف.
- **إرجاع ملفات الإقلاع:** نسخها الأصلية بجانبها في `/boot/firmware/` باسم `*.before-prayer-clock`.

## التحديث

على الجهاز:

```bash
cd prayer-clock && git pull && sudo bash deploy/setup.sh && sudo reboot
```

أو شغّل سكربت ويندوز مرة ثانية. الإعدادات والجدول والملفات المرفوعة تبقى كما هي، لأنها محفوظة في
`/var/lib/prayer-clock` خارج المجلد الذي نزّلته.

## التطوير

على أي جهاز فيه بايثون و pygame:

```bash
python -m unittest discover tests
python app/main.py --preview frame.png --at 2026-01-30T12:52:05 --size 720x1280
```

| المسار | وش فيه |
|---|---|
| `app/main.py` | الحلقة الرئيسية وفحص موثوقية الوقت |
| `app/clockface.py` | رسم شاشة ساعة المسجد |
| `app/photoface.py`، `app/weather.py` | شاشة صور العتبات والطقس |
| `app/backgrounds.py`، `assets/photos/` | صور الخلفية: التبديل مع الأذان والصور الخاصة |
| `app/output.py` | الكتابة المباشرة على `/dev/fb0`، بدون سطح مكتب |
| `app/prayertimes.py`، `app/hijri.py` | المواقيت الجعفرية والتقويم، بدون إنترنت |
| `app/schedule.py`، `app/player.py` | جدول الصوتيات والتشغيل عبر mpg123 |
| `app/server.py`، `app/dashboard.html` | اللوحة |
| `app/network.py` | الواي فاي وشبكة الإعداد عبر NetworkManager |
| `app/arabic.py` | وصل الحروف العربية للرسم |
| `audio/` | الأذان والأدعية من مشروع MITV، وتُنسخ للجهاز أول مرة |
| `deploy/` | التثبيت وخدمة systemd |

خطا IBM Plex Sans Arabic و Playfair Display برخصة SIL OFL. صور العتبات برخص CC BY و CC BY-SA، وأسماء مصوريها في
`app/backgrounds.py` وعلى الشاشة.
