package dev.yury.mathmark

/**
 * Подписи, которые собираются из чисел и слов. Отдельно от [MdItems], потому
 * что тот нарочно ничего не знает ни про Android, ни про язык.
 */
fun subtitleOf(c: Counts): String = when (c.kind) {
    FileKind.TASKS -> L.f("counts.tasks", c.tasksDone, c.tasksTotal)
    FileKind.TOPICS -> L.f("counts.topics", c.topicsDone, c.topicsTotal)
    FileKind.BOTH -> L.f("counts.both", c.tasksDone, c.tasksTotal, c.topicsDone, c.topicsTotal)
    FileKind.PLAIN ->
        if (c.sections > 0) L.f("sections." + MdItems.pluralForm(c.sections, L.current), c.sections)
        else L["counts.reference"]
}
