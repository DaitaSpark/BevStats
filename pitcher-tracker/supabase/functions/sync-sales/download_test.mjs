import { test } from 'node:test';
import { strict as assert } from 'node:assert';
import { validateDownload } from './download.mjs';

const data = text => new TextEncoder().encode(text).buffer;
test('expired link produces actionable error without exposing source HTML', () => {
  assert.throws(() => validateDownload(data('<html>This link expired on 11/11/2026. secret-url</html>')),
    {message: 'Report link expired on 11/11/2026; replace REPORT_URL with a fresh QuickLink'});
});
test('login page and empty response are rejected', () => {
  for (const text of ['<html>Please sign in</html>', '']) {
    assert.throws(() => validateDownload(data(text)), /not an Excel workbook/);
  }
});
test('ZIP workbook signature passes download validation', () => {
  assert.doesNotThrow(() => validateDownload(new Uint8Array([0x50, 0x4b, 3, 4]).buffer));
});
