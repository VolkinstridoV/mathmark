package dev.yury.mathmark

import android.util.Base64
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

/**
 * Синхронизация папки с математикой через GitHub.
 *
 * Обычное сетевое обращение, без git внутри приложения. Правила один в один
 * повторяют `sync.py` настольной версии — вплоть до тех же проверок.
 *
 * Рядом с настройками лежит теневая копия того, что было при прошлой
 * синхронизации. Она нужна, чтобы понимать, кто что менял, а не просто
 * затирать чужое своим.
 */

/** Что произошло за одну синхронизацию. */
data class SyncReport(
    val uploaded: MutableList<String> = mutableListOf(),
    val downloaded: MutableList<String> = mutableListOf(),
    val merged: MutableList<String> = mutableListOf(),
    val deletedHere: MutableList<String> = mutableListOf(),
    val deletedThere: MutableList<String> = mutableListOf(),
    val conflicts: MutableList<String> = mutableListOf(),
    var error: String? = null,
) {
    val changed: Int
        get() = uploaded.size + downloaded.size + merged.size + deletedHere.size + deletedThere.size
}

/** То, что умеет удалённая сторона. Отдельно — чтобы подменять в тестах. */
interface Remote {
    /** null, если всё хорошо; иначе понятное человеку описание беды. */
    fun check(): String?
    fun tree(): Map<String, String>
    fun read(path: String): String
    fun write(path: String, text: String, sha: String?, message: String): String
    fun remove(path: String, sha: String, message: String)
}

class GitHub(repo: String, token: String, branch: String = "main") : Remote {

    private val repo = repo.trim().trim('/')
    private val token = token.trim()
    private val branch = branch.ifBlank { "main" }

    private fun call(method: String, path: String, body: JSONObject? = null): String {
        val conn = (URL("$API$path").openConnection() as HttpURLConnection).apply {
            requestMethod = method
            setRequestProperty("Authorization", "Bearer $token")
            setRequestProperty("Accept", "application/vnd.github+json")
            setRequestProperty("X-GitHub-Api-Version", "2022-11-28")
            connectTimeout = 20_000
            readTimeout = 30_000
        }
        if (body != null) {
            conn.doOutput = true
            conn.setRequestProperty("Content-Type", "application/json")
            conn.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
        }
        val code = conn.responseCode
        val text = (if (code in 200..299) conn.inputStream else conn.errorStream)
            ?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
        conn.disconnect()
        if (code !in 200..299) throw HttpFail(code, text)
        return text
    }

    class HttpFail(val code: Int, val body: String) : Exception("GitHub ответил $code")

    override fun check(): String? = try {
        call("GET", "/repos/$repo")
        null
    } catch (e: HttpFail) {
        when (e.code) {
            401 -> L["sync.badToken"]
            404 -> L["sync.noRepo"]
            else -> L.f("sync.httpError", e.code)
        }
    } catch (e: Exception) {
        L.f("sync.noNetwork", e.message ?: "")
    }

    override fun tree(): Map<String, String> {
        val raw = try {
            call("GET", "/repos/$repo/git/trees/$branch?recursive=1")
        } catch (e: HttpFail) {
            if (e.code == 409 || e.code == 404) return emptyMap()   // репозиторий пуст
            throw e
        }
        val arr = JSONObject(raw).optJSONArray("tree") ?: return emptyMap()
        val out = HashMap<String, String>()
        for (i in 0 until arr.length()) {
            val n = arr.getJSONObject(i)
            val p = n.optString("path")
            if (n.optString("type") == "blob" && p.endsWith(".md", true)) {
                out[p] = n.optString("sha")
            }
        }
        return out
    }

    override fun read(path: String): String {
        val raw = call("GET", "/repos/$repo/contents/${enc(path)}?ref=$branch")
        val b64 = JSONObject(raw).optString("content").replace("\n", "")
        return String(Base64.decode(b64, Base64.DEFAULT), Charsets.UTF_8)
    }

    override fun write(path: String, text: String, sha: String?, message: String): String {
        val body = JSONObject()
            .put("message", message)
            .put("content", Base64.encodeToString(text.toByteArray(Charsets.UTF_8), Base64.NO_WRAP))
            .put("branch", branch)
        if (sha != null) body.put("sha", sha)
        val raw = call("PUT", "/repos/$repo/contents/${enc(path)}", body)
        return JSONObject(raw).optJSONObject("content")?.optString("sha").orEmpty()
    }

