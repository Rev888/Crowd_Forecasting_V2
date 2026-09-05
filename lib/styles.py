"""Shared CSS for the dashboard (not currently imported by app.py, which
inlines its own <style> block via st.markdown -- provided here for the
requested lib/ layout and for future reuse)."""

DARK_COMMAND_CENTER_CSS = """
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'JetBrains Mono', monospace; }
.stApp { background-color: #0b0c0d; }
.tci-header { border: 1px solid #2a2b2e; border-left: 3px solid #b3261e; background-color: #131416; padding: 18px 24px; margin-bottom: 22px; }
.tci-header h1 { font-size: 1.6rem; letter-spacing: 3px; color: #e8c874; margin: 0; font-weight: 700; }
.tci-header p { color: #7a7d82; margin: 4px 0 0 0; font-size: 0.8rem; letter-spacing: 1px; }
.tci-card { border: 1px solid #2a2b2e; background-color: #131416; padding: 14px 16px; height: 100%; }
.tci-card .label { color: #7a7d82; font-size: 0.68rem; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 6px; }
.tci-card .value { color: #e6e6e6; font-size: 1.35rem; font-weight: 600; }
.tci-card .sub { color: #55585e; font-size: 0.7rem; margin-top: 4px; }
.tci-section-title { color: #e8c874; font-size: 0.85rem; letter-spacing: 2px; text-transform: uppercase; border-bottom: 1px solid #2a2b2e; padding-bottom: 8px; margin: 30px 0 14px 0; }
.tci-badge { display: inline-block; padding: 4px 12px; border: 1px solid; font-size: 0.78rem; letter-spacing: 1px; text-transform: uppercase; font-weight: 600; }
.tci-status-live { color: #2e7d32; }
.tci-status-fallback { color: #d9731f; }
.tci-forecast-box { border: 1px solid #2a2b2e; border-left: 3px solid #e8c874; background-color: #131416; padding: 20px 24px; }
.tci-range { font-size: 2.1rem; font-weight: 700; color: #e6e6e6; letter-spacing: 1px; }
.tci-approx-tag { color: #7a7d82; font-size: 0.68rem; letter-spacing: 1px; text-transform: uppercase; }
.tci-event-chip { display: inline-block; border: 1px solid #b3261e; color: #e8c874; padding: 3px 10px; margin: 3px 6px 3px 0; font-size: 0.72rem; letter-spacing: 0.5px; }
"""
