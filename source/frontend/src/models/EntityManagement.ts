import type { EntityType } from "../utils/Constants";

export enum OperationType {
  MOVE = "move",
  CLEANUP = "cleanup",
}

export const CLEANUP_MAX_ENTITY_SIZE = 200;

export type TargetEntity = {
  entity_type: EntityType;
  entity_id: string;
};

export type MoveEntitiesPayload = {
  operation: OperationType.MOVE;
  source_entity_type: EntityType;
  source_entity_id?: string;
  destination_entity_type: EntityType;
  destination_entity_id?: string;
  target_entities: TargetEntity[];
};

export type CleanupEntityPayload = {
  operation: OperationType.CLEANUP;
  entity_type: EntityType;
  entity_ids: string[];
};

export type ManageEntitiesPayload = MoveEntitiesPayload | CleanupEntityPayload;
