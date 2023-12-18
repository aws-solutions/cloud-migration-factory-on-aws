import {exportAll, exportTable} from "./xlsx-export";
import * as XLSX from "xlsx";
import {
  generateTestApps,
  generateTestDatabases,
  generateTestServers,
  generateTestWaves
} from "../__tests__/mocks/user_api";

test('exports an array of objects to an excel spreadsheet', () => {
  // GIVEN
  jest.spyOn(XLSX, 'writeFile').mockImplementation(jest.fn());

  const items = generateTestApps(2);

  // WHEN
  exportTable(items, 'applications', 'bar');

  // THEN
  expect(XLSX.writeFile).toHaveBeenCalledWith(
    expect.objectContaining({
      SheetNames: ['applications'],
      Sheets: {
        applications: expect.any(Object),
      }
    }),
    'bar.xlsx'
  );
});

test('exports all items', () => {
  // GIVEN
  jest.spyOn(XLSX, 'writeFile').mockImplementation(jest.fn());

  const items = {
    applications: generateTestApps(3),
    databases: generateTestDatabases(2),
    servers: generateTestServers(4),
    waves: generateTestWaves(1),
  };

  // WHEN
  exportAll(items, 'bar')

  // THEN
  expect(XLSX.writeFile).toHaveBeenCalledWith(
    expect.objectContaining({
      SheetNames: ["applications", "databases", "servers", "waves"],
      Sheets: {
        applications: expect.any(Object),
        databases: expect.any(Object),
        servers: expect.any(Object),
        waves: expect.any(Object),
      }
    }),
    'bar.xlsx'
  );
});