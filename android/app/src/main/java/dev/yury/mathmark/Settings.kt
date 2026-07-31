package dev.yury.mathmark

import android.content.Context
import java.io.File

/**
 * Настройки обычным текстовым файлом, чтобы их можно было менять снаружи:
 *
 *     /data/data/dev.yury.mathmark/files/mathmark.conf
 *
 *     folder=/sdcard/Math
 *     scale=1.0
 *     theme=auto
 *
 * Никакой базы и никакого скрытого состояния: всё, что делает приложение,
 * можно сделать правкой текста — и наоборот.
 */
class Settings(ctx: Context) {

    private val file = File(ctx.filesDir, "mathmark.conf")

    var folder: String = DEFAULT_FOLDER
    var scale: Float = 1.0f
    var theme: String = "auto"   // auto | light | dark
    var lang: String = "auto"    // auto | en | ru | es

    // синхронизация: по умолчанию выключена, ничего никуда не уходит
    var syncOn: Boolean = false
    var syncRepo: String = ""
    var syncToken: String = ""

    /** Какую версию человек уже видел: чтобы «что нового» показать один раз. */
    var seen: String = ""

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
                    "lang" -> if (v in setOf("auto", "en", "ru", "es")) lang = v
                    "sync" -> syncOn = v == "1" || v == "true"
                    "repo" -> syncRepo = v
                    "token" -> syncToken = v
                    "seen" -> seen = v
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
                    appendLine("lang=$lang")
                    appendLine("sync=${if (syncOn) 1 else 0}")
                    appendLine("repo=$syncRepo")
                    appendLine("token=$syncToken")
                    appendLine("seen=$seen")
                },
                Charsets.UTF_8,
            )
        }
    }

    /** Настроено ли всё, что нужно для кнопки. */
    val syncReady: Boolean
        get() = syncOn && syncRepo.isNotBlank() && syncToken.isNotBlank()

    companion object {
        const val DEFAULT_FOLDER = "/sdcard/Math"
    }
}
