"""Hijri dates from the Umm al-Qura table in hijri_table.py, the calendar the MITV launcher uses. The real month
start can differ by a day with the moon sighting, so settings carry a day offset."""

from datetime import timedelta

from hijri_table import FIRST_YEAR, MONTH_LENGTHS, START_ORDINAL

MONTHS = ("محرم", "صفر", "ربيع الأول", "ربيع الآخر", "جمادى الأولى", "جمادى الآخرة",
          "رجب", "شعبان", "رمضان", "شوال", "ذو القعدة", "ذو الحجة")


def of(date, offset=0):
    """(year, month 1-12, day) of date shifted by offset days, or None outside the table."""
    days = (date + timedelta(days=offset)).toordinal() - START_ORDINAL
    if days < 0:
        return None
    for i, row in enumerate(MONTH_LENGTHS):
        for m in range(12):
            length = int(row[m * 2:m * 2 + 2])
            if days < length:
                return FIRST_YEAR + i, m + 1, days + 1
            days -= length
    return None
