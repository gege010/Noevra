const { test } = require("node:test");
const assert = require("node:assert/strict");
const { renderMarkdown, safeUrl } = require("../src/static/app.js");

test("untrusted HTML stays text and executable links cannot become anchors", () => {
  const { html } = renderMarkdown(
    "<img src=x onerror=alert(1)>\n\n[click](javascript:alert%281%29)",
  );
  assert.ok(!html.includes("<img"));
  assert.ok(!html.includes('href="javascript:'));
  assert.ok(html.includes("&lt;img"));
});

test("source citations are accessible actions and preserve numeric identities", () => {
  const { html } = renderMarkdown("Compare the evidence [3] and [12].");
  assert.ok(html.includes('data-citation="3"'));
  assert.ok(html.includes('aria-label="Inspect source 12"'));
});

test("code never becomes a citation or active HTML", () => {
  const { html } = renderMarkdown("```html\n<script>run()</script> [12]\n```");
  assert.ok(html.includes("&lt;script&gt;"));
  assert.ok(!html.includes("data-citation"));
});

test("duplicate section headings receive distinct navigable anchors", () => {
  const { html, toc } = renderMarkdown("## Findings\n\nA\n\n## Findings\n\nB");
  assert.equal(toc.length, 2);
  assert.notEqual(toc[0].id, toc[1].id);
  assert.ok(html.includes(`id="${toc[1].id}"`));
});

test("tables remain bounded and escaped pipes remain within their cell", () => {
  const { html } = renderMarkdown(
    "| Setup | Result |\n|---|---|\n| a \\| b | 3 |",
  );
  assert.ok(html.includes('class="table-wrap"'));
  assert.equal((html.match(/<td>/g) || []).length, 2);
  assert.ok(html.includes("a | b"));
});

test("TeX escapes survive Markdown until the math renderer runs", () => {
  const { html } = renderMarkdown("Equation \\(\\frac{a}{b}\\) and $x_{i}$.");
  assert.ok(html.includes("\\(\\frac{a}{b}\\)"));
  assert.ok(html.includes("$x_{i}$"));
});

test("external references have safe browsing attributes", () => {
  const { html } = renderMarkdown("[paper](https://example.org/paper)");
  assert.ok(html.includes('rel="noopener noreferrer"'));
  assert.equal(safeUrl("data:text/html,test"), "");
  assert.equal(safeUrl("javascript:alert(1)"), "");
  assert.equal(safeUrl("https://example.org/"), "https://example.org/");
});

test("remote images are text, with no unsolicited tracking requests", () => {
  const { html } = renderMarkdown(
    "![description](https://example.org/track.png)",
  );
  assert.ok(!html.includes("<img"));
  assert.ok(html.includes("description"));
});