    override fun remove(path: String, sha: String, message: String) {
        call(
            "DELETE", "/repos/$repo/contents/${enc(path)}",
            JSONObject().put("message", message).put("sha", sha).put("branch", branch),
        )
    }

    private fun enc(path: String): String =
        path.split("/").joinToString("/") { URLEncoder.encode(it, "UTF-8").replace("+", "%20") }

    companion object {
        private const val API = "https://api.github.com"
    }
}

class Sync(
    private val folder: File,
    stateDir: File,
    private val remote: Remote,
    private val device: String = "телефон",
) {
    private val baseDir = File(stateDir, "base")

    // ——— теневая копия ———

    private fun basePath(rel: String) = File(baseDir, rel)

    private fun baseRead(rel: String): String? =
        runCatching { basePath(rel).readText(Charsets.UTF_8) }.getOrNull()

    private fun baseWrite(rel: String, text: String) {
        val p = basePath(rel)
        p.parentFile?.mkdirs()
        runCatching { p.writeText(text, Charsets.UTF_8) }
    }

    private fun baseDrop(rel: String) {
        runCatching { basePath(rel).delete() }
    }

    // ——— свои файлы ———

    private fun localFiles(): Map<String, String> {
        val out = HashMap<String, String>()
        fun walk(dir: File) {
            dir.listFiles()?.forEach { f ->
                if (f.name.startsWith(".")) return@forEach
                if (f.isDirectory) walk(f)
                else if (f.name.endsWith(".md", true)) {
                    val rel = f.path.removePrefix(folder.path).trimStart('/')
                    runCatching { out[rel] = f.readText(Charsets.UTF_8) }
                }
            }
        }
        walk(folder)
        return out
    }

    private fun writeLocal(rel: String, text: String) {
        val p = File(folder, rel)
        p.parentFile?.mkdirs()
        runCatching { p.writeText(text, Charsets.UTF_8) }
    }

    // ——— главное ———

    fun run(): SyncReport {
        val r = SyncReport()
        remote.check()?.let { r.error = it; return r }

        val tree: Map<String, String>
        val local: Map<String, String>
        try {
            tree = remote.tree()
            local = localFiles()
        } catch (e: Exception) {
            r.error = e.message
            return r
        }

        for (rel in (local.keys + tree.keys).sorted()) {
            try {
                one(rel, local[rel], tree[rel], r)
            } catch (e: Exception) {
                r.error = "$rel: ${e.message}"
                return r
            }
        }
        return r
    }

    private fun one(rel: String, mine: String?, remoteSha: String?, r: SyncReport) {
        val base = baseRead(rel)
        val theirs = if (remoteSha != null) remote.read(rel) else null
        val msg = "MathMark: $device"

        if (mine == null) {
            if (base != null && theirs != null && theirs == base) {
                remote.remove(rel, remoteSha!!, msg)
                baseDrop(rel)
                r.deletedThere.add(rel)
            } else if (theirs != null) {
                writeLocal(rel, theirs)
                baseWrite(rel, theirs)
                r.downloaded.add(rel)
            }
            return
        }

        if (theirs == null) {
            if (base != null) {
                File(folder, rel).delete()
                baseDrop(rel)
                r.deletedHere.add(rel)
            } else {
                remote.write(rel, mine, null, msg)
                baseWrite(rel, mine)
                r.uploaded.add(rel)
            }
            return
        }

        val (text, conflict) = Merge.merge(base, mine, theirs)
        if (conflict) {
            writeLocal(rel.removeSuffix(".md") + " (спор).md", theirs)
            r.conflicts.add(rel)
            return
        }

        if (text != mine) writeLocal(rel, text)
        if (text != theirs) remote.write(rel, text, remoteSha, msg)
        baseWrite(rel, text)

        when {
            text != mine && text != theirs -> r.merged.add(rel)
            text != mine -> r.downloaded.add(rel)
            text != theirs -> r.uploaded.add(rel)
        }
    }
}
