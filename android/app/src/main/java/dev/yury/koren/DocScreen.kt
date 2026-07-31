package dev.yury.koren

import android.annotation.SuppressLint
import androidx.activity.compose.BackHandler
import android.webkit.JavascriptInterface
import android.webkit.WebView
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.viewinterop.AndroidView
import androidx.compose.ui.unit.dp
import android.content.res.Configuration
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/**
 * Экран чтения. Разметку и формулы рисует страница в `assets/reader.html`,
 * здесь — только шапка, оглавление и правка одного байта по нажатию.
 *
 * Обмен со страницей нарочно узкий: наружу уходит текст файла, обратно
 * приходят два события — оглавление и нажатие на кружок.
 */
@OptIn(ExperimentalMaterial3Api::class)
@SuppressLint("SetJavaScriptEnabled")
@Composable
fun DocScreen(
    file: File,
    repo: FilesRepo,
    colors: KorenColors,
    theme: String,
    scale: Float,
    onBack: () -> Unit,
) {
    var text by remember(file) { mutableStateOf(repo.read(file)) }
    var toc by remember(file) { mutableStateOf(listOf<Pair<String, String>>()) }
    var tocOpen by remember { mutableStateOf(false) }
    var web by remember { mutableStateOf<WebView?>(null) }

    val systemDark = (LocalConfiguration.current.uiMode and Configuration.UI_MODE_NIGHT_MASK) ==
        Configuration.UI_MODE_NIGHT_YES
    val dark = isDarkFor(theme, systemDark)

    val counts = remember(text) { MdItems.counts(text) }

    // системная кнопка «назад» — это возврат к списку, а не выход из приложения
    BackHandler { onBack() }

    Column(Modifier.fillMaxSize()) {
        Bar(
            colors = colors,
            title = file.name.removeSuffix(".md").removeSuffix(".MD"),
            subtitle = subtitleOf(counts),
            left = { IconBtn("‹") { onBack() } },
            right = { if (toc.isNotEmpty()) IconBtn("≡") { tocOpen = true } },
        )

        AndroidView(
            modifier = Modifier.fillMaxSize(),
            factory = { ctx ->
                WebView(ctx).apply {
                    settings.javaScriptEnabled = true
                    settings.domStorageEnabled = false
                    settings.allowFileAccess = false
                    settings.allowContentAccess = false
                    settings.textZoom = 100
                    setBackgroundColor(if (dark) 0xFF131017.toInt() else 0xFFFCFBFE.toInt())
                    addJavascriptInterface(
                        Bridge(
                            tocSink = { json ->
                                runCatching { JSONArray(json) }.getOrNull()?.let { arr ->
                                    val out = ArrayList<Pair<String, String>>()
                                    for (i in 0 until arr.length()) {
                                        val o = arr.getJSONObject(i)
                                        out.add(o.getString("id") to o.getString("txt"))
                                    }
                                    post { toc = out }
                                }
                            },
                            cycleSink = { off ->
                                post {
                                    val updated = runCatching { MdItems.cycle(text, off) }.getOrNull()
                                        ?: return@post
                                    if (repo.write(file, updated)) {
                                        text = updated
                                        val mark = Mark.of(updated[off]).name.lowercase()
                                        evaluateJavascript("Koren.setMark($off,'$mark')", null)
                                    }
                                }
                            },
                        ),
                        "Android",
                    )
                    webViewClient = object : android.webkit.WebViewClient() {
                        override fun onPageFinished(view: WebView, url: String) {
                            view.evaluateJavascript(
                                "Koren.setLabels({empty:" +
                                    JSONObject.quote(L["doc.empty"]) + "});" +
                                "Koren.setTheme($dark);" +
                                    "Koren.setScale($scale);" +
                                    "Koren.render(${JSONObject.quote(text)});",
                                null,
                            )
                        }
                    }
                    loadUrl("file:///android_asset/reader.html")
                    web = this
                }
            },
            update = { view ->
                view.evaluateJavascript("Koren.setTheme($dark);Koren.setScale($scale);", null)
            },
        )
    }

    if (tocOpen) {
        ModalBottomSheet(onDismissRequest = { tocOpen = false }, containerColor = colors.sheet) {
            Text(
                L["doc.sections"],
                Modifier.padding(start = 22.dp, end = 22.dp, bottom = 10.dp),
                color = colors.dim,
                style = MaterialTheme.typography.labelLarge,
            )
            HorizontalDivider(color = colors.divider)
            toc.forEach { (id, label) ->
                SheetItem(label, colors) {
                    tocOpen = false
                    web?.evaluateJavascript("Koren.goto('$id')", null)
                }
            }
            Spacer(Modifier.height(18.dp))
        }
    }
}

/** Мост между страницей чтения и приложением. Только два события, оба входящие. */
private class Bridge(
    private val tocSink: (String) -> Unit,
    private val cycleSink: (Int) -> Unit,
) {
    @JavascriptInterface
    fun onToc(json: String) = tocSink(json)

    @JavascriptInterface
    fun onCycle(offset: Int) = cycleSink(offset)
}
