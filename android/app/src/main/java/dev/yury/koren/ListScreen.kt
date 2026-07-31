package dev.yury.koren

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import java.io.File

/**
 * Экран списка: вложенные папки сверху, файлы снизу.
 * Долгое нажатие на строке открывает шторку с действиями.
 */
@OptIn(ExperimentalFoundationApi::class, ExperimentalMaterial3Api::class)
@Composable
fun ListScreen(
    repo: FilesRepo,
    colors: KorenColors,
    reload: Int,
    onOpen: (File) -> Unit,
    onSettings: () -> Unit,
    onChanged: () -> Unit,
) {
    val ctx = LocalContext.current
    var access by remember { mutableStateOf(hasFilesAccess()) }
    var here by remember { mutableStateOf(repo.cwd) }
    var entries by remember { mutableStateOf(emptyList<Entry>()) }
    var counts by remember { mutableStateOf(mapOf<String, Counts>()) }

    var sheetFor by remember { mutableStateOf<Entry?>(null) }
    var renaming by remember { mutableStateOf<Entry?>(null) }
    var deleting by remember { mutableStateOf<Entry?>(null) }
    var moving by remember { mutableStateOf<Entry.Doc?>(null) }
    var newFolder by remember { mutableStateOf(false) }

    fun refresh() {
        access = hasFilesAccess()
        repo.createRoot()
        here = repo.cwd
        val list = repo.list()
        entries = list
        counts = list.filterIsInstance<Entry.Doc>()
            .associate { it.file.path to MdItems.counts(repo.read(it.file)) }
    }

    LaunchedEffect(reload, repo) { refresh() }

    // из вложенной папки «назад» поднимает на уровень выше,
    // и только из корня выходит из приложения
    BackHandler(enabled = !repo.atRoot) { repo.up(); refresh() }

    val crumbs = repo.crumbs()
    val title = if (repo.atRoot) "Корень" else here.name
    val sub = if (repo.atRoot) {
        "${repo.root.path} · ${entries.size}"
    } else {
        crumbs.joinToString(" / ") { it.name }
    }

    Column(Modifier.fillMaxSize()) {
        Bar(
            colors = colors,
            title = title,
            subtitle = sub,
            left = if (!repo.atRoot) {
                { IconBtn("‹") { repo.up(); refresh() } }
            } else null,
            right = {
                Row {
                    IconBtn("+") { newFolder = true }
                    IconBtn("⚙") { onSettings() }
                }
            },
        )

        if (entries.isEmpty()) {
            EmptyFolder(colors, repo.root.path, access) {
                openFilesAccessSettings(ctx)
            }
        } else {
            LazyColumn(Modifier.fillMaxSize()) {
                items(entries, key = { it.file.path }) { e ->
                    EntryRow(
                        entry = e,
                        counts = counts[e.file.path],
                        colors = colors,
                        onClick = {
                            when (e) {
                                is Entry.Folder -> { repo.enter(e.file); refresh() }
                                is Entry.Doc -> onOpen(e.file)
                            }
                        },
                        onLong = { sheetFor = e },
                    )
                    HorizontalDivider(color = colors.divider, thickness = 1.dp)
                }
            }
        }
    }

    // ——— шторка действий ———
    sheetFor?.let { e ->
        ModalBottomSheet(onDismissRequest = { sheetFor = null }, containerColor = colors.sheet) {
            Text(
                e.name,
                Modifier.padding(start = 22.dp, end = 22.dp, bottom = 12.dp),
                color = colors.text,
                style = MaterialTheme.typography.titleMedium,
            )
            HorizontalDivider(color = colors.divider)
            SheetItem("Открыть", colors) {
                sheetFor = null
                when (e) {
                    is Entry.Folder -> { repo.enter(e.file); refresh() }
                    is Entry.Doc -> onOpen(e.file)
                }
            }
            SheetItem("Переименовать", colors) { sheetFor = null; renaming = e }
            if (e is Entry.Doc) {
                SheetItem("Переместить в папку", colors) { sheetFor = null; moving = e }
            }
            SheetItem("Удалить", colors, danger = true) { sheetFor = null; deleting = e }
            Spacer(Modifier.height(18.dp))
        }
    }

    // ——— переименование и создание папки ———
    renaming?.let { e ->
        NameDialog(
            title = "Новое имя",
            initial = if (e is Entry.Doc) e.title else e.name,
            colors = colors,
            onCancel = { renaming = null },
            onOk = { name ->
                repo.rename(e, name)
                renaming = null
                refresh(); onChanged()
            },
        )
    }

    if (newFolder) {
        NameDialog(
            title = "Новая папка",
            initial = "",
            colors = colors,
            onCancel = { newFolder = false },
            onOk = { name ->
                repo.createFolder(name)
                newFolder = false
                refresh(); onChanged()
            },
        )
    }

    // ——— удаление ———
    deleting?.let { e ->
        AlertDialog(
            onDismissRequest = { deleting = null },
            containerColor = colors.sheet,
            title = { Text("Удалить?", color = colors.text) },
            text = {
                Text(
                    if (e is Entry.Folder)
                        "Папка «${e.name}» удалится вместе со всем, что внутри."
                    else "Файл «${e.name}» удалится с телефона.",
                    color = colors.dim,
                )
            },
            confirmButton = {
                TextButton(onClick = {
                    repo.delete(e); deleting = null; refresh(); onChanged()
                }) { Text("Удалить", color = colors.danger) }
            },
            dismissButton = {
                TextButton(onClick = { deleting = null }) { Text("Отмена", color = colors.dim) }
            },
        )
    }

    // ——— перемещение ———
    moving?.let { d ->
        val targets = listOf(repo.root) + repo.allFolders()
        ModalBottomSheet(onDismissRequest = { moving = null }, containerColor = colors.sheet) {
            Text(
                "Куда переместить «${d.title}»",
                Modifier.padding(start = 22.dp, end = 22.dp, bottom = 12.dp),
                color = colors.text,
                style = MaterialTheme.typography.titleMedium,
            )
            HorizontalDivider(color = colors.divider)
            targets.forEach { dir ->
                val label = if (dir == repo.root) "Корень папки" else
                    dir.path.removePrefix(repo.root.path + "/")
                SheetItem(label, colors) {
                    repo.move(d, dir); moving = null; refresh(); onChanged()
                }
            }
            Spacer(Modifier.height(18.dp))
        }
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun EntryRow(
    entry: Entry,
    counts: Counts?,
    colors: KorenColors,
    onClick: () -> Unit,
    onLong: () -> Unit,
) {
    Row(
        Modifier
            .fillMaxWidth()
            .combinedClickable(onClick = onClick, onLongClick = onLong)
            .padding(horizontal = 16.dp, vertical = 13.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        when (entry) {
            is Entry.Folder -> FolderGlyph(colors)
            is Entry.Doc -> KindGlyph(counts?.kind ?: FileKind.PLAIN, colors)
        }
        Spacer(Modifier.width(13.dp))
        Column(Modifier.weight(1f)) {
            Text(
                when (entry) {
                    is Entry.Folder -> entry.name
                    is Entry.Doc -> entry.title
                },
                color = colors.text,
                style = MaterialTheme.typography.titleMedium,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
            Spacer(Modifier.height(3.dp))
            Text(
                when (entry) {
                    is Entry.Folder -> "${entry.items} внутри"
                    is Entry.Doc -> counts?.let { MdItems.subtitle(it) } ?: ""
                },
                color = colors.dim,
                style = MaterialTheme.typography.bodySmall,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            if (entry is Entry.Doc && counts != null && counts.kind != FileKind.PLAIN) {
                Spacer(Modifier.height(7.dp))
                Progress(counts.progress, colors)
            }
        }
    }
}

@Composable
private fun Progress(value: Float, colors: KorenColors) {
    Box(
        Modifier
            .fillMaxWidth()
            .height(4.dp)
            .clip(RoundedCornerShape(3.dp))
            .background(colors.divider)
    ) {
        Box(
            Modifier
                .fillMaxHeight()
                .fillMaxWidth(value.coerceIn(0f, 1f))
                .background(Brush.horizontalGradient(colors.gradient))
        )
    }
}

@Composable
fun IconBtn(glyph: String, onClick: () -> Unit) {
    TextButton(onClick = onClick, contentPadding = PaddingValues(0.dp)) {
        Text(glyph, color = Color.White, style = MaterialTheme.typography.titleLarge)
    }
}

@Composable
fun SheetItem(text: String, colors: KorenColors, danger: Boolean = false, onClick: () -> Unit) {
    Text(
        text,
        Modifier
            .fillMaxWidth()
            .combinedClickableCompat(onClick)
            .padding(horizontal = 22.dp, vertical = 15.dp),
        color = if (danger) colors.danger else colors.text,
        style = MaterialTheme.typography.bodyLarge,
    )
}

@OptIn(ExperimentalFoundationApi::class)
private fun Modifier.combinedClickableCompat(onClick: () -> Unit): Modifier =
    this.combinedClickable(onClick = onClick)

@Composable
fun NameDialog(
    title: String,
    initial: String,
    colors: KorenColors,
    onCancel: () -> Unit,
    onOk: (String) -> Unit,
) {
    var value by remember { mutableStateOf(initial) }
    AlertDialog(
        onDismissRequest = onCancel,
        containerColor = colors.sheet,
        title = { Text(title, color = colors.text) },
        text = {
            OutlinedTextField(
                value = value,
                onValueChange = { value = it },
                singleLine = true,
                colors = OutlinedTextFieldDefaults.colors(
                    focusedTextColor = colors.text,
                    unfocusedTextColor = colors.text,
                    focusedBorderColor = colors.accent,
                    unfocusedBorderColor = colors.divider,
                    cursorColor = colors.accent,
                ),
            )
        },
        confirmButton = {
            TextButton(onClick = { if (value.isNotBlank()) onOk(value) }) {
                Text("Готово", color = colors.accent)
            }
        },
        dismissButton = {
            TextButton(onClick = onCancel) { Text("Отмена", color = colors.dim) }
        },
    )
}
