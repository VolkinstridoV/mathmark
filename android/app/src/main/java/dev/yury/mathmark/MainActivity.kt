package dev.yury.mathmark

import android.app.Activity
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.DocumentsContract
import android.provider.Settings as AndroidSettings
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File

/**
 * «MathMark» — читалка математики.
 *
 * Три экрана: список папки, чтение файла, настройки. Всё состояние живёт
 * в файлах — отметки в самих `.md`, настройки в `mathmark.conf`, — поэтому
 * приложение и Claude Code в терминале не мешают друг другу.
 */
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { App() }
    }
}

private enum class Screen { LIST, DOC, SET, STATS }

@Composable
private fun App() {
    val ctx = LocalContext.current
    val settings = remember { Settings(ctx) }

    var theme by remember { mutableStateOf(settings.theme) }
    var scale by remember { mutableFloatStateOf(settings.scale) }
    var folder by remember { mutableStateOf(settings.folder) }
    var lang by remember { mutableStateOf(settings.lang) }

    // надписи берутся из общей папки переводов — та же, что у настольной версии
    L.load(ctx, lang)

    val version = remember {
        runCatching { ctx.packageManager.getPackageInfo(ctx.packageName, 0).versionName }
            .getOrNull().orEmpty()
    }
    var news by remember { mutableStateOf<List<String>>(emptyList()) }
    LaunchedEffect(version, lang) {
        if (version.isNotBlank() && settings.seen != version) {
            news = WhatsNew.items(ctx, version)
            if (news.isEmpty()) { settings.seen = version; settings.save() }
        }
    }

    // будильники надо ставить заново при каждом запуске: система их не хранит
    val notifyAsk = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { }
    LaunchedEffect(Unit) {
        Notify.scheduleAll(ctx)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            notifyAsk.launch(android.Manifest.permission.POST_NOTIFICATIONS)
        }
    }

    MathMarkTheme(theme) {
        val colors = LocalMathMark.current
        val repo = remember(folder) { FilesRepo(File(folder)) }

        var screen by remember { mutableStateOf(Screen.LIST) }
        var doc by remember { mutableStateOf<File?>(null) }
        var reload by remember { mutableIntStateOf(0) }

        val scope = rememberCoroutineScope()
        var syncing by remember { mutableStateOf(false) }

        /** Синхронизация идёт в стороне от рисования — иначе окно замирает. */
        fun doSync() {
            if (SYNC_FROZEN) {
                android.widget.Toast.makeText(ctx, L["sync.frozen"], android.widget.Toast.LENGTH_LONG).show()
                return
            }
            if (syncing) return
            if (!settings.syncReady) {
                android.widget.Toast.makeText(ctx, L["sync.notSet"], android.widget.Toast.LENGTH_LONG).show()
                return
            }
            syncing = true
            android.widget.Toast.makeText(ctx, L["sync.running"], android.widget.Toast.LENGTH_SHORT).show()
            scope.launch {
                val report = withContext(Dispatchers.IO) {
                    Sync(
                        folder = File(settings.folder),
                        stateDir = ctx.filesDir,
                        remote = GitHub(settings.syncRepo, settings.syncToken),
                        device = "телефон",
                    ).run()
                }
                syncing = false
                android.widget.Toast.makeText(ctx, syncMessage(report), android.widget.Toast.LENGTH_LONG).show()
                reload++
            }
        }


        // возвращение из фона: файлы могли поменяться из терминала
        val owner = LocalLifecycleOwner.current
        DisposableEffect(owner) {
            val obs = LifecycleEventObserver { _, e ->
                if (e == Lifecycle.Event.ON_RESUME) reload++
            }
            owner.lifecycle.addObserver(obs)
            onDispose { owner.lifecycle.removeObserver(obs) }
        }

        if (news.isNotEmpty()) {
            AlertDialog(
                onDismissRequest = { },
                containerColor = colors.sheet,
                title = { Text(L["new.title"], color = colors.text) },
                text = {
                    Column {
                        news.forEach { line ->
                            Row(Modifier.padding(bottom = 10.dp)) {
                                Text("•  ", color = colors.accent)
                                Text(line, color = colors.dim,
                                     style = MaterialTheme.typography.bodyMedium)
                            }
                        }
                    }
                },
                confirmButton = {
                    TextButton(onClick = {
                        settings.seen = version; settings.save(); news = emptyList()
                    }) { Text(L["new.ok"], color = colors.accent) }
                },
            )
        }

        Surface(Modifier.fillMaxSize(), color = colors.bg) {
            when (screen) {
                Screen.LIST -> ListScreen(
                    repo = repo,
                    colors = colors,
                    reload = reload,
                    onOpen = { f -> doc = f; screen = Screen.DOC },
                    onSettings = { screen = Screen.SET },
                    onChanged = { reload++ },
                    syncing = syncing,
                    onSync = { doSync() },
                )

                Screen.DOC -> doc?.let { f ->
                    DocScreen(
                        file = f,
                        repo = repo,
                        colors = colors,
                        theme = theme,
                        scale = scale,
                        onBack = { screen = Screen.LIST; reload++ },
                    )
                } ?: run { screen = Screen.LIST }

                Screen.SET -> SettingsScreen(
                    settings = settings,
                    colors = colors,
                    theme = theme,
                    scale = scale,
                    folder = folder,
                    onTheme = { theme = it; settings.theme = it; settings.save() },
                    onScale = { scale = it; settings.scale = it; settings.save() },
                    onFolder = { folder = it; settings.folder = it; settings.save() },
                    lang = lang,
                    onLang = { lang = it; settings.lang = it; settings.save(); L.load(ctx, it) },
                    onSync = { doSync() },
                    onBack = { screen = Screen.LIST; reload++ },
                    onStats = { screen = Screen.STATS },
                )

                Screen.STATS -> StatsScreen(
                    colors = colors,
                    onBack = { screen = Screen.SET },
                )
            }
        }
    }
}

