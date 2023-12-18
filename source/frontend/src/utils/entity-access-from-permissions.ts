// attention, these functions mutate the input parameter. it's a bad practice, but I don't understand this code well enough to refactor right now
function merge(result: any, entity: any) {
  //Grant most privileged access on conflict.
  if (result[entity.schema_name].create === false && entity.create) {
    result[entity.schema_name].create = true;
  }
  if (result[entity.schema_name].read === false && entity.read) {
    result[entity.schema_name].read = true;
  }
  if (result[entity.schema_name].update === false && entity.update) {
    result[entity.schema_name].update = true;
  }
  if (result[entity.schema_name].delete === false && entity.delete) {
    result[entity.schema_name].delete = true;
  }

  //Append additional attributes.
  if (entity.attributes && Array.isArray(entity.attributes)) { //Does policy have attributes defined.

    if (Array.isArray(result[entity.schema_name].attributes)) {
      if (result[entity.schema_name].attributes.length === 0) {
        result[entity.schema_name].attributes = entity.attributes;
      } else { //Need to append values to existing.
        for (const attr of entity.attributes) {
          if (!result[entity.schema_name].attributes.includes(attr)) {
            result[entity.schema_name].attributes.push(attr);
          }
        }
      }
    } else {
      result[entity.schema_name].attributes = entity.attributes;
    }
  }
}

function processPolicy(policy: { entity_access: any; }, result: any) {
  for (const entity of policy.entity_access) {
    if (result[entity.schema_name]) {
      merge(result, entity);
    } else {
      result[entity.schema_name] = {
        create: entity.create,
        read: entity.read,
        update: entity.update,
        delete: entity.delete,
        attributes: entity.attributes ? entity.attributes : []
      };
    }
  }
}

function processRole(role: { policies: any; }, permissionsData: any, entity_access: any) {
  for (const rolePolicy of role.policies) { // loop through all polices attached to role.
    for (const policy of permissionsData.policies) {
      if (policy.policy_id === rolePolicy.policy_id) {
        processPolicy(policy, entity_access);
      }
    }
  }
}

export function entityAccessFromPermissions(permissionsData: any, userGroups: string[]) {
  // Get list of policies user is authorized for, apply the most privileged access over others.

  let entity_access: any = {};
  for (const role of permissionsData.roles) {
    for (const group of role.groups) {
      if (userGroups.includes(group.group_name)) { //Check if this user has this group membership.
        processRole(role, permissionsData, entity_access);
      }
    }
  }
  return entity_access;
}
