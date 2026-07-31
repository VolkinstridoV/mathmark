package dev.yury.mathmark

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color

/**
 * Цвета приложения. У Галки зелёный, здесь фиолетовый — тот же строй,
 * другой оттенок.
 */
data class MathMarkColors(
    val bg: Color,
    val bar: Color,
    val text: Color,
    val dim: Color,
    val outline: Color,
    val divider: Color,
    val accent: Color,
    val accent2: Color,
    val sheet: Color,
    val codeBg: Color,
    val quote: Color,
    val danger: Color,
) {
    /** Градиент шапки и залитых кружков. */
    val gradient: List<Color> get() = listOf(accent, accent2)
}

private val DarkColors = MathMarkColors(
    bg = Color(0xFF131017),
    bar = Color(0xFF1A1622),
    text = Color(0xFFE4DFEC),
    dim = Color(0xFF9A91AC),
    outline = Color(0xFF8E85A0),
    divider = Color(0xFF292235),
    accent = Color(0xFF7C3AED),
    accent2 = Color(0xFF9333EA),
    sheet = Color(0xFF1D1826),
    codeBg = Color(0xFF1E1828),
    quote = Color(0xFF241E30),
    danger = Color(0xFFE5534B),
)

private val LightColors = MathMarkColors(
    bg = Color(0xFFFCFBFE),
    bar = Color(0xFFF3EFFA),
    text = Color(0xFF1B1720),
    dim = Color(0xFF6B6279),
    outline = Color(0xFF7A7189),
    divider = Color(0xFFE7E1F1),
    accent = Color(0xFF7C3AED),
    accent2 = Color(0xFFA855F7),
    sheet = Color(0xFFFFFFFF),
    codeBg = Color(0xFFF3EFFA),
    quote = Color(0xFFF1ECFA),
    danger = Color(0xFFC5221F),
)

val LocalMathMark = staticCompositionLocalOf { DarkColors }

@Composable
fun MathMarkTheme(theme: String, content: @Composable () -> Unit) {
    val dark = when (theme) {
        "light" -> false
        "dark" -> true
        else -> isSystemInDarkTheme()
    }
    val c = if (dark) DarkColors else LightColors
    val scheme = if (dark) {
        darkColorScheme(
            primary = c.accent2,
            onPrimary = Color.White,
            background = c.bg,
            onBackground = c.text,
            surface = c.sheet,
            onSurface = c.text,
            error = c.danger,
        )
    } else {
        lightColorScheme(
            primary = c.accent,
            onPrimary = Color.White,
            background = c.bg,
            onBackground = c.text,
            surface = c.sheet,
            onSurface = c.text,
            error = c.danger,
        )
    }
    CompositionLocalProvider(LocalMathMark provides c) {
        MaterialTheme(colorScheme = scheme, content = content)
    }
}

/** Тот же выбор, но вне Compose — нужен для страницы чтения. */
fun isDarkFor(theme: String, systemDark: Boolean): Boolean = when (theme) {
    "light" -> false
    "dark" -> true
    else -> systemDark
}
