package dev.yury.mathmark

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.File

/**
 * Те же проверки, что и у настольной версии, и без единого обращения в сеть:
 * вместо GitHub — заглушка, держащая файлы в памяти.
 */
class SyncTest {

    @get:Rule
    val tmp = TemporaryFolder()

    private class FakeRemote(files: Map<String, String> = emptyMap()) : Remote {
        val files = HashMap(files)
        val log = ArrayList<String>()
        var problem: String? = null

        override fun check(): String? = problem
        override fun tree(): Map<String, String> =
            files.mapValues { (p, t) -> "sha-$p-${t.length}" }

        override fun read(path: String): String = files.getValue(path)

        override fun write(path: String, text: String, sha: String?, message: String): String {
            files[path] = text
            log.add("write $path")
            return "sha-$path-${text.length}"
        }

        override fun remove(path: String, sha: String, message: String) {
            files.remove(path)
            log.add("remove $path")
        }
    }

    private lateinit var folder: File
    private lateinit var state: File

    private fun setup(remoteFiles: Map<String, String> = emptyMap()): Pair<Sync, FakeRemote> {
        folder = tmp.newFolder("math")
        state = tmp.newFolder("state")
        val remote = FakeRemote(remoteFiles)
        return Sync(folder, state, remote, "телефон") to remote
    }

    private fun write(rel: String, text: String) {
        val p = File(folder, rel)
        p.parentFile?.mkdirs()
        p.writeText(text, Charsets.UTF_8)
    }

    private fun read(rel: String) = File(folder, rel).readText(Charsets.UTF_8)

    @Test
    fun `новый свой файл уезжает`() {
        val (sync, remote) = setup()
        write("шпора.md", "- [ ] раз\n")

        val r = sync.run()
        assertEquals(listOf("шпора.md"), r.uploaded)
        assertEquals("- [ ] раз\n", remote.files["шпора.md"])
    }

    @Test
    fun `новый чужой файл приезжает`() {
        val (sync, _) = setup(mapOf("линал.md" to "- ( ) Ряды\n"))

        val r = sync.run()
        assertEquals(listOf("линал.md"), r.downloaded)
        assertEquals("- ( ) Ряды\n", read("линал.md"))
    }

    @Test
    fun `вложенные папки переносятся`() {
        val (sync, remote) = setup()
        write("Линал/собственные.md", "- [ ] раз\n")

        sync.run()
        assertTrue(remote.files.containsKey("Линал/собственные.md"))
    }

    @Test
    fun `отметки с двух сторон сводятся`() {
        val (sync, remote) = setup()
        write("ф.md", "- [ ] раз\n- ( ) два\n")
        sync.run()

        write("ф.md", "- [x] раз\n- ( ) два\n")
        remote.files["ф.md"] = "- [ ] раз\n- (x) два\n"

        val r = sync.run()
        assertEquals(listOf("ф.md"), r.merged)
        assertEquals("- [x] раз\n- (x) два\n", read("ф.md"))
        assertEquals("- [x] раз\n- (x) два\n", remote.files["ф.md"])
    }

    @Test
    fun `спор об отметке решается в пользу продвинутого`() {
        val (sync, remote) = setup()
        write("ф.md", "- [ ] раз\n")
        sync.run()

        write("ф.md", "- [~] раз\n")
        remote.files["ф.md"] = "- [x] раз\n"

        val r = sync.run()
        assertTrue(r.conflicts.isEmpty())
        assertEquals("- [x] раз\n", read("ф.md"))
    }

    @Test
    fun `свой файл удалён значит удаляется и там`() {
        val (sync, remote) = setup()
        write("ф.md", "- [ ] раз\n")
        sync.run()

        File(folder, "ф.md").delete()
        val r = sync.run()
        assertEquals(listOf("ф.md"), r.deletedThere)
        assertFalse(remote.files.containsKey("ф.md"))
    }

    @Test
    fun `чужой файл удалён значит удаляется и здесь`() {
        val (sync, remote) = setup()
        write("ф.md", "- [ ] раз\n")
        sync.run()

        remote.files.remove("ф.md")
        val r = sync.run()
        assertEquals(listOf("ф.md"), r.deletedHere)
        assertFalse(File(folder, "ф.md").exists())
    }

    @Test
    fun `спор о тексте ничего не теряет`() {
        val (sync, remote) = setup()
        write("ф.md", "- [ ] раз\n")
        sync.run()

        write("ф.md", "- [ ] раз по-моему\n")
        remote.files["ф.md"] = "- [ ] раз по-ихнему\n"

        val r = sync.run()
        assertEquals(listOf("ф.md"), r.conflicts)
        assertEquals("- [ ] раз по-моему\n", read("ф.md"))
        assertEquals("- [ ] раз по-ихнему\n", read("ф (спор).md"))
    }

    @Test
    fun `повторная синхронизация ничего не делает`() {
        val (sync, remote) = setup()
        write("ф.md", "- [ ] раз\n")
        sync.run()
        remote.log.clear()

        val r = sync.run()
        assertEquals(0, r.changed)
        assertTrue(remote.log.isEmpty())
    }

    @Test
    fun `беда со связью видна человеку`() {
        val (sync, remote) = setup()
        remote.problem = "ключ не подошёл"

        val r = sync.run()
        assertEquals("ключ не подошёл", r.error)
    }
}
