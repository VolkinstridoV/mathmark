package dev.yury.mathmark

import android.app.AlarmManager
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import java.io.File
import java.time.LocalDateTime
import java.time.ZoneId

/**
 * Будильники и уведомления для напоминаний.
 *
 * Android не даёт программе просто «ждать»: время нужно отдать системному
 * будильнику, а тот разбудит приёмник. Поэтому после каждого срабатывания
 * следующее ставится заново.
 */
object Notify {

    const val CHANNEL = "reminders"
    const val ACTION = "dev.yury.mathmark.REMIND"
    const val EXTRA_PATH = "path"
    const val EXTRA_TEXT = "text"

    fun ensureChannel(ctx: Context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val nm = ctx.getSystemService(NotificationManager::class.java)
        if (nm.getNotificationChannel(CHANNEL) != null) return
        nm.createNotificationChannel(
            NotificationChannel(CHANNEL, L["rem.title"], NotificationManager.IMPORTANCE_DEFAULT)
        )
    }

    fun remindersFile(ctx: Context): File = File(ctx.filesDir, "reminders.conf")

    /**
     * Поставить будильники на ближайшее срабатывание каждого напоминания.
     * Вызывается после правки списка, после запуска и после перезагрузки.
     */
    fun scheduleAll(ctx: Context) {
        ensureChannel(ctx)
        val am = ctx.getSystemService(AlarmManager::class.java) ?: return
        val items = Reminders.load(remindersFile(ctx))
        val now = LocalDateTime.now()

        items.forEachIndexed { i, r ->
            val next = r.nextAfter(now) ?: return@forEachIndexed
            val at = next.atZone(ZoneId.systemDefault()).toInstant().toEpochMilli()
            val pi = pending(ctx, i, r)
            runCatching {
                // точное время не запрашиваем: напоминание про учёбу спокойно
                // переживёт сдвиг на несколько минут, зато не нужно особое разрешение
                am.setWindow(AlarmManager.RTC_WAKEUP, at, 5 * 60 * 1000L, pi)
            }
        }
    }

    private fun pending(ctx: Context, id: Int, r: Reminder): PendingIntent {
        val intent = Intent(ctx, AlarmReceiver::class.java).apply {
            action = ACTION
            putExtra(EXTRA_PATH, r.path)
            putExtra(EXTRA_TEXT, r.text)
        }
        return PendingIntent.getBroadcast(
            ctx, id, intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
    }

    fun show(ctx: Context, path: String, text: String) {
        ensureChannel(ctx)
        val open = Intent(ctx, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra(EXTRA_PATH, path)
        }
        val pi = PendingIntent.getActivity(
            ctx, path.hashCode(), open,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val note = NotificationCompat.Builder(ctx, CHANNEL)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle(text.ifBlank { L["rem.title"] })
            .setContentText(path.removeSuffix(".md"))
            .setContentIntent(pi)
            .setAutoCancel(true)
            .build()
        runCatching { NotificationManagerCompat.from(ctx).notify(path.hashCode(), note) }
    }
}

/** Просыпается по будильнику и после перезагрузки телефона. */
class AlarmReceiver : BroadcastReceiver() {
    override fun onReceive(ctx: Context, intent: Intent) {
        L.load(ctx, Settings(ctx).lang)
        when (intent.action) {
            Notify.ACTION -> {
                Notify.show(
                    ctx,
                    intent.getStringExtra(Notify.EXTRA_PATH).orEmpty(),
                    intent.getStringExtra(Notify.EXTRA_TEXT).orEmpty(),
                )
                Notify.scheduleAll(ctx)     // ставим следующее
            }
            Intent.ACTION_BOOT_COMPLETED -> Notify.scheduleAll(ctx)
        }
    }
}
