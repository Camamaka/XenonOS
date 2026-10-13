// Xenon News - XenonOS masaustu haber widget'i (sol alt).
// - Basliktaki "Xe 54" karosuna 3 kez tiklayinca: Founders: DTA & CMK, Designer: EHA
// - Haberler BBC World RSS'ten alinir (15 dk'da bir yenilenir); habere tiklayinca tarayicida acilir.
import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import St from 'gi://St';
import Soup from 'gi://Soup';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

const FEED = 'https://feeds.bbci.co.uk/news/world/rss.xml';
const MAX_ITEMS = 5;
const REFRESH_SECONDS = 900;
const MARGIN = 28;

export default class XenonNews extends Extension {
    enable() {
        this._session = new Soup.Session({timeout: 20});
        this._items = [];
        this._timer = 0;
        this._destroyed = false;

        this._box = new St.BoxLayout({
            style_class: 'xenon-news',
            vertical: true,
            reactive: false,
        });

        // ---- baslik: [Xe 54 karosu]  XENON NEWS ----
        const header = new St.BoxLayout({style_class: 'xenon-news-header', vertical: false});
        this._tile = new St.Button({style_class: 'xenon-tile', reactive: true, can_focus: true, track_hover: true});
        const tileBox = new St.BoxLayout({vertical: true});
        tileBox.add_child(new St.Label({text: '54', style_class: 'xenon-tile-number'}));
        tileBox.add_child(new St.Label({text: 'Xe', style_class: 'xenon-tile-symbol'}));
        this._tile.set_child(tileBox);
        // 3 tikla: hem Clutter'in tiklama sayaci hem kendi zamanlayicimiz (hangisi once 3'e ulasirsa)
        this._clicks = 0;
        this._clickTimer = 0;
        // St.Button tiklamayi kendi isler: 'button-press-event' degil 'clicked' sinyali kullanilir.
        // 3 tiklama 800 ms icinde olursa kurucular gosterilir.
        this._tile.connect('clicked', () => {
            this._clicks++;
            if (this._clickTimer)
                GLib.source_remove(this._clickTimer);
            this._clickTimer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 800, () => {
                this._clicks = 0;
                this._clickTimer = 0;
                return GLib.SOURCE_REMOVE;
            });
            if (this._clicks >= 3) {
                this._clicks = 0;
                this._toggleCredits();
            }
        });
        header.add_child(this._tile);

        const titles = new St.BoxLayout({vertical: true, y_align: Clutter.ActorAlign.CENTER});
        titles.add_child(new St.Label({text: 'XENON NEWS', style_class: 'xenon-news-title'}));
        this._status = new St.Label({text: 'Loading headlines…', style_class: 'xenon-news-sub'});
        titles.add_child(this._status);
        header.add_child(titles);
        this._box.add_child(header);

        // ---- kurucular (gizli, 3 tikla acilir) ----
        this._credits = new St.Label({
            text: 'Founders: DTA & CMK\nDesigner: EHA',
            style_class: 'xenon-credits',
            visible: false,
        });
        this._box.add_child(this._credits);

        // ---- haber listesi ----
        this._list = new St.BoxLayout({vertical: true, style_class: 'xenon-news-list'});
        this._box.add_child(this._list);

        // masaustu katmani: pencerelerin altinda, duvar kagidinin ustunde
        Main.layoutManager._backgroundGroup.add_child(this._box);
        this._reposition();
        this._allocId = this._box.connect('notify::allocation', () => this._reposition());
        this._monId = Main.layoutManager.connect('monitors-changed', () => this._reposition());

        this._fetch();
        this._timer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, REFRESH_SECONDS, () => {
            this._fetch();
            return GLib.SOURCE_CONTINUE;
        });
    }

    disable() {
        this._destroyed = true;
        if (this._timer) {
            GLib.source_remove(this._timer);
            this._timer = 0;
        }
        if (this._monId) {
            Main.layoutManager.disconnect(this._monId);
            this._monId = 0;
        }
        if (this._creditsTimer) {
            GLib.source_remove(this._creditsTimer);
            this._creditsTimer = 0;
        }
        if (this._clickTimer) {
            GLib.source_remove(this._clickTimer);
            this._clickTimer = 0;
        }
        if (this._box) {
            this._box.destroy();
            this._box = null;
        }
        this._session?.abort();
        this._session = null;
    }

    _reposition() {
        if (!this._box)
            return;
        const m = Main.layoutManager.primaryMonitor;
        if (!m)
            return;
        const [, h] = this._box.get_size();
        this._box.set_position(m.x + MARGIN, Math.round(m.y + m.height - h - MARGIN));
    }

    _toggleCredits() {
        this._credits.visible = !this._credits.visible;
        Main.notify('XenonOS', 'Founders: DTA & CMK  ·  Designer: EHA');
        if (this._creditsTimer)
            GLib.source_remove(this._creditsTimer);
        if (this._credits.visible) {
            this._creditsTimer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 12, () => {
                this._creditsTimer = 0;
                if (this._credits)
                    this._credits.visible = false;
                return GLib.SOURCE_REMOVE;
            });
        }
        this._reposition();
    }

    _fetch() {
        const msg = Soup.Message.new('GET', FEED);
        msg.request_headers.append('User-Agent', 'XenonOS-News/1.0');
        this._session.send_and_read_async(msg, GLib.PRIORITY_DEFAULT, null, (session, res) => {
            if (this._destroyed)
                return;
            try {
                const bytes = session.send_and_read_finish(res);
                if (msg.get_status() !== Soup.Status.OK)
                    throw new Error(`HTTP ${msg.get_status()}`);
                const text = new TextDecoder('utf-8').decode(bytes.get_data());
                this._items = this._parse(text);
                this._render();
            } catch (e) {
                if (this._status)
                    this._status.text = 'No connection - will retry';
                console.warn(`[xenonnews] ${e.message}`);
            }
        });
    }

    _parse(xml) {
        const out = [];
        const re = /<item>([\s\S]*?)<\/item>/g;
        let m;
        while ((m = re.exec(xml)) && out.length < MAX_ITEMS) {
            const t = /<title>(?:<!\[CDATA\[)?([\s\S]*?)(?:\]\]>)?<\/title>/.exec(m[1]);
            const l = /<link>(?:<!\[CDATA\[)?([\s\S]*?)(?:\]\]>)?<\/link>/.exec(m[1]);
            if (t && l) {
                out.push({
                    title: t[1].replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#39;|&apos;/g, "'")
                        .replace(/&lt;/g, '<').replace(/&gt;/g, '>').trim(),
                    link: l[1].trim(),
                });
            }
        }
        return out;
    }

    _render() {
        if (!this._list)
            return;
        this._list.destroy_all_children();
        for (const it of this._items) {
            const b = new St.Button({style_class: 'xenon-news-item', reactive: true, can_focus: true, track_hover: true});
            const lbl = new St.Label({text: it.title, x_align: Clutter.ActorAlign.START, x_expand: true});
            lbl.clutter_text.set_line_wrap(true);
            lbl.clutter_text.set_ellipsize(0);
            lbl.clutter_text.set_line_alignment(0);
            b.x_align = Clutter.ActorAlign.FILL;
            b.set_child(lbl);
            b.connect('clicked', () => {
                try {
                    Gio.AppInfo.launch_default_for_uri(it.link, null);
                } catch (e) {
                    console.warn(`[xenonnews] cannot open link: ${e.message}`);
                }
            });
            this._list.add_child(b);
        }
        const d = new Date();
        this._status.text = `BBC World · updated ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
        this._reposition();
    }
}
