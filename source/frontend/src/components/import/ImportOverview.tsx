// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import { ColumnLayout, Container, ExpandableSection, Header, Popover, SpaceBetween } from "@awsui/components-react";

import { capitalize } from "../../resources/main";
import AllViewerAttributes from "../ui_attributes/AllViewerAttributes";

const ItemDetails = (props) => {
  let items = [];

  items = props.items.map((item, index) => {
    const recordNumber = index + 1;
    return (
      <Container header={"Record " + recordNumber} key={recordNumber}>
        <AllViewerAttributes
          schema={props.schema}
          schemas={props.schemas}
          item={item}
          hideEmpty
          dataAll={props.allData ? props.allData : undefined}
        />
      </Container>
    );
  });

  return items;
};

const SummaryItem = (props) => {
  if (!props.item) {
    return <h3>{"-"}</h3>;
  }
  // There is no visual clue that clicking this brings up the popover
  // Since all the info is available in the Details pane below, is this really needed?
  return (
    <Popover
      position="top"
      size="small"
      triggerType="custom"
      content={<ArrayToList list={props.item} displayKey={props.displayKey} />}
    >
      <h3>{props.item.length === 0 ? "-" : props.item.length}</h3>
    </Popover>
  );
};

const SummaryEntity = (props) => {
  return (
    <Container
      className="custom-dashboard-container"
      header={
        <Header variant="h2">
          <SpaceBetween size={"xl"} direction={"vertical"}>
            {capitalize(props.entityName)}
          </SpaceBetween>
        </Header>
      }
    >
      <ColumnLayout borders="vertical" columns={3}>
        <SpaceBetween size={"s"} direction={"vertical"}>
          <SpaceBetween size={"s"} direction={"horizontal"}>
            <h3>Create</h3>
            <SummaryItem
              item={props.entityItem["Create"]}
              displayKey={props.entityName === "application" ? "app" + "_name" : props.entityName + "_name"}
            />
          </SpaceBetween>
          {props.entityItem["Create"].length > 0 ? (
            <ExpandableSection header={"Details"}>
              <ItemDetails
                items={props.entityItem["Create"]}
                schemas={props.schemas}
                schema={props.schemas[props.entityName]}
                allData={props.dataAll ? props.dataAll : undefined}
              />
            </ExpandableSection>
          ) : undefined}
        </SpaceBetween>

        <SpaceBetween size={"s"} direction={"vertical"}>
          <SpaceBetween size={"s"} direction={"horizontal"}>
            <h3>Update</h3>
            <SummaryItem
              item={props.entityItem["Update"]}
              displayKey={props.entityName === "application" ? "app" + "_name" : props.entityName + "_name"}
            />
          </SpaceBetween>
          {props.entityItem["Update"].length > 0 ? (
            <ExpandableSection header={"Details"}>
              <ItemDetails
                items={props.entityItem["Update"]}
                schemas={props.schemas}
                schema={props.schemas[props.entityName]}
                allData={props.dataAll ? props.dataAll : undefined}
              />
            </ExpandableSection>
          ) : undefined}
        </SpaceBetween>
        <SpaceBetween size={"s"} direction={"vertical"}>
          <SpaceBetween size={"s"} direction={"horizontal"}>
            <h3>No Update</h3>
            <SummaryItem
              item={props.entityItem["NoChange"]}
              displayKey={props.entityName === "application" ? "app" + "_name" : props.entityName + "_name"}
            />
          </SpaceBetween>
          {props.entityItem["NoChange"].length > 0 ? (
            <ExpandableSection header={"Details"}>
              <ItemDetails
                items={props.entityItem["NoChange"]}
                schemas={props.schemas}
                schema={props.schemas[props.entityName]}
                allData={props.dataAll ? props.dataAll : undefined}
              />
            </ExpandableSection>
          ) : undefined}
        </SpaceBetween>
      </ColumnLayout>
    </Container>
  );
};

const ArrayToList = (props) => {
  return (
    <div>
      {props.list.map((item, i) => {
        const displayKey = i;
        return <p key={displayKey}>{item[props.displayKey]}</p>;
      })}
    </div>
  );
};

function getSummaries(items, schemas, dataAll) {
  let summaries = [];

  for (const entity in items.entities) {
    summaries.push(
      <SummaryEntity
        key={entity}
        entityName={entity}
        entityItem={items.entities[entity]}
        schemas={schemas}
        dataAll={dataAll}
      />
    );
  }

  return summaries;
}

// Attribute Display message content
const ImportOverview = (props) => {
  return (
    <Container
      className="custom-dashboard-container"
      header={
        <Header
          variant="h2"
          description="The following records will be amended or created on Upload, please ensure you are happy with this before continuing."
        >
          Upload Overview
        </Header>
      }
    >
      <SpaceBetween size={"l"} direction={"vertical"}>
        {getSummaries(props.items, props.schemas, props.dataAll)}
      </SpaceBetween>
    </Container>
  );
};

export default ImportOverview;