/** Шапка с фиолетовым градиентом — общая для всех экранов. */
@Composable
fun Bar(
    colors: MathMarkColors,
    title: String,
    subtitle: String? = null,
    left: (@Composable () -> Unit)? = null,
    right: (@Composable () -> Unit)? = null,
) {
    Column(
        Modifier
            .fillMaxWidth()
            .background(Brush.horizontalGradient(colors.gradient))
    ) {
        Spacer(Modifier.windowInsetsTopHeight(WindowInsets.statusBars))
        Row(
            Modifier
                .fillMaxWidth()
                .heightIn(min = 56.dp)
                .padding(horizontal = 6.dp, vertical = 6.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            if (left != null) left() else Spacer(Modifier.width(10.dp))
            Column(Modifier.weight(1f).padding(horizontal = 6.dp)) {
                Text(
                    title,
                    color = androidx.compose.ui.graphics.Color.White,
                    style = MaterialTheme.typography.titleLarge,
                    maxLines = 1,
                )
                if (subtitle != null) {
                    Text(
                        subtitle,
                        color = androidx.compose.ui.graphics.Color.White.copy(alpha = 0.82f),
                        style = MaterialTheme.typography.labelMedium,
                        maxLines = 1,
                    )
                }
            }
            right?.invoke()
        }
    }
}

// ——— доступ к файлам и выбор папки ———

fun hasFilesAccess(): Boolean =
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) Environment.isExternalStorageManager() else true

fun openFilesAccessSettings(ctx: Context) {
    runCatching {
        ctx.startActivity(
            Intent(
                AndroidSettings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION,
                Uri.parse("package:${ctx.packageName}"),
            )
        )
    }.onFailure {
        runCatching { ctx.startActivity(Intent(AndroidSettings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION)) }
    }
}

/**
 * Системный выбор папки отдаёт не путь, а ссылку вида `primary:Math`.
 * Для встроенной памяти её можно развернуть в обычный путь — с ним работает
 * весь остальной код. Для карты памяти путь не восстановить, тогда остаётся
 * вписать его вручную.
 */
fun treeUriToPath(uri: Uri): String? {
    val id = runCatching { DocumentsContract.getTreeDocumentId(uri) }.getOrNull() ?: return null
    val parts = id.split(":", limit = 2)
    if (parts.size != 2 || parts[0] != "primary") return null
    val tail = parts[1]
    val base = Environment.getExternalStorageDirectory().absolutePath
    return if (tail.isEmpty()) base else "$base/$tail"
}

@Composable
fun rememberFolderPicker(onPicked: (String?) -> Unit) =
    rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { res ->
        if (res.resultCode == Activity.RESULT_OK) {
            onPicked(res.data?.data?.let(::treeUriToPath))
        }
    }

fun folderPickIntent(): Intent = Intent(Intent.ACTION_OPEN_DOCUMENT_TREE)

fun copyToClipboard(ctx: Context, label: String, text: String) {
    val cm = ctx.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
    cm.setPrimaryClip(ClipData.newPlainText(label, text))
}

/** Пустой список — с подсказкой, куда класть файлы. */
@Composable
fun EmptyFolder(colors: MathMarkColors, folder: String, canRead: Boolean, onGrant: () -> Unit) {
    Column(
        Modifier.fillMaxSize().padding(34.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        RootMark(colors, 72.dp)
        Spacer(Modifier.height(20.dp))
        if (!canRead) {
            Text(
                L["access.title"],
                color = colors.text,
                style = MaterialTheme.typography.titleMedium,
            )
            Spacer(Modifier.height(8.dp))
            Text(
                L["access.body"],
                color = colors.dim,
                style = MaterialTheme.typography.bodyMedium,
            )
            Spacer(Modifier.height(16.dp))
            Button(onClick = onGrant) { Text(L["access.grant"]) }
        } else {
            Text(L["empty.title"], color = colors.text, style = MaterialTheme.typography.titleMedium)
            Spacer(Modifier.height(8.dp))
            Text(
                L.f("empty.hint", folder),
                color = colors.dim,
                style = MaterialTheme.typography.bodyMedium,
            )
        }
    }
}

@Composable
fun <T> ListOf(items: List<T>, row: @Composable (T) -> Unit) {
    LazyColumn(Modifier.fillMaxSize()) { items(items) { row(it) } }
}
