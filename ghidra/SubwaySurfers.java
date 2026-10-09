// Plays Subway Surfers in a dockable Ghidra window so your attention span survives the pwn chall.
// Default: runs subway_ascii.py (next to this script) as `python subway_ascii.py --stream` and
// paints the ASCII frames it prints; click the window, then arrow keys / WASD to play.
// SUBWAY_MODE=video plays subway_surfers.gif (or SUBWAY_VIDEO) instead; Swing animates GIFs natively.
// SUBWAY_PYTHON overrides the Python executable. Enable "In Tool" in the Script Manager for the menu entry.
//@author alphanin9
//@category Fun
//@menupath Window.Subway Surfers

import java.awt.*;
import java.awt.event.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

import javax.swing.*;

import docking.ComponentProvider;
import docking.WindowPosition;
import ghidra.app.script.GhidraScript;
import ghidra.framework.plugintool.PluginTool;
import ghidra.util.Swing;

public class SubwaySurfers extends GhidraScript {

	private static final String NAME = "Subway Surfers";

	@Override
	protected void run() throws Exception {
		PluginTool tool = state.getTool();
		if (tool == null) {
			println("Subway Surfers needs the Ghidra GUI.");
			return;
		}
		File dir = getSourceFile().getParentFile().getFile(false);
		boolean video = "video".equalsIgnoreCase(System.getenv("SUBWAY_MODE"));
		File gif = video ? findGif(dir) : null;
		Swing.runNow(() -> {
			ComponentProvider existing = tool.getComponentProvider(NAME);
			if (existing != null) {
				tool.showComponentProvider(existing, true);
				return;
			}
			JComponent component = gif != null ? new GifPanel(gif)
					: new AsciiPanel(new File(dir, "subway_ascii.py"));
			new SubwayProvider(tool, component).setVisible(true);
		});
		println("[subway] loaded: " + (gif != null ? "video=" + gif : "ascii"));
	}

	private static File findGif(File dir) {
		String env = System.getenv("SUBWAY_VIDEO");
		if (env != null && env.toLowerCase().endsWith(".gif") && new File(env).isFile()) {
			return new File(env);
		}
		File local = new File(dir, "subway_surfers.gif");
		return local.isFile() ? local : null;
	}

	/** Something that should only burn CPU while its window is visible. */
	private interface Pausable {
		void resume();

		void pause();
	}

	private static class SubwayProvider extends ComponentProvider {
		private final JComponent component;

		SubwayProvider(PluginTool tool, JComponent component) {
			super(tool, NAME, "SubwaySurfersScript");
			this.component = component;
			setTransient(); // closing the window removes it instead of just hiding it
			setDefaultWindowPosition(WindowPosition.RIGHT);
			addToTool();
		}

		@Override
		public JComponent getComponent() {
			return component;
		}

		@Override
		public void componentShown() {
			((Pausable) component).resume();
		}

		@Override
		public void componentHidden() {
			((Pausable) component).pause();
		}
	}

	/** Runs the Python game in --stream mode, paints its frames, and forwards keys to its stdin. */
	private static class AsciiPanel extends JComponent implements Pausable {
		// Mirrors PALETTE in subway_ascii.py; escaped so the script compiles under any default encoding.
		private static final String[] CHARS = {
			"\u250c\u2500\u2510\u2502\u2592\u2593\u25d8\u2514\u252c\u2518", // trains: box drawing, shades
			"\u25cf", // coin
			"O/\\|()@", // runner
			"\u2584\u2580\u2588", // barriers: half and full blocks
			"\u2551\u2550", // rails, sleepers
			"\u00b7_" }; // gravel, jump shadow
		private static final Color[] COLORS = { new Color(0xe05a4f), new Color(0xffd23f),
			new Color(0x4fc3f7), new Color(0xff9a3c), new Color(0x6b6b6b), new Color(0x4a4a4a) };
		private static final Color HUD = Color.WHITE;
		private static final Color DEFAULT = new Color(0xc8c8c8);

		private final File script;
		private volatile String[] lines = { "", " starting python..." };
		private Process process;
		private Writer keys;
		private Font font;
		private Dimension fittedFor;
		private int cols;

		AsciiPanel(File script) {
			this.script = script;
			setOpaque(true);
			setFocusable(true);
			setPreferredSize(new Dimension(300, 500));
			addMouseListener(new MouseAdapter() {
				@Override
				public void mousePressed(MouseEvent e) {
					requestFocusInWindow();
				}
			});
			addKeyListener(new KeyAdapter() {
				@Override
				public void keyPressed(KeyEvent e) {
					String key = switch (e.getKeyCode()) {
						case KeyEvent.VK_LEFT, KeyEvent.VK_A -> "left";
						case KeyEvent.VK_RIGHT, KeyEvent.VK_D -> "right";
						case KeyEvent.VK_UP, KeyEvent.VK_W -> "up";
						case KeyEvent.VK_DOWN, KeyEvent.VK_S -> "down";
						default -> null;
					};
					if (key != null) {
						send(key);
						e.consume();
					}
				}
			});
			resume();
		}

