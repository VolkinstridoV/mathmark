package dev.yury.mathmark

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

/**
 * Что нового: показывается один раз после обновления и больше не мешает.
 *
 * Список лежит в общей папке `shared/whatsnew/<версия>.json` на трёх языках —
 * тот же файл читает настольная версия.
 */
object WhatsNew {

    /** Пункты для этой версии на текущем языке. Пусто — окно не показываем. */
    fun items(ctx: Context, version: String): List<String> {
        val raw = runCatching {
            ctx.assets.open("$version.json").bufferedReader(Charsets.UTF_8).use { it.readText() }
        }.getOrNull() ?: return emptyList()
        val json = runCatching { JSONObject(raw) }.getOrNull() ?: return emptyList()
        val arr: JSONArray = json.optJSONArray(L.current) ?: json.optJSONArray("en") ?: return emptyList()
        return (0 until arr.length()).map { arr.getString(it) }
    }
}
