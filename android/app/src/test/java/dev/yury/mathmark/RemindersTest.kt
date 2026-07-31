package dev.yury.mathmark

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.File
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.LocalTime

/** Те же проверки, что и у настольной версии. */
class RemindersTest {

    @get:Rule
    val tmp = TemporaryFolder()

    @Test
    fun `ежедневное записывается и читается`() {
        val r = Reminder("Линал.md", Repeat.DAILY, LocalTime.of(19, 0), "повторить линал")
        assertEquals("Линал.md|daily|19:00|повторить линал", r.line())
        assertEquals(listOf(r), Reminders.parse(r.line()))
    }

    @Test
    fun `еженедельное записывается и читается`() {
        val r = Reminder("Матан.md", Repeat.WEEKLY, LocalTime.of(9, 30), "Тейлор", weekday = 1)
        assertEquals("Матан.md|weekly|1|09:30|Тейлор", r.line())
        assertEquals(listOf(r), Reminders.parse(r.line()))
    }

    @Test
    fun `однократное записывается и читается`() {
        val r = Reminder("Шпора.md", Repeat.ONCE, LocalTime.of(19, 0), "перед экзаменом",
                         on = LocalDate.of(2026, 8, 5))
        assertEquals("Шпора.md|once|2026-08-05T19:00|перед экзаменом", r.line())
        assertEquals(listOf(r), Reminders.parse(r.line()))
    }

    @Test
    fun `кривые строки пропускаются`() {
        val text = "мусор\nЛинал.md|daily|19:00|ок\nМатан.md|weekly|9|10:00|плохой день\n"
        val got = Reminders.parse(text)
        assertEquals(1, got.size)
        assertEquals("ок", got[0].text)
    }

    @Test
    fun `текст с пробелами и запятыми переживает круг`() {
        val r = Reminder("ф.md", Repeat.DAILY, LocalTime.of(8, 5), "повторить: ряды, пределы")
        assertEquals(listOf(r), Reminders.parse(Reminders.dump(listOf(r))))
    }

    @Test
    fun `в какой день сработает`() {
        val daily = Reminder("ф.md", Repeat.DAILY, LocalTime.of(19, 0), "т")
        val weekly = Reminder("ф.md", Repeat.WEEKLY, LocalTime.of(19, 0), "т", weekday = 1)
        val once = Reminder("ф.md", Repeat.ONCE, LocalTime.of(19, 0), "т", on = LocalDate.of(2026, 8, 5))

        val monday = LocalDate.of(2026, 8, 3)
        val tuesday = LocalDate.of(2026, 8, 4)
        assertTrue(daily.dueOn(monday) && daily.dueOn(tuesday))
        assertTrue(weekly.dueOn(monday))
        assertFalse(weekly.dueOn(tuesday))
        assertTrue(once.dueOn(LocalDate.of(2026, 8, 5)))
        assertFalse(once.dueOn(monday))
    }

    @Test
    fun `ближайшее срабатывание ежедневного`() {
        val r = Reminder("ф.md", Repeat.DAILY, LocalTime.of(19, 0), "т")
        assertEquals(LocalDateTime.of(2026, 8, 3, 19, 0), r.nextAfter(LocalDateTime.of(2026, 8, 3, 10, 0)))
        assertEquals(LocalDateTime.of(2026, 8, 4, 19, 0), r.nextAfter(LocalDateTime.of(2026, 8, 3, 20, 0)))
    }

    @Test
    fun `ближайшее срабатывание еженедельного`() {
        val r = Reminder("ф.md", Repeat.WEEKLY, LocalTime.of(19, 0), "т", weekday = 1)
        assertEquals(LocalDateTime.of(2026, 8, 10, 19, 0), r.nextAfter(LocalDateTime.of(2026, 8, 4, 10, 0)))
    }

    @Test
    fun `однократное в прошлом больше не сработает`() {
        val r = Reminder("ф.md", Repeat.ONCE, LocalTime.of(19, 0), "т", on = LocalDate.of(2026, 8, 1))
        assertNull(r.nextAfter(LocalDateTime.of(2026, 8, 2, 0, 0)))
    }

    @Test
    fun `список на день по времени`() {
        val items = listOf(
            Reminder("а.md", Repeat.DAILY, LocalTime.of(21, 0), "вечер"),
            Reminder("б.md", Repeat.DAILY, LocalTime.of(8, 0), "утро"),
            Reminder("в.md", Repeat.WEEKLY, LocalTime.of(12, 0), "среда", weekday = 3),
        )
        val got = Reminders.forDay(items, LocalDate.of(2026, 8, 3))
        assertEquals(listOf("утро", "вечер"), got.map { it.text })
    }

    @Test
    fun `запись в файл и чтение`() {
        val f = File(tmp.newFolder(), "reminders.conf")
        val items = listOf(Reminder("ф.md", Repeat.DAILY, LocalTime.of(7, 45), "зарядка мозгу"))
        Reminders.save(f, items)
        assertEquals(items, Reminders.load(f))
    }
}
