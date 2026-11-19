package com.jkfran.tivimatebridge;

import android.accessibilityservice.AccessibilityService;
import android.graphics.Rect;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;

import java.io.File;
import java.io.FileInputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Properties;
import java.util.regex.Pattern;

/**
 * TiviMate Channel Bridge — reads the currently playing channel (and programme) from TiviMate's
 * on-screen info bar using the Android accessibility API (no root) and POSTs it to a
 * Home Assistant webhook.
 *
 * Based on https://github.com/jkfran/tivimate-channel-bridge (MIT, (c) 2026 Fran / @jkfran).
 * Extended for LG webOS Extras: also reports the current programme, its time, the next
 * programme, the channel number and all banner texts (for tuning the heuristics).
 *
 * Payload: {"channel": "...", "number": "...", "program": "...", "program_time": "...",
 *           "next_program": "...", "texts": ["...", ...], "source": "infobar|click"}
 *
 * Config: config.properties in the app's external files dir, e.g.
 *   adb push config.properties /sdcard/Android/data/com.jkfran.tivimatebridge/files/config.properties
 * with:
 *   ha_webhook_url=http://192.168.1.10:8123/api/webhook/tivimate_channel
 *   banner_height=260   (optional, px around the badge row that belongs to the info bar)
 */
public class ChannelAccessibilityService extends AccessibilityService {

    private static final String TAG = "TiviMateBridge";
    private static final String TVIMATE_PKG = "ar.tvplayer.tv";
    private static final String DEFAULT_HA_WEBHOOK_URL =
            "http://homeassistant.local:8123/api/webhook/tivimate_channel";

    private static final Pattern FPS = Pattern.compile("(?i)\\b\\d+\\s*FPS\\b");
    private static final Pattern AUDIO = Pattern.compile("(?i)^(STEREO|MONO|DUAL|DOLBY.*|AC[-\\s]?3|E?AC3|AAC|MP2|DTS.*|\\d\\.\\d)$");
    private static final Pattern RES = Pattern.compile("(?i)^(FHD|UHD|4K|8K|HD|SD|HDR.*|\\d{3,4}p|\\d{3,4}x\\d{3,4})$");
    private static final Pattern TIME = Pattern.compile("^\\d{1,2}[:.]\\d{2}.*");
    private static final Pattern DURATION = Pattern.compile("(?i)^[+-]?\\d+\\s*(min|h|hr|m)\\b.*");
    private static final Pattern DATECLOCK = Pattern.compile("(?iu).*\\b(mon|tue|wed|thu|fri|sat|sun|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|po|ut|st|št|pi|so|ne)[,.]?\\s+\\d{1,2}\\b.*");
    private static final Pattern NOINFO = Pattern.compile("(?i)^(no information|no info|sin información|žiadne informácie|bez informácií|—|-)?$");
    private static final Pattern NUMBER = Pattern.compile("^\\d{1,5}$");
    private static final Pattern PREFIX = Pattern.compile("^\\s*[A-Z]{2,4}\\s*\\|\\s*\\S.*");
    private static final Pattern NEXT_LABEL = Pattern.compile("(?i)^(next|ďalej|ďalší|potom|následuje|neskôr)\\s*:?\\s*");

    private final Handler main = new Handler(Looper.getMainLooper());
    private volatile String lastKey = null;
    private volatile String haWebhookUrl = DEFAULT_HA_WEBHOOK_URL;
    private volatile int bannerHeight = 260;
    private long lastEventAt = 0;

    private static class Item {
        final String text; final Rect b;
        Item(String t, Rect r) { text = t.trim(); b = r; }
    }

    private static class Info {
        String channel, number, program, programTime, nextProgram, source;
        List<String> texts = new ArrayList<>();
    }

    @Override
    protected void onServiceConnected() {
        super.onServiceConnected();
        loadConfig();
        Log.i(TAG, "connected; webhook=" + haWebhookUrl + " banner_height=" + bannerHeight);
    }

