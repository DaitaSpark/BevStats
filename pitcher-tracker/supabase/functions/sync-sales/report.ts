import ExcelJS from "npm:exceljs@4.4.0";

export function parseRows(rows: unknown[][]) {
  const header = rows[0]?.map(String);
  if (header?.[0] !== "Customer Name / Product Name" || header[1] !== "Case Equiv Oct" || header[2] !== "Case Equiv Nov") throw new Error("Unexpected report columns");
  const result: {name: string; current_beers: number; prior_beers: number; reported_change_beers: number; reported_percent: number}[] = [];
  const seen = new Set<string>();
  let total: number | undefined;
  for (const row of rows.slice(1)) {
    const name = String(row[0] ?? "").replace(/\s+/g, " ").trim();
    if (!name) continue;
    if (name === "Total") { total = Number(row[2]); continue; }
    if (name.startsWith("Bud Light ")) continue;
    const values = row.slice(1, 5);
    if (values.length !== 4 || values.some(v => typeof v !== "number" || !Number.isFinite(v)) || Number(values[0]) < 0 || Number(values[1]) < 0) throw new Error("Invalid restaurant values");
    const identity = name.toLowerCase();
    if (seen.has(identity)) throw new Error("Duplicate restaurant");
    seen.add(identity);
    const [prior, current, change, percent] = values as number[];
    const round = (v: number) => Math.round(v * 100) / 100;
    result.push({name, prior_beers: round(prior * 24), current_beers: round(current * 24), reported_change_beers: round(change * 24), reported_percent: round(percent * 100)});
  }
  if (!result.length || result.length > 1000 || total === undefined || !Number.isFinite(total)) throw new Error("Incomplete report");
  if (Math.abs(result.reduce((sum, row) => sum + row.current_beers, 0) - total * 24) > result.length * 0.02) throw new Error("Restaurant totals do not reconcile");
  return result;
}

export async function parseWorkbook(data: ArrayBuffer) {
  const book = new ExcelJS.Workbook();
  await book.xlsx.load(data as never);
  const sheet = book.worksheets[0];
  if (!sheet || !book.worksheets[1]) throw new Error("Missing report sheets");
  const rows: unknown[][] = [];
  sheet.eachRow(row => rows.push([1,2,3,4,5].map(i => row.getCell(i).value)));
  const metadata = new Map<string, string>();
  book.worksheets[1].eachRow(row => metadata.set(row.getCell(1).text, row.getCell(2).text));
  const period = metadata.get("Period") ?? "";
  if (!period.includes("From: 10/1/2026 To: 10/31/2026") || !period.includes("From: 11/1/2026 To: 11/30/2026")) throw new Error("Reporting periods changed; review configuration");
  return {rows: parseRows(rows), source_cache_time: metadata.get("Cache Created Time") ?? null};
}
