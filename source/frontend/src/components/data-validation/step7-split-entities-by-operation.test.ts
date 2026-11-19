import { splitEntitiesByOperation } from "./step7-split-entities-by-operation";
import { DeduplicatedEntity } from "./types";
import { defaultTestProps } from "../../__tests__/TestUtils";

describe("splitEntitiesByOperation", () => {
  const mockSchema = defaultTestProps.schemas.application;

  describe("Basic functionality", () => {
    it("should split entities into create and update categories correctly", () => {
      const entities: DeduplicatedEntity[] = [
        {
          entityName: "application",
          schema: mockSchema,
          data: {
            "existing-app-1": { app_name: "existing-app-1", aws_region: "us-east-1" },
            "new-app-1": { app_name: "new-app-1", aws_region: "us-west-2" },
            "new-app-2": { app_name: "new-app-2", aws_region: "us-west-2" },
          },
        },
      ];

      const existingItemsBySchema = new Map([
        [
          "app",
          [
            { app_name: "existing-app-1", app_id: "1" },
            { app_name: "another-existing-app", app_id: "2" },
          ],
        ],
      ]);

      const result = splitEntitiesByOperation(entities, existingItemsBySchema);

      expect(result.entitiesToCreate).toHaveLength(1);
      expect(result.entitiesToUpdate).toHaveLength(1);
      expect(Object.keys(result.entitiesToCreate[0].data)).toHaveLength(2);
      expect(Object.keys(result.entitiesToUpdate[0].data)).toHaveLength(1);

      expect(result.entitiesToCreate[0].data).toEqual({
        "new-app-1": { app_name: "new-app-1", aws_region: "us-west-2" },
        "new-app-2": { app_name: "new-app-2", aws_region: "us-west-2" },
      });

      expect(result.entitiesToUpdate[0].data).toEqual({
        "existing-app-1": { app_name: "existing-app-1", aws_region: "us-east-1" },
      });
    });
  });
});