    private void loadConfig() {
        try {
            File dir = getExternalFilesDir(null);
            if (dir == null) return;
            File cfg = new File(dir, "config.properties");
            if (!cfg.exists()) return;
            Properties p = new Properties();
            try (FileInputStream in = new FileInputStream(cfg)) { p.load(in); }
            String u = p.getProperty("ha_webhook_url");
            if (u != null && !u.trim().isEmpty()) haWebhookUrl = u.trim();
            String h = p.getProperty("banner_height");
            if (h != null && !h.trim().isEmpty()) bannerHeight = Integer.parseInt(h.trim());
        } catch (Throwable t) { Log.w(TAG, "config load failed: " + t); }
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        if (event == null || event.getPackageName() == null) return;
        if (!TVIMATE_PKG.contentEquals(event.getPackageName())) return;

        if (event.getEventType() == AccessibilityEvent.TYPE_VIEW_CLICKED) {
            String ch = channelFromNode(event.getSource());
            if (ch != null) {
                Info info = new Info();
                info.channel = ch;
                info.source = "click";
                reportIfNew(info);
            }
            return;
        }
        long now = System.currentTimeMillis();
        lastEventAt = now;
        // Debounce: wait until the banner has settled (programme text loads after the name).
        main.postDelayed(() -> {
            if (System.currentTimeMillis() - lastEventAt < 250) return;
            try {
                AccessibilityNodeInfo root = getRootInActiveWindow();
                if (root == null) return;
                List<Item> items = new ArrayList<>();
                collect(root, items);
                Info info = extractFromInfoBar(items);
                if (info != null) reportIfNew(info);
            } catch (Throwable t) { Log.w(TAG, "scan error", t); }
        }, 300);
    }

    private void reportIfNew(Info info) {
        if (info.channel == null || info.channel.isEmpty()) return;
        String key = info.channel + "|" + (info.program == null ? "" : info.program);
        // A click only knows the channel: don't let it erase a known programme of the same channel.
        if ("click".equals(info.source) && lastKey != null && lastKey.startsWith(info.channel + "|")) return;
        if (key.equals(lastKey)) return;
        lastKey = key;
        Log.i(TAG, "CHANNEL=" + info.channel + " PROGRAM=" + info.program + " TEXTS=" + info.texts);
        report(info);
    }

    private void collect(AccessibilityNodeInfo node, List<Item> out) {
        if (node == null) return;
        CharSequence t = node.getText();
        if (t == null || t.length() == 0) t = node.getContentDescription();
        if (t != null && t.toString().trim().length() > 0) {
            Rect r = new Rect(); node.getBoundsInScreen(r);
            out.add(new Item(t.toString(), r));
        }
        for (int i = 0; i < node.getChildCount(); i++) {
            AccessibilityNodeInfo c = node.getChild(i);
            if (c != null) { collect(c, out); c.recycle(); }
        }
    }

    private boolean isBadgeOrMeta(String s) {
        return FPS.matcher(s).find() || AUDIO.matcher(s).matches() || RES.matcher(s).matches()
                || TIME.matcher(s).matches() || DURATION.matcher(s).matches()
                || DATECLOCK.matcher(s).matches() || NOINFO.matcher(s).matches();
    }

    private boolean isChannelish(String s) {
        if (s == null) return false;
        s = s.trim();
        if (s.length() < 2 || s.length() > 60) return false;
        if (NUMBER.matcher(s).matches()) return false;
        return !isBadgeOrMeta(s);
    }

    private boolean isProgramish(String s) {
        if (s == null) return false;
        s = s.trim();
        if (s.length() < 2 || s.length() > 160) return false;
        if (NUMBER.matcher(s).matches()) return false;
        return !isBadgeOrMeta(s);
    }

    /** From a clicked (guide/list) node subtree, pick the channel name. */
    private String channelFromNode(AccessibilityNodeInfo node) {
        if (node == null) return null;
        List<Item> items = new ArrayList<>();
        collect(node, items);
        for (Item it : items) if (PREFIX.matcher(it.text).matches() && isChannelish(it.text)) return it.text;
        for (Item it : items) if (isChannelish(it.text)) return it.text;
        return null;
    }

