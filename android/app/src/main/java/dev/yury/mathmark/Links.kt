package dev.yury.mathmark

import android.content.Context
import android.content.Intent
import android.net.Uri
import org.json.JSONObject

/** Ссылки наружу — общий файл на обе версии, чтобы не расходились. */
object Links {

    private var cached: JSONObject? = null

    private fun table(ctx: Context): JSONObject =
        cached ?: runCatching {
            JSONObject(ctx.assets.open("links.json").bufferedReader(Charsets.UTF_8).use { it.readText() })
        }.getOrDefault(JSONObject()).also { cached = it }

    fun get(ctx: Context, key: String): String = table(ctx).optString(key)

    fun open(ctx: Context, key: String) {
        val url = get(ctx, key)
        if (url.isBlank()) return
        runCatching {
            ctx.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            })
        }
    }
}
