/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import type { Meta, StoryObj } from "@storybook/react";

import ManageWaveStep, { ManageWaveStepProps } from "./ManageWaveStep";
import { sampleApplications } from "../../../test_data/wpm_applications";
import { sampleDatabases } from "../../../test_data/wpm_databases";
import { sampleServers } from "../../../test_data/wpm_servers";
import { sampleMoveGroups } from "../../../test_data/wpm_move_groups";
import { sampleWaves } from "../../../test_data/wpm_waves";
import { wpmSchemas } from "../../../test_data";
import { ErrorWithType } from "../../actions/ErrorHandlerHook";
import { MoveGroup, Wave } from "../../models";

const meta: Meta<typeof ManageWaveStep> = {
  title: "ManageWaveStep",
  component: ManageWaveStep,
  parameters: {
    layout: "top",
    docs: {
      description: {
        component: "The UI component for WPM Job Wizard Manage Wave step",
      },
    },
    design: {
      type: "figma",
      url: "https://www.figma.com/design/Bq7LwEwhEzMUxuPwPHv8Ng/Wave-Planning-Manager?node-id=1548-34096&t=XEXMivJdvhdQ3clQ-0",
    },
  },
  tags: ["autodocs"],
};

export default meta;

type Story = StoryObj<typeof meta>;

const schemas = wpmSchemas();

// Create a wrapper for the `onChange` callback to work
const StoryWrapper = (props: Partial<ManageWaveStepProps>) => {
  const [applications] = React.useState(sampleApplications());
  const [databases] = React.useState(sampleDatabases());
  const [servers] = React.useState(sampleServers());
  const [moveGroups, setMoveGroups] = React.useState(sampleMoveGroups());
  const [waves, setWaves] = React.useState(sampleWaves());

  const defaultProps = {
    dataAll: {
      app: { data: applications, isLoading: false },
      database: { data: databases, isLoading: false },
      server: { data: servers, isLoading: false },
      move_group: { data: moveGroups, isLoading: false },
      wave: { data: waves, isLoading: false },
    },
    schemas,
    applications,
    databases,
    servers,
    moveGroups,
    waves,
    onConfirm: (w: Wave[], mg: MoveGroup[]) => {
      setWaves([...w]);
      setMoveGroups([...mg]);
    },
    isLoading: false,
  };

  return <ManageWaveStep {...{ ...defaultProps, ...props }} />;
};

export const Default: Story = {
  render: () => <StoryWrapper />,
};

export const Loading: Story = {
  render: () => <StoryWrapper isLoading={true} />,
};

export const ReadOnly: Story = {
  render: () => <StoryWrapper readOnly={true} />,
};

export const ErrorOnConfirm: Story = {
  render: () => (
    <StoryWrapper
      onConfirm={() =>
        new Promise((_, reject) =>
          setTimeout(() => reject(new ErrorWithType("There are some validation error", "warning")), 1000)
        )
      }
    />
  ),
};
