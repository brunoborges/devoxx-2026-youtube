const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { test } = require("node:test");

const root = path.join(__dirname, "..");
const rows = JSON.parse(fs.readFileSync(path.join(root, "data/devoxx_stats.json"), "utf8"));
const template = fs.readFileSync(path.join(root, "src/devoxx-dashboard.template.html"), "utf8");
const source = [...template.matchAll(/<script>([\s\S]*?)<\/script>/g)].at(-1)[1];

function dashboard() {
  const elements = new Map();
  const defaults = { dataset: JSON.stringify(rows), match: "all", minviews: "0",
    rankmetric: "views", scale: "log", cohortmetric: "median", pagesize: "25",
    "benchmark-population": "all" };
  const get = id => {
    if (!elements.has(id)) elements.set(id, {
      value: defaults[id] || "", textContent: defaults[id] || "", innerHTML: "",
      classList: { toggle() {} }, addEventListener() {}, append() {},
    });
    return elements.get(id);
  };
  const context = vm.createContext({
    document: { getElementById: get, querySelectorAll: () => [],
      createElement: () => ({}), addEventListener() {} },
    window: {}, Intl, console, setTimeout, clearTimeout,
  });
  vm.runInContext(source, context);
  return { api: context.window.devoxx, get, run: expression => vm.runInContext(expression, context) };
}

test("inclusive quantiles and upper-tie CDF ranks handle empty, singleton, zeros and missing", () => {
  const { api } = dashboard();
  assert.equal(api.quantile([], .5), null);
  assert.equal(api.quantile([7], .99), 7);
  assert.equal(api.quantile([0, 10], .95), 9.5);
  const result = api.percentileStats([{ comments: 0 }, { comments: 0 }, { comments: 4 },
    { comments: null }, { comments: undefined }], "comments", 0);
  assert.equal(result.count, 3);
  assert.equal(result.rank, 200 / 3);
  assert.deepEqual(Array.from(result.thresholds), [0, 3.2, 3.5999999999999996, 3.92]);
  const empty = api.percentileStats([{ comments: null }], "comments", 0);
  assert.equal(empty.rank, null);
  assert.ok(empty.thresholds.every(v => v === null));
  assert.equal(api.percentileStats([{ views: 7 }], "views", 7).rank, 100);
  assert.equal(api.percentileStats([{ views: 7 }], "views", 6).rank, 0);
  assert.equal(api.percentileStats([{ views: 7 }], "views", 8).rank, 100);
  assert.equal(api.percentileStats(rows, "comments", null).rank, null);
});

test("talk selection is independent from filters; all videos is the default population", () => {
  const { api, get } = dashboard();
  get("talk").value = rows[0].url;
  get("query").value = '"' + rows[0].title.replaceAll('"', "") + '"';
  api.render();
  assert.equal(api.selected.length, 1);
  assert.match(get("speaker-summary").innerHTML, /all videos · 192 videos/);
  assert.match(get("percentile-charts").innerHTML, /cdf-marker/);
  get("benchmark-population").value = "filtered";
  api.speakerBenchmark();
  assert.match(get("speaker-summary").innerHTML, /current dashboard filters · 1 videos/);
  const previous = api.selected.length;
  get("talk").value = rows[1].url;
  api.speakerBenchmark();
  assert.equal(api.selected.length, previous);
  assert.match(get("speaker-summary").innerHTML, /outside this comparison population/);
  get("query").value = "doesnotexistanywhere";
  api.render();
  assert.equal(api.selected.length, 0);
  assert.match(get("percentile-charts").innerHTML, /No available counts/);
  assert.doesNotMatch(get("percentile-charts").innerHTML, /NaN|Infinity/);
  get("benchmark-population").value = "all";
  api.speakerBenchmark();
  assert.match(get("speaker-summary").innerHTML, /192 videos/);
});

test("search phrases, exclusions, normalization, any/all and date boundaries survive", () => {
  const { api, get } = dashboard();
  const record = { normalized: "spring boot cafe java" };
  assert.ok(api.matches(record, '"SPRING BOOT" café -python', "all"));
  assert.ok(!api.matches(record, '"boot spring"', "all"));
  assert.ok(api.matches(record, "java python", "any"));
  assert.ok(!api.matches(record, "java python", "all"));
  assert.ok(!api.matches(record, "java -boot", "any"));
  get("start").value = rows[0].date_published;
  get("end").value = rows[0].date_published;
  assert.ok(api.filterRows().some(r => r.url === rows[0].url));
  get("minviews").value = "-1";
  api.render();
  assert.equal(api.selected.length, 0);
});

test("null comments sort last both ways and exports distinguish missing counts from zero", () => {
  const { api, run } = dashboard();
  run("DATA[0].comments=null;DATA[0].comments_status='unavailable';sortKey='comments';sortDir=1;render()");
  assert.equal(run("ordered().at(-1).comments"), null);
  run("sortDir=-1");
  assert.equal(run("ordered().at(-1).comments"), null);
  const exported = api.csvText([{ ...api.DATA[0], title: "=formula" }, { ...api.DATA[1], comments: 0 }]);
  assert.match(exported, /comments_status/);
  assert.match(exported, /comments_captured_at_utc/);
  assert.match(exported, /"'=formula"/);
  assert.match(exported, /"","unavailable"/);
  assert.match(exported, /"0","available"/);
});
