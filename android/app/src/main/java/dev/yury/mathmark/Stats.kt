package dev.yury.mathmark

import java.io.File
import java.time.LocalDate
import java.time.LocalDateTime

/**
 * Журнал отметок и подсчёт движения по нему.
 *
 * Каждое нажатие на кружок дописывает одну строку в обычный текстовый файл
 * рядом с настройками:
 *
 *     2026-07-31T18:50:12|Матан.md|task|done
 *
 * Именно момент отметки, а не момент синхронизации: отметил утром,
 * синхронизировал через три дня — статистика должна показать утро.
 *
 * Файл только растёт и никогда не переписывается. Строку можно удалить
 * руками, ничего не сломается.
 *
 * Точный повтор `stats.py` настольной версии, вплоть до тех же проверок.
 */

data class JournalEntry(
    val whenAt: LocalDateTime,
    val path: String,
    val kind: Kind,
    val mark: Mark,
)

data class Stats(
    var todayTasks: Int = 0,
    var todayTopics: Int = 0,
    var weekTasks: Int = 0,
    var weekTopics: Int = 0,
    var monthTasks: Int = 0,
    var monthTopics: Int = 0,
    var streak: Int = 0,
    var perDay: List<Pair<LocalDate, Int>> = emptyList(),
)

object Journal {

    /** Дописать строку. Беда с записью не должна мешать работе — молчим. */
    fun record(file: File, path: String, kind: Kind, mark: Mark, at: LocalDateTime = LocalDateTime.now()) {
        val line = "${at.withNano(0)}|$path|${kind.name.lowercase()}|${mark.char}\n"
        runCatching {
            file.parentFile?.mkdirs()
            file.appendText(line, Charsets.UTF_8)
        }
    }

    fun parse(text: String): List<JournalEntry> {
        val out = ArrayList<JournalEntry>()
        for (raw in text.split("\n")) {
            val parts = raw.trim().split("|")
            if (parts.size != 4) continue
            val at = runCatching { LocalDateTime.parse(parts[0]) }.getOrNull() ?: continue
            out.add(
                JournalEntry(
                    whenAt = at,
                    path = parts[1],
                    kind = if (parts[2] == "task") Kind.TASK else Kind.TOPIC,
                    mark = Mark.of(parts[3].firstOrNull() ?: ' '),
                )
            )
        }
        return out
    }

    /**
     * Считаем только закрытия — переход в «готово». Снятие отметки не отнимает:
     * это не отчётность, а счётчик движения вперёд.
     */
    fun summarise(entries: List<JournalEntry>, today: LocalDate = LocalDate.now()): Stats {
        val s = Stats()
        val byDay = HashMap<LocalDate, Int>()

        for (e in entries) {
            if (e.mark != Mark.DONE) continue
            val d = e.whenAt.toLocalDate()
            byDay[d] = (byDay[d] ?: 0) + 1
            val days = java.time.temporal.ChronoUnit.DAYS.between(d, today).toInt()
            if (days == 0) {
                if (e.kind == Kind.TASK) s.todayTasks++ else s.todayTopics++
            }
            if (days in 0..6) {
                if (e.kind == Kind.TASK) s.weekTasks++ else s.weekTopics++
            }
            if (days in 0..29) {
                if (e.kind == Kind.TASK) s.monthTasks++ else s.monthTopics++
            }
        }

        var day = today
        while ((byDay[day] ?: 0) > 0) {
            s.streak++
            day = day.minusDays(1)
        }

        s.perDay = (29 downTo 0).map { i ->
            val d = today.minusDays(i.toLong())
            d to (byDay[d] ?: 0)
        }
        return s
    }
}
