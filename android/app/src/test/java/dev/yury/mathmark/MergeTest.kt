package dev.yury.mathmark

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Те же проверки, что и у настольной версии. Разъедутся — упадёт здесь. */
class MergeTest {

    @Test
    fun `одинаковые версии сводятся молча`() {
        val text = "- [ ] раз\n- ( ) два\n"
        val r = Merge.merge(text, text, text)
        assertEquals(text, r.text)
        assertFalse(r.conflict)
    }

    @Test
    fun `изменилась только одна сторона`() {
        val base = "- [ ] раз\n"
        assertEquals("- [x] раз\n", Merge.merge(base, "- [x] раз\n", base).text)
        assertEquals("- [x] раз\n", Merge.merge(base, base, "- [x] раз\n").text)
    }

    @Test
    fun `спор об отметке выигрывает продвинутое`() {
        val base = "- [ ] раз\n"
        val a = Merge.merge(base, "- [~] раз\n", "- [x] раз\n")
        assertEquals("- [x] раз\n", a.text)
        assertFalse(a.conflict)

        val b = Merge.merge(base, "- [x] раз\n", "- [~] раз\n")
        assertEquals("- [x] раз\n", b.text)
        assertFalse(b.conflict)
    }

    @Test
    fun `у тем то же правило`() {
        val base = "- ( ) Ряды Фурье\n"
        val r = Merge.merge(base, "- (~) Ряды Фурье\n", "- (x) Ряды Фурье\n")
        assertEquals("- (x) Ряды Фурье\n", r.text)
        assertFalse(r.conflict)
    }

    @Test
    fun `разные строки сводятся каждая по себе`() {
        val base = "- [ ] раз\n- ( ) два\n"
        val r = Merge.merge(base, "- [x] раз\n- ( ) два\n", "- [ ] раз\n- (x) два\n")
        assertEquals("- [x] раз\n- (x) два\n", r.text)
        assertFalse(r.conflict)
    }

    @Test
    fun `разошёлся текст а не отметка это спор`() {
        val base = "- [ ] раз\n"
        val r = Merge.merge(base, "- [ ] раз другой\n", "- [ ] раз третий\n")
        assertTrue(r.conflict)
        assertEquals("- [ ] раз другой\n", r.text)   // своё не теряем
    }

    @Test
    fun `разное число строк это спор`() {
        val base = "- [ ] раз\n"
        val r = Merge.merge(base, "- [ ] раз\n- [ ] два\n", "- [ ] раз\n- [ ] три\n")
        assertTrue(r.conflict)
    }

    @Test
    fun `файл появился с двух сторон с одинаковым текстом`() {
        val text = "# Шпора\n"
        val r = Merge.merge(null, text, text)
        assertEquals(text, r.text)
        assertFalse(r.conflict)
    }

    @Test
    fun `обычный текст не считается отметкой`() {
        val r = Merge.merge("просто строка\n", "строка слева\n", "строка справа\n")
        assertTrue(r.conflict)
    }
}