		@Override
		public synchronized void resume() {
			if (process != null && process.isAlive()) {
				return;
			}
			if (!script.isFile()) {
				show(" subway_ascii.py not found next to", " SubwaySurfers.java");
				return;
			}
			String python = System.getenv("SUBWAY_PYTHON");
			if (python == null) {
				python = System.getProperty("os.name").startsWith("Windows") ? "python" : "python3";
			}
			try {
				ProcessBuilder pb = new ProcessBuilder(python, "-u", script.getAbsolutePath(), "--stream");
				pb.redirectErrorStream(true); // tracebacks show up in the panel
				process = pb.start();
			}
			catch (IOException e) {
				show(" couldn't start " + python + ":", " " + e.getMessage(), " set SUBWAY_PYTHON");
				return;
			}
			keys = new OutputStreamWriter(process.getOutputStream(), StandardCharsets.UTF_8);
			Process p = process;
			Thread reader = new Thread(() -> readFrames(p), "subway-ascii-reader");
			reader.setDaemon(true);
			reader.start();
		}

		@Override
		public synchronized void pause() {
			if (process != null) {
				process.destroy();
				process = null;
			}
		}

		private synchronized void send(String key) {
			try {
				if (keys != null) {
					keys.write(key + "\n");
					keys.flush();
				}
			}
			catch (IOException e) {
				// game exited; the reader thread shows why
			}
		}

		/** Frames are blocks of lines terminated by a lone form-feed line. */
		private void readFrames(Process p) {
			List<String> frame = new ArrayList<>();
			try (BufferedReader in = new BufferedReader(
				new InputStreamReader(p.getInputStream(), StandardCharsets.UTF_8))) {
				String line;
				while ((line = in.readLine()) != null) {
					if (line.equals("\f")) {
						show(frame.toArray(String[]::new));
						frame.clear();
					}
					else {
						frame.add(line);
					}
				}
			}
			catch (IOException e) {
				// destroyed by pause()
			}
			boolean current;
			synchronized (this) {
				current = process == p; // false if pause() killed it on purpose
			}
			if (current && !frame.isEmpty()) {
				frame.add(" [python exited]");
				show(frame.toArray(String[]::new));
			}
		}

		private void show(String... newLines) {
			lines = newLines;
			repaint();
		}

		/** Largest monospaced font whose character grid fits the panel. */
		private void fit(Graphics g, String[] frame) {
			int frameCols = 1;
			for (String l : frame) {
				frameCols = Math.max(frameCols, l.length());
			}
			if (font != null && getSize().equals(fittedFor) && frameCols == cols) {
				return;
			}
			Font base = new Font("Consolas", Font.PLAIN, 100);
			if (!base.getFamily().equals("Consolas")) {
				base = new Font(Font.MONOSPACED, Font.PLAIN, 100);
			}
			FontMetrics fm = g.getFontMetrics(base);
			double size = 100 * Math.min((double) getWidth() / (frameCols * fm.charWidth('M')),
				(double) getHeight() / (frame.length * fm.getHeight()));
			font = base.deriveFont((float) Math.max(4, Math.floor(size)));
			fittedFor = getSize();
			cols = frameCols;
		}

		@Override
		protected void paintComponent(Graphics g) {
			String[] frame = lines;
			g.setColor(Color.BLACK);
			g.fillRect(0, 0, getWidth(), getHeight());
			fit(g, frame);
			Graphics2D g2 = (Graphics2D) g;
			g2.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON);
			g2.setFont(font);
			FontMetrics fm = g2.getFontMetrics();
			int cw = fm.charWidth('M');
			int ch = fm.getHeight();
			int ox = (getWidth() - cols * cw) / 2;
			int oy = (getHeight() - frame.length * ch) / 2 + fm.getAscent();
			for (int r = 0; r < frame.length; r++) {
				boolean hud = frame.length > 2 && (r == 0 || r == frame.length - 1);
				String line = frame[r];
				// One drawString per char keeps the grid aligned even with fallback glyphs.
				for (int c = 0; c < line.length(); c++) {
					char chr = line.charAt(c);
					if (chr != ' ') {
						g2.setColor(hud ? HUD : colorOf(chr));
						g2.drawString(String.valueOf(chr), ox + c * cw, oy + r * ch);
					}
				}
			}
		}

		private static Color colorOf(char c) {
			for (int i = 0; i < CHARS.length; i++) {
				if (CHARS[i].indexOf(c) >= 0) {
					return COLORS[i];
				}
			}
			return DEFAULT;
		}
	}

	/** Paints an animated GIF scaled to fit, keeping aspect ratio, on black. */
	private static class GifPanel extends JComponent implements Pausable {
		private final Image image;

		GifPanel(File gif) {
			// createImage (not getImage) so Toolkit doesn't cache it; this component is the
			// ImageObserver, so every decoded GIF frame triggers a repaint.
			image = Toolkit.getDefaultToolkit().createImage(gif.getAbsolutePath());
			setOpaque(true);
			setPreferredSize(new Dimension(240, 480));
		}

		@Override
		public void resume() {
			repaint(); // the next paint restarts the animation
		}

		@Override
		public void pause() {
			image.flush(); // stops the decoder
		}

		@Override
		protected void paintComponent(Graphics g) {
			g.setColor(Color.BLACK);
			g.fillRect(0, 0, getWidth(), getHeight());
			int iw = image.getWidth(this);
			int ih = image.getHeight(this);
			if (iw <= 0 || ih <= 0) {
				return; // not decoded yet; imageUpdate will repaint us
			}
			double scale = Math.min((double) getWidth() / iw, (double) getHeight() / ih);
			int w = (int) (iw * scale);
			int h = (int) (ih * scale);
			Graphics2D g2 = (Graphics2D) g;
			g2.setRenderingHint(RenderingHints.KEY_INTERPOLATION, RenderingHints.VALUE_INTERPOLATION_BILINEAR);
			g2.drawImage(image, (getWidth() - w) / 2, (getHeight() - h) / 2, w, h, this);
		}
	}
}
