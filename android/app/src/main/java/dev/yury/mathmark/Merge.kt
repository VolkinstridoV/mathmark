package dev.yury.mathmark

/**
 * Сведение двух версий одного файла при синхронизации.
 *
 * Правило: если один и тот же пункт отмечен по-разному на телефоне и на
 * компьютере, выигрывает более продвинутое состояние — пройдено бьёт
 * «разбираю», «разбираю» бьёт пустое. Вперёд, а не назад.
 *
 * Если разошёлся сам текст, а не отметки, программа ничего не выбирает:
 * сообщает о споре и оставляет своё, а чужое сохраняется отдельным файлом.
 *
 * Точный повтор `merge.py` из настольной версии, вплоть до тех же тестов.
 */
object Merge {

    data class Result(val text: String, val conflict: Boolean)

    private fun rank(m: Mark): Int = when (m) {
        Mark.NONE -> 0
        Mark.HALF -> 1
        Mark.DONE -> 2
    }

    /**
     * @param base то, что было при прошлой синхронизации; null, если файл
     *             появился сразу с двух сторон.
     */
    fun merge(base: String?, local: String, remote: String): Result {
        if (local == remote) return Result(local, false)
        if (base != null && local == base) return Result(remote, false)
        if (base != null && remote == base) return Result(local, false)

        val ll = local.split("\n")
        val rl = remote.split("\n")
        if (ll.size != rl.size) return Result(local, true)

        val out = ArrayList<String>(ll.size)
        for (i in ll.indices) {
            val a = ll[i]
            val b = rl[i]
            if (a == b) {
                out.add(a)
                continue
            }
            val sa = MdItems.stripMark(a)
            val sb = MdItems.stripMark(b)
            if (sa == null || sb == null || sa != sb) {
                return Result(local, true)      // разошёлся текст, а не отметка
            }
            val ma = MdItems.markOf(a) ?: return Result(local, true)
            val mb = MdItems.markOf(b) ?: return Result(local, true)
            out.add(if (rank(ma) >= rank(mb)) a else b)
        }
        return Result(out.joinToString("\n"), false)
    }
}
