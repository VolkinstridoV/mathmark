package dev.yury.koren

import android.content.Context
import java.io.File

/**
 * Настройки обычным текстовым файлом, чтобы их можно было менять снаружи:
 *
 *     /data/data/dev.yury.koren/files/koren.conf
 *
 *     folder=/sdcard/Math
 *     scale=1.0
 *     theme=auto
 *
 * Никакой базы и никакого скрытого состояния: всё, что делает приложение,
 * можно сделать правкой текста — и наоборот.
 */
class Settings(ctx: Context) {

    private val file = File(ctx.filesDir, "koren.conf")

    var folder: String = DEFAULT_FOLDER
    var scale: Float = 1.0f
    var theme: String = "auto"   // auto | light | dark

    init {
        load()
    }

    fun load() {
        if (!file.exists()) return
        runCatching {
            file.readLines().forEach { raw ->
                val line = raw.trim()
                if (line.isEmpty() || line.startsWith("#")) return@forEach
                val k = line.substringBefore('=').trim()
                val v = line.substringAfter('=', "").trim()
                when (k) {
                    "folder" -> if (v.isNotEmpty()) folder = v
                    "scale" -> v.toFloatOrNull()?.let { scale = it.coerceIn(0.8f, 1.6f) }
                    "theme" -> if (v in setOf("auto", "light", "dark")) theme = v
                }
            }
        }
    }

    fun save() {
        runCatching {
            file.writeText(
                buildString {
                    appendLine("folder=$folder")
                    appendLine("scale=$scale")
                    appendLine("theme=$theme")
                },
                Charsets.UTF_8,
            )
        }
    }

    companion object {
        const val DEFAULT_FOLDER = "/sdcard/Math"
    }
}
