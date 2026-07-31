package dev.yury.koren

import androidx.activity.compose.BackHandler
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
 * Настройки. Всё, что здесь меняется, ложится в `koren.conf` обычным текстом —
 * то же самое можно сделать правкой файла из терминала.
 */
@Composable
fun SettingsScreen(
    settings: Settings,
    colors: KorenColors,
    theme: String,
    scale: Float,
    folder: String,
    onTheme: (String) -> Unit,
    onScale: (Float) -> Unit,
    onFolder: (String) -> Unit,
    onBack: () -> Unit,
) {
    val ctx = LocalContext.current
    var typing by remember { mutableStateOf(false) }

    BackHandler { onBack() }
    var live by remember(scale) { mutableFloatStateOf(scale) }

    val picker = rememberFolderPicker { path ->
        if (path != null) onFolder(path)
        else Toast.makeText(
            ctx,
            "Такую папку не получилось развернуть в путь — впиши вручную",
            Toast.LENGTH_LONG,
        ).show()
    }

    Column(Modifier.fillMaxSize()) {
        Bar(colors, "Настройки", left = { IconBtn("‹") { onBack() } })

        Column(Modifier.verticalScroll(rememberScrollState()).padding(bottom = 40.dp)) {

            Group("Файлы", colors)
            Item("Папка", folder, colors) { picker.launch(folderPickIntent()) }
            Item(
                "Вписать путь вручную",
                "если папка на карте памяти",
                colors,
            ) { typing = true }
            Item(
                "Что показывается",
                "только файлы .md и вложенные папки",
                colors,
                clickable = false,
            )

            Group("Вид", colors)
            Column(Modifier.padding(horizontal = 18.dp, vertical = 12.dp)) {
                Text("Размер текста", color = colors.text, style = MaterialTheme.typography.titleSmall)
                Text(
                    "формулы тянутся вместе с текстом",
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
                Text("Тема", color = colors.text, style = MaterialTheme.typography.titleSmall)
                Spacer(Modifier.height(10.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Choice("как в системе", theme == "auto", colors) { onTheme("auto") }
                    Choice("светлая", theme == "light", colors) { onTheme("light") }
                    Choice("тёмная", theme == "dark", colors) { onTheme("dark") }
                }
            }
            HorizontalDivider(color = colors.divider)

            Group("Для нейросети", colors)
            Item(
                "Скопировать промпт",
                "инструкция, как писать файлы для этого приложения",
                colors,
            ) {
                copyToClipboard(ctx, "Промпт «Корень»", Prompt.TEXT)
                Toast.makeText(ctx, "Промпт в буфере обмена", Toast.LENGTH_SHORT).show()
            }
            Item(
                "Запрос из терминала",
                "content query --uri content://dev.yury.koren/prompt",
                colors,
            ) {
                copyToClipboard(
                    ctx,
                    "Запрос",
                    "content query --uri content://dev.yury.koren/prompt",
                )
                Toast.makeText(ctx, "Команда в буфере обмена", Toast.LENGTH_SHORT).show()
            }

            Group("О программе", colors)
            Row(
                Modifier.fillMaxWidth().padding(18.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                RootMark(colors, 54.dp)
                Spacer(Modifier.width(14.dp))
                Column {
                    Text("Корень 1.0", color = colors.text, style = MaterialTheme.typography.titleMedium)
                    Text(
                        "формулы рисует KaTeX, интернет не нужен",
                        color = colors.dim,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            }
        }
    }

    if (typing) {
        NameDialog(
            title = "Путь к папке",
            initial = folder,
            colors = colors,
            onCancel = { typing = false },
            onOk = { onFolder(it.trim()); typing = false },
        )
    }
}

@Composable
private fun Group(title: String, colors: KorenColors) {
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
    colors: KorenColors,
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
private fun Choice(label: String, on: Boolean, colors: KorenColors, onClick: () -> Unit) {
    if (on) {
        Button(
            onClick = onClick,
            colors = ButtonDefaults.buttonColors(containerColor = colors.accent),
        ) { Text(label) }
    } else {
        OutlinedButton(
            onClick = onClick,
            colors = ButtonDefaults.outlinedButtonColors(contentColor = colors.text),
        ) { Text(label) }
    }
}
