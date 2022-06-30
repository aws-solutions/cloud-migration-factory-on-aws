import {
  Header,
  SpaceBetween,
  Button,
  ButtonDropdown,
} from '@awsui/components-react';
import React from "react";

// Table header content, shows how many items are selected and contains the action stripe
const TableHeader = ({ title, description, selectedItems, counter, handleRefreshClick, handleDeleteClick, handleEditClick, handleAddClick, handleActionSelection, actionItems, handleDownload, actionsButtonDisabled, disabledButtons, info}) => {
  const isOnlyOneSelected = selectedItems ? selectedItems.length === 1 : false;

  const disableActionsButton = actionsButtonDisabled !== undefined ? actionsButtonDisabled : !isOnlyOneSelected

  return (
    <Header
      variant="h2"
      counter={counter ? counter : undefined}
      description={description ? description : undefined}
      info={info}
      actions={
        <SpaceBetween direction="horizontal" size="s">
          {handleRefreshClick ? <Button onClick={handleRefreshClick} iconAlign="right" iconName="refresh"/> : null}
          {handleActionSelection ? <ButtonDropdown
            items={actionItems}
            onItemClick={handleActionSelection}
            disabled={disableActionsButton}
            expandableGroups
            >Actions
            </ButtonDropdown> : null}
          {handleEditClick ? <Button onClick={handleEditClick} disabled={!isOnlyOneSelected || (disabledButtons ? disabledButtons.edit ? disabledButtons.edit : false : false)}> Edit</Button> : null}
          {handleDeleteClick ? <Button onClick={handleDeleteClick} disabled={selectedItems.length === 0  || (disabledButtons ? disabledButtons.delete ? disabledButtons.delete: false : false)}> Delete</Button> : null}
          {handleAddClick ? <Button onClick={handleAddClick} disabled={disabledButtons ? disabledButtons.add ? disabledButtons.add : false : false} variant="primary"> Add</Button> : null}
          {handleDownload ? <Button onClick={handleDownload} iconName="download" variant="icon"/> : null}
        </SpaceBetween>
      }
    >
      {title}
    </Header>
  );
};

export default TableHeader;
