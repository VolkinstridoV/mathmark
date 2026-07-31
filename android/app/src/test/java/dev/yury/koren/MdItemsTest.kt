package dev.yury.koren

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class MdItemsTest {

    private val sample = """
        # Шпора

        ## Пределы

        - [ ] Вывести производную ${'$'}f(x)=\sqrt{x^3}${'$'}
        - [x] Разобрать эпсилон-дельта
        - [~] Предел по двум переменным

        ## Темы

        - ( ) Ряды Фурье
        - (x) Кратные интегралы

        Просто строка, не задача.
        - обычный пункт списка
    """.trimIndent()

    @Test
    fun `находит задачи и темы, различая скобки`() {
        val items = MdItems.items(sample)
        assertEquals(5, items.size)
        assertEquals(3, items.count { it.kind == Kind.TASK })
        assertEquals(2, items.count { it.kind == Kind.TOPIC })
    }

    @Test
    fun `читает три состояния`() {
        val items = MdItems.items(sample)
        assertEquals(Mark.NONE, items[0].mark)
        assertEquals(Mark.DONE, items[1].mark)
        assertEquals(Mark.HALF, items[2].mark)
    }

    @Test
    fun `обычный список и текст задачами не считаются`() {
        assertFalse(MdItems.isItem("- обычный пункт списка"))
        assertFalse(MdItems.isItem("Просто строка, не задача."))
        assertFalse(MdItems.isItem("## Заголовок"))
    }

    @Test
    fun `несовпадающие скобки не считаются отметкой`() {
        assertFalse(MdItems.isItem("- [ ) кривая строка"))
        assertFalse(MdItems.isItem("- ( ] кривая строка"))
    }

    @Test
    fun `отметка меняет ровно один байт в UTF-8`() {
        val before = sample
        val item = MdItems.items(before).first()
        val after = MdItems.cycle(before, item.boxOffset)

        val a = before.toByteArray(Charsets.UTF_8)
        val b = after.toByteArray(Charsets.UTF_8)
        assertEquals("длина файла обязана сохраниться", a.size, b.size)

        var diff = 0
        for (i in a.indices) if (a[i] != b[i]) diff++
        assertEquals("отличаться должен ровно один байт", 1, diff)
    }

    @Test
    fun `состояния идут по кругу`() {
        var text = "- [ ] дело"
        val off = MdItems.items(text).first().boxOffset

        text = MdItems.cycle(text, off)
        assertEquals("- [~] дело", text)
        text = MdItems.cycle(text, off)
        assertEquals("- [x] дело", text)
        text = MdItems.cycle(text, off)
        assertEquals("- [ ] дело", text)
    }

    @Test
    fun `у тем состояния переключаются так же`() {
        var text = "- ( ) Ряды Фурье"
        val off = MdItems.items(text).first().boxOffset
        text = MdItems.cycle(text, off)
        assertEquals("- (~) Ряды Фурье", text)
        text = MdItems.cycle(text, off)
        assertEquals("- (x) Ряды Фурье", text)
    }

    @Test
    fun `порядок строк и отступы не меняются`() {
        val before = "  - [ ] с отступом\n\n\n- [x] после пустых строк\n"
        val after = MdItems.cycle(before, MdItems.items(before)[1].boxOffset)
        assertEquals(before.split("\n").size, after.split("\n").size)
        assertEquals("  - [ ] с отступом", after.split("\n")[0])
        assertTrue(after.endsWith("\n"))
    }

    @Test
    fun `одинаковые строки не путаются между собой`() {
        val text = "- [ ] одно и то же\n- [ ] одно и то же\n"
        val second = MdItems.items(text)[1]
        val after = MdItems.cycle(text, second.boxOffset)
        assertEquals("- [ ] одно и то же", after.split("\n")[0])
        assertEquals("- [~] одно и то же", after.split("\n")[1])
    }

    @Test
    fun `вид файла определяется содержимым`() {
        assertEquals(FileKind.BOTH, MdItems.counts(sample).kind)
        assertEquals(FileKind.TASKS, MdItems.counts("- [ ] раз\n- [x] два").kind)
        assertEquals(FileKind.TOPICS, MdItems.counts("- ( ) раз").kind)
        assertEquals(FileKind.PLAIN, MdItems.counts("# Шпора\n\n## Ряды\n\nтекст").kind)
    }

    @Test
    fun `половинка считается за половину`() {
        val c = MdItems.counts("- [x] раз\n- [~] два\n- [ ] три\n- [ ] четыре")
        assertEquals(1.5f / 4f, c.progress, 0.0001f)
    }

    @Test
    fun `подпись склоняет разделы по-русски`() {
        assertEquals("1 раздел", MdItems.subtitle(MdItems.counts("## а")))
        assertEquals("2 раздела", MdItems.subtitle(MdItems.counts("## а\n## б")))
        assertEquals("5 разделов", MdItems.subtitle(MdItems.counts("## а\n".repeat(5))))
        assertEquals("11 разделов", MdItems.subtitle(MdItems.counts("## а\n".repeat(11))))
    }

    @Test
    fun `формулы с долларами и скобками не ломают разбор`() {
        val text = "- [ ] Посчитать ${'$'}\\int_0^1 (x+1)\\,dx${'$'} и ${'$'}[a,b]${'$'}"
        val items = MdItems.items(text)
        assertEquals(1, items.size)
        assertEquals(Kind.TASK, items[0].kind)
        assertTrue(items[0].label.contains("\\int"))
    }
}
