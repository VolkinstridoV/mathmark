package dev.yury.mathmark

import android.content.ContentProvider
import android.content.ContentValues
import android.database.Cursor
import android.database.MatrixCursor
import android.net.Uri

/**
 * Приложение отдаёт инструкцию по запросу — чтобы Claude Code в Termux мог
 * получить её прямо из приложения, не роясь в его внутренностях и без рута:
 *
 *     content query --uri content://dev.yury.mathmark/prompt
 *
 * Наружу уходит только текст промпта, который и так лежит под кнопкой в
 * настройках. Ни файлов, ни папок, ни настроек через этот путь не отдаётся
 * и не меняется: [insert], [update] и [delete] ничего не делают.
 */
class PromptProvider : ContentProvider() {

    override fun onCreate(): Boolean = true

    override fun query(
        uri: Uri,
        projection: Array<out String>?,
        selection: String?,
        selectionArgs: Array<out String>?,
        sortOrder: String?,
    ): Cursor? {
        if (uri.path?.trimEnd('/') != "/prompt") return null
        val c = MatrixCursor(arrayOf("prompt"))
        c.addRow(arrayOf(Prompt.text(context ?: return null)))
        return c
    }

    override fun getType(uri: Uri): String = "text/plain"

    override fun insert(uri: Uri, values: ContentValues?): Uri? = null

    override fun update(
        uri: Uri,
        values: ContentValues?,
        selection: String?,
        selectionArgs: Array<out String>?,
    ): Int = 0

    override fun delete(uri: Uri, selection: String?, selectionArgs: Array<out String>?): Int = 0

    companion object {
        const val AUTHORITY = "dev.yury.mathmark"
    }
}
