package dev.yury.mathmark

import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.time.LocalDate
import java.time.LocalDateTime

/** Те же проверки, что и у настольной версии. */
class StatsTest {

    @get:Rule
    val tmp = TemporaryFolder()

    private val today: LocalDate = LocalDate.of(2026, 7, 31)

    private fun at(daysAgo: Int, hour: Int = 12): LocalDateTime =
        today.minusDays(daysAgo.toLong()).atTime(hour, 0)

    private fun entry(daysAgo: Int, kind: Kind = Kind.TASK, mark: Mark = Mark.DONE) =
        JournalEntry(at(daysAgo), "ф.md", kind, mark)

    @Test
    fun `запись и чтение журнала`() {
        val f = java.io.File(tmp.newFolder(), "journal.log")
        Journal.record(f, "Матан.md", Kind.TASK, Mark.DONE, at(0))
        Journal.record(f, "Линал.md", Kind.TOPIC, Mark.HALF, at(0))

        val got = Journal.parse(f.readText())
        assertEquals(2, got.size)
        assertEquals("Матан.md", got[0].path)
        assertEquals(Kind.TASK, got[0].kind)
        assertEquals(Mark.DONE, got[0].mark)
        assertEquals(Mark.HALF, got[1].mark)
    }

    @Test
    fun `кривые строки пропускаются`() {
        val text = "мусор\n2026-07-31T12:00|ф.md|task|x\nещё мусор|две|части\n"
        assertEquals(1, Journal.parse(text).size)
    }

    @Test
    fun `считается только закрытие`() {
        val s = Journal.summarise(
            listOf(entry(0), entry(0, mark = Mark.HALF), entry(0, mark = Mark.NONE)), today)
        assertEquals(1, s.todayTasks)
    }

    @Test
    fun `задачи и темы считаются отдельно`() {
        val s = Journal.summarise(listOf(entry(0), entry(0, Kind.TOPIC), entry(0, Kind.TOPIC)), today)
        assertEquals(1, s.todayTasks)
        assertEquals(2, s.todayTopics)
    }

    @Test
    fun `окна недели и месяца`() {
        val s = Journal.summarise(listOf(entry(0), entry(3), entry(10), entry(40)), today)
        assertEquals(1, s.todayTasks)
        assertEquals(2, s.weekTasks)
        assertEquals(3, s.monthTasks)
    }

    @Test
    fun `серия дней подряд`() {
        val s = Journal.summarise(listOf(entry(0), entry(1), entry(2), entry(4)), today)
        assertEquals(3, s.streak)
    }

    @Test
    fun `серия обрывается если сегодня пусто`() {
        val s = Journal.summarise(listOf(entry(1), entry(2)), today)
        assertEquals(0, s.streak)
    }

    @Test
    fun `разбивка по дням ровно тридцать`() {
        val s = Journal.summarise(listOf(entry(0), entry(0), entry(5)), today)
        assertEquals(30, s.perDay.size)
        assertEquals(today to 2, s.perDay.last())
        assertEquals(1, s.perDay[24].second)
    }
}
