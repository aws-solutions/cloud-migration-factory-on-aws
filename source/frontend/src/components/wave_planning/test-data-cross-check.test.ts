/* eslint-disable @typescript-eslint/no-explicit-any */
import { sampleApplications, sampleDatabases, sampleMoveGroups, sampleServers, sampleWaves } from "../../../test_data";

const applications = sampleApplications();
const databases = sampleDatabases();
const servers = sampleServers();
const moveGroups = sampleMoveGroups();
const waves = sampleWaves();

function manyToManyCheck(souces: any[], targets: any[], pk1: string, pk2: string) {
  const mismatches: Record<string, any> = {};
  for (const item of souces) {
    const spkv = item[pk1];
    const sfkv = item[`${pk2}s`];

    if (!spkv) throw new Error(`${JSON.stringify(item)} has no ${pk1}`);
    if (!sfkv) throw new Error(`${JSON.stringify(item)} has no ${pk2}s`);

    const related = targets.filter((x) => sfkv.includes(x[pk2]));
    const unmatched = related.filter((x) => !x[`${pk1}s`].includes(spkv)).map((x) => x[pk2]);
    if (unmatched.length > 0) mismatches[spkv] = { unmatched };
  }
  return mismatches;
}

function oneToManyCheck(souces: any[], targets: any[], pk1: string, pk2: string) {
  const mismatches: Record<string, any> = {};
  for (const item of souces) {
    const spkv = item[pk1];
    const sfkv = item[`${pk2}s`];

    if (!spkv) throw new Error(`${JSON.stringify(item)} has no ${pk1}`);
    if (!sfkv) throw new Error(`${JSON.stringify(item)} has no ${pk2}s`);

    const related = targets.filter((x) => sfkv.includes(x[pk2]));
    const unmatched = related.filter((x) => x[pk1] !== spkv).map((x) => x[pk2]);
    if (unmatched.length > 0) mismatches[spkv] = { unmatched };
  }
  return mismatches;
}

function manyToOneCheck(souces: any[], targets: any[], pk1: string, pk2: string, allowNoFk: boolean = false) {
  const mismatches: Record<string, any> = {};
  for (const item of souces) {
    const spkv = item[pk1];
    const sfkv = item[pk2];

    if (!spkv) throw new Error(`${JSON.stringify(item)} has no ${pk1}`);
    if (!sfkv) {
      if (allowNoFk) continue;
      throw new Error(`${JSON.stringify(item)} has no ${pk2}`);
    }

    const related = targets.filter((x) => x[`${pk1}s`].includes(sfkv));
    const unmatched = related.filter((x) => x[pk2] !== spkv).map((x) => x[pk2]);
    if (unmatched.length > 0) mismatches[spkv] = { unmatched };
  }
  return mismatches;
}

describe("cross check wpm test data", () => {
  describe("apps", () => {
    test("database_ids", () => {
      const mismatches = manyToManyCheck(applications, databases, "app_id", "database_id");
      expect(mismatches).toEqual({});
    });

    test("server_ids", () => {
      const mismatches = manyToManyCheck(applications, servers, "app_id", "server_id");
      expect(mismatches).toEqual({});
    });

    test("move_group_ids", () => {
      const mismatches = manyToManyCheck(applications, moveGroups, "app_id", "move_group_id");
      expect(mismatches).toEqual({});
    });

    test("wave_ids", () => {
      const mismatches = manyToManyCheck(applications, waves, "app_id", "wave_id");
      expect(mismatches).toEqual({});
    });
  });

  describe("groups", () => {
    test("database_ids", () => {
      const mismatches = oneToManyCheck(moveGroups, databases, "move_group_id", "database_id");
      expect(mismatches).toEqual({});
    });

    test("server_ids", () => {
      const mismatches = oneToManyCheck(moveGroups, servers, "move_group_id", "server_id");
      expect(mismatches).toEqual({});
    });

    test("app_ids", () => {
      const mismatches = manyToManyCheck(moveGroups, applications, "move_group_id", "app_id");
      expect(mismatches).toEqual({});
    });

    test("wave_id", () => {
      const mismatches = manyToOneCheck(moveGroups, waves, "move_group_id", "wave_id", true);
      expect(mismatches).toEqual({});
    });
  });

  describe("wave", () => {
    test("move_group_ids", () => {
      const mismatches = oneToManyCheck(waves, moveGroups, "wave_id", "move_group_id");
      expect(mismatches).toEqual({});
    });

    test("app_ids", () => {
      const mismatches = manyToManyCheck(waves, applications, "wave_id", "app_id");
      expect(mismatches).toEqual({});
    });

    test("database_ids", () => {
      const mismatches = oneToManyCheck(waves, databases, "wave_id", "database_id");
      expect(mismatches).toEqual({});
    });

    test("server_ids", () => {
      const mismatches = oneToManyCheck(waves, servers, "wave_id", "server_id");
      expect(mismatches).toEqual({});
    });
  });

  describe("database", () => {
    test("wave_id", () => {
      const mismatches = manyToOneCheck(databases, waves, "database_id", "wave_id", true);
      expect(mismatches).toEqual({});
    });

    test("move_group_id", () => {
      const mismatches = manyToOneCheck(databases, moveGroups, "database_id", "move_group_id");
      expect(mismatches).toEqual({});
    });

    test("app_ids", () => {
      const mismatches = manyToManyCheck(databases, applications, "database_id", "app_id");
      expect(mismatches).toEqual({});
    });
  });

  describe("servers", () => {
    test("wave_id", () => {
      const mismatches = manyToOneCheck(servers, waves, "server_id", "wave_id", true);
      expect(mismatches).toEqual({});
    });

    test("move_group_id", () => {
      const mismatches = manyToOneCheck(servers, moveGroups, "server_id", "move_group_id");
      expect(mismatches).toEqual({});
    });

    test("app_ids", () => {
      const mismatches = manyToManyCheck(servers, applications, "server_id", "app_id");
      expect(mismatches).toEqual({});
    });
  });
});
