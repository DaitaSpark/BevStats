// Reject upstream HTML errors before handing the download to the XLSX parser.
export function validateDownload(data) {
  if (data.byteLength > 5000000) throw new Error("Report exceeds size limit");
  const bytes = new Uint8Array(data);
  if (bytes[0] === 0x50 && bytes[1] === 0x4b) return;
  const text = new TextDecoder().decode(bytes.slice(0, 16000));
  const expired = text.match(/This link expired on\s+(\d{1,2}\/\d{1,2}\/\d{4})/i);
  if (expired) throw new Error(`Report link expired on ${expired[1]}; replace REPORT_URL with a fresh QuickLink`);
  throw new Error("Report download is not an Excel workbook; check the report link");
}
