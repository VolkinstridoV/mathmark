package dev.yury.mathmark

import android.content.Context
import org.json.JSONObject
import java.util.Locale

/**
 * Надписи приложения. Лежат в общей папке `shared/i18n/` обычным JSON —
 * те же самые файлы читает настольная версия, поэтому перевод один на обе.
 *
 * Язык берётся из системы, если в настройках стоит «как в системе»,
 * иначе — выбранный вручную.
 */
object L {

    val LANGUAGES = listOf("en", "ru", "es")

    /** Флажок и родное название — для выбора в настройках. */
    val FLAGS = mapOf("en" to "🇬🇧", "ru" to "🇷🇺", "es" to "🇪🇸")
    val NATIVE = mapOf("en" to "English", "ru" to "Русский", "es" to "Español")

    @Volatile
    private var table: Map<String, String> = emptyMap()

    @Volatile
    var current: String = "en"
        private set

    fun load(ctx: Context, setting: String) {
        val code = resolve(setting)
        if (code == current && table.isNotEmpty()) return
        val raw = runCatching {
            ctx.assets.open("$code.json").bufferedReader(Charsets.UTF_8).use { it.readText() }
        }.getOrNull() ?: return
        val json = runCatching { JSONObject(raw) }.getOrNull() ?: return
        val map = HashMap<String, String>()
        json.keys().forEach { k -> map[k] = json.getString(k) }
        table = map
        current = code
    }

    private fun resolve(setting: String): String =
        if (setting in LANGUAGES) setting
        else Locale.getDefault().language.let { if (it in LANGUAGES) it else "en" }

    /** Надпись по ключу. Если ключа нет — виден он сам, а не пустота. */
    operator fun get(key: String): String = table[key] ?: key

    fun f(key: String, vararg args: Any): String =
        runCatching { String.format(get(key), *args) }.getOrDefault(get(key))
}
