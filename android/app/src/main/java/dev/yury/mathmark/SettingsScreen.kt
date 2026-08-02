package dev.yury.mathmark

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import android.widget.Toast

/**
 * Настройки. Всё, что здесь меняется, ложится в `mathmark.conf` обычным текстом —
 * то же самое можно сделать правкой файла из терминала.
 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
fun SettingsScreen(
    settings: Settings,
    colors: MathMarkColors,
    theme: String,
    scale: Float,
    folder: String,
    lang: String,
    onLang: (String) -> Unit,
    onSync: () -> Unit,
    onStats: () -> Unit,
    onTheme: (String) -> Unit,
    onScale: (Float) -> Unit,
    onFolder: (String) -> Unit,
    onBack: () -> Unit,
) {
    val ctx = LocalContext.current
    var typing by remember { mutableStateOf(false) }
    var editing by remember { mutableStateOf<String?>(null) }
    var syncOn by remember { mutableStateOf(settings.syncOn) }
    var repo by remember { mutableStateOf(settings.syncRepo) }
    var token by remember { mutableStateOf(settings.syncToken) }

    BackHandler { onBack() }
    var live by remember(scale) { mutableFloatStateOf(scale) }

    val picker = rememberFolderPicker { path ->
        if (path != null) onFolder(path)
        else Toast.makeText(
            ctx,
            L["toast.folderNotResolved"],
            Toast.LENGTH_LONG,
        ).show()
    }

    Column(Modifier.fillMaxSize()) {
        Bar(colors, L["settings.title"], left = { IconBtn("‹") { onBack() } })

        Column(Modifier.verticalScroll(rememberScrollState()).padding(bottom = 40.dp)) {

            Group(L["settings.files"], colors)
            Item(L["settings.folder"], folder, colors) { picker.launch(folderPickIntent()) }
            Item(
                L["settings.manualPath"],
                L["settings.manualPathHint"],
                colors,
            ) { typing = true }
            Item(
                L["settings.shows"],
                L["settings.showsHint"],
                colors,
                clickable = false,
            )

            Group(L["settings.view"], colors)
            Column(Modifier.padding(horizontal = 18.dp, vertical = 12.dp)) {
                Text(L["settings.textSize"], color = colors.text, style = MaterialTheme.typography.titleSmall)
                Text(
                    L["settings.textSizeHint"],
                    color = colors.dim,
                    style = MaterialTheme.typography.bodySmall,
                )
                Slider(
                    value = live,
                    onValueChange = { live = it },
                    onValueChangeFinished = { onScale(live) },
                    valueRange = 0.85f..1.4f,
                    steps = 10,
                    colors = SliderDefaults.colors(
                        thumbColor = colors.accent,
                        activeTrackColor = colors.accent,
                        inactiveTrackColor = colors.divider,
                    ),
                )
            }
            HorizontalDivider(color = colors.divider)

            Column(Modifier.padding(horizontal = 18.dp, vertical = 14.dp)) {
                Text(L["settings.theme"], color = colors.text, style = MaterialTheme.typography.titleSmall)
                Spacer(Modifier.height(10.dp))
                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    Choice(L["settings.themeAuto"], theme == "auto", colors) { onTheme("auto") }
                    Choice(L["settings.themeLight"], theme == "light", colors) { onTheme("light") }
                    Choice(L["settings.themeDark"], theme == "dark", colors) { onTheme("dark") }
                }
            }
            HorizontalDivider(color = colors.divider)

            Column(Modifier.padding(horizontal = 18.dp, vertical = 14.dp)) {
                Text(L["settings.language"], color = colors.text, style = MaterialTheme.typography.titleSmall)
                Spacer(Modifier.height(10.dp))
                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    Choice(L["settings.languageAuto"], lang == "auto", colors) { onLang("auto") }
                    L.LANGUAGES.forEach { code ->
                        Choice(
                            "${L.FLAGS[code]}  ${L.NATIVE[code]}",
                            lang == code, colors,
                        ) { onLang(code) }
                    }
                }
            }
            HorizontalDivider(color = colors.divider)

            Item(L["stats.title"], L["stats.last30"], colors) { onStats() }

            Group(L["sync.title"], colors)
            Row(
                Modifier.fillMaxWidth().padding(horizontal = 18.dp, vertical = 14.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(Modifier.weight(1f)) {
                    Text(L["sync.enabled"], color = colors.text,
                         style = MaterialTheme.typography.titleSmall)
                    Text(
                        when {
                            SYNC_FROZEN -> L["sync.frozen"]
                            settings.syncReady -> settings.syncRepo
                            else -> L["sync.notSet"]
                        },
                        color = colors.dim, style = MaterialTheme.typography.bodySmall,
                    )
                }
                Switch(
                    checked = syncOn,
                    onCheckedChange = { syncOn = it; settings.syncOn = it; settings.save() },
                    colors = SwitchDefaults.colors(checkedTrackColor = colors.accent),
                )
            }
            HorizontalDivider(color = colors.divider)
            Item(L["sync.repo"], repo.ifBlank { L["sync.repoHint"] }, colors) { editing = "repo" }
            Item(
                L["sync.token"],
                if (token.isBlank()) L["sync.tokenEmpty"] else L["sync.tokenSet"],
                colors,
            ) { editing = "token" }
            Item(L["sync.check"], L["sync.checkHint"], colors) {
                if (SYNC_FROZEN) {
                    Toast.makeText(ctx, L["sync.frozen"], Toast.LENGTH_LONG).show()
                } else if (!settings.syncReady) {
                    Toast.makeText(ctx, L["sync.notSet"], Toast.LENGTH_LONG).show()
                } else {
                    Toast.makeText(ctx, L["sync.running"], Toast.LENGTH_SHORT).show()
                    Thread {
                        val problem = GitHub(settings.syncRepo, settings.syncToken).check()
                        android.os.Handler(android.os.Looper.getMainLooper()).post {
                            Toast.makeText(ctx, problem ?: L["sync.ok"], Toast.LENGTH_LONG).show()
                        }
                    }.start()
                }
            }
            Item(L["sync.button"], L["sync.title"], colors) { onSync() }

            Group(L["settings.ai"], colors)
            Item(
                L["settings.copyPrompt"],
                L["settings.copyPromptHint"],
                colors,
            ) {
                copyToClipboard(ctx, L["settings.copyPrompt"], Prompt.text(ctx))
                Toast.makeText(ctx, L["toast.promptCopied"], Toast.LENGTH_SHORT).show()
            }
            Item(
                L["settings.termQuery"],
                "content query --uri content://dev.yury.mathmark/prompt",
                colors,
            ) {
                copyToClipboard(
                    ctx,
                    L["settings.termQuery"],
                    "content query --uri content://dev.yury.mathmark/prompt",
                )
                Toast.makeText(ctx, L["toast.commandCopied"], Toast.LENGTH_SHORT).show()
            }

            Group(L["settings.feedback"], colors)
            Item(L["settings.feedback"], L["settings.feedbackHint"], colors) {
                Links.open(ctx, "telegram")
            }
            Item(L["settings.issues"], L["settings.issuesHint"], colors) {
                Links.open(ctx, "issues")
            }

            Group(L["settings.about"], colors)
            Row(
                Modifier.fillMaxWidth().padding(18.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                RootMark(colors, 54.dp)
                Spacer(Modifier.width(14.dp))
                Column {
                    Text(L["settings.version"], color = colors.text, style = MaterialTheme.typography.titleMedium)
                    Text(
                        L["settings.versionHint"],
                        color = colors.dim,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            }
        }
    }

    editing?.let { what ->
        NameDialog(
            title = if (what == "repo") L["sync.repo"] else L["sync.token"],
            initial = if (what == "repo") repo else token,
            colors = colors,
            onCancel = { editing = null },
            onOk = { value ->
                if (what == "repo") { repo = value.trim(); settings.syncRepo = repo }
                else { token = value.trim(); settings.syncToken = token }
                settings.save()
                editing = null
            },
        )
    }

    if (typing) {
        NameDialog(
            title = L["list.pathTitle"],
            initial = folder,
            colors = colors,
            onCancel = { typing = false },
            onOk = { onFolder(it.trim()); typing = false },
        )
    }
}

@Composable
private fun Group(title: String, colors: MathMarkColors) {
    Text(
        title.uppercase(),
        Modifier.padding(start = 18.dp, end = 18.dp, top = 18.dp, bottom = 6.dp),
        color = colors.accent,
        style = MaterialTheme.typography.labelMedium,
    )
}

@Composable
private fun Item(
    key: String,
    value: String,
    colors: MathMarkColors,
    clickable: Boolean = true,
    onClick: () -> Unit = {},
) {
    Column(
        Modifier
            .fillMaxWidth()
            .then(if (clickable) Modifier.clickable(onClick = onClick) else Modifier)
            .padding(horizontal = 18.dp, vertical = 14.dp)
    ) {
        Text(key, color = colors.text, style = MaterialTheme.typography.titleSmall)
        Spacer(Modifier.height(3.dp))
        Text(value, color = colors.dim, style = MaterialTheme.typography.bodySmall)
    }
    HorizontalDivider(color = colors.divider)
}

@Composable
private fun Choice(label: String, on: Boolean, colors: MathMarkColors, onClick: () -> Unit) {
    val text: @Composable () -> Unit = { Text(label, maxLines = 1) }
    if (on) {
        Button(
            onClick = onClick,
            colors = ButtonDefaults.buttonColors(containerColor = colors.accent),
            contentPadding = PaddingValues(horizontal = 14.dp, vertical = 8.dp),
        ) { text() }
    } else {
        OutlinedButton(
            onClick = onClick,
            colors = ButtonDefaults.outlinedButtonColors(contentColor = colors.text),
            contentPadding = PaddingValues(horizontal = 14.dp, vertical = 8.dp),
        ) { text() }
    }
}
