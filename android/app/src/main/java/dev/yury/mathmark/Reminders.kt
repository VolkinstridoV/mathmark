package dev.yury.mathmark

import java.io.File
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.LocalTime

/**
 * Напоминания, навешенные на файл.
 *
 * Хранятся отдельным текстовым файлом рядом с настройками — внутрь `.md`
 * не пишется ничего:
 *
 *     Линал/собственные.md|daily|19:00|повторить линал
 *     Матан.md|weekly|1|09:30|разобрать Тейлора
 *     Шпора.md|once|2026-08-05T19:00|перед экзаменом
 *
 * Раз файл лежит не в папке с математикой, синхронизация его не переносит:
 * на каждом устройстве свои напоминания.
 *
 * Точный повтор `reminders.py` настольной версии.
 */

enum class Repeat { DAILY, WEEKLY, ONCE }

data class Reminder(
    val path: String,
    val repeat: Repeat,
    val at: LocalTime,
    val text: String,
    val weekday: Int = 0,          // 1 — понедельник … 7 — воскресенье
    val on: LocalDate? = null,     // для однократного
) {
    fun line(): String = when (repeat) {
        Repeat.DAILY -> "$path|daily|${hhmm()}|$text"
        Repeat.WEEKLY -> "$path|weekly|$weekday|${hhmm()}|$text"
        Repeat.ONCE -> "$path|once|${LocalDateTime.of(on ?: LocalDate.now(), at)}|$text"
    }

    private fun hhmm(): String = "%02d:%02d".format(at.hour, at.minute)

    fun dueOn(day: LocalDate): Boolean = when (repeat) {
        Repeat.DAILY -> true
        Repeat.WEEKLY -> day.dayOfWeek.value == weekday
        Repeat.ONCE -> on == day
    }

    /** Ближайшее срабатывание строго после указанного момента. */
    fun nextAfter(moment: LocalDateTime): LocalDateTime? {
        if (repeat == Repeat.ONCE) {
            val when0 = on?.let { LocalDateTime.of(it, at) } ?: return null
            return if (when0.isAfter(moment)) when0 else null
        }
        for (step in 0..7) {
            val d = moment.toLocalDate().plusDays(step.toLong())
            if (!dueOn(d)) continue
            val w = LocalDateTime.of(d, at)
            if (w.isAfter(moment)) return w
        }
        return null
    }
}

object Reminders {

    fun parse(text: String): List<Reminder> {
        val out = ArrayList<Reminder>()
        for (raw in text.split("\n")) {
            val line = raw.trim()
            if (line.isEmpty() || line.startsWith("#")) continue
            val p = line.split("|")
            runCatching {
                when {
                    p.size == 4 && p[1] == "daily" ->
                        out.add(Reminder(p[0], Repeat.DAILY, time(p[2]), p[3]))
                    p.size == 5 && p[1] == "weekly" -> {
                        val wd = p[2].toInt()
                        if (wd in 1..7) out.add(Reminder(p[0], Repeat.WEEKLY, time(p[3]), p[4], weekday = wd))
                    }
                    p.size == 4 && p[1] == "once" -> {
                        val w = LocalDateTime.parse(p[2])
                        out.add(Reminder(p[0], Repeat.ONCE, w.toLocalTime(), p[3], on = w.toLocalDate()))
                    }
                }
            }
        }
        return out
    }

    private fun time(s: String): LocalTime {
        val (h, m) = s.split(":")
        return LocalTime.of(h.toInt(), m.toInt())
    }

    fun dump(items: List<Reminder>): String = items.joinToString("") { it.line() + "\n" }

    fun load(file: File): List<Reminder> =
        runCatching { parse(file.readText(Charsets.UTF_8)) }.getOrDefault(emptyList())

    fun save(file: File, items: List<Reminder>) {
        runCatching {
            file.parentFile?.mkdirs()
            file.writeText(dump(items), Charsets.UTF_8)
        }
    }

    /** Что сработает в этот день — по возрастанию времени. */
    fun forDay(items: List<Reminder>, day: LocalDate): List<Reminder> =
        items.filter { it.dueOn(day) }.sortedBy { it.at }

    /** Понятное человеку описание: «каждый день в 19:00». */
    fun describe(r: Reminder): String {
        val time = "%02d:%02d".format(r.at.hour, r.at.minute)
        return when (r.repeat) {
            Repeat.DAILY -> L.f("rem.everyDay", time)
            Repeat.WEEKLY -> L.f("rem.everyWeek", L["rem.day" + r.weekday], time)
            Repeat.ONCE -> L.f("rem.once", r.on?.toString().orEmpty(), time)
        }
    }
}
