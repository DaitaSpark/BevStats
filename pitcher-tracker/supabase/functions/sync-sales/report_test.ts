import { parseRows } from "./report.ts";

const header = ["Customer Name / Product Name", "Case Equiv Oct", "Case Equiv Nov", "Case Equiv ±", "Case Equiv % ±"];
function assert(value: boolean) { if (!value) throw new Error("Assertion failed"); }
function rejects(rows: unknown[][]) {
  let rejected = false;
  try { parseRows(rows); } catch { rejected = true; }
  assert(rejected);
}
Deno.test("converts full precision once, excludes product rows, handles percentage fractions", () => {
  const rows = parseRows([header, ["Total",62.000001,41.333334,-20.666667,-0.333333], ["Wild Wing",62.000001,41.333334,-20.666667,-0.333333], ["Bud Light 1/2 Keg",62.000001,41.333334,-20.666667,-0.333333]]);
  assert(rows.length === 1 && rows[0].current_beers === 992 && rows[0].prior_beers === 1488 && rows[0].reported_percent === -33.33);
});
Deno.test("rejects invalid headers, duplicate names, partial reports and nonnumeric sales", () => {
  rejects([["Login"]]);
  rejects([header]);
  rejects([header,["Total",0,2,0,0],["A",0,1,1,0],["a",0,1,1,0]]);
  rejects([header,["Total",0,2,0,0],["A",0,1,1,0]]);
  rejects([header,["Total",0,0,0,0],["A",0,"",0,0]]);
});
Deno.test("reported zeros remain zero", () => {
  const rows = parseRows([header,["Total",0,0,0,0],["A",0,0,0,0]]);
  assert(rows[0].current_beers === 0);
});
