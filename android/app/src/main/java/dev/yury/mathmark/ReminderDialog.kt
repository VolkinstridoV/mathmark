package dev.yury.mathmark

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.LocalTime

/**
 * Настройка напоминания для одного файла.
 *
 * Дня недели для «один раз» не спрашиваем: это ближайший момент, когда
 * указанное время ещё не прошло — сегодня или завтра. Календарь ради
 * такой мелочи только мешает.
 */
@OptIn(ExperimentalMaterial3Api::class, androidx.compose.foundation.layout.ExperimentalLayoutApi::class)
@Composable
fun ReminderDialog(
    fileName: String,
    existing: Reminder?,
    colors: MathMarkColors,
    onCancel: () -> Unit,
    onSave: (Reminder) -> Unit,
) {
    val start = existing?.at ?: LocalTime.of(19, 0)
    val timeState = rememberTimePickerState(start.hour, start.minute, true)
    var repeat by remember { mutableStateOf(existing?.repeat ?: Repeat.DAILY) }
    var weekday by remember { mutableIntStateOf(existing?.weekday?.takeIf { it in 1..7 } ?: 1) }
    var text by remember { mutableStateOf(existing?.text ?: "") }

    AlertDialog(
        onDismissRequest = onCancel,
        containerColor = colors.sheet,
        title = { Text(L["rem.title"], color = colors.text) },
        text = {
            Column(Modifier.fillMaxWidth()) {
                OutlinedTextField(
                    value = text,
                    onValueChange = { text = it },
                    label = { Text(L["rem.text"], color = colors.dim) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedTextColor = colors.text,
                        unfocusedTextColor = colors.text,
                        focusedBorderColor = colors.accent,
                        unfocusedBorderColor = colors.divider,
                        cursorColor = colors.accent,
                    ),
                )
                Spacer(Modifier.height(14.dp))

                Text(L["rem.repeat"], color = colors.dim, style = MaterialTheme.typography.labelLarge)
                Spacer(Modifier.height(6.dp))
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Chip(L["rem.daily"], repeat == Repeat.DAILY, colors) { repeat = Repeat.DAILY }
                    Chip(L["rem.weekly"], repeat == Repeat.WEEKLY, colors) { repeat = Repeat.WEEKLY }
                    Chip(L["rem.once"], repeat == Repeat.ONCE, colors) { repeat = Repeat.ONCE }
                }

                if (repeat == Repeat.WEEKLY) {
                    Spacer(Modifier.height(10.dp))
                    FlowRow(
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                        verticalArrangement = Arrangement.spacedBy(6.dp),
                    ) {
                        (1..7).forEach { d ->
                            Chip(L["rem.day$d"].take(2), weekday == d, colors) { weekday = d }
                        }
                    }
                }

                Spacer(Modifier.height(14.dp))
                TimeInput(state = timeState)
            }
        },
        confirmButton = {
            TextButton(onClick = {
                val at = LocalTime.of(timeState.hour, timeState.minute)
                val on = if (repeat == Repeat.ONCE) {
                    val today = LocalDate.now()
                    if (LocalDateTime.of(today, at).isAfter(LocalDateTime.now())) today
                    else today.plusDays(1)
                } else null
                onSave(
                    Reminder(
                        path = fileName,
                        repeat = repeat,
                        at = at,
                        text = text.trim(),
                        weekday = if (repeat == Repeat.WEEKLY) weekday else 0,
                        on = on,
                    )
                )
            }) { Text(L["common.done"], color = colors.accent) }
        },
        dismissButton = {
            TextButton(onClick = onCancel) { Text(L["common.cancel"], color = colors.dim) }
        },
    )
}

@Composable
private fun Chip(label: String, on: Boolean, colors: MathMarkColors, onClick: () -> Unit) {
    if (on) {
        Button(
            onClick = onClick,
            colors = ButtonDefaults.buttonColors(containerColor = colors.accent),
            contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp),
        ) { Text(label, maxLines = 1) }
    } else {
        OutlinedButton(
            onClick = onClick,
            colors = ButtonDefaults.outlinedButtonColors(contentColor = colors.text),
            contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp),
        ) { Text(label, maxLines = 1) }
    }
}
