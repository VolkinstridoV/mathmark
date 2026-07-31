package dev.yury.koren

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

/**
 * Значок строки списка. Рисуется, а не берётся картинкой, — чтобы совпадать
 * с цветами темы и не тащить четыре png на каждую плотность экрана.
 *
 *   задачи          скруглённый квадрат с галочкой   — как `[ ]`
 *   темы            круг с галочкой                  — как `( )`
 *   и то и другое   квадрат и круг внахлёст
 *   ни то ни то     закладка (шпора, справочник)
 *   папка           папка
 */

@Composable
fun KindGlyph(kind: FileKind, colors: KorenColors, size: Dp = 42.dp) {
    Canvas(Modifier.size(size)) {
        plate(colors, deeper = kind == FileKind.PLAIN)
        val s = this.size.minDimension
        when (kind) {
            FileKind.TASKS -> {
                square(center = Offset(s / 2, s / 2), side = s * 0.44f, stroke = s * 0.075f)
                check(center = Offset(s / 2, s / 2), w = s * 0.26f, stroke = s * 0.085f)
            }
            FileKind.TOPICS -> {
                drawCircle(
                    color = Color.White, radius = s * 0.23f, center = Offset(s / 2, s / 2),
                    style = Stroke(width = s * 0.075f)
                )
                check(center = Offset(s / 2, s / 2), w = s * 0.24f, stroke = s * 0.085f)
            }
            FileKind.BOTH -> {
                square(center = Offset(s * 0.40f, s * 0.40f), side = s * 0.38f, stroke = s * 0.07f)
                drawCircle(
                    color = Color.White, radius = s * 0.20f, center = Offset(s * 0.62f, s * 0.62f),
                    style = Stroke(width = s * 0.07f)
                )
            }
            FileKind.PLAIN -> bookmark(s)
        }
    }
}

@Composable
fun FolderGlyph(colors: KorenColors, size: Dp = 42.dp) {
    Canvas(Modifier.size(size)) {
        plate(colors, deeper = true)
        val s = this.size.minDimension
        val p = Path().apply {
            moveTo(s * 0.24f, s * 0.68f)
            lineTo(s * 0.24f, s * 0.34f)
            lineTo(s * 0.44f, s * 0.34f)
            lineTo(s * 0.51f, s * 0.42f)
            lineTo(s * 0.76f, s * 0.42f)
            lineTo(s * 0.76f, s * 0.68f)
            close()
        }
        drawPath(p, Color.White, style = Stroke(width = s * 0.075f, join = StrokeJoin.Round))
    }
}

/** Фиолетовая подложка. Справочник и папки чуть темнее — так список читается взглядом. */
private fun DrawScope.plate(colors: KorenColors, deeper: Boolean) {
    val s = size.minDimension
    val brush = if (deeper) {
        Brush.linearGradient(listOf(colors.accent, Color(0xFF4C1D95)))
    } else {
        Brush.linearGradient(listOf(colors.accent2, colors.accent))
    }
    drawRoundRect(
        brush = brush,
        cornerRadius = androidx.compose.ui.geometry.CornerRadius(s * 0.30f, s * 0.30f),
    )
}

private fun DrawScope.square(center: Offset, side: Float, stroke: Float) {
    val half = side / 2
    drawRoundRect(
        color = Color.White,
        topLeft = Offset(center.x - half, center.y - half),
        size = Size(side, side),
        cornerRadius = androidx.compose.ui.geometry.CornerRadius(side * 0.22f, side * 0.22f),
        style = Stroke(width = stroke),
    )
}

private fun DrawScope.check(center: Offset, w: Float, stroke: Float) {
    val p = Path().apply {
        moveTo(center.x - w * 0.5f, center.y + w * 0.04f)
        lineTo(center.x - w * 0.12f, center.y + w * 0.42f)
        lineTo(center.x + w * 0.55f, center.y - w * 0.42f)
    }
    drawPath(p, Color.White, style = Stroke(width = stroke, cap = StrokeCap.Round, join = StrokeJoin.Round))
}

private fun DrawScope.bookmark(s: Float) {
    val p = Path().apply {
        moveTo(s * 0.34f, s * 0.26f)
        lineTo(s * 0.66f, s * 0.26f)
        lineTo(s * 0.66f, s * 0.74f)
        lineTo(s * 0.50f, s * 0.60f)
        lineTo(s * 0.34f, s * 0.74f)
        close()
    }
    drawPath(p, Color.White, style = Stroke(width = s * 0.075f, join = StrokeJoin.Round))
}

/** Значок самого приложения — корень из икс. Используется на экране «о программе». */
@Composable
fun RootMark(colors: KorenColors, size: Dp = 64.dp) {
    Canvas(Modifier.size(size)) {
        plate(colors, deeper = false)
        val s = this.size.minDimension
        val p = Path().apply {
            moveTo(s * 0.19f, s * 0.54f)
            lineTo(s * 0.28f, s * 0.54f)
            lineTo(s * 0.37f, s * 0.74f)
            lineTo(s * 0.51f, s * 0.28f)
            lineTo(s * 0.84f, s * 0.28f)
        }
        drawPath(
            p, Color.White,
            style = Stroke(width = s * 0.055f, cap = StrokeCap.Round, join = StrokeJoin.Round)
        )
        // палочка икса под чертой — упрощённая, чтобы читалась на мелком размере
        drawLine(
            Color.White,
            start = Offset(s * 0.58f, s * 0.44f), end = Offset(s * 0.72f, s * 0.64f),
            strokeWidth = s * 0.055f, cap = StrokeCap.Round,
        )
        drawLine(
            Color.White,
            start = Offset(s * 0.72f, s * 0.44f), end = Offset(s * 0.58f, s * 0.64f),
            strokeWidth = s * 0.055f, cap = StrokeCap.Round,
        )
    }
}
