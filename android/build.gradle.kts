plugins {
    // AGP 9 умеет Kotlin сам — отдельный плагин kotlin.android не нужен
    id("com.android.application") version "9.3.1" apply false
    id("org.jetbrains.kotlin.plugin.compose") version "2.4.10" apply false
}
