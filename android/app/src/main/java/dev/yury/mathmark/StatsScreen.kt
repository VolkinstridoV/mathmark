package dev.yury.mathmark

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import java.io.File

/**
 * Экран «сколько сделано». Считается по журналу отметок, а не по содержимому
 * файлов: файл показывает, что сделано, журнал — когда.
 */
@Composable
fun StatsScreen(colors: MathMarkColors, onBack: () -> Unit) {
    val ctx = LocalContext.current
    val stats by remember {
        mutableStateOf(
            Journal.summarise(
                Journal.parse(
                    runCatching { File(ctx.filesDir, "journal.log").readText() }.getOrDefault("")
                )
            )
        )
    }

    BackHandler { onBack() }

    Column(Modifier.fillMaxSize()) {
        Bar(colors, L["stats.title"], left = { IconBtn("‹") { onBack() } })

        val empty = stats.monthTasks == 0 && stats.monthTopics == 0 && stats.streak == 0
        if (empty) {
            Box(Modifier.fillMaxSize().padding(34.dp), contentAlignment = Alignment.Center) {
                Text(L["stats.empty"], color = colors.dim, style = MaterialTheme.typography.bodyLarge)
            }
            return@Column
        }

        Column(Modifier.verticalScroll(rememberScrollState()).padding(bottom = 40.dp)) {
            Row(
                Modifier.fillMaxWidth().padding(16.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                Tile(L["stats.today"], stats.todayTasks, stats.todayTopics, colors, Modifier.weight(1f))
                Tile(L["stats.week"], stats.weekTasks, stats.weekTopics, colors, Modifier.weight(1f))
            }
            Row(
                Modifier.fillMaxWidth().padding(start = 16.dp, end = 16.dp, bottom = 16.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                Tile(L["stats.month"], stats.monthTasks, stats.monthTopics, colors, Modifier.weight(1f))
                StreakTile(stats.streak, colors, Modifier.weight(1f))
            }

            Text(
                L["stats.last30"],
                Modifier.padding(start = 18.dp, top = 8.dp, bottom = 10.dp),
                color = colors.accent,
                style = MaterialTheme.typography.labelMedium,
            )
            Bars(stats, colors)
        }
    }
}

@Composable
private fun Tile(title: String, tasks: Int, topics: Int, colors: MathMarkColors, mod: Modifier) {
    Column(
        mod
            .clip(RoundedCornerShape(14.dp))
            .background(colors.sheet)
            .padding(14.dp)
    ) {
        Text(title, color = colors.dim, style = MaterialTheme.typography.labelMedium)
        Spacer(Modifier.height(8.dp))
        Text(
            "${tasks + topics}",
            color = colors.text,
            style = MaterialTheme.typography.headlineMedium,
        )
        Spacer(Modifier.height(4.dp))
        Text(
            L.f("stats.tasks", tasks) + " · " + L.f("stats.topics", topics),
            color = colors.dim,
            style = MaterialTheme.typography.bodySmall,
        )
    }
}

@Composable
private fun StreakTile(days: Int, colors: MathMarkColors, mod: Modifier) {
    Column(
        mod
            .clip(RoundedCornerShape(14.dp))
            .background(Brush.linearGradient(colors.gradient))
            .padding(14.dp)
    ) {
        Text(
            L["stats.streak"],
            color = androidx.compose.ui.graphics.Color.White.copy(alpha = 0.85f),
            style = MaterialTheme.typography.labelMedium,
        )
        Spacer(Modifier.height(8.dp))
        Text(
            "$days",
            color = androidx.compose.ui.graphics.Color.White,
            style = MaterialTheme.typography.headlineMedium,
        )
        Spacer(Modifier.height(4.dp))
        Text(
            L.f("days." + MdItems.pluralForm(days, L.current), days),
            color = androidx.compose.ui.graphics.Color.White.copy(alpha = 0.85f),
            style = MaterialTheme.typography.bodySmall,
        )
    }
}

/** Столбики по дням: видно, где работал, а где пропал. */
@Composable
private fun Bars(stats: Stats, colors: MathMarkColors) {
    val top = (stats.perDay.maxOfOrNull { it.second } ?: 0).coerceAtLeast(1)
    Row(
        Modifier
            .fillMaxWidth()
            .height(96.dp)
            .padding(horizontal = 16.dp),
        horizontalArrangement = Arrangement.spacedBy(3.dp),
        verticalAlignment = Alignment.Bottom,
    ) {
        stats.perDay.forEach { (_, n) ->
            Box(
                Modifier
                    .weight(1f)
                    .fillMaxHeight(if (n == 0) 0.04f else (n.toFloat() / top).coerceAtLeast(0.12f))
                    .clip(RoundedCornerShape(3.dp))
                    .background(if (n == 0) colors.divider else colors.accent)
            )
        }
    }
}
