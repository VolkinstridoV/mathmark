package dev.yury.mathmark

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
    colors: MathMarkColors,
    theme: String,
    scale: Float,
    onBack: () -> Unit,
) {
    var text by remember(file) { mutableStateOf(repo.read(file)) }
    var toc by remember(file) { mutableStateOf(listOf<Pair<String, String>>()) }
    var tocOpen by remember { mutableStateOf(false) }
    var web by remember { mutableStateOf<WebView?>(null) }
    var editing by remember { mutableStateOf(false) }
    var clash by remember { mutableStateOf<String?>(null) }   // текст, который спорит с диском

    val systemDark = (LocalConfiguration.current.uiMode and Configuration.UI_MODE_NIGHT_MASK) ==
        Configuration.UI_MODE_NIGHT_YES
    val dark = isDarkFor(theme, systemDark)

    val counts = remember(text) { MdItems.counts(text) }

    /** Надписи редактора: страница их сама не знает, язык выбирает приложение. */
    fun editLabels(): String = JSONObject().apply {
        listOf(
            "edit.save", "edit.cancel", "edit.task", "edit.topic", "edit.hidden",
            "edit.formula", "edit.matrix", "edit.heading", "edit.plot",
            "edit.problems", "edit.clean", "edit.matrixSize",
        ).forEach { put(it, L[it]) }
    }.toString()

    // из правки «назад» возвращает к чтению, из чтения — к списку
    BackHandler {
        if (editing) {
            editing = false
            web?.evaluateJavascript("MathMarkEdit.close();", null)
        } else onBack()
    }

    Column(Modifier.fillMaxSize()) {
        Bar(
            colors = colors,
            title = file.name.removeSuffix(".md").removeSuffix(".MD"),
            subtitle = subtitleOf(counts),
            left = {
                IconBtn("‹") {
                    if (editing) {
                        editing = false
                        web?.evaluateJavascript("MathMarkEdit.close();", null)
                    } else onBack()
                }
            },
            right = {
                Row {
                    if (!editing) {
                        IconBtn("✎") {
                            editing = true
                            web?.evaluateJavascript(
                                "MathMarkEdit.setLabels(${editLabels()});" +
                                    "MathMarkEdit.open(${JSONObject.quote(text)});",
                                null,
                            )
                        }
                    }
                    if (toc.isNotEmpty() && !editing) IconBtn("≡") { tocOpen = true }
                }
            },
        )

        AndroidView(
            modifier = Modifier.fillMaxSize(),
            factory = { ctx ->
                @Suppress("NAME_SHADOWING")
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
                            saveSink = { fresh ->
                                post {
                                    val onDisk = repo.read(file)
                                    if (onDisk != text) {
                                        clash = fresh          // файл увели из-под нас
                                    } else if (repo.write(file, fresh)) {
                                        text = fresh
                                        editing = false
                                        evaluateJavascript(
                                            "MathMarkEdit.close();" +
                                                "MathMark.render(${JSONObject.quote(fresh)});",
                                            null,
                                        )
                                        android.widget.Toast.makeText(
                                            ctx, L["edit.saved"], android.widget.Toast.LENGTH_SHORT,
                                        ).show()
                                    }
                                }
                            },
                            cancelSink = {
                                post {
                                    editing = false
                                    evaluateJavascript("MathMarkEdit.close();", null)
                                }
                            },
                            cycleSink = { off ->
                                post {
                                    val updated = runCatching { MdItems.cycle(text, off) }.getOrNull()
                                        ?: return@post
                                    if (repo.write(file, updated)) {
                                        text = updated
                                        val newMark = Mark.of(updated[off])
                                        evaluateJavascript(
                                            "MathMark.setMark($off,'${newMark.name.lowercase()}')", null)
                                        // журнал помнит, КОГДА отмечено —
                                        // в самом файле этого нет
                                        MdItems.items(updated).firstOrNull { it.boxOffset == off }
                                            ?.let { item ->
                                                Journal.record(
                                                    File(ctx.filesDir, "journal.log"),
                                                    file.name, item.kind, newMark,
                                                )
                                            }
                                    }
                                }
                            },
                        ),
                        "Android",
                    )
                    webViewClient = object : android.webkit.WebViewClient() {
                        override fun onPageFinished(view: WebView, url: String) {
                            view.evaluateJavascript(
                                "MathMark.setLabels({empty:" +
                                    JSONObject.quote(L["doc.empty"]) + "});" +
                                "MathMark.setTheme($dark);" +
                                    "MathMark.setScale($scale);" +
                                    "MathMark.render(${JSONObject.quote(text)});",
                                null,
                            )
                        }
                    }
                    loadUrl("file:///android_asset/reader.html")
                    web = this
                }
            },
            update = { view ->
                view.evaluateJavascript("MathMark.setTheme($dark);MathMark.setScale($scale);", null)
            },
        )
    }

    clash?.let { fresh ->
        AlertDialog(
            onDismissRequest = { clash = null },
            containerColor = colors.sheet,
            title = { Text(L["edit.title"], color = colors.text) },
            text = { Text(L["edit.changedOutside"], color = colors.dim) },
            confirmButton = {
                TextButton(onClick = {
                    if (repo.write(file, fresh)) {
                        text = fresh
                        editing = false
                        web?.evaluateJavascript(
                            "MathMarkEdit.close();MathMark.render(${JSONObject.quote(fresh)});", null)
                    }
                    clash = null
                }) { Text(L["edit.save"], color = colors.danger) }
            },
            dismissButton = {
                TextButton(onClick = { clash = null }) { Text(L["common.cancel"], color = colors.dim) }
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
                    web?.evaluateJavascript("MathMark.goto('$id')", null)
                }
            }
            Spacer(Modifier.height(18.dp))
        }
    }
}

/** Мост между страницей и приложением. Наружу уходит текст, обратно — события. */
private class Bridge(
    private val tocSink: (String) -> Unit,
    private val cycleSink: (Int) -> Unit,
    private val saveSink: (String) -> Unit,
    private val cancelSink: () -> Unit,
) {
    @JavascriptInterface
    fun onToc(json: String) = tocSink(json)

    @JavascriptInterface
    fun onCycle(offset: Int) = cycleSink(offset)

    @JavascriptInterface
    fun onEditSave(text: String) = saveSink(text)

    @JavascriptInterface
    fun onEditCancel(ignored: String) = cancelSink()
}
