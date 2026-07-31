package dev.yury.koren

import java.io.File

/**
 * Папка с математикой: чтение содержимого, переходы по вложенным папкам
 * и действия над самими файлами и папками.
 *
 * Содержимое файлов приложение не переписывает — только один символ отметки,
 * и делает это [MdItems]. Здесь — работа с файловой системой.
 */

/** Строка списка: либо вложенная папка, либо файл .md. */
sealed class Entry {
    abstract val file: File
    val name: String get() = file.name

    data class Folder(override val file: File, val items: Int) : Entry()

    data class Doc(override val file: File) : Entry() {
        val title: String get() = file.name.removeSuffix(".md").removeSuffix(".MD")
    }
}

class FilesRepo(@Volatile var root: File) {

    /** Текущая папка, всегда внутри [root]. */
    @Volatile
    var cwd: File = root
        private set

    val atRoot: Boolean get() = cwd.canonicalPath == root.canonicalPath

    val rootExists: Boolean get() = root.isDirectory

    fun createRoot(): Boolean = root.isDirectory || root.mkdirs()

    fun resetToRoot() {
        cwd = root
    }

    fun enter(folder: File) {
        if (folder.isDirectory && folder.canonicalPath.startsWith(root.canonicalPath)) {
            cwd = folder
        }
    }

    fun up(): Boolean {
        if (atRoot) return false
        cwd = cwd.parentFile ?: root
        return true
    }

    /** Дорожка от корня до текущей папки: `Math / Линал`. */
    fun crumbs(): List<File> {
        val out = ArrayList<File>()
        var f: File? = cwd
        while (f != null && f.canonicalPath.startsWith(root.canonicalPath)) {
            out.add(0, f)
            if (f.canonicalPath == root.canonicalPath) break
            f = f.parentFile
        }
        return out
    }

    /**
     * Содержимое текущей папки: сначала папки, потом файлы `.md`.
     * Скрытые файлы и всё, что не `.md`, не показывается — приложение не знает
     * файлы по именам, что положил, то и появилось.
     */
    fun list(): List<Entry> {
        val all = cwd.listFiles() ?: return emptyList()
        val folders = all
            .filter { it.isDirectory && !it.name.startsWith(".") }
            .sortedBy { it.name.lowercase() }
            .map { Entry.Folder(it, countInside(it)) }
        val docs = all
            .filter { it.isFile && !it.name.startsWith(".") && it.name.endsWith(".md", true) }
            .sortedBy { it.name.lowercase() }
            .map { Entry.Doc(it) }
        return folders + docs
    }

    /** Сколько файлов и папок внутри — для подписи под именем папки. */
    private fun countInside(dir: File): Int =
        dir.listFiles()
            ?.count { !it.name.startsWith(".") && (it.isDirectory || it.name.endsWith(".md", true)) }
            ?: 0

    fun read(file: File): String =
        runCatching { file.readText(Charsets.UTF_8) }.getOrDefault("")

    /**
     * Атомарная запись: во временный файл, затем переименование.
     * Разряд батареи посреди записи не оставит обрезанный файл.
     */
    fun write(file: File, text: String): Boolean {
        val tmp = File(file.parentFile, ".${file.name}.tmp")
        return runCatching {
            tmp.writeText(text, Charsets.UTF_8)
            if (!tmp.renameTo(file)) {
                file.writeText(text, Charsets.UTF_8)
                tmp.delete()
            }
            true
        }.getOrElse {
            tmp.delete()
            false
        }
    }

    // ——— действия из шторки долгого нажатия ———

    fun createFolder(name: String): Boolean {
        val clean = safeName(name) ?: return false
        return File(cwd, clean).mkdir()
    }

    fun rename(entry: Entry, newName: String): Boolean {
        val clean = safeName(newName) ?: return false
        val target = when (entry) {
            is Entry.Folder -> File(entry.file.parentFile, clean)
            is Entry.Doc -> File(entry.file.parentFile, if (clean.endsWith(".md", true)) clean else "$clean.md")
        }
        if (target.exists()) return false
        return entry.file.renameTo(target)
    }

    /** Переместить файл в папку. Содержимое файла не трогается. */
    fun move(doc: Entry.Doc, targetDir: File): Boolean {
        if (!targetDir.isDirectory) return false
        val target = File(targetDir, doc.file.name)
        if (target.exists()) return false
        return doc.file.renameTo(target)
    }

    fun delete(entry: Entry): Boolean = when (entry) {
        is Entry.Doc -> entry.file.delete()
        is Entry.Folder -> entry.file.deleteRecursively()
    }

    /** Все файлы .md во всём дереве — для поиска. */
    fun allDocs(): List<File> {
        val out = ArrayList<File>()
        fun walk(dir: File, depth: Int) {
            if (depth > 6) return
            val kids = dir.listFiles()?.filter { !it.name.startsWith(".") } ?: return
            kids.filter { it.isFile && it.name.endsWith(".md", true) }
                .sortedBy { it.name.lowercase() }
                .forEach { out.add(it) }
            kids.filter { it.isDirectory }
                .sortedBy { it.name.lowercase() }
                .forEach { walk(it, depth + 1) }
        }
        walk(root, 0)
        return out
    }

    /**
     * Поиск по всем файлам: сначала совпадения в имени, потом в тексте.
     * Возвращает файл и строку, в которой нашлось.
     */
    fun search(query: String, limit: Int = 200): List<Pair<File, String>> {
        val q = query.trim().lowercase()
        if (q.isEmpty()) return emptyList()
        val byName = ArrayList<Pair<File, String>>()
        val byText = ArrayList<Pair<File, String>>()
        for (f in allDocs()) {
            if (f.name.lowercase().contains(q)) {
                byName.add(f to L["search.nameMatch"])
                continue
            }
            val hit = read(f).lineSequence().firstOrNull { it.lowercase().contains(q) }
            if (hit != null) byText.add(f to hit.trim().take(120))
            if (byName.size + byText.size >= limit) break
        }
        return byName + byText
    }

    /** Все папки внутри корня — для выбора, куда переместить файл. */
    fun allFolders(): List<File> {
        val out = ArrayList<File>()
        fun walk(dir: File, depth: Int) {
            if (depth > 4) return
            dir.listFiles()
                ?.filter { it.isDirectory && !it.name.startsWith(".") }
                ?.sortedBy { it.name.lowercase() }
                ?.forEach { out.add(it); walk(it, depth + 1) }
        }
        walk(root, 0)
        return out
    }

    private fun safeName(raw: String): String? {
        // пробелы в именах разрешены, косые черты — нет: они уводят из папки
        val n = raw.trim().replace(Regex("""[/\\]"""), "")
        return if (n.isEmpty() || n == "." || n == "..") null else n
    }
}