    /** The channel name shares the row with the FPS/audio badge; the programme sits around it. */
    private Info extractFromInfoBar(List<Item> items) {
        Item anchor = null;
        for (Item it : items) if (FPS.matcher(it.text).find()) { anchor = it; break; }
        if (anchor == null)
            for (Item it : items) if (AUDIO.matcher(it.text).matches()) { anchor = it; break; }
        if (anchor == null) return null;

        int row = anchor.b.centerY();
        Item channel = null;
        for (Item it : items) {
            if (Math.abs(it.b.centerY() - row) > 40) continue;
            if (!isChannelish(it.text)) continue;
            if (channel == null || it.b.left < channel.b.left) channel = it;
        }
        if (channel == null) return null;

        Info info = new Info();
        info.channel = channel.text;
        info.source = "infobar";

        // Everything that belongs to the banner, in reading order.
        List<Item> banner = new ArrayList<>();
        for (Item it : items) if (Math.abs(it.b.centerY() - row) <= bannerHeight) banner.add(it);
        Collections.sort(banner, (a, b) -> {
            if (Math.abs(a.b.centerY() - b.b.centerY()) > 15) return Integer.compare(a.b.centerY(), b.b.centerY());
            return Integer.compare(a.b.left, b.b.left);
        });
        for (Item it : banner) info.texts.add(it.text);

        // Channel number: a bare number left of the channel name on the same row.
        for (Item it : banner) {
            if (NUMBER.matcher(it.text).matches() && Math.abs(it.b.centerY() - channel.b.centerY()) <= 40
                    && it.b.left <= channel.b.left) { info.number = it.text; break; }
        }

        // Programmes: plausible texts that are not the channel, in reading order.
        List<Item> programs = new ArrayList<>();
        for (Item it : banner) {
            if (it == channel || it.text.equals(channel.text)) continue;
            if (isProgramish(it.text)) programs.add(it);
        }
        for (Item p : programs) {
            String text = NEXT_LABEL.matcher(p.text).replaceFirst("");
            boolean isNext = !text.equals(p.text);
            if (!isNext && info.program == null) {
                info.program = text;
                info.programTime = nearestTime(banner, p);
            } else if (info.nextProgram == null && (isNext || info.program != null)) {
                info.nextProgram = text;
            }
        }
        return info;
    }

    /** The time range ("20:00 - 21:30") closest to the given programme text. */
    private String nearestTime(List<Item> banner, Item program) {
        Item best = null;
        int bestDist = Integer.MAX_VALUE;
        for (Item it : banner) {
            if (!TIME.matcher(it.text).matches()) continue;
            int d = Math.abs(it.b.centerY() - program.b.centerY()) * 3 + Math.abs(it.b.left - program.b.right);
            if (d < bestDist) { bestDist = d; best = it; }
        }
        return best == null ? null : best.text;
    }

    private static String json(String s) {
        if (s == null) return "null";
        StringBuilder sb = new StringBuilder("\"");
        for (char c : s.toCharArray()) {
            switch (c) {
                case '"': sb.append("\\\""); break;
                case '\\': sb.append("\\\\"); break;
                case '\n': sb.append("\\n"); break;
                case '\r': sb.append("\\r"); break;
                case '\t': sb.append("\\t"); break;
                default:
                    if (c < 0x20) sb.append(String.format("\\u%04x", (int) c));
                    else sb.append(c);
            }
        }
        return sb.append('"').toString();
    }

    private static String toJson(Info i) {
        StringBuilder texts = new StringBuilder("[");
        for (int n = 0; n < i.texts.size(); n++) {
            if (n > 0) texts.append(',');
            texts.append(json(i.texts.get(n)));
        }
        texts.append(']');
        return "{\"channel\":" + json(i.channel)
                + ",\"number\":" + json(i.number)
                + ",\"program\":" + json(i.program)
                + ",\"program_time\":" + json(i.programTime)
                + ",\"next_program\":" + json(i.nextProgram)
                + ",\"source\":" + json(i.source)
                + ",\"texts\":" + texts + "}";
    }

    private void report(final Info info) {
        final String url = haWebhookUrl;
        final String body = toJson(info);
        new Thread(() -> {
            HttpURLConnection c = null;
            try {
                c = (HttpURLConnection) new URL(url).openConnection();
                c.setConnectTimeout(4000); c.setReadTimeout(4000);
                c.setRequestMethod("POST"); c.setDoOutput(true);
                c.setRequestProperty("Content-Type", "application/json; charset=utf-8");
                try (OutputStream os = c.getOutputStream()) { os.write(body.getBytes("UTF-8")); }
                Log.i(TAG, "POST " + c.getResponseCode() + " " + body);
            } catch (Throwable t) { Log.w(TAG, "POST failed: " + t); }
            finally { if (c != null) c.disconnect(); }
        }).start();
    }

    @Override public void onInterrupt() { }
}
