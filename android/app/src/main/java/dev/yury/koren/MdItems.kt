package dev.yury.koren

/**
 * Разбор отмечаемых строк в тексте markdown и их правка.
 *
 * Здесь нет ни одной ссылки на Android — всё покрывается юнит-тестами на JVM.
 *
 * Главное правило приложения: отметка меняет РОВНО ОДИН символ исходного текста.
 * Текст не разбирается в модель и не собирается обратно, порядок строк не меняется
 * никогда, длина файла остаётся прежней.
 *
 * Две разновидности строк, различаются скобками:
 *
 *   - [ ] Вывести производную     задача  — сделанная перечёркивается
 *   - ( ) Ряды Фурье              тема    — пройденная гаснет, но остаётся целой
 *
 * Три состояния вместо двух: пусто → наполовину → готово → пусто.
 */

enum class Kind { TASK, TOPIC }

enum class Mark(val char: Char) {
    NONE(' '), HALF('~'), DONE('x');

    companion object {
        fun of(c: Char): Mark = when (c) {
            '~', '/' -> HALF
            'x', 'X' -> DONE
            else -> NONE
        }
    }
}

/** Одна отмечаемая строка, найденная в тексте. */
data class MdItem(
    /** номер строки, считая с нуля */
    val lineIndex: Int,
    /** смещение символа между скобками в исходном тексте */
    val boxOffset: Int,
    val kind: Kind,
    val mark: Mark,
    val label: String,
)

/** Что за файл — по тому, что в нём нашлось. От этого зависит значок в списке. */
enum class FileKind { TASKS, TOPICS, BOTH, PLAIN }

/** Сводка по файлу для подписи в списке. */
data class Counts(
    val tasksTotal: Int = 0,
    val tasksDone: Int = 0,
    val tasksHalf: Int = 0,
    val topicsTotal: Int = 0,
    val topicsDone: Int = 0,
    val topicsHalf: Int = 0,
    val sections: Int = 0,
) {
    val kind: FileKind
        get() = when {
            tasksTotal > 0 && topicsTotal > 0 -> FileKind.BOTH
            tasksTotal > 0 -> FileKind.TASKS
            topicsTotal > 0 -> FileKind.TOPICS
            else -> FileKind.PLAIN
        }

    /** Половинка считается за половину — иначе прогресс стоит на месте. */
    val progress: Float
        get() {
            val total = tasksTotal + topicsTotal
            if (total == 0) return 0f
            val done = tasksDone + topicsDone + (tasksHalf + topicsHalf) * 0.5f
            return done / total
        }
}

object MdItems {

    /** `- [ ] текст` или `- ( ) текст`, с любым отступом слева. */
    private val ITEM = Regex("""^(\s*)-\s([\[(])([ xX~/])([]\)])\s(.*)$""")

    /** Заголовок раздела — по ним считаются разделы и строится оглавление. */
    private val HEAD = Regex("""^(#{1,3})\s+(.+)$""")

    fun isItem(line: String): Boolean {
        val m = ITEM.matchEntire(line) ?: return false
        return pairs(m.groupValues[2], m.groupValues[4])
    }

    private fun pairs(open: String, close: String): Boolean =
        (open == "[" && close == "]") || (open == "(" && close == ")")

    /** Смещение начала каждой строки в исходном тексте. */
    private fun lineStarts(text: String): IntArray {
        val starts = ArrayList<Int>()
        starts.add(0)
        for (i in text.indices) if (text[i] == '\n') starts.add(i + 1)
        return starts.toIntArray()
    }

    /** Все отмечаемые строки текста, в порядке появления. */
    fun items(text: String): List<MdItem> {
        val starts = lineStarts(text)
        val lines = text.split("\n")
        val out = ArrayList<MdItem>()
        for (i in lines.indices) {
            val m = ITEM.matchEntire(lines[i]) ?: continue
            val open = m.groupValues[2]
            if (!pairs(open, m.groupValues[4])) continue
            val box = starts[i] + lines[i].indexOf(open) + 1
            out.add(
                MdItem(
                    lineIndex = i,
                    boxOffset = box,
                    kind = if (open == "[") Kind.TASK else Kind.TOPIC,
                    mark = Mark.of(m.groupValues[3][0]),
                    label = m.groupValues[5].trimEnd('\r'),
                )
            )
        }
        return out
    }

    /**
     * Переключить отметку по кругу: пусто → наполовину → готово → пусто.
     *
     * Меняется ровно один символ по смещению [boxOffset]. Длина текста не
     * меняется, все остальные байты остаются прежними.
     */
    fun cycle(text: String, boxOffset: Int): String {
        require(boxOffset >= 0 && boxOffset < text.length) {
            "смещение $boxOffset вне текста длиной ${text.length}"
        }
        val c = text[boxOffset]
        val next = when (Mark.of(c)) {
            Mark.NONE -> if (c == ' ') Mark.HALF.char else throw IllegalArgumentException(
                "по смещению $boxOffset ожидался пробел, ~ или x, а там '$c'"
            )
            Mark.HALF -> Mark.DONE.char
            Mark.DONE -> Mark.NONE.char
        }
        return text.substring(0, boxOffset) + next + text.substring(boxOffset + 1)
    }

    /** Сводка по файлу — для подписи и значка в списке. */
    fun counts(text: String): Counts {
        val list = items(text)
        val tasks = list.filter { it.kind == Kind.TASK }
        val topics = list.filter { it.kind == Kind.TOPIC }
        val sections = text.split("\n").count { HEAD.matches(it) }
        return Counts(
            tasksTotal = tasks.size,
            tasksDone = tasks.count { it.mark == Mark.DONE },
            tasksHalf = tasks.count { it.mark == Mark.HALF },
            topicsTotal = topics.size,
            topicsDone = topics.count { it.mark == Mark.DONE },
            topicsHalf = topics.count { it.mark == Mark.HALF },
            sections = sections,
        )
    }

    /**
     * Какая форма слова нужна для числа: у русского три, у английского
     * и испанского две. Правило чистое, без Android, поэтому проверяется тестом.
     */
    fun pluralForm(n: Int, lang: String): String = when (lang) {
        "ru" -> {
            val h = n % 100
            when {
                h in 11..14 -> "many"
                n % 10 == 1 -> "one"
                n % 10 in 2..4 -> "few"
                else -> "many"
            }
        }
        else -> if (n == 1) "one" else "few"
    }
}
