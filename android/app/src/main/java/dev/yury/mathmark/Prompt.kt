package dev.yury.mathmark

import android.content.Context

/**
 * Инструкция для нейросети: как писать файлы, которые это приложение покажет
 * правильно. Лежит в общей папке `shared/prompt/prompt.md` — тот же самый файл
 * читает десктопная версия, чтобы правила не разъехались.
 *
 * В рабочей папке приложение ничего не создаёт. Достать инструкцию можно двумя
 * путями: кнопкой «Скопировать промпт» в настройках или запросом из терминала:
 *
 *     content query, uri content://dev.yury.mathmark/prompt
 */
object Prompt {

    @Volatile
    private var cached: String? = null

    fun text(ctx: Context): String = cached ?: runCatching {
        ctx.assets.open("prompt.md").bufferedReader(Charsets.UTF_8).use { it.readText() }
    }.getOrDefault("").also { cached = it }
}
